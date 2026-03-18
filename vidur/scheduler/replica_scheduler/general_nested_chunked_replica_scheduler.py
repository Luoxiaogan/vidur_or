"""
WAIT-CP: Unified Segmented Chunked Prefill Scheduler

统一调度框架，N_SEG 和 total_limit 均可运行时自适应调整。

参数空间:
    N_SEG = 1   → decode-first (≈ Sarathi)
    N_SEG = 4   → 分段（中间态）
    N_SEG = l₁  → per-stage（paper 原始算法）

    total_limit: booking limit，通过 n*(λ) 自适应

调度结构:
    1. Preempted decode → 直接分组到 segments（不经 queue）
    2. 段间门控：凑够 seg_limit 才处理（WAIT 核心）
       - 但 work-conserving 兜底：如果全部段都不够，仍处理最大的段
    3. Prefill：用剩余 chunk 预算处理

自适应机制:
    - λ̂: EMA 估计到达率
    - n*(λ̂): 理论最优 total_limit
    - N_SEG: 可根据系统负载动态调整
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
        self._chunk_size = self._config.chunk_size
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )

        # 从 prompt_types 获取参数
        pt = self._config.prompt_types[0] if self._config.prompt_types else {}
        self._l0 = pt.get("prefill", 630)
        self._l1 = pt.get("decode", 20)
        self._K = max(1, ceil(self._l0 / self._chunk_size))

        # ---- 自适应参数 ----
        self._n_max = self.total_limit  # 配置的 total_limit 作为上限
        # N_SEG: 初始值（可运行时调整）
        self._n_seg = min(4, self._l1)
        self._decode_segments = self._build_segments(self._l1, self._n_seg)
        self._seg_limit = max(1, self.total_limit // (self._n_seg + 1))

        # λ 估计
        self._ema_alpha = 0.05
        self._lambda_hat = 0.0
        self._last_arrival_time = None

        # d₀, d₁ (from profiler: A100 + Llama-3-8B)
        self._d0 = 0.0443
        self._d1 = 0.000223
        self._pipeline_depth = self._K + self._l1

        # 运行时统计（用于自适应 N_SEG）
        self._batch_count = 0
        self._total_decode_in_batches = 0

        print(f"WAIT-CP Unified: chunk={self._chunk_size}, N_SEG={self._n_seg}, "
              f"total_limit={self.total_limit}, K={self._K}, l1={self._l1}")

    # ------------------------------------------------------------------ #
    #  Segment construction
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_segments(l1: int, n_seg: int) -> List[Tuple[int, int]]:
        """将 l1 个 decode steps (stage 1..l1) 均分为 n_seg 段"""
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
    #  Adaptive: λ estimation + n* + N_SEG
    # ------------------------------------------------------------------ #

    def add_request(self, request: Request) -> None:
        t = request.arrived_at
        if self._last_arrival_time is not None and t > self._last_arrival_time:
            rate = 1.0 / (t - self._last_arrival_time)
            self._lambda_hat = (
                self._ema_alpha * rate + (1 - self._ema_alpha) * self._lambda_hat
                if self._lambda_hat > 0 else rate
            )
            self._adapt()
        self._last_arrival_time = t
        super().add_request(request)

    def _adapt(self):
        """自适应调整 total_limit 和 N_SEG"""
        # ---- 自适应 total_limit = n*(λ) ----
        denom = 1 - self._pipeline_depth * self._d1 * self._lambda_hat
        if denom <= 0.01:
            new_limit = self._n_max
        else:
            n_star = self._pipeline_depth * self._d0 * self._lambda_hat / denom
            new_limit = min(max(1, ceil(n_star)), self._n_max)

        if new_limit != self.total_limit:
            self.total_limit = new_limit
            self._seg_limit = max(1, self.total_limit // (self._n_seg + 1))

        # ---- 自适应 N_SEG ----
        # 思路: 根据平均 decode 数量调整分段粒度
        # decode 多（忙）→ 更多段（更细的流量控制）
        # decode 少（闲）→ 更少段（更低 overhead）
        if self._batch_count > 0 and self._batch_count % 100 == 0:
            avg_decode = self._total_decode_in_batches / self._batch_count
            if avg_decode < 3:
                new_n_seg = 1  # 很闲，不需要分段
            elif avg_decode < 8:
                new_n_seg = 2
            elif avg_decode < 15:
                new_n_seg = 4
            else:
                new_n_seg = min(8, self._l1)

            if new_n_seg != self._n_seg:
                self._n_seg = new_n_seg
                self._decode_segments = self._build_segments(self._l1, self._n_seg)
                self._seg_limit = max(1, self.total_limit // (self._n_seg + 1))

    # ------------------------------------------------------------------ #
    #  Memory & Token count
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

    def _get_request_next_num_tokens(
        self, request: Request, num_batch_tokens: int = 0
    ) -> int:
        if request.completed:
            return 0
        if request.is_prefill_complete:
            return 1
        remaining = request.num_prefill_tokens - request.num_processed_tokens
        available = self._chunk_size - num_batch_tokens
        return max(0, min(remaining, available))

    # ------------------------------------------------------------------ #
    #  Batch construction
    # ------------------------------------------------------------------ #

    def _get_next_batch(self) -> Batch:
        """
        统一分段调度:
          1. Preempted → 直接分组到 segments（不经 queue）
          2. Queue → 分组
          3. Decode segments: 段间门控 + work-conserving 兜底
          4. Prefill: chunk 预算
        """
        # ---- Step 1: 分组（preempted 直接分组，不经 queue）----
        prefill_group: List[Request] = []
        decode_seg_groups: List[List[Request]] = [[] for _ in self._decode_segments]

        for req in self._preempted_requests:
            if req.is_prefill_complete:
                seg_idx = self._get_seg_index(getattr(req, 'current_stage', 1))
                decode_seg_groups[seg_idx].append(req)
            else:
                prefill_group.append(req)
        self._preempted_requests.clear()

        for req in self._request_queue:
            stage = getattr(req, 'current_stage', 0)
            if stage == 0 and req.is_prefill_complete:
                req.advance_stage()
                stage = req.current_stage
            if stage == 0:
                prefill_group.append(req)
            else:
                seg_idx = self._get_seg_index(stage)
                decode_seg_groups[seg_idx].append(req)

        selected: List[Request] = []
        tokens: List[int] = []

        # ---- Step 2: Decode segments ----
        # 段间门控：凑够 seg_limit 才处理
        # work-conserving 兜底：如果没有任何段凑够，仍处理所有可用的（不 idle GPU）
        any_seg_fired = False
        batch_count = 0

        for seg_idx in reversed(range(len(self._decode_segments))):
            group = decode_seg_groups[seg_idx]
            if not group:
                continue

            # 门控检查
            if len(group) >= self._seg_limit or self.all_requests_arrived:
                # 凑够了（或 drain 模式）→ 处理
                for req in group:
                    self._allocate_request(req)
                    req.advance_stage()
                    selected.append(req)
                    tokens.append(1)
                    batch_count += 1
                any_seg_fired = True
            else:
                # 不够 → 放回 preempted 等下次
                for req in group:
                    self._preempted_requests.append(req)

        # Work-conserving 兜底：如果没有段凑够，取出最大的段处理（不 idle GPU）
        if not any_seg_fired and not self.all_requests_arrived:
            # 找有请求的最大段
            best_seg = -1
            best_count = 0
            for seg_idx in reversed(range(len(self._decode_segments))):
                count = len(decode_seg_groups[seg_idx])
                if count > best_count:
                    best_count = count
                    best_seg = seg_idx

            if best_seg >= 0:
                # 从 preempted 取回（刚放进去的）
                to_process = []
                remaining_preempted = []
                seg_start, seg_end = self._decode_segments[best_seg]
                for req in self._preempted_requests:
                    stage = getattr(req, 'current_stage', 0)
                    if seg_start <= stage <= seg_end:
                        to_process.append(req)
                    else:
                        remaining_preempted.append(req)
                self._preempted_requests = remaining_preempted

                for req in to_process:
                    self._allocate_request(req)
                    req.advance_stage()
                    selected.append(req)
                    tokens.append(1)
                    batch_count += 1

        # ---- Step 3: Prefill ----
        num_batch_tokens = batch_count  # decode 计入 chunk 预算
        prefill_cap = max(1, self.total_limit - batch_count)

        for _ in range(prefill_cap):
            if not prefill_group:
                break
            req = prefill_group[0]
            if not self._can_allocate_request(req):
                break
            next_num = self._get_request_next_num_tokens(req, num_batch_tokens)
            if next_num == 0:
                break
            prefill_group.pop(0)
            if req in self._request_queue:
                self._request_queue.remove(req)
            self._allocate_request(req)
            selected.append(req)
            tokens.append(next_num)
            num_batch_tokens += next_num

        # 已处理的 decode 从 queue 移除
        for req in selected:
            if req.is_prefill_complete and req in self._request_queue:
                self._request_queue.remove(req)

        # 更新统计
        self._batch_count += 1
        self._total_decode_in_batches += batch_count

        # ---- Force clear ----
        if not selected and self.all_requests_arrived:
            if self._request_queue or self._preempted_requests:
                # 清 queue
                for req in self._request_queue:
                    if req.id in self._allocation_map:
                        self.free(req.id)
                self._request_queue.clear()
                # 清 preempted
                for req in self._preempted_requests:
                    if req.id in self._allocation_map:
                        self.free(req.id)
                self._preempted_requests.clear()
            return None

        if selected:
            return Batch(self._replica_id, selected, tokens)
        return None
