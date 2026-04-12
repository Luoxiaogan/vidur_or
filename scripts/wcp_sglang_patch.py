#!/usr/bin/env python3
"""
Minimal WCP patch layer for SGLang.

This module does not edit the SGLang source tree in-place. Instead, it
monkey-patches a few scheduling hooks at runtime:

1. Replace `PrefillAdder` with a WCP-aware subclass.
2. Post-process `SchedulePolicy.calc_priority` to enforce WCP type-mix order.

The goal is to stay close to the Vidur WAIT-CP mechanism while preserving the
existing SGLang scheduler infrastructure.

Important limitation:
SGLang's upstream scheduler currently tracks a single `chunked_req` across
rounds. Therefore this patch approximates Vidur's "multiple running prefills"
semantics, but cannot perfectly match it without deeper source changes.
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class WCPPromptType:
    """Prompt-type description used for mix-balancing and segment derivation."""

    name: str
    prefill: int
    decode: int
    arrival_rate: float


@dataclass(frozen=True)
class WCPSegment:
    """Decode segment budget, aligned with Vidur's nested scheduler semantics."""

    index: int
    start: int
    end: int
    target_share: float
    seg_total_limit: int
    n_k: float


@dataclass
class WCPSGLangConfig:
    """
    Runtime config for the SGLang WCP patch.

    The two core controls match Vidur:
    - `total_limit` (tl): in-system admission ceiling
    - `chunk_size`  (cs): per-request prefill cap for each round

    `prefill_budget_tokens` plays the role of a global gate in SGLang's
    existing PrefillAdder path.
    """

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
    enable_mix_balance: bool = True
    enable_segment_bias: bool = True
    enable_underload_bypass: bool = True
    underload_bypass_threshold: Optional[int] = None
    prefill_budget_tokens: Optional[int] = None
    source_root: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.prompt_types:
            raise ValueError("prompt_types must not be empty")
        if self.total_limit <= 0:
            raise ValueError("total_limit must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

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
        unique_decodes = sorted({pt.decode for pt in self.prompt_types})
        total_rate = self.total_arrival_rate or 1.0

        segment_specs: List[Tuple[int, float]] = []
        prev = 0
        for decode in unique_decodes:
            count = decode - prev
            arrival_sum = sum(
                pt.arrival_rate for pt in self.prompt_types if pt.decode > prev
            )
            segment_specs.append((count, arrival_sum / total_rate))
            prev = decode

        weighted_denominator = sum(count * share for count, share in segment_specs)
        if weighted_denominator <= 0:
            weighted_denominator = 1.0

        segments: List[WCPSegment] = []
        start = 1
        for idx, (count, share) in enumerate(segment_specs):
            seg_total_limit = max(
                1, int(round(self.total_limit * (count * share) / weighted_denominator))
            )
            n_k = seg_total_limit / max(count, 1)
            segments.append(
                WCPSegment(
                    index=idx,
                    start=start,
                    end=start + count - 1,
                    target_share=share,
                    seg_total_limit=seg_total_limit,
                    n_k=n_k,
                )
            )
            start += count
        return segments


def _ensure_source_root(source_root: Optional[str]) -> str:
    root = source_root or os.environ.get("SGLANG_SOURCE_ROOT")
    if not root:
        root = "/home/archer/sglang-batch-metrics/python"
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"SGLang source root not found: {root_path}")
    if str(root_path) not in sys.path:
        sys.path.insert(0, str(root_path))
    return str(root_path)


class _PatchState:
    config: Optional[WCPSGLangConfig] = None
    installed: bool = False
    original_prefill_adder: Any = None
    original_calc_priority: Any = None


PATCH_STATE = _PatchState()


def _req_prefill_len(req: Any) -> int:
    return len(getattr(req, "origin_input_ids", []) or [])


def _req_decode_cap(req: Any) -> int:
    sampling_params = getattr(req, "sampling_params", None)
    if sampling_params is None:
        return 0
    return int(getattr(sampling_params, "max_new_tokens", 0) or 0)


def _match_prompt_type(req: Any, config: WCPSGLangConfig) -> WCPPromptType:
    custom_params = getattr(getattr(req, "sampling_params", None), "custom_params", None)
    if isinstance(custom_params, dict):
        wcp_name = custom_params.get("wcp_prompt_type")
        if wcp_name:
            for pt in config.prompt_types:
                if pt.name == wcp_name:
                    return pt

    req_prefill = _req_prefill_len(req)
    req_decode = _req_decode_cap(req)
    best = None
    best_score = None
    for pt in config.prompt_types:
        score = abs(pt.prefill - req_prefill) + abs(pt.decode - req_decode)
        if best is None or score < best_score:
            best = pt
            best_score = score
    return best or config.prompt_types[0]


