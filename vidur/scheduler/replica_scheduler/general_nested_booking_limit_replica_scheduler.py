from math import ceil
from typing import List, Dict, Tuple
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.base_replica_scheduler import BaseReplicaScheduler

class GeneralizedNestedBookingLimitReplicaScheduler(BaseReplicaScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._preempted_requests: List[Request] = []
        self._num_running_batches = 0

        self.total_limit = self._config.total_limit
        print("total_limit:", self.total_limit)
        self.total_num_requests = self._config.total_num_requests
        self.force_clear= self._config.force_clear
        if self.force_clear:
            print("会在最后强制清空队列")
        self.all_requests_arrived = False
        self.num_arrival_requests = 0 # 记录到达的请求数
        
        # 保证 prefill 相同，但 decode 和 arrival_rate 可能不同，
        # 并且可能不止三个 type
        self.prompt_types = [
            {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000},
    {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000},
    {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 2000},
            # 可以继续添加更多类型……
        ]
        self.request_count_per_type = {pt["type"]: 0 for pt in self.prompt_types}
        # 由于所有类型的 prefill 相同，这里取第一个即可；并假设 prefill 阶段视为 1 个 stage
        self.prefill = self.prompt_types[0]["prefill"]
        self.prefill_stage_count = 1
        
        # 计算嵌套 booking limit：返回两个结果
        # 1. nested_booking_limits: 一个字典 mapping 全局 stage index -> 每个 stage 的 limit
        # 2. segments: 一个列表，每个元素记录该 segment 的起始、结束 stage 及每个 stage 的 limit（便于后续判断启动条件）
        self.nested_booking_limits, self.segments = self.calculate_nested_booking_limits()
    
    def add_request(self, request: Request) -> None:
        self._request_queue.append(request)
        self.num_arrival_requests += 1

        prompt_type = request.prompt_type  # 假设 request 具有 prompt_type 属性
        if prompt_type in self.request_count_per_type:
            self.request_count_per_type[prompt_type] += 1
        else:
            print(f"Warning: Received request with unknown type '{prompt_type}'")

        if self.num_arrival_requests == self.total_num_requests:
            self.all_requests_arrived = True
            print(f"计划到达个数:{self.total_num_requests}=已到达个数:{self.num_arrival_requests}")
            print("当最后一个request到达时, scheduler里面还剩下的request的数目是:", len(self._request_queue))

            total_throughput = 0
            for prompt_type, count in self.request_count_per_type.items():
                print(f"Type:{prompt_type}, Count:{count}")
                prompt_info = next((pt for pt in self.prompt_types if pt["type"] == prompt_type), None)
                if prompt_info:
                    total_throughput += count * (prompt_info["decode"] + 1)
                else:
                    print(f"Warning: prompt_type '{prompt_type}' not found in self.prompt_types")
            print("理论上的throughput是:", total_throughput)
    
    def calculate_nested_booking_limits(self) -> Tuple[Dict[int, int], List[Dict[str, int]]]:
        """
        根据 self.prompt_types 的 decode 和 arrival_rate, 一般化地划分 segments
        并计算每个 global stage 的 booking limit

        返回：
          - nested_booking_limits: {global_stage_index: per_stage_limit}
          - segments: 列表，每个元素形如 { "start": int, "end": int, "per_stage_limit": int }
                    其中 start, end 为该 segment 在全局阶段中的起始和结束 index
        """
        # 1. 收集所有唯一的 decode 值，并排序
        unique_decodes = sorted({pt["decode"] for pt in self.prompt_types})
        
        segments = []
        # Segment1：所有请求至少需要 prefill 阶段（计1个 stage）加上最小 decode 次数
        seg1_count = self.prefill_stage_count + unique_decodes[0]
        seg1_arrival_sum = sum(pt["arrival_rate"] for pt in self.prompt_types)
        segments.append({"count": seg1_count, "arrival_sum": seg1_arrival_sum})
        
        # 后续每个 segment依次处理额外的 decode 次数
        for i in range(1, len(unique_decodes)):
            seg_count = unique_decodes[i] - unique_decodes[i-1]  # 额外需要处理的 decode 次数
            # 仅考虑 decode 大于上一阈值的类型参与本 segment
            seg_arrival_sum = sum(pt["arrival_rate"] for pt in self.prompt_types if pt["decode"] > unique_decodes[i-1])
            segments.append({"count": seg_count, "arrival_sum": seg_arrival_sum})
        
        # 计算各 segment 的权重，并求总权重
        total_weight = sum(seg["count"] * seg["arrival_sum"] for seg in segments)
        
        nested_booking_limits = {}
        segments_info = []  # 用于记录每个 segment 在全局 stage 的起止边界及其 per_stage_limit
        global_stage = 0
        for seg in segments:
            seg_weight = seg["count"] * seg["arrival_sum"]
            seg_total_limit = self.total_limit * (seg_weight / total_weight) if total_weight > 0 else 0
            per_stage_limit = int(max(seg_total_limit / seg["count"],1)) if seg["count"] > 0 else 0 
            seg_start = global_stage
            for _ in range(seg["count"]):
                # 这里使用 int(max(,1)) 来取整，实际应用中可根据需要调整取整策略
                nested_booking_limits[global_stage] = per_stage_limit
                global_stage += 1
            seg_end = global_stage - 1
            segments_info.append({"start": seg_start, "end": seg_end, "per_stage_limit": per_stage_limit})
            print(f"start: {seg_start}, end: {seg_end}, per_stage_limit: {per_stage_limit}")
        
        # 输出调试信息
        print("Nested Booking Limits per stage:", nested_booking_limits)
        print("Segments info:", segments_info)
        
        return nested_booking_limits, segments_info

    def _allocate_request(self, request: Request) -> None:
        """
        分配资源给 request。
        - 如果是新请求，则根据其 prefill tokens 计算所需 block 数量进行分配；
        - 如果 request 已存在，则按需额外分配 1 个 block。
        """
        if request.id not in self._allocation_map:
            num_required_blocks = ceil(request.num_prefill_tokens / self._config.block_size)
            self.allocate(request.id, num_required_blocks)
        else:
            num_tokens_reserved = self._allocation_map[request.id] * self._config.block_size
            num_tokens_required = max(0, request.num_processed_tokens - num_tokens_reserved)
            if num_tokens_required:
                self.allocate(request.id, 1)
    
    def _get_next_batch(self) -> Batch:
        """
        调度逻辑：
          1. 将上次未完成的请求(preempted)重新归入队列;
          2. 按 request.current_stage(全局 stage)将请求分组;
          3. 按 segments 顺序依次调度：
             - 对于每个 segment, 首先检查该 segment 起始 stage 上的请求数是否达到预设的 booking limit(即 nested_booking_limits[segment.start])
             - 只有当前一段已经启动后，后续 segment 才允许启动;
             - 对于满足条件的 segment,从该段内每个 stage中各取出不超过预设 limit 数量的请求
               并调用 _allocate_request() 以及 req.advance_stage() 使请求进入下一阶段
          4. 将选中的请求打包成一个 Batch 返回
        
        调度逻辑修改说明：
        - 如果 self.all_requests_arrived 为 False,则沿用原有的顺序调度逻辑
        - 如果 self.all_requests_arrived 为 True,则逐个检查每个 segment 的起始阶段(seg["start"])是否满足预设的 booking limit
            (1) 如果至少有一个 segment 的起始阶段满足条件, 则对所有满足条件的 segment 进行调度
                即从该 segment 内各个阶段中各自取出不超过预设 limit 的请求
            (2) 如果所有 segment 的起始阶段都不满足预设条件, 则执行强制清空队列的逻辑
                打印相关信息, 释放已分配资源, 并清空 _request_queue, 最后返回 None
        """
        # 将上次未完成的（preempted）请求重新归入队列
        for req in self._preempted_requests:
            if req not in self._request_queue:
                self._request_queue.append(req)
        self._preempted_requests.clear()

        # 按请求的 current_stage 将请求分组
        grouped_requests: Dict[int, List[Request]] = {}
        for req in self._request_queue:
            stage = getattr(req, 'current_stage', 0)
            grouped_requests.setdefault(stage, []).append(req)

        selected_requests: List[Request] = []
        selected_num_tokens: List[int] = []

        # 根据 all_requests_arrived 标识分两种逻辑
        if not self.all_requests_arrived:
            # 原有逻辑：依次检查各个 segment，要求前一个 segment 必须满足条件才能启动后续 segment
            for seg in self.segments:
                seg_start = seg["start"]
                required = self.nested_booking_limits.get(seg_start, 0)
                if len(grouped_requests.get(seg_start, [])) < required:
                    # 如果该 segment 的起始阶段请求数不够，则不启动后续 segment
                    break

                # 对该 segment 内每个阶段调度请求
                for stage in range(seg["start"], seg["end"] + 1):
                    limit = self.nested_booking_limits.get(stage, 0)
                    group = grouped_requests.get(stage, [])
                    for _ in range(limit):
                        if not group:
                            break
                        req = group.pop(0)
                        if req in self._request_queue:
                            self._request_queue.remove(req)
                        self._allocate_request(req)
                        req.advance_stage()
                        selected_requests.append(req)
                        next_num = self._get_request_next_num_tokens(req)
                        selected_num_tokens.append(next_num)
        else:
            # 新逻辑：所有请求已到达
            found_segment = False  # 标记是否有至少一个 segment 的起始阶段满足 booking limit
            for seg in self.segments:
                seg_start = seg["start"]
                required = self.nested_booking_limits.get(seg_start, 0)
                if len(grouped_requests.get(seg_start, [])) >= required:
                    # 如果该 segment 的起始阶段满足预设条件，则进行调度
                    found_segment = True
                    for stage in range(seg["start"], seg["end"] + 1):
                        limit = self.nested_booking_limits.get(stage, 0)
                        group = grouped_requests.get(stage, [])
                        for _ in range(limit):
                            if not group:
                                break
                            req = group.pop(0)
                            if req in self._request_queue:
                                self._request_queue.remove(req)
                            self._allocate_request(req)
                            req.advance_stage()
                            selected_requests.append(req)
                            next_num = self._get_request_next_num_tokens(req)
                            selected_num_tokens.append(next_num)
                # 对于不满足条件的 segment，不进行处理

            if not found_segment:
                # 如果所有 segment 的起始阶段都不满足 booking limit，则执行强制清空队列逻辑
                print("所有请求已到达, 每个segment都不能运行了 ,强制清除队列")
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
    
    def on_batch_end(self, batch: Batch) -> None:
        """
        批次执行结束后：
          - 若请求已完成，则释放资源；
          - 否则将其加入 preempted 队列，待下次调度时重新归队。
        """
        self._num_running_batches -= 1
        for request in batch.requests:
            if request.completed:
                self.free(request.id)
            else:
                self._preempted_requests.append(request)
    
    def is_empty(self) -> bool:
        """
        判断队列和 preempted 请求是否均为空。
        """
        return not self._request_queue and not self._preempted_requests
