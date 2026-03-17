from math import ceil
from typing import List, Dict
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.general_nested_booking_limit_replica_scheduler import (
    GeneralizedNestedBookingLimitReplicaScheduler,
)


class GeneralNestedChunkedReplicaScheduler(GeneralizedNestedBookingLimitReplicaScheduler):
    """
    General Nested Booking Limit + Sarathi Chunked Prefill 融合调度器

    继承关系:
        BaseReplicaScheduler -> GeneralizedNestedBookingLimitReplicaScheduler -> GeneralNestedChunkedReplicaScheduler

    核心特性:
        1. 保留GeneralNested的segment/booking limit机制（Stage 1+）
        2. 引入Sarathi的chunked prefill优化（仅在Stage 0）
        3. 两级Stage系统：
           - Stage 0: 使用chunked机制，可停留多次调度周期
           - Stage 1+: 保持原GeneralNested逻辑，每次1个token，每次推进

    Stage语义:
        - Stage 0 (Prefill阶段):
            * 请求可以被调度多次
            * 每次处理min(剩余prefill, chunk_size - num_batch_tokens)个tokens
            * 只有当is_prefill_complete=True时才推进到Stage 1
            * 不调用advance_stage()
        - Stage 1+ (Decode阶段):
            * 保持原GeneralNested逻辑
            * 每次处理1个token
            * 每次调度后调用advance_stage()推进

    兼容性: 100%向后兼容GeneralNested配置，只需添加chunk_size参数

    作者: Vidur Scheduling优化项目组
    版本: 1.0.0
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Sarathi配置：chunk_size
        self._chunk_size = self._config.chunk_size
        # 内存水位线（参考Sarathi）
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )
        print(f"GeneralNestedChunked Scheduler initialized with chunk_size={self._chunk_size}")

    def _can_allocate_request(self, request: Request) -> bool:
        """
        检查是否有足够的内存分配给请求（参考Sarathi实现）

        Args:
            request: 请求对象

        Returns:
            True: 可以分配
            False: 内存不足
        """
        if request.id not in self._allocation_map:
            # 新请求：需要分配全部prefill所需的blocks
            num_required_blocks = ceil(request.num_prefill_tokens / self._config.block_size)
            return (
                self._config.num_blocks
                - self._num_allocated_blocks
                - num_required_blocks
                >= self._watermark_blocks
            )
        # 已存在请求：只需要1个block（decode阶段）
        return self._config.num_blocks - self._num_allocated_blocks >= 1

    def _get_request_next_num_tokens(
        self, request: Request, num_batch_tokens: int = 0
    ) -> int:
        """
        动态计算请求下次处理的token数 - 融合Sarathi的chunked逻辑

        与BaseReplicaScheduler的区别：
            - BaseReplicaScheduler: prefill阶段返回全部prefill_tokens
            - 本调度器: prefill阶段使用chunked机制，返回chunk大小

        Args:
            request: 请求对象
            num_batch_tokens: 当前batch已累计的token数（用于chunked prefill）

        Returns:
            下次处理的token数
                - Decode阶段 (is_prefill_complete=True): 返回1
                - Prefill阶段 (is_prefill_complete=False): 返回min(剩余prefill, chunk容量)
        """
        if request.completed:
            return 0

        # Decode阶段：每次1个token（保持GeneralNested原逻辑）
        if request.is_prefill_complete:
            return 1

        # Prefill阶段（Stage 0）：使用Sarathi的chunked机制
        remaining_prefill = request.num_prefill_tokens - request.num_processed_tokens
        available_in_chunk = self._chunk_size - num_batch_tokens
        next_num_tokens = min(remaining_prefill, available_in_chunk)

        return max(0, next_num_tokens)

    def _get_next_batch(self) -> Batch:
        """
        调度逻辑 - 在Stage 0使用chunked prefill，其他stage保持原逻辑

        修改说明：
            1. 将上次未完成的请求(preempted)重新归入队列（保持原逻辑）
            2. 按request.current_stage将请求分组（保持原逻辑）
            3. 按segments顺序依次调度：
               - Stage 0: 使用chunked机制，累计num_batch_tokens，不调用advance_stage()
               - Stage 1+: 保持原GeneralNested逻辑，每次1个token，调用advance_stage()
            4. 将选中的请求打包成Batch返回（保持原逻辑）

        调度逻辑修改说明（继承自父类）：
            - 如果self.all_requests_arrived为False，则沿用原有的顺序调度逻辑
            - 如果self.all_requests_arrived为True，则检查第一个segment是否满足条件
        """
        # 将上次未完成的（preempted）请求重新归入队列
        for req in self._preempted_requests:
            if req not in self._request_queue:
                self._request_queue.append(req)
        self._preempted_requests.clear()

        # 按请求的current_stage将请求分组
        grouped_requests: Dict[int, List[Request]] = {}
        for req in self._request_queue:
            stage = getattr(req, 'current_stage', 0)
            grouped_requests.setdefault(stage, []).append(req)

        selected_requests: List[Request] = []
        selected_num_tokens: List[int] = []

        first_segment_satisfied = False
        first_segment = self.segments[0]
        firts_seg_start = first_segment["start"]
        # required 是第一个限制, 是之前严格的booking limit限制
        required = self.nested_booking_limits.get(firts_seg_start, 0)
        # occupied 是当前在这个segment但不在初始位置的请求的数目, 也是已经被占用的limit
        occupied = sum(1 for req in self._request_queue
                   if getattr(req, 'current_stage', 0) > first_segment["start"]
                   and getattr(req, 'current_stage', 0)<= first_segment["end"])
        # limit_for_this_segment 是这个segment的limit
        limit_for_this_segment = first_segment["seg_total_limit"]
        # remain 是剩余的limit
        remain = limit_for_this_segment - occupied
        stage_0_num = len(grouped_requests.get(firts_seg_start, []))

        # 不要下限
        first_segment_satisfied = True

        if not self.all_requests_arrived or (self.all_requests_arrived and first_segment_satisfied):
            # 原有逻辑：依次检查各个segment，要求前一个segment必须满足条件才能启动后续segment
            # 现在修改成了: 要么所有请求还没有到达, 要么已经全部到达但是第一个segment满足了
            seg_num = 0
            for seg in self.segments:
                seg_num += 1
                seg_start = seg["start"]
                required = self.nested_booking_limits.get(seg_start, 0)
                occupied = sum(1 for req in self._request_queue
                    if getattr(req, 'current_stage', 0) > seg["start"]
                    and getattr(req, 'current_stage', 0) <= seg["end"])
                limit_for_this_segment = seg["seg_total_limit"]
                remain = limit_for_this_segment - occupied

                # 关键修改：Stage 0 放宽 Admission 条件
                # 原因：chunked prefill 机制下，limit 个请求可能只能处理一部分
                #       如果严格要求凑够 limit 个请求，会导致请求卡死
                if seg_start == 0:
                    # Stage 0: 只要有请求就可以调度（chunk_size 已经限制了处理量）
                    if len(grouped_requests.get(seg_start, [])) == 0:
                        break
                else:
                    # Stage 1+: 保持原有的 admission 检查
                    if len(grouped_requests.get(seg_start, [])) < min(required, remain):
                        break

                # 对该segment内每个阶段调度请求
                for stage in range(seg["start"], seg["end"] + 1):
                    required = self.nested_booking_limits.get(stage, 0)

                    if stage == seg["start"]:
                        limit = min(remain, required)
                    else:
                        limit = self.nested_booking_limits.get(stage, 0)

                    group = grouped_requests.get(stage, [])

                    # 关键修改：Stage 0使用chunked逻辑，其他stage保持原逻辑
                    if stage == 0:
                        # Stage 0: Chunked Prefill逻辑
                        num_batch_tokens = 0  # 初始化chunk累计器

                        for _ in range(limit):
                            if not group:
                                break

                            req = group[0]  # Peek first

                            # 检查内存是否足够（关键：防止OOM）
                            if not self._can_allocate_request(req):
                                break  # 内存不足，停止选择更多请求

                            # 计算该请求需要的tokens（使用chunked逻辑）
                            next_num = self._get_request_next_num_tokens(req, num_batch_tokens)

                            if next_num == 0:
                                break  # 当前chunk已满，无法添加更多prefill

                            # 确认选择该请求
                            req = group.pop(0)
                            if req in self._request_queue:
                                self._request_queue.remove(req)

                            self._allocate_request(req)

                            # 关键：Stage 0不调用advance_stage()！
                            # 只有在batch处理完成后，on_batch_end会更新num_processed_tokens
                            # 如果此时is_prefill_complete=True，下次调度时会被分到Stage 1

                            selected_requests.append(req)
                            selected_num_tokens.append(next_num)
                            num_batch_tokens += next_num  # 累计batch中的tokens
                    else:
                        # Stage 1+: 保持原GeneralNested逻辑
                        for _ in range(limit):
                            if not group:
                                break

                            req = group[0]  # Peek first

                            # 检查内存是否足够
                            if not self._can_allocate_request(req):
                                break  # 内存不足，停止选择更多请求

                            req = group.pop(0)
                            if req in self._request_queue:
                                self._request_queue.remove(req)
                            self._allocate_request(req)
                            req.advance_stage()  # Decode阶段正常推进
                            selected_requests.append(req)
                            next_num = self._get_request_next_num_tokens(req)
                            selected_num_tokens.append(next_num)
        else:
            # 新逻辑：所有请求已到达，但第一个segment不满足条件
            print("所有请求已到达, 但是第一个segment不够, 所以都不能运行了 ,强制清除队列")
            print("此时scheduler里面还剩下的request的数目是:", len(self._request_queue))
            for req in self._request_queue:
                if req.id in self._allocation_map:
                    self.free(req.id)
            self._request_queue.clear()
            print("已经强制清空, 此时scheduler里面还剩下的request的数目是:", len(self._request_queue))
            return None

        if selected_requests:
            return Batch(self._replica_id, selected_requests, selected_num_tokens)
        return None
