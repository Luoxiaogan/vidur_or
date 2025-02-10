from math import ceil
import time 
from typing import List, Dict, Tuple
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.base_replica_scheduler import BaseReplicaScheduler

class NestedBookingLimitReplicaScheduler(BaseReplicaScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._preempted_requests: List[Request] = []
        self._num_running_batches = 0
        
        # self._last_schedule_time = time.time()  # 新增：记录上一次调度时间
        self._last_schedule_time = 0
        self._current_time = 0

        # 假定总限制设置为 200
        self.total_limit = 256
        
        # 所有类型的 prefill 都相同，这里 decode、arrival_rate 不同
        self.prompt_types = [
            {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 0.25},
            {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 0.5},
            {"type": "type3", "prefill": 10, "decode": 30, "arrival_rate": 0.1},
            {"type": "type4", "prefill": 10, "decode": 40, "arrival_rate": 0.01},
        ]
        # self.prompt_types = [
        #     {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 100},
        #     {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 200},
        #     {"type": "type3", "prefill": 10, "decode": 30, "arrival_rate": 40},
        #     {"type": "type4", "prefill": 10, "decode": 40, "arrival_rate": 4},
        # ]
        # 计算各个 segment 内各 stage 的 booking limit
        self.nested_booking_limits = self.calculate_nested_booking_limits()
    
    def calculate_nested_booking_limits(self) -> Dict[int, int]:
        """
        按照 nested booking limit 策略计算每个 stage 的 limit。
        
        划分 segment 规则：
         - Segment1：所有请求都至少需要 1 + decode_min 次处理，其中 decode_min = 10，
                      故处理次数为 11；所有类型参与，arrival_rate_sum = 0.25+0.5+0.1 = 0.85。
         - Segment2：只处理 decode > 10 的请求，处理次数 = (min(decode>10) - 10) = 20-10 = 10，
                      arrival_rate_sum = 0.5+0.1 = 0.6。
         - Segment3：只处理 decode > 20 的请求，处理次数 = (max(decode)-20) = 30-20 = 10，
                      arrival_rate_sum = 0.1.
        
        然后按照每个 segment 的初始权重（processing_count × arrival_rate_sum）分配 total_limit，
        最后在 segment 内均摊到每个 stage。
        """
        # 固定值，因为 prefill 对所有类型都相同
        decode_min = min(pt["decode"] for pt in self.prompt_types)  # = 10
        
        # Segment1
        seg1_processing = 1 + decode_min  # 11
        seg1_arrival_sum = sum(pt["arrival_rate"] for pt in self.prompt_types)  # 0.25+0.5+0.1 = 0.85
        seg1_weight = seg1_processing * seg1_arrival_sum  # 11 * 0.85
        
        # Segment2：只考虑 decode 大于 decode_min 的类型
        seg2_types = [pt for pt in self.prompt_types if pt["decode"] > decode_min]
        if seg2_types:
            seg2_min = min(pt["decode"] for pt in seg2_types)  # 对于 type2 和 type3，min=20
            seg2_processing = seg2_min - decode_min  # 20-10 = 10
            seg2_arrival_sum = sum(pt["arrival_rate"] for pt in seg2_types)  # 0.5+0.1 = 0.6
        else:
            seg2_processing = 0
            seg2_arrival_sum = 0
        seg2_weight = seg2_processing * seg2_arrival_sum  # 10 * 0.6 = 6
        
        # Segment3：只考虑 decode 大于 seg2_min 的类型
        seg3_types = [pt for pt in seg2_types if pt["decode"] > seg2_min]
        if seg3_types:
            seg3_processing = max(pt["decode"] for pt in seg3_types) - seg2_min  # 30-20 = 10
            seg3_arrival_sum = sum(pt["arrival_rate"] for pt in seg3_types)  # 0.1
        else:
            seg3_processing = 0
            seg3_arrival_sum = 0
        seg3_weight = seg3_processing * seg3_arrival_sum  # 10 * 0.1 = 1
        
        total_weight = seg1_weight + seg2_weight + seg3_weight  # 11*0.85 + 6 + 1
        
        # 计算每个 segment 分到的总 limit，再均摊到每个 stage内
        seg1_total_limit = self.total_limit * (seg1_weight / total_weight) if total_weight else 0
        seg2_total_limit = self.total_limit * (seg2_weight / total_weight) if total_weight else 0
        seg3_total_limit = self.total_limit * (seg3_weight / total_weight) if total_weight else 0
        
        seg1_per_stage = seg1_total_limit / seg1_processing if seg1_processing else 0
        seg2_per_stage = seg2_total_limit / seg2_processing if seg2_processing else 0
        seg3_per_stage = seg3_total_limit / seg3_processing if seg3_processing else 0
        
        # 将全局 stage 分布：
        # Segment1 对应 stage 0 ~ 10
        # Segment2 对应 stage 11 ~ 20
        # Segment3 对应 stage 21 ~ 30
        nested_limits = {}
        for stage in range(0, seg1_processing):
            nested_limits[stage] = int(seg1_per_stage)
        for stage in range(seg1_processing, seg1_processing + seg2_processing):
            nested_limits[stage] = int(seg2_per_stage)
        for stage in range(seg1_processing + seg2_processing, seg1_processing + seg2_processing + seg3_processing):
            nested_limits[stage] = int(seg3_per_stage)
        
        # 例如，可能得到：
        # stage 0~10: 每个约 10 个，
        # stage 11~20: 每个约 7 个，
        # stage 21~30: 每个约 1 个。
        print("Nested Booking Limits per stage:", nested_limits)
        return nested_limits
    
    def _allocate_request(self, request: Request) -> None:
        # 与 BookingLimitReplicaScheduler 类似，新请求时分配对应块数，后续只分配额外的1块
        if request.id not in self._allocation_map:
            num_required_blocks = ceil(request.num_prefill_tokens / self._config.block_size)
            self.allocate(request.id, num_required_blocks)
        else:
            num_tokens_reserved = self._allocation_map[request.id] * self._config.block_size
            num_tokens_required = max(0, request.num_processed_tokens - num_tokens_reserved)
            # 此处假设每次多分配 1 个 block
            if num_tokens_required:
                self.allocate(request.id, 1)
    
    def _get_next_batch(self) -> Batch:
        """
        Nested booking limit 调度逻辑：
         1. 将上次未完成的请求重新加入队列。
         2. 按照 req.current_stage 对请求进行分组，分为各个 stage。
         3. 按 segment 顺序（Segment1: stage 0～10；Segment2: stage 11～20；Segment3: stage 21～30）判断：
              - 只有当某个 segment 的起始 stage（例如 stage0、stage11、stage21）的请求数达到对应的 booking limit 时，
                才认为该 segment 可以启动，并从该 segment 内的每个 stage中各取固定数量的请求加入批次。
              - 后续 segment 只有在前一个 segment 已启动的前提下才能启动。
         4. 选中的请求调用 _allocate_request() 后，调用 req.advance_stage() 进入下一阶段。
        """
        # 先将上次未完成的请求归回队列
        for req in self._preempted_requests:
            if req not in self._request_queue:
                self._request_queue.append(req)
        self._preempted_requests.clear()
        
        # 按照当前 stage 分组，key 为 req.current_stage
        grouped_requests: Dict[int, List[Request]] = {}
        for req in self._request_queue:
            stage = getattr(req, 'current_stage', 0)
            grouped_requests.setdefault(stage, []).append(req)
        
        self._current_time = time.time()
        print(self._current_time)
        
        
        # 这里我们只关注 stage=0 的请求是否达到 booking limit 要求
        # all_stage0_ready = True
        # for ptype in self.prompt_types:
        #     # 假设每个 prompt type 对应的 booking limit 可以从 nested_booking_limits 中根据某种规则取到
        #     # 例如:
        #     needed = self.nested_booking_limits.get(0, 0)  # 或者根据 ptype["type"] 来获取不同的 limit
        #     available = len([req for req in grouped_requests.get(0, []) if req.type == ptype["type"]])
        #     if available < needed:
        #         all_stage0_ready = False
        #         break
 
        # if not all_stage0_ready:
        #     # 如果等待时间超过 2 秒，则强制调度当前 stage=0 的所有请求
        #     if current_time - self._last_schedule_time >= 2:
        #         print("Timeout reached: forcing scheduling of available stage=0 requests.")
        #         forced_selected_requests: List[Request] = []
        #         forced_selected_num_tokens: List[int] = []
        #         # 强制调度：不考虑 booking limit 要求，取出所有 stage=0 请求
        #         for req in grouped_requests.get(0, []):
        #             if req in self._request_queue:
        #                 self._request_queue.remove(req)
        #             self._allocate_request(req)
        #             req.advance_stage()
        #             print(f"Force-scheduled request {req.id} to stage {req.current_stage}")
        #             forced_selected_requests.append(req)
        #             forced_selected_num_tokens.append(self._get_request_next_num_tokens(req))
        #         # 更新最后调度时间
        #         self._last_schedule_time = current_time
        #         if forced_selected_requests:
        #             batch = Batch(self._replica_id, forced_selected_requests, forced_selected_num_tokens)
        #             self.on_batch_end(batch)
        #             return batch
        #         else:
        #             return None
        #     else:
        #         print("Not enough stage=0 requests to meet booking limits, waiting...")
        #         return None
        # else:
        #     # 如果 stage=0 条件满足，则更新最后调度时间
        #     self._last_schedule_time = current_time

        selected_requests: List[Request] = []
        selected_num_tokens: List[int] = []
        
        # 定义三个 segment 的边界
        seg1_start, seg1_end = 0, 10
        seg2_start, seg2_end = 11, 20
        seg3_start, seg3_end = 21, 30
        
        # 分段调度：依次检查 segment 是否满足启动条件
        # 如果某个 segment 的起始 stage数量不足，则后续 segment 不启动
        # --- Segment1 ---
        seg1_required = self.nested_booking_limits.get(seg1_start, 0)
        if len(grouped_requests.get(seg1_start, [])) < seg1_required:
            # print(self._last_schedule_time, current_time)
            if self._current_time - self._last_schedule_time >= 1:
                print(self._last_schedule_time, self._current_time)
                # 强制调度：取出所有stage的请求，但总调度数量不超过总限制
                forced_selected_requests: List[Request] = []
                forced_selected_num_tokens: List[int] = []
                # # 使用全局总限制（例如 self.total_limit，这里你可以根据需求设置）
                total_limit = self.total_limit

                # # 将所有 stage 的请求统一到一个列表中
                all_requests: List[Request] = []
                print(grouped_requests.values())
                for reqs in grouped_requests.values():
                    all_requests.extend(reqs)
                # print(all_requests)

                # 如果队列中顺序无关紧要，直接遍历 all_requests，调度直到达到总限制
                for req in all_requests:
                    if len(forced_selected_requests) > total_limit:
                        break
                    # 如果请求还在队列中，则移除它
                    if req in self._request_queue:
                        self._request_queue.remove(req)
                    self._allocate_request(req)
                    req.advance_stage()
                    print(f"Force-scheduled request {req.id} to stage {req.current_stage}")
                    forced_selected_requests.append(req)
                    forced_selected_num_tokens.append(self._get_request_next_num_tokens(req))
                    

                print("Timeout reached: forcing scheduling of available stage=0 requests.")
                # forced_selected_requests: List[Request] = []
                # forced_selected_num_tokens: List[int] = []
                # # 强制调度：取出所有stage的请求，但每个stage仅调度不超过对应的booking limit数量
                # forced_selected_requests: List[Request] = []
                # forced_selected_num_tokens: List[int] = []
                # # 遍历所有的stage

                # for stage, reqs in grouped_requests.items():
                #     limit = self.nested_booking_limits.get(stage, 0)
                #     # print(limit)
                #     # print(grouped_requests)
                #     # 每个stage最多调度limit个请求
                #     for _ in range(limit):
                #         if not reqs:
                #             break
                #         req = reqs.pop(0)
                #         if req in self._request_queue:
                #             self._request_queue.remove(req)
                #         self._allocate_request(req)
                #         req.advance_stage()
                #         # print(f"Force-scheduled request {req.id} to stage {req.current_stage}")
                #         forced_selected_requests.append(req)
                #         forced_selected_num_tokens.append(self._get_request_next_num_tokens(req))
                # # 更新最后调度时间
                
                if forced_selected_requests:
                    self._last_schedule_time = self._current_time
                    batch = Batch(self._replica_id, forced_selected_requests, forced_selected_num_tokens)
                    # self.on_batch_end(batch)
                    return batch
                else:
                    
                    return None


            # return None  # 如果第一段都不满足，直接返回空
        
        # 选择 Segment1 内各个 stage 的请求，每个 stage 取不超过对应的 limit 数量
        for stage in range(seg1_start, seg1_end + 1):
            
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
        
        # --- Segment2 ---
        seg2_required = self.nested_booking_limits.get(seg2_start, 0)
        if len(grouped_requests.get(seg2_start, [])) >= seg2_required:
            for stage in range(seg2_start, seg2_end + 1):
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
            # Segment2 的起始 stage不足，则不启动 Segment2
            pass
        
        # --- Segment3 ---
        seg3_required = self.nested_booking_limits.get(seg3_start, 0)
        if len(grouped_requests.get(seg3_start, [])) >= seg3_required:
            # 仅在 Segment1 和 Segment2 均已启动的情况下启动 Segment3
            for stage in range(seg3_start, seg3_end + 1):
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
            pass


        
        if selected_requests:
            self._last_schedule_time = self._current_time
            return Batch(self._replica_id, selected_requests, selected_num_tokens)

        else:
            # print("Not enough stage=0 requests and timeout not exceeded. Waiting for more requests.")
            return None
        
        return None

    def on_batch_end(self, batch: Batch) -> None:
        self._num_running_batches -= 1
        for request in batch.requests:
            if request.completed:
                self.free(request.id)
            else:
                self._preempted_requests.append(request)
    
    def is_empty(self) -> bool:
        if self._request_queue:
            return False
        if self._preempted_requests:
            return False
        return True

        
    # def _get_request_next_num_tokens(
    #     self, request: Request, batch_contains_prefill: bool, num_batch_tokens: int
    # ) -> int:
    #     assert not request.completed

    #     if request.is_prefill_complete:
    #         return 1

    #     next_num_tokens = min(
    #         request.num_prefill_tokens - request.num_processed_tokens,
    #         self._config.chunk_size - num_batch_tokens,
    #     )

    #     next_num_tokens = max(0, next_num_tokens)

    #     return next_num_tokens