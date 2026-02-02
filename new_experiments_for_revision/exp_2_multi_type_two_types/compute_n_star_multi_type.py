#!/usr/bin/env python3
"""
计算多Type场景下的 KV Cache 容量 C 和 WAIT 算法最优 threshold

支持2个type的场景：
- type_A: prefill=l_0, decode=l_A, arrival_rate比例=p
- type_B: prefill=l_0, decode=l_B (l_B > l_A), arrival_rate比例=q

数学公式：
    Segment1 (decode step 1 到 l_A): 所有请求参与，每step有 n*(p+q) 个请求
    Segment2 (decode step l_A+1 到 l_B): 只有type_B，每step有 n*q 个请求

    M = n*(p+q) * Σ_{i=1}^{l_A}(l_0+i) + n*q * Σ_{i=l_A+1}^{l_B}(l_0+i)

    稳态条件: M = C，求解 n

    threshold_1 = n*(p+q)  (Segment1的per_step_limit)
    threshold_2 = n*q      (Segment2的per_step_limit)
    total_limit = n*(l_A*p + l_B*q)

使用方法:
    python compute_n_star_multi_type.py

    # 或指定参数
    python compute_n_star_multi_type.py --l_A 10 --l_B 20 --p 1 --q 1
"""

import os
import sys
import argparse
from math import ceil, floor
from dataclasses import dataclass, field
from typing import List, Dict

# 相对路径导入 vidur（项目根目录）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

# 从 config.py 导入默认参数
from config import (
    GPU_TYPE,
    MODEL_NAME,
    PREFILL_TOKENS,
    TYPE_A_DECODE,
    TYPE_B_DECODE,
    ARRIVAL_RATE_RATIO_P,
    ARRIVAL_RATE_RATIO_Q,
    MAX_TOKENS,
    MEMORY_MARGIN_FRACTION,
)

# 从 vidur 导入配置和计算模块
from vidur.config.config import ReplicaConfig, CustomRequestGeneratorConfig
from vidur.entities.replica import Replica
from vidur.scheduler.utils.memory_planner import MemoryPlanner


@dataclass
class MultiTypeResult:
    """多Type场景的计算结果"""
    # 配置信息
    device: str
    model_name: str
    total_memory_gb: int
    memory_margin: float

    # 请求配置
    l_0: int           # prefill tokens
    l_A: int           # type_A decode tokens
    l_B: int           # type_B decode tokens
    p: float           # type_A arrival rate ratio
    q: float           # type_B arrival rate ratio

    # 容量
    c_tokens: int

    # Segment 信息
    seg1_steps: int           # Segment1 的 decode steps 数量 (= l_A)
    seg2_steps: int           # Segment2 的 decode steps 数量 (= l_B - l_A)
    sum_seg1: float           # Σ_{i=1}^{l_A}(l_0+i)
    sum_seg2: float           # Σ_{i=l_A+1}^{l_B}(l_0+i)

    # 计算结果
    n_float: float            # n 的精确值
    n_int: int                # n 取整
    threshold_1: float        # Segment1 的 per_step_limit = n*(p+q)
    threshold_2: float        # Segment2 的 per_step_limit = n*q
    seg1_total_limit: float   # Segment1 总 limit = l_A * threshold_1
    seg2_total_limit: float   # Segment2 总 limit = (l_B-l_A) * threshold_2
    total_limit: float        # 总 limit = n*(l_A*p + l_B*q)

    # 验证
    actual_memory: float      # 实际使用的 memory (用 n_int 计算)
    memory_utilization: float # Memory 利用率


def compute_capacity(
    device: str = "a100",
    model_name: str = "meta-llama/Meta-Llama-3-8B",
    max_tokens: int = 4096,
    block_size: int = 16,
    memory_margin: float = 0.1,
    tensor_parallel: int = 1,
    pipeline_stages: int = 1,
) -> tuple:
    """
    使用 vidur 的 MemoryPlanner 计算 KV Cache 容量

    Returns:
        tuple: (c_tokens, total_memory_gb, num_blocks)
    """
    replica_config = ReplicaConfig(
        model_name=model_name,
        device=device,
        memory_margin_fraction=memory_margin,
        tensor_parallel_size=tensor_parallel,
        num_pipeline_stages=pipeline_stages,
    )

    generator_config = CustomRequestGeneratorConfig(max_tokens=max_tokens)
    replica = Replica(replica_config, generator_config)
    memory_planner = MemoryPlanner(replica_config, replica)

    max_request_slots = memory_planner.get_max_request_slots()
    max_blocks_per_sequence = ceil(max_tokens / block_size)
    num_blocks = max_blocks_per_sequence * max_request_slots
    c_tokens = num_blocks * block_size

    return c_tokens, replica.total_memory_gb, num_blocks