def _decode_progress(req: Any) -> int:
    return len(getattr(req, "output_ids", []) or [])


def _segment_for_decode_progress(
    decode_progress: int, decode_cap: int, config: WCPSGLangConfig
) -> Optional[WCPSegment]:
    if decode_cap <= 0:
        return None
    stage = max(1, decode_progress)
    for seg in config.segments:
        if stage <= seg.end:
            return seg
    return config.segments[-1] if config.segments else None


def _count_running_types(running_batch: Any, config: WCPSGLangConfig) -> Dict[str, int]:
    counts = {pt.name: 0 for pt in config.prompt_types}
    if running_batch is None:
        return counts
    for req in getattr(running_batch, "reqs", []):
        pt = _match_prompt_type(req, config)
        counts[pt.name] = counts.get(pt.name, 0) + 1
    return counts


def _mix_sort_key(
    req: Any,
    running_counts: Dict[str, int],
    current_admits: Dict[str, int],
    config: WCPSGLangConfig,
) -> Tuple[float, float, float, str]:
    pt = _match_prompt_type(req, config)
    total_target = config.total_arrival_rate or 1.0
    target_share = pt.arrival_rate / total_target
    target_count = target_share * max(config.total_limit, 1)

    current_count = running_counts.get(pt.name, 0) + current_admits.get(pt.name, 0)
    deficit = current_count - target_count

    decode_cap = _req_decode_cap(req)
    seg = _segment_for_decode_progress(0, decode_cap, config)
    seg_bias = seg.index if (seg is not None and config.enable_segment_bias) else 0

    # smaller deficit first => underrepresented types are admitted first
    return (deficit, seg_bias, decode_cap, pt.name)


def _reorder_waiting_queue(waiting_queue: List[Any], running_batch: Any) -> None:
    config = PATCH_STATE.config
    if config is None or not config.enable_mix_balance or len(waiting_queue) <= 1:
        return

    running_counts = _count_running_types(running_batch, config)
    current_admits = {pt.name: 0 for pt in config.prompt_types}

    reordered: List[Any] = []
    for req in waiting_queue:
        reordered.append(req)

    # Greedy stable selection to preserve original policy as much as possible.
    result: List[Any] = []
    pool = list(reordered)
    while pool:
        best_idx = min(
            range(len(pool)),
            key=lambda idx: _mix_sort_key(
                pool[idx],
                running_counts,
                current_admits,
                config,
            ),
        )
        req = pool.pop(best_idx)
        pt = _match_prompt_type(req, config)
        current_admits[pt.name] = current_admits.get(pt.name, 0) + 1
        result.append(req)

    waiting_queue[:] = result


def _should_bypass_reorder(waiting_queue: Sequence[Any], running_batch: Any) -> bool:
    config = PATCH_STATE.config
    if config is None or not config.enable_underload_bypass:
        return False
    running = len(getattr(running_batch, "reqs", []) or []) if running_batch else 0
    return (len(waiting_queue) + running) <= config.effective_underload_bypass_threshold


