#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from typing import List, Dict, Tuple

########################################################################
# 原来的函数：根据各类型的 per_stage_limit 计算总的 total_limit
########################################################################
def calculate_total_limit(prompt_types: List[Dict], per_stage_limits: Dict) -> Tuple[int, Dict]:
    """
    计算最小 total_limit 以满足给定的 per_stage_limit（按类型计算）
    :param prompt_types: 每个字典包含 'type', 'decode'（代表 decode 阶段数）以及 'arrival_rate'
    :param per_stage_limits: Dict，key 为 prompt type，value 为该类型每个 stage 所需的 limit
    :return: (最小 total_limit, 各类型所需的总量字典)
    """
    total_required_per_type = {}

    for pt in prompt_types:
        ptype = pt["type"]
        num_stages = pt["decode"] + 1  # 包括 prefill 阶段
        if ptype not in per_stage_limits:
            raise ValueError(f"Missing per_stage_limit for type {ptype}")
        per_stage_limit = per_stage_limits[ptype]
        total_required_per_type[ptype] = per_stage_limit * num_stages

    total_limit = sum(total_required_per_type.values())
    return total_limit, total_required_per_type

########################################################################
# 新的函数：根据新的调度器逻辑（按 segment 给定每个 stage 的 limit）计算 total_limit
########################################################################
def calculate_total_limit_new(prompt_types: List[Dict],
                              per_stage_limits_new: List[int],
                              prefill_stage_count: int = 1) -> Tuple[int, List[int], List[Dict]]:
    """
    计算新的最小 total_limit 以满足每个 segment 给定的 per_stage_limit（按 segment 顺序给出）。
    
    调度器中，每个 segment 的 computed per_stage_limit 计算公式为：
        computed_limit = int(max(total_limit * seg_arrival_sum / total_weight, 1))
    其中 total_weight = sum(seg["count"] * seg["arrival_sum"]) over all segments，
    seg_arrival_sum 是该 segment 中参与计算的 arrival_rate 之和，
    seg["count"] 为该 segment 包含的 stage 数。
    
    要使 computed_limit >= desired（即用户在 per_stage_limits_new 中给定的目标值），
    则需要满足：
         total_limit >= desired * total_weight / seg_arrival_sum   （对于 desired > 1时，否则下限为 1）
    
    由于 prompt_types 中每个类型的 arrival_rate 决定了各 segment 的 arrival_sum，
    第一段、第二段、第三段的 arrival_sum 分别为 60, 30, 10（示例），
    因此理想的 per_stage_limits_new 应该与 60:30:10 成正比（例如 [6, 3, 1] 或 [4, 2, ⅔] 等）。
    
    本函数要求传入的 per_stage_limits_new 必须满足：
      1. 从左到右非递增（即第一段期望不低于后续段）。
      2. 各段目标值与对应的 seg["arrival_sum"] 成正比，即
            per_stage_limits_new[i] / seg[i]["arrival_sum"] 近似相同，
         否则抛出异常。
    
    :param prompt_types: 每个字典包含 'type', 'prefill', 'decode' 和 'arrival_rate'
    :param per_stage_limits_new: List，按 segment 顺序给出每个 segment 所要求的每个 stage limit，
                                 理想比例应为 [seg1_arrival_sum, seg2_arrival_sum, ...]（例如 60:30:10）
    :param prefill_stage_count: int，prefill 阶段对应的 stage 数量（默认为1）
    :return: (最小 total_limit, 每个 segment 对 total_limit 的要求列表, segments 信息列表)
    """
    # 根据调度器逻辑计算 segments
    unique_decodes = sorted({pt["decode"] for pt in prompt_types})
    segments = []
    # 第一段：prefill 阶段（数量 prefill_stage_count）加上最小 decode 值对应的阶段数
    seg1_count = prefill_stage_count + unique_decodes[0]
    seg1_arrival_sum = sum(pt["arrival_rate"] for pt in prompt_types)
    segments.append({"count": seg1_count, "arrival_sum": seg1_arrival_sum})
    
    # 后续段：每一段处理额外的 decode 数
    for i in range(1, len(unique_decodes)):
        seg_count = unique_decodes[i] - unique_decodes[i-1]
        seg_arrival_sum = sum(pt["arrival_rate"] for pt in prompt_types if pt["decode"] > unique_decodes[i-1])
        segments.append({"count": seg_count, "arrival_sum": seg_arrival_sum})
    
    # 检查 per_stage_limits_new 的长度必须与 segments 数量一致
    if len(per_stage_limits_new) != len(segments):
        raise ValueError("per_stage_limits_new 的长度必须与计算出的 segments 数量一致。")
    
    # 检查从左到右是否非递增
    for i in range(len(per_stage_limits_new) - 1):
        if per_stage_limits_new[i] < per_stage_limits_new[i + 1]:
            raise ValueError("per_stage_limits_new 必须从左到右非递增，即第一段的目标 limit 应不低于后续各段。")
    
    # 计算各 segment 的比例因子：期望值 / seg_arrival_sum
    ratios = [per_stage_limits_new[i] / segments[i]["arrival_sum"] for i in range(len(segments))]
    # 允许一个很小的浮点误差
    eps = 1e-6
    if max(ratios) - min(ratios) > eps:
        expected = [segments[i]["arrival_sum"] for i in range(len(segments))]
        raise ValueError(f"per_stage_limits_new 必须与各 segment 的 arrival_sum 成正比，"
                         f"理想比例应为：{expected}，而目前比例为：{ratios}")
    
    # 计算 total_weight = Σ( seg["count"] * seg["arrival_sum"] )
    total_weight = sum(seg["count"] * seg["arrival_sum"] for seg in segments)
    
    # 对每个 segment，根据公式要求 total_limit >= desired * total_weight / seg_arrival_sum
    required_total_limits = []
    for i, seg in enumerate(segments):
        desired = per_stage_limits_new[i]
        if desired > 1:
            required_T = math.ceil(desired * total_weight / seg["arrival_sum"])
        else:
            required_T = 1
        required_total_limits.append(required_T)
    
    total_limit_new = max(required_total_limits) if required_total_limits else 1
    return total_limit_new, required_total_limits, segments

########################################################################
# 示例代码：输入 prompt_types、per_stage_limits（按类型） 和 per_stage_limits_new（按 segment 顺序）
########################################################################
if __name__ == "__main__":
    prompt_types = [
        {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 30},
        {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 20},
        {"type": "type3", "prefill": 10, "decode": 30, "arrival_rate": 10},
    ]
    per_stage_limits = {
        "type1": 4,  # 假设 type1 每个 stage 需要 4
        "type2": 2,  # 假设 type2 每个 stage 需要 2
        "type3": 1,  # 假设 type3 每个 stage 需要 1
    }
    # 这里理想的比例应该与各 segment 的 arrival_sum 成正比，即 [60, 30, 10]，
    # 所以一个符合要求的示例为 [6, 3, 1]（注意：6:3:1 == 60:30:10）
    per_stage_limits_new = [12, 6, 2]
    
    total_limit, total_required_per_type = calculate_total_limit(prompt_types, per_stage_limits)
    print("==============================================")
    print(f"【原函数】计算出的最小 total_limit: {total_limit}")
    print(f"各类型所需总量: {total_required_per_type}")
    
    total_limit_new, required_limits_list, segments_info = calculate_total_limit_new(prompt_types, per_stage_limits_new)
    print("==============================================")
    print(f"【新函数】计算出的最小 total_limit: {total_limit_new}")
    print(f"每个 segment 对 total_limit 的要求: {required_limits_list}")
    print(f"Segments 信息: {segments_info}")