def compute_n_star_multi_type(
    c_tokens: int,
    l_0: int,
    l_A: int,
    l_B: int,
    p: float,
    q: float,
) -> Dict:
    """
    计算多Type场景下的最优 threshold

    数学公式（与 compute_c.py 保持一致，i从1开始）：
        M = n*(p+q) * Σ_{i=1}^{l_A}(l_0+i) + n*q * Σ_{i=l_A+1}^{l_B}(l_0+i)
        令 M = C，求解 n

    Args:
        c_tokens: KV Cache 容量（tokens）
        l_0: prefill tokens 数
        l_A: type_A 的 decode tokens 数
        l_B: type_B 的 decode tokens 数 (l_B > l_A)
        p: type_A 的到达率比例
        q: type_B 的到达率比例

    Returns:
        dict: 计算结果
    """
    # 验证输入
    assert l_B > l_A, f"l_B ({l_B}) must be greater than l_A ({l_A})"
    assert p > 0 and q > 0, f"p ({p}) and q ({q}) must be positive"

    # Segment1: decode step 1 到 l_A
    # Σ_{i=1}^{l_A}(l_0+i) = l_A * l_0 + Σ_{i=1}^{l_A}(i)
    #                      = l_A * l_0 + l_A*(l_A+1)/2
    #                      = l_A * (l_0 + (l_A+1)/2)
    sum_seg1 = l_A * (l_0 + (l_A + 1) / 2)

    # Segment2: decode step l_A+1 到 l_B
    # Σ_{i=l_A+1}^{l_B}(l_0+i) = (l_B - l_A) * l_0 + Σ_{i=l_A+1}^{l_B}(i)
    #                          = (l_B - l_A) * l_0 + (l_A+1 + l_B)*(l_B - l_A)/2
    #                          = (l_B - l_A) * (l_0 + (l_A+1+l_B)/2)
    sum_seg2 = (l_B - l_A) * (l_0 + (l_A + 1 + l_B) / 2)

    # M = n*(p+q)*sum_seg1 + n*q*sum_seg2 = C
    # n * [(p+q)*sum_seg1 + q*sum_seg2] = C
    coef = (p + q) * sum_seg1 + q * sum_seg2
    n_float = c_tokens / coef
    n_int = floor(n_float)

    # 计算 threshold
    threshold_1 = n_float * (p + q)  # Segment1 的 per_step_limit
    threshold_2 = n_float * q        # Segment2 的 per_step_limit

    # 计算每个 segment 的 total_limit
    seg1_total_limit = l_A * threshold_1
    seg2_total_limit = (l_B - l_A) * threshold_2

    # 计算总 total_limit
    # total_limit = l_A * n*(p+q) + (l_B-l_A) * n*q
    #             = n * [l_A*(p+q) + (l_B-l_A)*q]
    #             = n * [l_A*p + l_A*q + l_B*q - l_A*q]
    #             = n * [l_A*p + l_B*q]
    total_limit = n_float * (l_A * p + l_B * q)

    # 用 n_int 验证实际 memory
    actual_memory = n_int * (p + q) * sum_seg1 + n_int * q * sum_seg2
    memory_utilization = actual_memory / c_tokens

    return {
        "n_float": n_float,
        "n_int": n_int,
        "threshold_1": threshold_1,
        "threshold_2": threshold_2,
        "seg1_total_limit": seg1_total_limit,
        "seg2_total_limit": seg2_total_limit,
        "total_limit": total_limit,
        "sum_seg1": sum_seg1,
        "sum_seg2": sum_seg2,
        "coef": coef,
        "actual_memory": actual_memory,
        "memory_utilization": memory_utilization,
    }


def compute_full_result(
    device: str,
    model_name: str,
    l_0: int,
    l_A: int,
    l_B: int,
    p: float,
    q: float,
    memory_margin: float,
) -> MultiTypeResult:
    """完整计算流程"""
    max_tokens = l_0 + l_B

    # 计算 C
    c_tokens, total_memory_gb, _ = compute_capacity(
        device=device,
        model_name=model_name,
        max_tokens=max_tokens,
        memory_margin=memory_margin,
    )

    # 计算 n*
    result = compute_n_star_multi_type(c_tokens, l_0, l_A, l_B, p, q)

    return MultiTypeResult(
        device=device,
        model_name=model_name,
        total_memory_gb=total_memory_gb,
        memory_margin=memory_margin,
        l_0=l_0,
        l_A=l_A,
        l_B=l_B,
        p=p,
        q=q,
        c_tokens=c_tokens,
        seg1_steps=l_A,
        seg2_steps=l_B - l_A,
        sum_seg1=result["sum_seg1"],
        sum_seg2=result["sum_seg2"],
        n_float=result["n_float"],
        n_int=result["n_int"],
        threshold_1=result["threshold_1"],
        threshold_2=result["threshold_2"],
        seg1_total_limit=result["seg1_total_limit"],
        seg2_total_limit=result["seg2_total_limit"],
        total_limit=result["total_limit"],
        actual_memory=result["actual_memory"],
        memory_utilization=result["memory_utilization"],
    )


