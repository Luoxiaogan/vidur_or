from math import ceil
from typing import List, Dict, Tuple
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.base_replica_scheduler import BaseReplicaScheduler

class GeneralizedNestedBookingLimitReplicaScheduler(BaseReplicaScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._preempted_requests: List[Request] = []
        self._num_running_batches = 0
        self._sched_batch_count = 0  # 用于 per-stage limit rotation

        self.total_limit = self._config.total_limit

        #self.seg_limit = [100, 30]
        self.seg_limit = [104, 26]

        print("total_limit:", self.total_limit)
        self.total_num_requests = self._config.total_num_requests
        self.force_clear= self._config.force_clear
        if self.force_clear:
            print("会在最后强制清空队列")
        self.all_requests_arrived = False
        self.num_arrival_requests = 0 # 记录到达的请求数
        
        # 保证 prefill 相同，但 decode 和 arrival_rate 可能不同，
        # 并且可能不止三个 type
        self.prompt_types = self._config.prompt_types
        #self.request_count_per_type = {pt["type"]: 0 for pt in self.prompt_types}
        # 由于所有类型的 prefill 相同，这里取第一个即可；并假设 prefill 阶段视为 1 个 stage
        #self.prefill = self.prompt_types[0]["prefill"]
        #print("统一的prefill阶段数:", self.prefill)
        #self.prefill_stage_count = 1
        
        # 计算嵌套 booking limit：返回两个结果
        # 1. nested_booking_limits: 一个字典 mapping 全局 stage index -> 每个 stage 的 limit
        # 2. segments: 一个列表，每个元素记录该 segment 的起始、结束 stage 及每个 stage 的 limit（便于后续判断启动条件）
        self.nested_booking_limits, self.segments = self.calculate_nested_booking_limits()
    
    def add_request(self, request: Request) -> None:
        self._request_queue.append(request)
        self.num_arrival_requests += 1

        #prompt_type = request.prompt_type  # 假设 request 具有 prompt_type 属性
        #if prompt_type in self.request_count_per_type:
            #self.request_count_per_type[prompt_type] += 1
        #else:
            #print(f"Warning: Received request with unknown type '{prompt_type}'")

        if self.num_arrival_requests == self.total_num_requests:
            self.all_requests_arrived = True
            print(f"计划到达个数:{self.total_num_requests}=已到达个数:{self.num_arrival_requests}")
            print("当最后一个request到达时, scheduler里面还剩下的request的数目是:", len(self._request_queue))

            # total_throughput = 0
            # for prompt_type, count in self.request_count_per_type.items():
            #     print(f"Type:{prompt_type}, Count:{count}")
            #     prompt_info = next((pt for pt in self.prompt_types if pt["type"] == prompt_type), None)
            #     if prompt_info:
            #         total_throughput += count * (prompt_info["decode"] + 1)
            #     else:
            #         print(f"Warning: prompt_type '{prompt_type}' not found in self.prompt_types")
            # print("理论上的throughput是:", total_throughput)
    
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
        #seg1_count = self.prefill_stage_count + unique_decodes[0]
        seg1_count = unique_decodes[0] # 这里修改了, 例如decode10次, 那么是从 stage0 到 stage9
        seg1_arrival_sum = sum(pt["arrival_rate"] for pt in self.prompt_types)
        segments.append({"count": seg1_count, "arrival_sum": seg1_arrival_sum})
        
        # 后续每个 segment依次处理额外的 decode 次数
        for i in range(1, len(unique_decodes)):
            seg_count = unique_decodes[i] - unique_decodes[i-1]  # 额外需要处理的 decode 次数
            # 仅考虑 decode 大于上一阈值的类型参与本 segment
            seg_arrival_sum = sum(pt["arrival_rate"] for pt in self.prompt_types if pt["decode"] > unique_decodes[i-1])
            segments.append({"count": seg_count, "arrival_sum": seg_arrival_sum})
        
        # ---- 按 paper 约束分配 per-stage limit ----
        # n_{k+1}/n_k = p_k + seg_margin, 其中 p_k = arrival_sum_{k+1} / arrival_sum_k
        # 从 tl 反推各 segment 的 n_k (per-stage limit)
        seg_margin = self._config.seg_margin

        num_segs = len(segments)
        # 计算每个 segment 间的比率 q_k = p_k + seg_margin
        # q_k 被 clamp 到 (0, 1) 以保证合理性
        ratios = []  # q_1, q_2, ..., q_{m-1}
        for k in range(num_segs - 1):
            p_k = segments[k + 1]["arrival_sum"] / segments[k]["arrival_sum"] if segments[k]["arrival_sum"] > 0 else 0
            q_k = min(p_k + seg_margin, 0.99)  # clamp < 1
            ratios.append(q_k)

        # n_k = n_1 * prod(q_1..q_{k-1})
        # tl = sum_k (n_k * count_k) = n_1 * sum_k (count_k * prod(q_1..q_{k-1}))
        cumulative_ratio = [1.0]  # prod(q_1..q_0) = 1 for seg 0
        for q in ratios:
            cumulative_ratio.append(cumulative_ratio[-1] * q)

        denominator = sum(segments[k]["count"] * cumulative_ratio[k] for k in range(num_segs))
        n_1 = self.total_limit / denominator if denominator > 0 else 0

        # 各 segment 的 per-stage limit (float) 和 seg_total_limit
        n_per_seg = [n_1 * cumulative_ratio[k] for k in range(num_segs)]

        print(f"seg_margin={seg_margin}, n_per_seg={[f'{n:.3f}' for n in n_per_seg]}")
        for k in range(num_segs - 1):
            p_k = segments[k + 1]["arrival_sum"] / segments[k]["arrival_sum"] if segments[k]["arrival_sum"] > 0 else 0
            print(f"  seg {k}->{k+1}: p_k={p_k:.3f}, q_k={ratios[k]:.3f}, n_{k+1}/n_{k}={n_per_seg[k+1]/n_per_seg[k]:.3f}")

        # ---- 整数化分配到各 stage ----
        nested_booking_limits = {}
        segments_info = []
        global_stage = 0
        total_limit_real = 0

        for k, seg in enumerate(segments):
            seg_total_limit_float = n_per_seg[k] * seg["count"]
            seg_total_limit_int = int(round(seg_total_limit_float))

            # 整数分配: base + 余数，保证 max - min <= 1
            base = seg_total_limit_int // seg["count"] if seg["count"] > 0 else 0
            remainder = seg_total_limit_int % seg["count"] if seg["count"] > 0 else 0

            seg_start = global_stage
            for i in range(seg["count"]):
                nested_booking_limits[global_stage] = base + 1 if i < remainder else base
                global_stage += 1

            seg_end = global_stage - 1
            per_stage_max = base + 1 if remainder > 0 else base
            per_stage_min = base

            total_limit_real += seg_total_limit_int

            # n_k: per-stage steady-state throughput (float)
            # n_k_floor: WAIT 触发阈值 (>=floor 就可以开始)
            # n_k_ceil: admission 上限 (最多 admit ceil 个)
            n_k = n_per_seg[k]
            n_k_floor = max(1, int(n_k))
            n_k_ceil = int(ceil(n_k))

            segments_info.append({
                "start": seg_start, "end": seg_end,
                "per_stage_limit": per_stage_max,
                "seg_total_limit": seg_total_limit_int,
                "n_k": n_k, "n_k_floor": n_k_floor, "n_k_ceil": n_k_ceil,
            })
            print(f"  seg {k}: stages {seg_start}-{seg_end}, per_stage: {per_stage_min}-{per_stage_max}, seg_limit: {seg_total_limit_int}, n_k={n_k:.3f} (wait>={n_k_floor}, admit<={n_k_ceil})")

        print(f"设定的总limit: {self.total_limit}, 实际的总limit: {total_limit_real}")

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

        # Entry gate + free internal flow + WAIT
        if not self.all_requests_arrived or True:
            for seg in self.segments:
                seg_start = seg["start"]
                seg_end = seg["end"]
                num_stages = seg_end - seg_start + 1
                budget = seg["seg_total_limit"]
                # Rotation: 严格按 seg_tl 分配 3 or 4
                base_nk = budget // num_stages  # 3
                remainder_nk = budget % num_stages  # 6
                batch_idx = self._sched_batch_count % num_stages
                this_limit = base_nk + 1 if batch_idx < remainder_nk else base_nk

                # WAIT: 两条件满足其一才放该 segment 进 batch
                entry_count = len(grouped_requests.get(seg_start, []))
                occupied_internal = sum(1 for req in self._request_queue
                    if getattr(req, 'current_stage', 0) > seg_start
                    and getattr(req, 'current_stage', 0) <= seg_end)
                total_in_seg = entry_count + occupied_internal
                # WAIT: 两条件满足其一才放该 segment 进 batch (各 seg 独立判断)
                if self._config.wait_gate:
                    seg_full = total_in_seg >= budget
                    entry_ready = entry_count >= this_limit
                    if not seg_full and not entry_ready:
                        continue  # WAIT — 该 seg 冻结，不影响其他 seg

                # Entry: admit this_limit, 受 seg_tl 约束
                remain = max(0, budget - occupied_internal)
                entry_limit = min(this_limit, remain)
                entry_group = grouped_requests.get(seg_start, [])
                count = 0
                while entry_group and count < entry_limit:
                    req = entry_group.pop(0)
                    if req in self._request_queue:
                        self._request_queue.remove(req)
                    self._allocate_request(req)
                    req.advance_stage()
                    selected_requests.append(req)
                    next_num = self._get_request_next_num_tokens(req)
                    selected_num_tokens.append(next_num)
                    count += 1

                # Internal stages: ALL advance freely
                for stage in range(seg_start + 1, seg_end + 1):
                    group = grouped_requests.get(stage, [])
                    for req in list(group):
                        if req in self._request_queue:
                            self._request_queue.remove(req)
                        self._allocate_request(req)
                        req.advance_stage()
                        selected_requests.append(req)
                        next_num = self._get_request_next_num_tokens(req)
                        selected_num_tokens.append(next_num)
        else: 
            # # 新逻辑：所有请求已到达
            # found_segment = False  # 标记是否有至少一个 segment 的起始阶段满足 booking limit
            # for seg in self.segments:
            #     seg_start = seg["start"]
            #     required = self.nested_booking_limits.get(seg_start, 0)
            #     if len(grouped_requests.get(seg_start, [])) >= required:
            #         # 如果该 segment 的起始阶段满足预设条件，则进行调度
            #         found_segment = True
            #         for stage in range(seg["start"], seg["end"] + 1):
            #             limit = self.nested_booking_limits.get(stage, 0)
            #             group = grouped_requests.get(stage, [])
            #             for _ in range(limit):
            #                 if not group:
            #                     break
            #                 req = group.pop(0)
            #                 if req in self._request_queue:
            #                     self._request_queue.remove(req)
            #                 self._allocate_request(req)
            #                 req.advance_stage()
            #                 selected_requests.append(req)
            #                 next_num = self._get_request_next_num_tokens(req)
            #                 selected_num_tokens.append(next_num)
            #     # 对于不满足条件的 segment，不进行处理break

            # if not found_segment:
            #     # 如果所有 segment 的起始阶段都不满足 booking limit，则执行强制清空队列逻辑
                print("所有请求已到达, 但是第一个segment不够, 所以都不能运行了 ,强制清除队列")
                print("此时scheduler里面还剩下的request的数目是:", len(self._request_queue))
                for req in self._request_queue:
                    if req.id in self._allocation_map:
                        self.free(req.id)
                self._request_queue.clear()
                print("已经强制清空, 此时scheduler里面还剩下的request的数目是:", len(self._request_queue))
                return None

        if selected_requests:
            self._sched_batch_count += 1
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

    @property
    def stage_0_queue_length(self) -> int:
        """返回 stage=0（等待 prefill）的请求数"""
        return sum(1 for req in self._request_queue
                   if getattr(req, 'current_stage', 0) == 0)

    # def _get_next_batch(self) -> Batch:
    #     """
    #     调度逻辑：
    #       1. 将上次未完成的请求(preempted)重新归入队列;
    #       2. 按 request.current_stage(全局 stage)将请求分组;
    #       3. 按 segments 顺序依次调度：
    #          - 对于每个 segment, 首先检查该 segment 起始 stage 上的请求数是否达到预设的 booking limit(即 nested_booking_limits[segment.start])
    #          - 只有当前一段已经启动后，后续 segment 才允许启动;
    #          - 对于满足条件的 segment,从该段内每个 stage中各取出不超过预设 limit 数量的请求
    #            并调用 _allocate_request() 以及 req.advance_stage() 使请求进入下一阶段
    #       4. 将选中的请求打包成一个 Batch 返回
        
    #     调度逻辑修改说明：
    #     - 如果 self.all_requests_arrived 为 False,则沿用原有的顺序调度逻辑
    #     - 如果 self.all_requests_arrived 为 True,则逐个检查每个 segment 的起始阶段(seg["start"])是否满足预设的 booking limit
    #         (1) 如果至少有一个 segment 的起始阶段满足条件, 则对所有满足条件的 segment 进行调度
    #             即从该 segment 内各个阶段中各自取出不超过预设 limit 的请求
    #         (2) 如果所有 segment 的起始阶段都不满足预设条件, 则执行强制清空队列的逻辑
    #             打印相关信息, 释放已分配资源, 并清空 _request_queue, 最后返回 None
    #     """
    #     # 将上次未完成的（preempted）请求重新归入队列
    #     for req in self._preempted_requests:
    #         if req not in self._request_queue:
    #             self._request_queue.append(req)
    #     self._preempted_requests.clear()

    #     # 按请求的 current_stage 将请求分组
    #     grouped_requests: Dict[int, List[Request]] = {}
    #     for req in self._request_queue:
    #         stage = getattr(req, 'current_stage', 0)
    #         grouped_requests.setdefault(stage, []).append(req)

    #     selected_requests: List[Request] = []
    #     selected_num_tokens: List[int] = []

    #     # first_segment_satisfied = False 
    #     # first_segment = self.segments[0]
    #     # firts_seg_start = first_segment["start"]
    #     # # required 是第一个限制, 是之前严格的booking limit限制
    #     # required = self.nested_booking_limits.get(firts_seg_start, 0)
    #     # # occupied 是当前在这个segment但不在初始位置的请求的数目, 也是已经被占用的limit
    #     # occupied = sum(1 for req in self._request_queue 
    #     #            if getattr(req, 'current_stage', 0) > first_segment["start"]
    #     #            and getattr(req, 'current_stage', 0)<= first_segment["end"])
    #     # # limit_for_this_segment 是这个segment的limit 
    #     # limit_for_this_segment = first_segment["seg_total_limit"]
    #     # # remain 是剩余的limit 
    #     # remain = limit_for_this_segment - occupied
    #     # stage_0_num = len(grouped_requests.get(firts_seg_start, []))
    #     # #print(f"\nlimit_for_first_segment={limit_for_this_segment},  occupied={occupied},  remain={remain},  required_limit={required},  stage_0_num={stage_0_num}")
    #     # if len(grouped_requests.get(firts_seg_start, [])) >= min(required, remain):
    #     #     first_segment_satisfied = True

    #     # 根据 all_requests_arrived 标识分两种逻辑
    #     # if not self.all_requests_arrived:
    #     #print("\n\n\n")
    #     # if not self.all_requests_arrived or (self.all_requests_arrived and first_segment_satisfied):
    #         # 原有逻辑：依次检查各个 segment，要求前一个 segment 必须满足条件才能启动后续 segment
    #         # 现在修改成了: 要么所有请求还没有到达, 要么已经全部到达但是第一个segment满足了
    #     seg_index = -1
    #     for seg in self.segments:
    #         seg_index += 1
    #         this_seg_limit = self.seg_limit[seg_index]
    #         # seg_start = seg["start"]
    #         # required = self.nested_booking_limits.get(seg_start, 0)
    #         # occupied = sum(1 for req in self._request_queue 
    #         #     if getattr(req, 'current_stage', 0) > seg["start"]
    #         #     and getattr(req, 'current_stage', 0) <= seg["end"])
    #         # limit_for_this_segment = seg["seg_total_limit"]
    #         # remain = limit_for_this_segment - occupied
    #         # print(f"start={seg_start}, end={seg["end"]}, required={required}, occupied={occupied}, remain={remain}, limit_for_this_segment={limit_for_this_segment}, start_num={len(grouped_requests.get(seg_start, []))}")
    #         # if seg == self.segments[-1] and len(grouped_requests.get(seg_start, [])) >= min(required, remain):
    #         #     print(f"一共启动了{seg_num}个segment")
    #         # if len(grouped_requests.get(seg_start, [])) < min(required, remain):
    #         #     # 如果该 segment 的起始阶段请求数不够，则不启动后续 segment
    #         #     #print(f"一共启动了{seg_num-1}个segment")
    #         #     break

    #         #print("\n")
    #         # 对该 segment 内每个阶段调度请求
    #         number = 0
    #         for stage in range(seg["start"]+1, seg["end"] + 1):
    #             limit = self.nested_booking_limits.get(stage, 0)
    #             #if stage == 0:
    #             #    limit -= int(limit*0.4)
    #                 #print("CAUTION! STAGE 0!!!")
    #             #print(f"stage={stage}, limit={limit}, allocated_blocks = {self._config.num_blocks -  self.num_allocated_blocks}")
    #             group = grouped_requests.get(stage, [])
    #             for _ in range(limit):
    #                 if not group:
    #                     break
    #                 req = group.pop(0)
    #                 if req in self._request_queue:
    #                     self._request_queue.remove(req)
    #                 self._allocate_request(req)
    #                 req.advance_stage()
    #                 selected_requests.append(req)
    #                 next_num = self._get_request_next_num_tokens(req)
    #                 selected_num_tokens.append(next_num)
    #                 number += 1
    #         stage = seg["start"]
    #         remain = this_seg_limit - number
    #         limit = min(remain, self.nested_booking_limits.get(stage, 0))
    #         group = grouped_requests.get(stage, [])
    #         for _ in range(limit):
    #             if not group:
    #                 break
    #             req = group.pop(0)
    #             if req in self._request_queue:
    #                 self._request_queue.remove(req)
    #             self._allocate_request(req)
    #             req.advance_stage()
    #             selected_requests.append(req)
    #             next_num = self._get_request_next_num_tokens(req)
    #             selected_num_tokens.append(next_num)
    #     # else: 
    #     #     # # 新逻辑：所有请求已到达
    #     #     # found_segment = False  # 标记是否有至少一个 segment 的起始阶段满足 booking limit
    #     #     # for seg in self.segments:
    #     #     #     seg_start = seg["start"]
    #     #     #     required = self.nested_booking_limits.get(seg_start, 0)
    #     #     #     if len(grouped_requests.get(seg_start, [])) >= required:
    #     #     #         # 如果该 segment 的起始阶段满足预设条件，则进行调度
    #     #     #         found_segment = True
    #     #     #         for stage in range(seg["start"], seg["end"] + 1):
    #     #     #             limit = self.nested_booking_limits.get(stage, 0)
    #     #     #             group = grouped_requests.get(stage, [])
    #     #     #             for _ in range(limit):
    #     #     #                 if not group:
    #     #     #                     break
    #     #     #                 req = group.pop(0)
    #     #     #                 if req in self._request_queue:
    #     #     #                     self._request_queue.remove(req)
    #     #     #                 self._allocate_request(req)
    #     #     #                 req.advance_stage()
    #     #     #                 selected_requests.append(req)
    #     #     #                 next_num = self._get_request_next_num_tokens(req)
    #     #     #                 selected_num_tokens.append(next_num)
    #     #     #     # 对于不满足条件的 segment，不进行处理break

    #     #     # if not found_segment:
    #     #     #     # 如果所有 segment 的起始阶段都不满足 booking limit，则执行强制清空队列逻辑
    #     #         print("所有请求已到达, 但是第一个segment不够, 所以都不能运行了 ,强制清除队列")
    #     #         print("此时scheduler里面还剩下的request的数目是:", len(self._request_queue))
    #     #         for req in self._request_queue:
    #     #             if req.id in self._allocation_map:
    #     #                 self.free(req.id)
    #     #         self._request_queue.clear()
    #     #         print("已经强制清空, 此时scheduler里面还剩下的request的数目是:", len(self._request_queue))
    #     #         return None

    #     if selected_requests:
    #         return Batch(self._replica_id, selected_requests, selected_num_tokens)
    #     return None