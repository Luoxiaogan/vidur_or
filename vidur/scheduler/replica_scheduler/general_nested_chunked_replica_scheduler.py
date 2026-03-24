"""
WAIT-CP: Nested Booking Limit + Per-Request Chunked Prefill

支持 single-type 和 multi-type workload:
  - Single type: tl 控制全局 in-system, segment 退化为 1 段
  - Multi type: segment-wise booking limit, 不同 type 在不同 segment 退出

可调参数:
    tl (total_limit): 全局 booking limit
    cs (chunk_size): per-request prefill chunk size
    gate (WAIT_CP_GATE env): ON=限制 batch 总 tokens, OFF=不限制

调度结构:
    1. Decode: 按 segment per_stage_limit 处理 (各 1 token)
    2. Running prefill: 各 min(remaining, cs) tokens, 受 gate 限制
    3. New admit: 受 segment 0 的 remain + gate 限制
"""

from math import ceil
from typing import List, Dict, Tuple
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.general_nested_booking_limit_replica_scheduler import (
    GeneralizedNestedBookingLimitReplicaScheduler,
)


class GeneralNestedChunkedReplicaScheduler(GeneralizedNestedBookingLimitReplicaScheduler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._per_req_budget = self._config.chunk_size
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )

        # Workload params — 加权计算 multi-type
        pts = self._config.prompt_types if self._config.prompt_types else [{"prefill": 512, "decode": 20, "arrival_rate": 1}]
        total_rate = sum(pt.get("arrival_rate", 1) for pt in pts)
        self._multi_type = len(pts) > 1

        # 加权 pipeline depth 和 K
        weighted_pipeline = 0
        weighted_K = 0
        for pt in pts:
            l0_i = pt.get("prefill", 512)
            l1_i = pt.get("decode", 20)
            rate_i = pt.get("arrival_rate", 1)
            K_i = max(1, ceil(l0_i / self._per_req_budget))
            w = rate_i / total_rate
            weighted_pipeline += w * (K_i + l1_i)
            weighted_K += w * K_i

        # 单 type 时退化为精确值
        pt0 = pts[0]
        self._l0 = pt0.get("prefill", 512)
        self._l1 = pt0.get("decode", 20)
        self._K = max(1, ceil(self._l0 / self._per_req_budget))

        self._pipeline_depth_weighted = weighted_pipeline
        self._pipeline_depth = self._K + self._l1  # 保留单 type 的
        self._P = self.total_limit / self._pipeline_depth_weighted

        # batch_est: 实际 batch 组成
        # decode tokens = (tl - prefill_in_progress) × 1
        # prefill tokens = prefill_in_progress × cs
        # prefill_in_progress = P × K_weighted
        prefill_in_progress = self._P * weighted_K
        decode_count = self.total_limit - prefill_in_progress
        self._batch_est = int(ceil(decode_count + prefill_in_progress * self._per_req_budget))

        # Gate
        import os
        self._gate = os.environ.get("WAIT_CP_GATE", "on") == "on"
        self._total_budget = self._batch_est if self._gate else float('inf')

        # 运行时统计
        self._batch_count = 0
        self._total_decode_in_batches = 0

        print(f"WAIT-CP: per_req={self._per_req_budget}, "
              f"tl={self.total_limit}, P={self._P:.2f}, "
              f"batch_est={self._batch_est}, gate={'ON' if self._gate else 'OFF'}, "
              f"multi_type={self._multi_type}, n_segments={len(self.segments)}, "
              f"pipeline_w={self._pipeline_depth_weighted:.1f}")

    # ------------------------------------------------------------------ #
    #  Memory
    # ------------------------------------------------------------------ #

    def _can_allocate_request(self, request: Request) -> bool:
        if request.id not in self._allocation_map:
            num_required_blocks = ceil(
                request.num_prefill_tokens / self._config.block_size
            )
            return (
                self._config.num_blocks
                - self._num_allocated_blocks
                - num_required_blocks
                >= self._watermark_blocks
            )
        return self._config.num_blocks - self._num_allocated_blocks >= 1

    # ------------------------------------------------------------------ #
    #  Adaptive (placeholder)
    # ------------------------------------------------------------------ #

    def add_request(self, request: Request) -> None:
        super().add_request(request)

    # ------------------------------------------------------------------ #
    #  Batch construction: segment-wise decode + per-request prefill
    # ------------------------------------------------------------------ #

    def _get_next_batch(self) -> Batch:
        """
        Nested WAIT-CP batch 构建:
          1. preempted → queue (父类风格，用于 segment 分组)
          2. 按 stage 分组
          3. Decode (stage 1+): 按 segment per_stage_limit 处理
          4. Prefill (stage 0): per-request chunk, 受 gate + segment 0 limit 限制
        """
        # ---- Step 1: preempted → queue ----
        for req in self._preempted_requests:
            if req not in self._request_queue:
                self._request_queue.append(req)
        self._preempted_requests.clear()

        # ---- Step 2: 按 stage 分组 ----
        grouped: Dict[int, List[Request]] = {}
        for req in self._request_queue:
            stage = getattr(req, 'current_stage', 0)
            # 已完成 prefill 但还在 stage 0 的，推进到 stage 1
            if stage == 0 and req.is_prefill_complete:
                req.advance_stage()
                stage = req.current_stage
            grouped.setdefault(stage, []).append(req)

        selected: List[Request] = []
        tokens: List[int] = []
        batch_tokens = 0
        decode_count = 0

        # ---- Step 3: Decode (stage 1+) — entry gate + free internal flow + WAIT ----
        for seg in self.segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            num_stages = seg_end - seg_start + 1
            budget = seg["seg_total_limit"]

            # Rotation: 严格按 seg_tl 分配
            base_nk = budget // num_stages
            remainder_nk = budget % num_stages
            batch_idx = self._batch_count % num_stages
            this_limit = base_nk + 1 if batch_idx < remainder_nk else base_nk

            # WAIT: 两条件满足其一才放该 segment 进 batch
            entry_count = len(grouped.get(seg_start, []))
            occupied_internal = sum(1 for req in self._request_queue
                if getattr(req, 'current_stage', 0) > seg_start
                and getattr(req, 'current_stage', 0) <= seg_end)
            total_in_seg = entry_count + occupied_internal
            # WAIT: 两条件满足其一才放该 segment 进 batch (各 seg 独立判断)
            if self._config.wait_gate:
                seg_full = total_in_seg >= budget
                entry_ready = entry_count >= this_limit
                if not seg_full and not entry_ready:
                    continue  # WAIT — 该 seg 冻结，但不影响其他 seg

            # 3a. Entry stage (segment 边界, seg_start >= 1): admit this_limit, 受 seg_tl 约束
            if seg_start >= 1:
                remain = max(0, budget - occupied_internal)
                entry_limit = min(this_limit, remain)
                entry_group = grouped.get(seg_start, [])
                count = 0
                while entry_group and count < entry_limit:
                    req = entry_group.pop(0)
                    if req in self._request_queue:
                        self._request_queue.remove(req)
                    self._allocate_request(req)
                    req.advance_stage()
                    selected.append(req)
                    tokens.append(1)
                    batch_tokens += 1
                    decode_count += 1
                    count += 1

            # 3b. Internal stages: ALWAYS free flow，不受 WAIT 影响
            for stage in range(max(seg_start + 1, 1), seg_end + 1):
                group = grouped.get(stage, [])
                for req in list(group):
                    if req in self._request_queue:
                        self._request_queue.remove(req)
                    self._allocate_request(req)
                    req.advance_stage()
                    selected.append(req)
                    tokens.append(1)
                    batch_tokens += 1
                    decode_count += 1

        # ---- Step 4: Prefill (stage 0) per-request chunk ----
        stage0 = grouped.get(0, [])

        # 分为: running prefill (已分配内存) 和 new prefill (未分配)
        running_prefill = [r for r in stage0 if r.id in self._allocation_map]
        new_prefill = [r for r in stage0 if r.id not in self._allocation_map]

        # 4a. Running prefill: 各 per_req_budget, 受 gate 限制
        for req in running_prefill:
            remaining = req.num_prefill_tokens - req.num_processed_tokens
            budget_left = self._total_budget - batch_tokens if self._gate else remaining
            give = min(remaining, self._per_req_budget, max(0, int(budget_left)))
            if give > 0:
                selected.append(req)
                tokens.append(give)
                batch_tokens += give
                if req in self._request_queue:
                    self._request_queue.remove(req)
            # give=0 的留在 queue，下次处理

        # 4b. New prefill: 严格按 rotation 分配 + seg_tl + global_tl 约束
        seg0 = self.segments[0]
        seg0_budget = seg0["seg_total_limit"]
        seg0_stages = seg0["end"] - seg0["start"] + 1
        base_nk0 = seg0_budget // seg0_stages
        remainder_nk0 = seg0_budget % seg0_stages
        batch_idx0 = self._batch_count % seg0_stages
        prefill_limit = base_nk0 + 1 if batch_idx0 < remainder_nk0 else base_nk0

        occupied0 = sum(1 for req in self._request_queue
                        if getattr(req, 'current_stage', 0) > seg0["start"]
                        and getattr(req, 'current_stage', 0) <= seg0["end"])
        remain_seg0 = max(0, seg0_budget - occupied0)

        in_system = len(self._allocation_map)
        remain_global = max(0, self.total_limit - in_system)
        remain = min(prefill_limit, remain_seg0, remain_global)

        admitted = 0
        for req in new_prefill:
            if admitted >= remain:
                break
            if self._gate and batch_tokens >= self._total_budget:
                break
            if not self._can_allocate_request(req):
                break
            remaining = req.num_prefill_tokens - req.num_processed_tokens
            budget_left = self._total_budget - batch_tokens if self._gate else remaining
            give = min(remaining, self._per_req_budget, max(0, int(budget_left)))
            if give <= 0:
                break
            self._allocate_request(req)
            selected.append(req)
            tokens.append(give)
            batch_tokens += give
            admitted += 1
            if req in self._request_queue:
                self._request_queue.remove(req)

        # 诊断: 每 500 个 batch 打一次
        if self._batch_count % 500 == 0 and selected:
            prefill_tokens_total = sum(t for r, t in zip(selected, tokens) if t > 1)
            n_prefill = sum(1 for t in tokens if t > 1)
            n_decode = sum(1 for t in tokens if t == 1)
            print(f"  [B{self._batch_count}] decode={n_decode}({decode_count}dt) prefill={n_prefill}({prefill_tokens_total}pt) total={batch_tokens}t gate_budget={self._total_budget}")

        # 统计
        self._batch_count += 1
        self._total_decode_in_batches += decode_count

        # Force clear
        if not selected and self.all_requests_arrived:
            for req in self._request_queue:
                if req.id in self._allocation_map:
                    self.free(req.id)
            self._request_queue.clear()
            return None

        if selected:
            return Batch(self._replica_id, selected, tokens)
        return None