def print_result(result: MultiTypeResult) -> None:
    """格式化打印计算结果"""
    print("=" * 70)
    print("多Type场景 WAIT 算法 Threshold 计算")
    print("=" * 70)

    print("\n[配置]")
    print(f"  GPU: {result.device} ({result.total_memory_gb} GB)")
    print(f"  模型: {result.model_name}")
    print(f"  memory_margin: {result.memory_margin}")

    print("\n[请求配置]")
    print(f"  l_0 (prefill tokens): {result.l_0}")
    print(f"  l_A (type_A decode):  {result.l_A}")
    print(f"  l_B (type_B decode):  {result.l_B}")
    print(f"  p:q (到达率比例):     {result.p}:{result.q}")

    print("\n[Segment 划分]")
    print(f"  Segment1: decode step 1 到 {result.l_A} (共 {result.seg1_steps} steps)")
    print(f"    - 参与类型: type_A + type_B")
    print(f"    - Σ(l_0+i) = {result.sum_seg1:.1f}")
    print(f"  Segment2: decode step {result.l_A+1} 到 {result.l_B} (共 {result.seg2_steps} steps)")
    print(f"    - 参与类型: type_B only")
    print(f"    - Σ(l_0+i) = {result.sum_seg2:.1f}")

    print("\n[容量]")
    print(f"  C_tokens: {result.c_tokens}")

    print("\n[计算结果]")
    print(f"  n (精确值): {result.n_float:.4f}")
    print(f"  n (取整):   {result.n_int}")

    print("\n[Threshold]")
    print(f"  threshold_1 = n*(p+q) = {result.n_float:.4f} * ({result.p}+{result.q}) = {result.threshold_1:.2f}")
    print(f"  threshold_2 = n*q     = {result.n_float:.4f} * {result.q} = {result.threshold_2:.2f}")

    print("\n[Segment Limits]")
    print(f"  seg1_total_limit = l_A * threshold_1 = {result.l_A} * {result.threshold_1:.2f} = {result.seg1_total_limit:.2f}")
    print(f"  seg2_total_limit = (l_B-l_A) * threshold_2 = {result.seg2_steps} * {result.threshold_2:.2f} = {result.seg2_total_limit:.2f}")

    print("\n[Total Limit]")
    print(f"  total_limit = n*(l_A*p + l_B*q)")
    print(f"              = {result.n_float:.4f} * ({result.l_A}*{result.p} + {result.l_B}*{result.q})")
    print(f"              = {result.n_float:.4f} * {result.l_A * result.p + result.l_B * result.q}")
    print(f"              = {result.total_limit:.2f}")

    print("\n[验证] (使用 n_int = {})".format(result.n_int))
    print(f"  实际 Memory: {result.actual_memory:.0f} tokens")
    print(f"  Memory 利用率: {result.memory_utilization * 100:.2f}%")

    # 实验建议
    print("\n[实验建议]")
    total_limit_int = floor(result.total_limit)
    print(f"  推荐 total_limit: {total_limit_int}")
    print(f"  ")
    print(f"  预期 Segment1 limit: {floor(result.seg1_total_limit)}")
    print(f"  预期 Segment2 limit: {floor(result.seg2_total_limit)}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="计算多Type场景下的WAIT算法Threshold")
    parser.add_argument("--device", type=str, default=GPU_TYPE, help="GPU类型")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="模型名称")
    parser.add_argument("--l_0", type=int, default=PREFILL_TOKENS, help="prefill tokens")
    parser.add_argument("--l_A", type=int, default=TYPE_A_DECODE, help="type_A decode tokens")
    parser.add_argument("--l_B", type=int, default=TYPE_B_DECODE, help="type_B decode tokens")
    parser.add_argument("--p", type=float, default=ARRIVAL_RATE_RATIO_P, help="type_A到达率比例")
    parser.add_argument("--q", type=float, default=ARRIVAL_RATE_RATIO_Q, help="type_B到达率比例")
    parser.add_argument("--memory_margin", type=float, default=MEMORY_MARGIN_FRACTION, help="内存预留比例")

    args = parser.parse_args()

    result = compute_full_result(
        device=args.device,
        model_name=args.model,
        l_0=args.l_0,
        l_A=args.l_A,
        l_B=args.l_B,
        p=args.p,
        q=args.q,
        memory_margin=args.memory_margin,
    )

    print_result(result)

    # 返回结果供其他脚本调用
    return result


if __name__ == "__main__":
    main()
