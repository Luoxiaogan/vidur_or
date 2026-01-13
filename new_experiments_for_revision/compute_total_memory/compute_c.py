#!/usr/bin/env python3
"""
计算 KV Cache 容量 C

使用 vidur 的 MemoryPlanner 计算给定 GPU 和模型配置下的 KV cache 容量。
可提前计算，无需运行模拟。

使用前请激活 conda 环境: conda activate qzh

使用方法:
    python compute_c.py
    python compute_c.py --device a100 --model "meta-llama/Meta-Llama-3-8B" --max-tokens 520
"""

import os
import sys
import argparse
from math import ceil
from dataclasses import dataclass, asdict
import json

# 相对路径导入 vidur（项目根目录）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

# 从 vidur 导入配置和计算模块
from vidur.config.config import ReplicaConfig, CustomRequestGeneratorConfig
from vidur.entities.replica import Replica
from vidur.scheduler.utils.memory_planner import MemoryPlanner


@dataclass
class CapacityResult:
    """KV Cache 容量计算结果"""
    # 配置信息
    device: str
    total_memory_gb: int
    model_name: str
    max_tokens: int
    block_size: int
    memory_margin: float
    tensor_parallel: int
    pipeline_stages: int

    # 模型信息
    num_layers: int
    num_q_heads: int
    num_kv_heads: int
    embedding_dim: int
    attention_head_dim: int

    # 内存信息（GB）
    parameter_memory_gb: float
    available_memory_gb: float
    kv_cache_memory_gb: float
    kv_cache_per_request_mb: float

    # 容量结果
    max_batch_size: int
    max_request_slots: int
    num_blocks: int
    c_tokens: int


def compute_capacity(
    device: str = "a100",
    model_name: str = "meta-llama/Meta-Llama-3-8B",
    max_tokens: int = 4096,
    block_size: int = 16,
    memory_margin: float = 0.1,
    tensor_parallel: int = 1,
    pipeline_stages: int = 1,
) -> CapacityResult:
    """
    计算 KV Cache 容量 C

    使用 vidur 的 MemoryPlanner 进行计算。

    Args:
        device: GPU 类型 (a40, a100, h100)
        model_name: 模型名称
        max_tokens: 单请求最大 token 数
        block_size: KV cache block 大小
        memory_margin: 内存预留比例
        tensor_parallel: Tensor parallel size
        pipeline_stages: Pipeline parallel stages

    Returns:
        CapacityResult: 包含所有计算结果的数据类
    """
    # 创建 ReplicaConfig
    replica_config = ReplicaConfig(
        model_name=model_name,
        device=device,
        memory_margin_fraction=memory_margin,
        tensor_parallel_size=tensor_parallel,
        num_pipeline_stages=pipeline_stages,
    )

    # 创建 GeneratorConfig（提供 max_tokens）
    generator_config = CustomRequestGeneratorConfig(max_tokens=max_tokens)

    # 创建 Replica
    replica = Replica(replica_config, generator_config)

    # 使用 MemoryPlanner 计算
    memory_planner = MemoryPlanner(replica_config, replica)

    # 获取基础结果
    max_batch_size = memory_planner.get_max_batch_size()
    max_request_slots = memory_planner.get_max_request_slots()

    # 计算 num_blocks
    max_blocks_per_sequence = ceil(max_tokens / block_size)
    num_blocks = max_blocks_per_sequence * max_request_slots

    # 计算 C_tokens
    c_tokens = num_blocks * block_size

    # 获取内存详情
    total_memory_gb = replica.total_memory_gb
    available_memory_gb = total_memory_gb * (1 - memory_margin)
    parameter_memory_bytes = memory_planner._get_parameter_memory_per_device()
    parameter_memory_gb = parameter_memory_bytes / (1024 ** 3)
    kv_cache_memory_gb = available_memory_gb - parameter_memory_gb
    kv_cache_per_request_bytes = memory_planner._get_kv_cache_memory_per_device_per_request()
    kv_cache_per_request_mb = kv_cache_per_request_bytes / (1024 ** 2)

    # 模型信息
    model_config = replica_config.model_config
    attention_head_dim = model_config.embedding_dim // model_config.num_q_heads

    return CapacityResult(
        device=device,
        total_memory_gb=total_memory_gb,
        model_name=model_name,
        max_tokens=max_tokens,
        block_size=block_size,
        memory_margin=memory_margin,
        tensor_parallel=tensor_parallel,
        pipeline_stages=pipeline_stages,
        num_layers=model_config.num_layers,
        num_q_heads=model_config.num_q_heads,
        num_kv_heads=model_config.num_kv_heads,
        embedding_dim=model_config.embedding_dim,
        attention_head_dim=attention_head_dim,
        parameter_memory_gb=parameter_memory_gb,
        available_memory_gb=available_memory_gb,
        kv_cache_memory_gb=kv_cache_memory_gb,
        kv_cache_per_request_mb=kv_cache_per_request_mb,
        max_batch_size=max_batch_size,
        max_request_slots=max_request_slots,
        num_blocks=num_blocks,
        c_tokens=c_tokens,
    )


