from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from math import ceil
from typing import Any, Dict, List, Optional, Sequence, Tuple


ENV_ENABLED = "SGLANG_WCP_NATIVE_ENABLE"
ENV_CONFIG_JSON = "SGLANG_WCP_NATIVE_CONFIG_JSON"


@dataclass(frozen=True)
class WCPPromptType:
    name: str
    prefill: int
    decode: int
    arrival_rate: float


@dataclass(frozen=True)
class WCPSegment:
    index: int
    start: int
    end: int
    target_share: float
    seg_total_limit: int
    n_k: float


@dataclass
class WCPSchedulerConfig:
    total_limit: int = 21
    chunk_size: int = 256
    prompt_types: List[WCPPromptType] = field(
        default_factory=lambda: [
            WCPPromptType(
                name="default",
                prefill=512,
                decode=20,
                arrival_rate=1.0,
            )
        ]
    )
    wait_gate: bool = False
    seg_margin: float = 0.0
    segment_mode: str = "derived"
    segment_size: Optional[int] = None
    enable_mix_balance: bool = True
    enable_segment_bias: bool = True
    enable_underload_bypass: bool = True
    underload_bypass_threshold: Optional[int] = None
    prefill_budget_tokens: Optional[int] = None

    def __post_init__(self) -> None:
        if self.total_limit <= 0:
            raise ValueError("total_limit must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if not self.prompt_types:
            raise ValueError("prompt_types must not be empty")
        if self.segment_mode not in {"derived", "uniform"}:
            raise ValueError("segment_mode must be one of: derived, uniform")
        if self.segment_size is not None and self.segment_size <= 0:
            raise ValueError("segment_size must be positive when provided")

    @property
    def total_arrival_rate(self) -> float:
        return sum(max(pt.arrival_rate, 0.0) for pt in self.prompt_types)

    @property
    def weighted_pipeline_depth(self) -> float:
        total_rate = self.total_arrival_rate or 1.0
        weighted = 0.0
        for pt in self.prompt_types:
            weight = pt.arrival_rate / total_rate
            weighted += weight * (ceil(pt.prefill / self.chunk_size) + pt.decode)
        return weighted

    @property
    def derived_prefill_budget_tokens(self) -> int:
        if self.prefill_budget_tokens is not None:
            return self.prefill_budget_tokens

        total_rate = self.total_arrival_rate or 1.0
        weighted_k = 0.0
        for pt in self.prompt_types:
            weight = pt.arrival_rate / total_rate
            weighted_k += weight * ceil(pt.prefill / self.chunk_size)

        throughput = self.total_limit / max(self.weighted_pipeline_depth, 1.0)
        running_prefill = throughput * weighted_k
        return max(self.chunk_size, int(ceil(running_prefill * self.chunk_size)))

    @property
    def effective_underload_bypass_threshold(self) -> int:
        if self.underload_bypass_threshold is not None:
            return max(1, self.underload_bypass_threshold)
        return min(8, max(2, self.total_limit // 2))

    @property
    def segments(self) -> List[WCPSegment]:
        if self.segment_mode == "uniform":
            return self._uniform_segments()
        return self._derived_segments()

    def _derived_segments(self) -> List[WCPSegment]:
        unique_decodes = sorted({pt.decode for pt in self.prompt_types})

        segment_specs: List[Tuple[int, float]] = []
        prev = 0
        for decode in unique_decodes:
            count = decode - prev
            arrival_sum = sum(
                pt.arrival_rate for pt in self.prompt_types if pt.decode > prev
            )
            segment_specs.append((count, arrival_sum))
            prev = decode

        total_rate = self.total_arrival_rate or 1.0
        ratios: List[float] = []
        for idx in range(len(segment_specs) - 1):
            cur_arrival = segment_specs[idx][1]
            next_arrival = segment_specs[idx + 1][1]
            p_k = (next_arrival / cur_arrival) if cur_arrival > 0 else 0.0
            q_k = max(0.01, min(p_k + self.seg_margin, 0.99))
            ratios.append(q_k)

        cumulative_ratio = [1.0]
        for q_k in ratios:
            cumulative_ratio.append(cumulative_ratio[-1] * q_k)

        denominator = sum(
            segment_specs[idx][0] * cumulative_ratio[idx]
            for idx in range(len(segment_specs))
        )
        if denominator <= 0:
            denominator = 1.0
        n_1 = self.total_limit / denominator

        segments: List[WCPSegment] = []
        start = 1
        for idx, (count, arrival_sum) in enumerate(segment_specs):
            n_k = n_1 * cumulative_ratio[idx]
            seg_total_limit = max(1, int(round(n_k * count)))
            segments.append(
                WCPSegment(
                    index=idx,
                    start=start,
                    end=start + count - 1,
                    target_share=(arrival_sum / total_rate) if total_rate > 0 else 0.0,
                    seg_total_limit=seg_total_limit,
                    n_k=n_k,
                )
            )
            start += count
        return segments

    def _uniform_segments(self) -> List[WCPSegment]:
        max_decode = max(1, max(pt.decode for pt in self.prompt_types))
        segment_size = min(max_decode, self.segment_size or max_decode)
        total_rate = self.total_arrival_rate or 1.0
        n_k = self.total_limit / max_decode

        segments: List[WCPSegment] = []
        start = 1
        prev = 0
        idx = 0
        while prev < max_decode:
            count = min(segment_size, max_decode - prev)
            arrival_sum = sum(
                pt.arrival_rate for pt in self.prompt_types if pt.decode > prev
            )
            seg_total_limit = max(1, int(round(n_k * count)))
            segments.append(
                WCPSegment(
                    index=idx,
                    start=start,
                    end=start + count - 1,
                    target_share=(arrival_sum / total_rate) if total_rate > 0 else 0.0,
                    seg_total_limit=seg_total_limit,
                    n_k=n_k,
                )
            )
            prev += count
            start += count
            idx += 1
        return segments


_CACHED_CONFIG: Optional[WCPSchedulerConfig] = None


def configure_env(config: WCPSchedulerConfig) -> None:
    payload = asdict(config)
    payload["prompt_types"] = [asdict(pt) for pt in config.prompt_types]
    os.environ[ENV_ENABLED] = "1"
    os.environ[ENV_CONFIG_JSON] = json.dumps(payload, separators=(",", ":"))


def clear_env() -> None:
    os.environ.pop(ENV_ENABLED, None)
    os.environ.pop(ENV_CONFIG_JSON, None)


def is_enabled() -> bool:
    return os.environ.get(ENV_ENABLED, "0") == "1"


def load_config_from_env() -> Optional[WCPSchedulerConfig]:
    global _CACHED_CONFIG
    if not is_enabled():
        _CACHED_CONFIG = None
        return None
    if _CACHED_CONFIG is not None:
        return _CACHED_CONFIG

    raw = os.environ.get(ENV_CONFIG_JSON)
    if not raw:
        return None
    payload = json.loads(raw)
    payload["prompt_types"] = [WCPPromptType(**pt) for pt in payload["prompt_types"]]
    _CACHED_CONFIG = WCPSchedulerConfig(**payload)
    return _CACHED_CONFIG


def req_prefill_len(req: Any) -> int:
    return len(getattr(req, "origin_input_ids", []) or [])


def req_decode_cap(req: Any) -> int:
    sampling_params = getattr(req, "sampling_params", None)
    if sampling_params is None:
        return 0
    return int(getattr(sampling_params, "max_new_tokens", 0) or 0)


def req_rid(req: Any) -> Any:
    return getattr(req, "rid", id(req))


def match_prompt_type(req: Any, config: WCPSchedulerConfig) -> WCPPromptType:
    custom_params = getattr(getattr(req, "sampling_params", None), "custom_params", None)
    if isinstance(custom_params, dict):
        wcp_name = custom_params.get("wcp_prompt_type")
        if wcp_name:
            for pt in config.prompt_types:
                if pt.name == wcp_name:
                    return pt

    req_prefill = req_prefill_len(req)
    req_decode = req_decode_cap(req)
    best = None
    best_score = None
    for pt in config.prompt_types:
        score = abs(pt.prefill - req_prefill) + abs(pt.decode - req_decode)
        if best is None or score < best_score:
            best = pt
            best_score = score
    return best or config.prompt_types[0]


def decode_progress(req: Any) -> int:
    return len(getattr(req, "output_ids", []) or [])


def segment_for_stage(
    stage: int, config: WCPSchedulerConfig
) -> Optional[WCPSegment]:
    if stage <= 0:
        return None
    for seg in config.segments:
        if stage <= seg.end:
            return seg
    return config.segments[-1] if config.segments else None


def segment_for_decode_progress(
    decode_progress_value: int,
    decode_cap: int,
    config: WCPSchedulerConfig,
) -> Optional[WCPSegment]:
    if decode_cap <= 0:
        return None
    stage = max(1, decode_progress_value)
    if stage > decode_cap:
        stage = decode_cap
    return segment_for_stage(stage, config)


def count_running_types(
    running_reqs: Sequence[Any], config: WCPSchedulerConfig
) -> Dict[str, int]:
    counts = {pt.name: 0 for pt in config.prompt_types}
    for req in running_reqs:
        pt = match_prompt_type(req, config)
        counts[pt.name] = counts.get(pt.name, 0) + 1
    return counts


def mix_sort_key(
    req: Any,
    running_counts: Dict[str, int],
    current_admits: Dict[str, int],
    config: WCPSchedulerConfig,
) -> Tuple[float, float, float, str]:
    pt = match_prompt_type(req, config)
    total_target = config.total_arrival_rate or 1.0
    target_share = pt.arrival_rate / total_target
    target_count = target_share * max(config.total_limit, 1)
    current_count = running_counts.get(pt.name, 0) + current_admits.get(pt.name, 0)
    deficit = current_count - target_count

    decode_cap_value = req_decode_cap(req)
    seg = segment_for_decode_progress(0, decode_cap_value, config)
    seg_bias = seg.index if (seg is not None and config.enable_segment_bias) else 0
    return (deficit, seg_bias, decode_cap_value, pt.name)


def reorder_waiting_queue(
    waiting_queue: List[Any], running_reqs: Sequence[Any], config: WCPSchedulerConfig
) -> None:
    if not config.enable_mix_balance or len(waiting_queue) <= 1:
        return

    running_counts = count_running_types(running_reqs, config)
    current_admits = {pt.name: 0 for pt in config.prompt_types}
    pool = list(waiting_queue)
    result: List[Any] = []
    while pool:
        best_idx = min(
            range(len(pool)),
            key=lambda idx: mix_sort_key(
                pool[idx],
                running_counts,
                current_admits,
                config,
            ),
        )
        req = pool.pop(best_idx)
        pt = match_prompt_type(req, config)
        current_admits[pt.name] = current_admits.get(pt.name, 0) + 1
        result.append(req)
    waiting_queue[:] = result


def segment_entry_limit(seg: WCPSegment, round_idx: int) -> int:
    num_stages = max(1, seg.end - seg.start + 1)
    # Do not rotate the remainder across rounds. For small uniform segments this
    # makes most rounds admit zero entry-stage requests, which inflates TTFT by
    # starving newly admitted requests before their first decode token.
    return max(1, int(ceil(seg.seg_total_limit / num_stages)))


def segment_runtime_state(
    running_reqs: Sequence[Any], config: WCPSchedulerConfig
) -> Dict[int, Dict[str, int]]:
    state = {
        seg.index: {"entry": 0, "internal": 0, "total": 0}
        for seg in config.segments
    }
    for req in running_reqs:
        decode_cap_value = req_decode_cap(req)
        if decode_cap_value <= 0:
            continue
        next_stage = min(decode_cap_value, decode_progress(req) + 1)
        seg = segment_for_stage(next_stage, config)
        if seg is None:
            continue
        bucket = state[seg.index]
        bucket["total"] += 1
        if next_stage <= seg.start:
            bucket["entry"] += 1
        else:
            bucket["internal"] += 1
    return state


def underload_bypass_active(
    waiting_queue_len: int,
    running_reqs: Sequence[Any],
    config: WCPSchedulerConfig,
) -> bool:
    if not config.enable_underload_bypass:
        return False
    return (waiting_queue_len + len(running_reqs)) <= config.effective_underload_bypass_threshold


def next_decode_stage(req: Any, config: WCPSchedulerConfig) -> Tuple[int, Optional[WCPSegment]]:
    decode_cap_value = req_decode_cap(req)
    if decode_cap_value <= 0:
        return 0, None
    stage = min(decode_cap_value, decode_progress(req) + 1)
    return stage, segment_for_stage(stage, config)


def compute_wait_gate_admit_rids(
    waiting_queue: Sequence[Any],
    running_reqs: Sequence[Any],
    config: WCPSchedulerConfig,
    round_idx: int,
) -> Optional[set[Any]]:
    if underload_bypass_active(len(waiting_queue), running_reqs, config):
        return None
    if not config.wait_gate or not waiting_queue or not config.segments:
        return None
    first_seg = config.segments[0]
    entry_limit = segment_entry_limit(first_seg, round_idx)
    seg_state = segment_runtime_state(running_reqs, config).get(
        first_seg.index,
        {"entry": 0, "internal": 0, "total": 0},
    )
    seg_full = seg_state["total"] >= first_seg.seg_total_limit
    entry_ready = len(waiting_queue) >= entry_limit
    if seg_full or entry_ready:
        return {req_rid(req) for req in waiting_queue}
    return set()


def compute_decode_gate_keep_rids(
    running_reqs: Sequence[Any],
    config: WCPSchedulerConfig,
    round_idx: int,
    waiting_queue_len: int = 0,
) -> Optional[set[Any]]:
    if underload_bypass_active(waiting_queue_len, running_reqs, config):
        return None
    if not running_reqs or not config.segments:
        return None

    seg_state = segment_runtime_state(running_reqs, config)
    grouped: Dict[int, Dict[str, Any]] = {
        seg.index: {"entry": [], "internal_by_stage": {}}
        for seg in config.segments
    }
    keep: set[Any] = set()

    for req in running_reqs:
        next_stage, seg = next_decode_stage(req, config)
        if seg is None:
            keep.add(req_rid(req))
            continue
        bucket = grouped[seg.index]
        if next_stage <= seg.start:
            bucket["entry"].append(req)
        else:
            bucket["internal_by_stage"].setdefault(next_stage, []).append(req)

    for seg in config.segments:
        bucket = grouped[seg.index]
        entry_reqs = bucket["entry"]
        internal_by_stage = bucket["internal_by_stage"]
        if not entry_reqs and not internal_by_stage:
            continue

        entry_limit = segment_entry_limit(seg, round_idx)
        allow_entry = True
        if config.wait_gate:
            state = seg_state.get(seg.index, {"total": 0})
            seg_full = state["total"] >= seg.seg_total_limit
            # WAIT should gate newly entering requests, not freeze requests that
            # are already progressing inside the segment. The earlier version
            # skipped the whole segment when there were too few entry-stage
            # requests, which aggressively retracted internal decode work and
            # caused large regressions at moderate arrival rates.
            entry_supply = len(entry_reqs)
            if seg.index == 0:
                # For the first decode segment, queued prefills are the upstream
                # source of future stage-1 decode work.
                entry_supply += waiting_queue_len
            entry_ready = entry_supply >= entry_limit
            allow_entry = seg_full or entry_ready

        seg_budget = max(1, seg.seg_total_limit)
        taken = 0

        if allow_entry:
            for req in entry_reqs[: min(entry_limit, seg_budget)]:
                keep.add(req_rid(req))
                taken += 1

        for stage in range(seg.start + 1, seg.end + 1):
            if taken >= seg_budget:
                break
            for req in internal_by_stage.get(stage, []):
                if taken >= seg_budget:
                    break
                keep.add(req_rid(req))
                taken += 1

    if not keep:
        # Liveness fallback: never freeze the whole decode side.
        keep.add(req_rid(running_reqs[0]))
    return keep


def prefill_request_budget(config: WCPSchedulerConfig, chunk_cap: Optional[int] = None) -> int:
    effective_chunk = chunk_cap or config.chunk_size
    effective_chunk = max(1, effective_chunk)
    return max(1, int(ceil(config.derived_prefill_budget_tokens / effective_chunk)))


def compute_new_prefill_admit_quota(
    waiting_queue: Sequence[Any],
    running_reqs: Sequence[Any],
    config: WCPSchedulerConfig,
    round_idx: int,
    already_scheduled_prefills: int = 0,
) -> Optional[int]:
    if underload_bypass_active(len(waiting_queue), running_reqs, config):
        return None
    if not config.segments:
        return None
    first_seg = config.segments[0]
    entry_limit = segment_entry_limit(first_seg, round_idx)
    seg_state = segment_runtime_state(running_reqs, config).get(
        first_seg.index,
        {"entry": 0, "internal": 0, "total": 0},
    )
    seg_capacity = max(0, first_seg.seg_total_limit - seg_state["total"] - already_scheduled_prefills)
    return max(0, min(entry_limit, seg_capacity))
