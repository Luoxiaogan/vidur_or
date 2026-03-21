"""
WAIT-CP: Per-Request Chunked Prefill + Booking Limit Scheduler

核心语义（区别于 Sarathi）:
    - chunk_size = 每个请求的 prefill chunk 大小（per-request 独立预算）
    - Sarathi: chunk_size = batch 总 token 预算 → 每 batch 只能 1 个 prefill
    - WAIT-CP: 每 batch 可并行处理 P 个 prefill，P 由 booking limit 控制

流量平衡:
    P = remain = total_limit - in_system   # 每 batch 可 admit 的新 prefill 数
    K = ceil(l₀ / chunk_size)              # 每个 prefill 需要的 chunk 数
    稳态 in-system = P × (K + l₁) = tl    # booking limit 直接控制

调度结构:
    1. Decode: 所有 in-system 的 decode 请求，各处理 1 token（segment cap 控制）
    2. Running prefill: 所有正在做 prefill 的请求，各处理 min(remaining, chunk_size) tokens
    3. New prefill: admit remain 个新请求，各处理 chunk_size tokens
    → batch 总 tokens = n_decode + n_running_prefill_tokens + n_new_prefill_tokens
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
        self._chunk_size = self._config.chunk_size  # per-request chunk 大小
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )

        # 从 prompt_types 获取参数
        pt = self._config.prompt_types[0] if self._config.prompt_types else {}
        self._l0 = pt.get("prefill", 630)
        self._l1 = pt.get("decode", 20)
        self._K = max(1, ceil(self._l0 / self._chunk_size))

        # Booking limit
        self._n_max = self.total_limit
        self._pipeline_depth = self._K + self._l1

        # Per-stage limit (流量平衡)
        self._per_stage = max(1, self.total_limit // self._pipeline_depth)

        # Segments (for decode cap)
        self._n_seg = min(2, self._l1)
        self._decode_segments = self._build_segments(self._l1, self._n_seg)
        self._seg_limit = max(1, self.total_limit // (self._n_seg + 1))

        # λ 估计
        self._ema_alpha = 0.05
        self._lambda_hat = 0.0
        self._last_arrival_time = None

        # 运行时统计
        self._batch_count = 0
        self._total_decode_in_batches = 0

        print(f"WAIT-CP: chunk={self._chunk_size}(per-req), K={self._K}, "
              f"tl={self.total_limit}, per_stage={self._per_stage}, "
              f"pipeline={self._pipeline_depth}, l0={self._l0}, l1={self._l1}")

    # ------------------------------------------------------------------ #
    #  Segment construction
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_segments(l1: int, n_seg: int) -> List[Tuple[int, int]]:
        n_seg = max(1, min(n_seg, l1))
        segs = []
        step = max(1, l1 // n_seg)
        for i in range(n_seg):
            start = 1 + i * step
            end = 1 + (i + 1) * step - 1 if i < n_seg - 1 else l1
            segs.append((start, end))
        return segs

    def _get_seg_index(self, stage: int) -> int:
        for i, (s, e) in enumerate(self._decode_segments):
            if s <= stage <= e:
                return i
        return len(self._decode_segments) - 1

    # ------------------------------------------------------------------ #
    #  Adaptive
    # ------------------------------------------------------------------ #

    def add_request(self, request: Request) -> None:
        t = request.arrived_at
        if self._last_arrival_time is not None and t > self._last_arrival_time:
            rate = 1.0 / (t - self._last_arrival_time)
            self._lambda_hat = (
                self._ema_alpha * rate + (1 - self._ema_alpha) * self._lambda_hat
                if self._lambda_hat > 0 else rate
            )
        self._last_arrival_time = t
        super().add_request(request)

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
    #  Per-request token calculation (核心改动!)
    # ------------------------------------------------------------------ #

    def _get_prefill_chunk(self, request: Request) -> int:
        """每个 prefill 请求独立获得 chunk_size tokens（不共享 batch 预算）"""
        if request.completed or request.is_prefill_complete:
            return 0
        remaining = request.num_prefill_tokens - request.num_processed_tokens
        return min(remaining, self._chunk_size)

    # ------------------------------------------------------------------ #
    #  Batch construction (重写: per-request chunk + flow balance)
    # ------------------------------------------------------------------ #

    def _get_next_batch(self) -> Batch:
        """
        WAIT-CP batch 构建（per-request chunk 语义）:

        1. Decode: 所有 in-system decode 请求，各 1 token（segment cap 控制）
        2. Running prefill (preempted): 各 min(remaining, chunk_size) tokens
        3. New prefill (queue): admit remain 个，各 chunk_size tokens
           remain = total_limit - in_system (booking limit 控制)

        batch 总 tokens 不固定，由 in-system 数量决定。
        booking limit 通过控制 in-system 间接控制 batch 大小 → 流量平衡。
        """
        selected: List[Request] = []
        tokens: List[int] = []

        # ---- Step 1: Decode (所有 in-system decode 请求) ----
        decode_count = 0
        remaining_preempted: List[Request] = []

        for req in self._preempted_requests:
            if req.is_prefill_complete:
                self._allocate_request(req)
                req.advance_stage()
                selected.append(req)
                tokens.append(1)
                decode_count += 1
            else:
                remaining_preempted.append(req)
        self._preempted_requests = remaining_preempted

        # Queue 中已完成 prefill 的 decode 请求
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
                decode_count += 1
            else:
                new_queue.append(req)
        self._request_queue = new_queue

        # ---- Step 2: Running prefill (preempted 中的未完成 prefill) ----
        # 每个请求独立获得 chunk_size tokens
        still_preempted = []
        for req in self._preempted_requests:
            if not req.is_prefill_complete:
                next_num = self._get_prefill_chunk(req)
                if next_num > 0:
                    selected.append(req)
                    tokens.append(next_num)
                else:
                    still_preempted.append(req)
            else:
                still_preempted.append(req)
        self._preempted_requests = still_preempted

        # ---- Step 3: New prefill (booking limit 控制 admission) ----
        # remain = total_limit - in_system: 还能 admit 多少新请求
        in_system = len(self._allocation_map)
        remain = max(0, self.total_limit - in_system)

        admitted = 0
        while self._request_queue and admitted < remain:
            req = self._request_queue[0]
            if getattr(req, 'current_stage', 0) != 0:
                break
            if not self._can_allocate_request(req):
                break
            next_num = self._get_prefill_chunk(req)
            if next_num == 0:
                break
            self._request_queue.pop(0)
            self._allocate_request(req)
            selected.append(req)
            tokens.append(next_num)
            admitted += 1

        # 更新统计
        self._batch_count += 1
        self._total_decode_in_batches += decode_count

        # ---- Force clear ----
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
