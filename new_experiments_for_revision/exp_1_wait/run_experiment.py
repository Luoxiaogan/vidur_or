"""
实验 1: WAIT 算法 - Mean Latency vs Arrival Rate

运行脚本：固定 threshold n，变化 arrival rate λ

使用 custom 请求生成器 + general_nested_booking_limit 调度器（单一类型时退化为 WAIT）
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from utils import get_latest_simulation_folder

# 实验配置
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# 单一类型请求配置
PREFILL_TOKENS = 60
DECODE_TOKENS = 200

# Booking Limit threshold (固定)
TOTAL_LIMIT = 100  # 需要根据实际情况调整

# 请求数量
NUM_REQUESTS = 2000

# Arrival Rate 范围 (qps)
ARRIVAL_RATES = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")


def generate_folder_name(
    total_limit: int,
    arrival_rate: float,
    num_requests: int,
    prefill_tokens: int,
    decode_tokens: int
) -> str:
    """
    根据实验参数生成文件夹名称

    格式: n{n}_lambda{λ}_req{num}_prefill{prefill}_decode{decode}_{date}_{time}
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"n{total_limit}_lambda{arrival_rate}_req{num_requests}_prefill{prefill_tokens}_decode{decode_tokens}_{timestamp}"


def copy_simulation_output(output_dir: str, folder_name: str) -> str:
    """
    复制最新的 simulator_output 文件夹到指定目录

    Args:
        output_dir: 目标目录
        folder_name: 目标文件夹名称

    Returns:
        复制后的完整路径
    """
    latest_folder = get_latest_simulation_folder()
    if latest_folder is None:
        print("未找到最新的模拟结果文件夹")
        return None

    os.makedirs(output_dir, exist_ok=True)
    dest_path = os.path.join(output_dir, folder_name)

    # 如果目标已存在，先删除
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    # 复制整个文件夹
    shutil.copytree(latest_folder, dest_path)
    print(f"已复制结果到: {dest_path}")

    return dest_path


def run_wait_single_rate(
    arrival_rate: float,
    total_limit: int,
    num_requests: int,
    prefill_tokens: int,
    decode_tokens: int,
    output_dir: str
) -> str:
    """
    运行单次 WAIT 算法实验

    Args:
        arrival_rate: 到达率 (qps)
        total_limit: Booking Limit 的 threshold n
        num_requests: 请求总数
        prefill_tokens: Prefill token 数
        decode_tokens: Decode token 数
        output_dir: 输出目录

    Returns:
        结果文件夹路径
    """
    # 单一类型请求 - arrival_rate 用作 Poisson 过程的总到达率
    prompt_types = [
        {
            "type": "type1",
            "prefill": prefill_tokens,
            "decode": decode_tokens,
            "arrival_rate": arrival_rate
        }
    ]

    cmd = [
        "python", "-m", "vidur.main",
        "--replica_config_device", GPU_TYPE,
        "--replica_config_model_name", MODEL_NAME,
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        # 请求生成配置 - 使用 custom 生成器
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
        "--custom_request_generator_config_num_requests", str(num_requests),
        # 调度器配置 - 使用 general_nested_booking_limit (单一类型时退化为 WAIT)
        "--replica_scheduler_config_type", "general_nested_booking_limit",
        "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_booking_limit_scheduler_config_total_limit", str(total_limit),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(num_requests),
        "--general_nested_booking_limit_scheduler_config_force_clear",
        # 执行时间预测器配置
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
    ]

    print(f"运行 WAIT: n={total_limit}, λ={arrival_rate}, req={num_requests}, prefill={prefill_tokens}, decode={decode_tokens}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    print(f"完成 WAIT: λ={arrival_rate}")

    # 生成文件夹名称并复制结果
    folder_name = generate_folder_name(
        total_limit=total_limit,
        arrival_rate=arrival_rate,
        num_requests=num_requests,
        prefill_tokens=prefill_tokens,
        decode_tokens=decode_tokens
    )

    result_path = copy_simulation_output(output_dir, folder_name)
    return result_path


def run_all_experiments(
    arrival_rates: list = None,
    total_limit: int = TOTAL_LIMIT,
    num_requests: int = NUM_REQUESTS,
    prefill_tokens: int = PREFILL_TOKENS,
    decode_tokens: int = DECODE_TOKENS,
    output_dir: str = OUTPUT_DIR
):
    """
    运行所有 arrival rate 的实验
    """
    if arrival_rates is None:
        arrival_rates = ARRIVAL_RATES

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("实验 1: WAIT 算法 - Mean Latency vs Arrival Rate")
    print("=" * 60)
    print(f"GPU: {GPU_TYPE}")
    print(f"Model: {MODEL_NAME}")
    print(f"Prefill tokens: {prefill_tokens}")
    print(f"Decode tokens: {decode_tokens}")
    print(f"Total limit (threshold n): {total_limit}")
    print(f"Num requests: {num_requests}")
    print(f"Arrival rates: {arrival_rates}")
    print(f"Output dir: {output_dir}")
    print("=" * 60)

    result_paths = []
    for rate in arrival_rates:
        result_path = run_wait_single_rate(
            arrival_rate=rate,
            total_limit=total_limit,
            num_requests=num_requests,
            prefill_tokens=prefill_tokens,
            decode_tokens=decode_tokens,
            output_dir=output_dir
        )
        result_paths.append(result_path)
        print()

    print("=" * 60)
    print("所有实验完成!")
    print(f"结果保存在: {output_dir}")
    print("生成的文件夹:")
    for path in result_paths:
        if path:
            print(f"  - {os.path.basename(path)}")
    print("=" * 60)

    return result_paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WAIT 算法实验: Mean Latency vs Arrival Rate")
    parser.add_argument("--rates", type=float, nargs="+", default=ARRIVAL_RATES,
                        help="Arrival rates to test (qps)")
    parser.add_argument("--limit", type=int, default=TOTAL_LIMIT,
                        help="Booking limit threshold n")
    parser.add_argument("--num_requests", type=int, default=NUM_REQUESTS,
                        help="Number of requests per experiment")
    parser.add_argument("--prefill", type=int, default=PREFILL_TOKENS,
                        help="Prefill tokens")
    parser.add_argument("--decode", type=int, default=DECODE_TOKENS,
                        help="Decode tokens")
    parser.add_argument("--output_dir", type=str, default=OUTPUT_DIR,
                        help="Output directory for results")

    args = parser.parse_args()

    run_all_experiments(
        arrival_rates=args.rates,
        total_limit=args.limit,
        num_requests=args.num_requests,
        prefill_tokens=args.prefill,
        decode_tokens=args.decode,
        output_dir=args.output_dir
    )
