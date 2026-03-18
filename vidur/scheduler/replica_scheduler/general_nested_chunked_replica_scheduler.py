"""
WAIT-CP: Adaptive Chunked Prefill Scheduler

核心创新：自适应 chunk size
    - decode 多（系统忙）→ 缩小 chunk → batch 更快 → 优先推 decode
    - decode 少（系统闲）→ 放大 chunk → 快速完成 prefill → 填满 pipeline
    Sarathi 的 chunk_size 是固定的，不能做这个优化。

调度结构：Decode-First + Direct Preempt（底层 = Sarathi 效率）
准入控制：booking limit 提供 decode 数量信息用于 chunk 自适应
"""

from math import ceil
from typing import List, Dict
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.general_nested_booking_limit_replica_scheduler import (
    GeneralizedNestedBookingLimitReplicaScheduler,
)


class GeneralNestedChunkedReplicaScheduler(GeneralizedNestedBookingLimitReplicaScheduler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chunk_size = self._config.chunk_size  # base chunk (max)
        self._min_chunk_size = max(64, self._chunk_size // 4)  # min chunk
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )
        print(f"WAIT-CP Adaptive Chunk: base={self._chunk_size}, min={self._min_chunk_size}")

    # ---- Memory ----

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

    # ---- Adaptive chunk size ----

    def _get_adaptive_chunk(self, decode_count: int) -> int:
        """根据 decode 数量自适应 chunk size。

        decode 多 → 小 chunk（让 batch 更快，优先推 decode）
        decode 少 → 大 chunk（快速完成 prefill）
        """
        if decode_count <= 2:
            return self._chunk_size  # 系统闲，用满 chunk
        # 线性缩放：decode 越多 chunk 越小
        # chunk = max_chunk × (1 - decode_count / threshold)
        threshold = 20  # decode 数到这个值时 chunk 缩到最小
        ratio = max(0.0, 1.0 - decode_count / threshold)
        chunk = int(self._min_chunk_size + ratio * (self._chunk_size - self._min_chunk_size))
        return max(self._min_chunk_size, chunk)

    # ---- Token count ----

    def _get_request_next_num_tokens(
        self, request: Request, num_batch_tokens: int = 0, effective_chunk: int = 512
    ) -> int:
        if request.completed:
            return 0
        if request.is_prefill_complete:
            return 1
        remaining = request.num_prefill_tokens - request.num_processed_tokens
        available = effective_chunk - num_batch_tokens
        return max(0, min(remaining, available))

    # ---- Decode-First + Adaptive Chunk batch construction ----

    def _get_next_batch(self) -> Batch:
        """
        Decode-First + Adaptive Chunk:
          1. Preempted decode → 直接进 batch
          2. Preempted prefill → 续传
          3. 新请求 → 用自适应 chunk 预算
        """
        selected: List[Request] = []
        tokens: List[int] = []
        running_prefills: List[Request] = []

        # ---- Step 1: Preempted decode 直接进 batch ----
        decode_count = 0
        for req in self._preempted_requests:
            if req.is_prefill_complete:
                self._allocate_request(req)
                selected.append(req)
                tokens.append(1)
                decode_count += 1
            else:
                running_prefills.append(req)
        self._preempted_requests.clear()

        # ---- 自适应 chunk size ----
        effective_chunk = self._get_adaptive_chunk(decode_count)
        num_batch_tokens = decode_count  # decode 也计入预算

        # ---- Step 2: Running prefills 续传 ----
        skipped = []
        for req in running_prefills:
            next_num = self._get_request_next_num_tokens(req, num_batch_tokens, effective_chunk)
            if next_num == 0:
                skipped.append(req)
                continue
            selected.append(req)
            tokens.append(next_num)
            num_batch_tokens += next_num

        # skipped 放回 preempted 前端
        if skipped:
            self._preempted_requests = skipped + list(self._preempted_requests)

        # ---- Step 3: 新请求从 queue ----
        while self._request_queue:
            req = self._request_queue[0]
            if not self._can_allocate_request(req):
                break
            next_num = self._get_request_next_num_tokens(req, num_batch_tokens, effective_chunk)
            if next_num == 0:
                break
            self._request_queue.pop(0)
            self._allocate_request(req)
            selected.append(req)
            tokens.append(next_num)
            num_batch_tokens += next_num

        # ---- 已处理的 decode 从 queue 移除 ----
        for req in selected:
            if req.is_prefill_complete and req in self._request_queue:
                self._request_queue.remove(req)

        # ---- Force clear ----
        if not selected and self.all_requests_arrived and self._request_queue:
            print(f"强制清空队列，剩余: {len(self._request_queue)}")
            for req in self._request_queue:
                if req.id in self._allocation_map:
                    self.free(req.id)
            self._request_queue.clear()
            return None

        if selected:
            return Batch(self._replica_id, selected, tokens)
        return None