def print_result(result: CapacityResult) -> None:
    """格式化打印计算结果"""
    print("=" * 60)
    print("KV Cache 容量计算结果")
    print("=" * 60)

    print("\n[配置]")
    print(f"  GPU: {result.device} ({result.total_memory_gb} GB)")
    print(f"  模型: {result.model_name}")
    print(f"  max_tokens: {result.max_tokens}")
    print(f"  block_size: {result.block_size}")
    print(f"  memory_margin: {result.memory_margin}")
    print(f"  tensor_parallel: {result.tensor_parallel}")
    print(f"  pipeline_stages: {result.pipeline_stages}")

    print("\n[模型信息]")
    print(f"  num_layers: {result.num_layers}")
    print(f"  num_q_heads: {result.num_q_heads}")
    print(f"  num_kv_heads: {result.num_kv_heads}")
    print(f"  embedding_dim: {result.embedding_dim}")
    print(f"  attention_head_dim: {result.attention_head_dim}")

    print("\n[内存分配]")
    print(f"  可用显存: {result.available_memory_gb:.2f} GB")
    print(f"  模型参数内存: {result.parameter_memory_gb:.2f} GB")
    print(f"  KV Cache 可用: {result.kv_cache_memory_gb:.2f} GB")
    print(f"  每请求 KV Cache: {result.kv_cache_per_request_mb:.2f} MB")

    print("\n[容量结果]")
    print(f"  max_batch_size (C_requests): {int(result.max_batch_size)}")
    print(f"  max_request_slots: {int(result.max_request_slots)}")
    print(f"  num_blocks: {int(result.num_blocks)}")
    print(f"  C_tokens: {int(result.c_tokens)}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="计算 KV Cache 容量 C",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python compute_c.py
  python compute_c.py --device a100 --model "meta-llama/Meta-Llama-3-8B" --max-tokens 260
  python compute_c.py --device h100 --max-tokens 4096 --tp 4
        """
    )

    parser.add_argument(
        "--device",
        type=str,
        default="a100",
        help="GPU 类型 (默认: a100)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="meta-llama/Meta-Llama-3-8B",
        help="模型名称 (默认: meta-llama/Meta-Llama-3-8B)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="单请求最大 token 数 (默认: 4096)"
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=16,
        help="KV cache block 大小 (默认: 16)"
    )
    parser.add_argument(
        "--memory-margin",
        type=float,
        default=0.1,
        help="内存预留比例 (默认: 0.1)"
    )
    parser.add_argument(
        "--tp",
        type=int,
        default=1,
        help="Tensor parallel size (默认: 1)"
    )
    parser.add_argument(
        "--pp",
        type=int,
        default=1,
        help="Pipeline parallel stages (默认: 1)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式"
    )

    args = parser.parse_args()

    result = compute_capacity(
        device=args.device,
        model_name=args.model,
        max_tokens=args.max_tokens,
        block_size=args.block_size,
        memory_margin=args.memory_margin,
        tensor_parallel=args.tp,
        pipeline_stages=args.pp,
    )

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print_result(result)


if __name__ == "__main__":
    main()
