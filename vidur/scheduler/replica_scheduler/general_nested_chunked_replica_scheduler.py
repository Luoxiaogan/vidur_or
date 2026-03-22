"""
WAIT-CP: Flow-Balanced Chunked Prefill + Booking Limit Scheduler

可调参数:
    tl (total_limit): booking limit, 控制 in-system 请求总数
    per_req_budget (chunk_size): 每个 prefill 请求每 batch 处理的 token 数

派生量 (自动计算):
    K = ceil(l₀ / per_req_budget)          # 每个 prefill 需要的 batch 数
    P = tl / (K + l₁)                      # per-stage throughput (每 batch 完成的 prefill 数)
    total_budget = P × (l₀ + l₁)           # batch 总 token 预算 (保证 flow balance)

流量平衡:
    每 batch: P 个 prefill 完成 → 进入 decode
    每 batch: P 个 decode 完成 → 离开系统
    每 batch: P 个新请求 admit → 进入 prefill
    → prefill outflow = decode inflow = P

调度结构:
    1. Decode: 全部处理 (各 1 token)
    2. Running prefill: 各 per_req_budget tokens, 受 total_budget 限制
    3. New admit: 各 per_req_budget tokens, 受 tl 和 total_budget 双重限制
"""

from math import ceil
from typing import List, Tuple
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.general_nested_booking_limit_replica_scheduler import (
    GeneralizedNestedBookingLimitReplicaScheduler,
)


class GeneralNestedChunkedReplicaScheduler(GeneralizedNestedBookingLimitReplicaScheduler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._per_req_budget = self._config.chunk_size  # per-request prefill budget
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )

        # Workload params
        pt = self._config.prompt_types[0] if self._config.prompt_types else {}
        self._l0 = pt.get("prefill", 512)
        self._l1 = pt.get("decode", 20)

        # Flow balance 派生量
        self._K = max(1, ceil(self._l0 / self._per_req_budget))
        self._pipeline_depth = self._K + self._l1
        self._P = self.total_limit / self._pipeline_depth
        self._batch_est = int(ceil(self._P * (self._l0 + self._l1)))

        # Gate: WAIT_CP_GATE=on → 用 total_budget 限制 batch; off → 不限制
        import os
        self._gate = os.environ.get("WAIT_CP_GATE", "on") == "on"
        self._total_budget = self._batch_est if self._gate else float('inf')

        # 运行时统计
        self._batch_count = 0
        self._total_decode_in_batches = 0

        print(f"WAIT-CP: per_req={self._per_req_budget}, K={self._K}, "
              f"tl={self.total_limit}, P={self._P:.2f}, "
              f"batch_est={self._batch_est}, gate={'ON' if self._gate else 'OFF'}, "
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
    #  Batch construction: flow-balanced
    # ------------------------------------------------------------------ #

    def _get_next_batch(self) -> Batch:
        """
        Flow-balanced batch 构建:
          1. Decode: 全部处理 (各 1 token), 计入 batch 预算
          2. Running prefill: 各 per_req_budget, 受 total_budget 限制
          3. New admit: 各 per_req_budget, 受 tl + total_budget 限制
        """
        selected: List[Request] = []
        tokens: List[int] = []
        batch_tokens = 0

        # ---- Step 1: Decode ----
        decode_count = 0
        remaining_preempted: List[Request] = []

        for req in self._preempted_requests:
            if req.is_prefill_complete:
                self._allocate_request(req)
                req.advance_stage()
                selected.append(req)
                tokens.append(1)
                batch_tokens += 1
                decode_count += 1
            else:
                remaining_preempted.append(req)
        self._preempted_requests = remaining_preempted

        # Queue 中已完成 prefill 的 decode
        new_queue: List[Request] = []
        for req in self._request_queue:
            stage = getattr(req, 'current_stage', 0)
            if stage == 0 and req.is_prefill_complete:
                req.advance_stage()
                stage = req.current_stage
            if stage > 0:
                self._allocate_request(req)
                req.advance_stage()
                selected.append(req)
                tokens.append(1)
                batch_tokens += 1
                decode_count += 1
            else:
                new_queue.append(req)
        self._request_queue = new_queue

        # ---- Step 2: Running prefill (各 per_req_budget, 受 total_budget 限) ----
        still_preempted = []
        for req in self._preempted_requests:
            if not req.is_prefill_complete:
                remaining = req.num_prefill_tokens - req.num_processed_tokens
                give = min(remaining, self._per_req_budget,
                           self._total_budget - batch_tokens)
                if give > 0:
                    selected.append(req)
                    tokens.append(give)
                    batch_tokens += give
                else:
                    still_preempted.append(req)
            else:
                still_preempted.append(req)
        self._preempted_requests = still_preempted

        # ---- Step 3: New admit (受 tl + total_budget 双重限制) ----
        in_system = len(self._allocation_map)
        remain = max(0, self.total_limit - in_system)
        admitted = 0

        while self._request_queue and admitted < remain:
            if batch_tokens >= self._total_budget:
                break
            req = self._request_queue[0]
            if getattr(req, 'current_stage', 0) != 0:
                break
            if not self._can_allocate_request(req):
                break
            remaining = req.num_prefill_tokens - req.num_processed_tokens
            give = min(remaining, self._per_req_budget,
                       self._total_budget - batch_tokens)
            if give <= 0:
                break
            self._request_queue.pop(0)
            self._allocate_request(req)
            selected.append(req)
            tokens.append(give)
            batch_tokens += give
            admitted += 1

        # 统计
        self._batch_count += 1
        self._total_decode_in_batches += decode_count

        # Force clear
        if not selected and self.all_requests_arrived:
            for req in self._request_queue:
                if req.id in self._allocation_map:
                    self.free(req.id)
            self._request_queue.clear()
            for req in self._preempted_requests:
                if req.id in self._allocation_map:
                    self.free(req.id)
            self._preempted_requests.clear()
            return None

        if selected:
            return Batch(self._replica_id, selected, tokens)
        return None
