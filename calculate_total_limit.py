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
    # 假设 prompt_types 和 per_stage_limits 已定义
    total_required_per_type = {}

    for pt in prompt_types:
        ptype = pt["type"]
        num_stages = pt["decode"] + 1  # 包括 prefill 阶段
        if ptype not in per_stage_limits:
            raise ValueError(f"Missing per_stage_limit for type {ptype}")
        per_stage_limit = per_stage_limits[ptype]
        total_required_per_type[ptype] = per_stage_limit * num_stages

    total_limit = sum(total_required_per_type.values())
    print(f"知道decode的情况, 计算出的最小 total_limit: {total_limit}")
    print(f"各类型所需总量: {total_required_per_type}\n")
    print("需要注意的是, 这样的 total_limit 正向计算出来的是:")

    # 计算 prompt_rates
    prompt_rates = {pt["type"]: pt["arrival_rate"] * (pt["decode"] + 1) for pt in prompt_types}
    total_rate = sum(prompt_rates.values())

    # 计算 booking_limits_per_type 和 per_stage_limit
    booking_limits_per_type = {}
    for ptype, rate in prompt_rates.items():
        # 动态获取该类型的 decode 数目 + 1
        num_stages = next(pt["decode"] + 1 for pt in prompt_types if pt["type"] == ptype)
        booking_limits_per_type[ptype] = (rate / total_rate) * total_limit
        # 动态计算 per_stage_limit
        per_stage_limit = int(max(booking_limits_per_type[ptype] / num_stages, 1))
        print(f"Type {ptype}: {booking_limits_per_type[ptype]}, per_stage_limit 是 {per_stage_limit}")
    
    return booking_limits_per_type
########################################################################
# 新增函数：根据 total_limit 和 prompt_types 计算每个 segment 的 per-stage-limit
########################################################################
def calculate_nested_booking_limits(total_limit, prompt_types):
    """
    根据 total_limit 和 prompt_types 计算每个 segment 的 per-stage-limit。

    Args:
        total_limit (int): 总的资源限制。
        prompt_types (list): 每个 prompt 类型的配置，形如：
            [
                {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 30},
                {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 20},
                {"type": "type3", "prefill": 10, "decode": 30, "arrival_rate": 10},
            ]

    Returns:
        dict: 每个 segment 的 per-stage-limit, 形如 {segment_index: per_stage_limit}。
    """
    # 提取所有唯一的 decode 值并排序
    unique_decodes = sorted({pt["decode"] for pt in prompt_types})
    print("Unique decodes:", unique_decodes)

    # Segment 划分
    segments = []
    prefill_stage_count = prompt_types[0]["prefill"]  # 假设所有类型的 prefill 相同

    # Segment 0: prefill + 最小 decode
    seg0_count = prefill_stage_count + unique_decodes[0]
    seg0_arrival_sum = sum(pt["arrival_rate"] for pt in prompt_types)
    segments.append({"count": seg0_count, "arrival_sum": seg0_arrival_sum})

    # 后续 segments
    for i in range(1, len(unique_decodes)):
        seg_count = unique_decodes[i] - unique_decodes[i - 1]
        seg_arrival_sum = sum(
            pt["arrival_rate"] for pt in prompt_types if pt["decode"] > unique_decodes[i - 1]
        )
        segments.append({"count": seg_count, "arrival_sum": seg_arrival_sum})

    print("Segments before weight calculation:", segments)

    # 计算各 segment 的权重
    total_weight = sum(seg["count"] * seg["arrival_sum"] for seg in segments)
    print("Total weight:", total_weight)

    # 计算每个 segment 的 per-stage-limit
    nested_booking_limits = {}
    global_stage = 0
    for idx, seg in enumerate(segments):
        seg_weight = seg["count"] * seg["arrival_sum"]
        seg_total_limit = total_limit * (seg_weight / total_weight) if total_weight > 0 else 0
        per_stage_limit = int(max(seg_total_limit / seg["count"], 1)) if seg["count"] > 0 else 0

        # 记录每个 segment 的起始和结束阶段
        seg_start = global_stage
        for _ in range(seg["count"]):
            nested_booking_limits[global_stage] = per_stage_limit
            global_stage += 1
        seg_end = global_stage - 1

        print(
            f"Segment {idx}: "
            f"count={seg['count']}, arrival_sum={seg['arrival_sum']}, "
            f"weight={seg_weight}, total_limit={seg_total_limit}, "
            f"per_stage_limit={per_stage_limit}, "
            f"stages={seg_start}-{seg_end}"
        )
    return nested_booking_limits

########################################################################
# 示例代码
########################################################################
if __name__ == "__main__":
    prompt_types = [
        {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 300},
        {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 200},
        {"type": "type3", "prefill": 10, "decode": 30, "arrival_rate": 100},
    ]
    per_stage_limits = {
        "type1": 6,  # 假设 type1 每个 stage 需要 4
        "type2": 4,  # 假设 type2 每个 stage 需要 2
        "type3": 2,  # 假设 type3 每个 stage 需要 1
    }
    
    calculate_total_limit(prompt_types, per_stage_limits)
    print("\n\n")

    total_limit = 1000
    print("不知道decode的情况, 使用nested booking计算各segment的per-stage-limit:")
    calculate_nested_booking_limits(total_limit, prompt_types)