def install_wcp_patch(config: WCPSGLangConfig) -> Dict[str, Any]:
    """
    Install the WCP monkey patch onto the SGLang runtime.

    Returns imported modules for convenience so the caller can continue to use
    SGLang symbols without importing them twice.
    """

    source_root = _ensure_source_root(config.source_root)

    try:
        scheduler_mod = importlib.import_module("sglang.srt.managers.scheduler")
        policy_mod = importlib.import_module("sglang.srt.managers.schedule_policy")
    except ModuleNotFoundError as exc:
        missing = exc.name or "<unknown>"
        raise RuntimeError(
            "Unable to import the SGLang runtime from the configured source root. "
            f"Missing Python dependency: {missing}. "
            "Run this patch inside the same Python environment that normally "
            "launches SGLang."
        ) from exc

    if PATCH_STATE.installed:
        PATCH_STATE.config = config
        return {
            "scheduler_mod": scheduler_mod,
            "policy_mod": policy_mod,
            "source_root": source_root,
        }

    PATCH_STATE.config = config
    PATCH_STATE.original_prefill_adder = policy_mod.PrefillAdder
    PATCH_STATE.original_calc_priority = policy_mod.SchedulePolicy.calc_priority

    base_prefill_adder = policy_mod.PrefillAdder
    add_req_result = policy_mod.AddReqResult

    class WCPPrefillAdder(base_prefill_adder):
        """SGLang PrefillAdder with a minimal WCP admission/chunking patch."""

        def _wcp_available_slots(self) -> int:
            cfg = PATCH_STATE.config
            if cfg is None:
                return 1 << 30
            return max(0, cfg.total_limit - len(self.running_batch.reqs))

        def _should_bypass_wcp(self, has_chunked_req: bool) -> bool:
            cfg = PATCH_STATE.config
            if cfg is None or not cfg.enable_underload_bypass:
                return False
            if has_chunked_req or self.new_chunked_req is not None:
                return False
            current_load = len(getattr(self.running_batch, "reqs", []) or []) + len(
                self.can_run_list
            )
            return current_load < cfg.effective_underload_bypass_threshold

        def _aligned_cap(self, raw_cap: int) -> int:
            if raw_cap <= 0:
                return 0
            if raw_cap < self.page_size:
                return raw_cap
            return max(self.page_size, (raw_cap // self.page_size) * self.page_size)

        def _apply_cap(self, req: Any, cap: int) -> Tuple[int, List[int]]:
            old_extend = req.extend_input_len
            old_fill_ids = list(req.fill_ids)
            if cap <= 0 or old_extend <= cap:
                return old_extend, old_fill_ids
            req.set_extend_input_len(cap)
            req.fill_ids = req.fill_ids[: len(req.prefix_indices) + cap]
            return old_extend, old_fill_ids

        def _restore_req(self, req: Any, old_extend: int, old_fill_ids: Sequence[int]) -> None:
            req.set_extend_input_len(old_extend)
            req.fill_ids = list(old_fill_ids)

        def add_chunked_req(self, req: Any):
            cfg = PATCH_STATE.config
            if cfg is None:
                return super().add_chunked_req(req)
            cap = self._aligned_cap(cfg.chunk_size)
            old_extend, old_fill_ids = self._apply_cap(req, cap)
            try:
                return super().add_chunked_req(req)
            finally:
                # keep the chunked state produced by super() when it accepted the req
                if req not in self.can_run_list:
                    self._restore_req(req, old_extend, old_fill_ids)

        def add_one_req(
            self,
            req: Any,
            has_chunked_req: bool,
            truncation_align_size: Optional[int],
        ):
            cfg = PATCH_STATE.config
            if cfg is None:
                return super().add_one_req(req, has_chunked_req, truncation_align_size)
            if self._should_bypass_wcp(has_chunked_req):
                return super().add_one_req(req, has_chunked_req, truncation_align_size)

            if len(self.can_run_list) >= self._wcp_available_slots():
                return add_req_result.OTHER

            cap = self._aligned_cap(cfg.chunk_size)
            old_extend, old_fill_ids = self._apply_cap(req, cap)
            result = super().add_one_req(req, has_chunked_req, truncation_align_size)
            if req not in self.can_run_list and self.new_chunked_req is not req:
                self._restore_req(req, old_extend, old_fill_ids)
            return result

    def patched_calc_priority(self, waiting_queue, running_batch=None):
        prefix_computed = PATCH_STATE.original_calc_priority(self, waiting_queue)
        if _should_bypass_reorder(waiting_queue, running_batch):
            return prefix_computed
        _reorder_waiting_queue(waiting_queue, running_batch)
        return prefix_computed

    policy_mod.PrefillAdder = WCPPrefillAdder
    scheduler_mod.PrefillAdder = WCPPrefillAdder
    policy_mod.SchedulePolicy.calc_priority = patched_calc_priority

    PATCH_STATE.installed = True
    return {
        "scheduler_mod": scheduler_mod,
        "policy_mod": policy_mod,
        "source_root": source_root,
    }


def recommended_server_args(config: WCPSGLangConfig) -> Dict[str, int]:
    """
    Recommend the two existing SGLang knobs that best complement the patch.

    - `chunked_prefill_size`: should act like the global prefill gate.
    - `prefill_max_requests`: keep it close to the tl ceiling for safety.
    """

    return {
        "chunked_prefill_size": config.derived_prefill_budget_tokens,
        "prefill_max_requests": config.total_limit,
    }


def default_single_type_config() -> WCPSGLangConfig:
    """A conservative single-type config aligned with the Vidur p512d20 setup."""

    return WCPSGLangConfig(
        total_limit=21,
        chunk_size=256,
        prompt_types=[
            WCPPromptType(
                name="p512d20",
                prefill=512,
                decode=20,
                arrival_rate=1.0,
            )
        ],
    )


if __name__ == "__main__":
    config = default_single_type_config()
    args = recommended_server_args(config)
    print("WCP SGLang patch module ready.")
    print(f"Suggested chunked_prefill_size={args['chunked_prefill_size']}")
    print(f"Suggested prefill_max_requests={args['prefill_max_requests']}")
