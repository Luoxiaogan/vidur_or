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

        # Workload params (用第一个 type 计算派生量，multi-type 时是近似)
        pt = self._config.prompt_types[0] if self._config.prompt_types else {}
        self._l0 = pt.get("prefill", 512)
        self._l1 = pt.get("decode", 20)
        self._K = max(1, ceil(self._l0 / self._per_req_budget))
        self._pipeline_depth = self._K + self._l1
        self._P = self.total_limit / self._pipeline_depth
        self._batch_est = int(ceil(self._P * (self._l0 + self._l1)))

        # Gate
        import os
        self._gate = os.environ.get("WAIT_CP_GATE", "on") == "on"
        self._total_budget = self._batch_est if self._gate else float('inf')

        # 运行时统计
        self._batch_count = 0
        self._total_decode_in_batches = 0

        # 多 type 信息
        self._multi_type = len(self._config.prompt_types) > 1

        print(f"WAIT-CP: per_req={self._per_req_budget}, K={self._K}, "
              f"tl={self.total_limit}, P={self._P:.2f}, "
              f"batch_est={self._batch_est}, gate={'ON' if self._gate else 'OFF'}, "
              f"multi_type={self._multi_type}, n_segments={len(self.segments)}, "
              f"pipeline={self._pipeline_depth}, l0={self._l0}, l1={self._l1}")

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

        # ---- Step 3: Decode (stage 1+) 按 segment 处理 ----
        for seg in self.segments:
            seg_start = seg["start"]
            seg_end = seg["end"]

            # 只处理 stage ≥ 1 的 decode (stage 0 = prefill, 单独处理)
            for stage in range(max(1, seg_start), seg_end + 1):
                limit = self.nested_booking_limits.get(stage, 0)
                group = grouped.get(stage, [])
                count = 0
                while group and count < limit:
                    req = group.pop(0)
                    if req in self._request_queue:
                        self._request_queue.remove(req)
                    self._allocate_request(req)
                    req.advance_stage()
                    selected.append(req)
                    tokens.append(1)
                    batch_tokens += 1
                    decode_count += 1
                    count += 1

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

        # 4b. New prefill: 受 segment 0 remain + gate 限制
        # Segment 0 的 remain = seg_total_limit - occupied
        seg0 = self.segments[0]
        occupied0 = sum(1 for req in self._request_queue
                        if getattr(req, 'current_stage', 0) > seg0["start"]
                        and getattr(req, 'current_stage', 0) <= seg0["end"])
        remain_seg0 = max(0, seg0["seg_total_limit"] - occupied0)

        # 也受全局 tl 限制
        in_system = len(self._allocation_map)
        remain_global = max(0, self.total_limit - in_system)
        remain = min(remain_seg0, remain_global)

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
