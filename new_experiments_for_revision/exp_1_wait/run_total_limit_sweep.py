#!/usr/bin/env python3
"""
遍历不同 total_limit 运行 WAIT 实验
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from utils import get_latest_simulation_folder

# ============ 固定配置 ============
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
PREFILL_TOKENS = 630
DECODE_TOKENS = 20
MAX_TOKENS = PREFILL_TOKENS + DECODE_TOKENS
MEMORY_MARGIN_FRACTION = 0.1
NUM_REQUESTS = 10000
ARRIVAL_RATES = [14, 15, 16, 17, 18, 19, 20, 21]

# ============ 要遍历的 total_limit ============
TOTAL_LIMITS = [40, 60, 80, 200]

# ============ 输出基础目录 ============
BASE_OUTPUT_DIR = "./比较测试_3_1_baseline_use_defaults"


def generate_folder_name(arrival_rate):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"lambda{arrival_rate}_req{NUM_REQUESTS}_prefill{PREFILL_TOKENS}_decode{DECODE_TOKENS}_{timestamp}"


def copy_simulation_output(output_dir, folder_name):
    latest_folder = get_latest_simulation_folder()
    if latest_folder is None:
        print("未找到最新的模拟结果文件夹")
        return None

    os.makedirs(output_dir, exist_ok=True)
    dest_path = os.path.join(output_dir, folder_name)

    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    shutil.copytree(latest_folder, dest_path)
    print(f"  已复制结果到: {dest_path}")
    return dest_path


def run_single_experiment(arrival_rate, total_limit, output_dir):
    prompt_types = [{
        "type": "type1",
        "prefill": PREFILL_TOKENS,
        "decode": DECODE_TOKENS,
        "arrival_rate": arrival_rate
    }]

    cmd = [
        "python", "-m", "vidur.main",
        "--replica_config_device", GPU_TYPE,
        "--replica_config_model_name", MODEL_NAME,
        "--replica_config_memory_margin_fraction", str(MEMORY_MARGIN_FRACTION),
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_max_tokens", str(MAX_TOKENS),
        "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
        "--custom_request_generator_config_num_requests", str(NUM_REQUESTS),
        "--replica_scheduler_config_type", "general_nested_booking_limit",
        "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_booking_limit_scheduler_config_total_limit", str(total_limit),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(NUM_REQUESTS),
        "--general_nested_booking_limit_scheduler_config_force_clear",
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
        "--metrics_config_keep_individual_batch_metrics"
    ]

    print(f"  运行: lambda={arrival_rate}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(arrival_rate)
    return copy_simulation_output(output_dir, folder_name)


def main():
    print("=" * 60)
    print("WAIT total_limit 遍历实验")
    print("=" * 60)
    print(f"TOTAL_LIMITS: {TOTAL_LIMITS}")
    print(f"ARRIVAL_RATES: {ARRIVAL_RATES}")
    print(f"NUM_REQUESTS: {NUM_REQUESTS}")
    print("=" * 60)

    total_experiments = len(TOTAL_LIMITS) * len(ARRIVAL_RATES)
    count = 0

    for total_limit in TOTAL_LIMITS:
        output_dir = os.path.join(BASE_OUTPUT_DIR, f"02_28_small_wait_total_limit={total_limit}", "wait")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"total_limit = {total_limit}")
        print(f"输出目录: {output_dir}")
        print(f"{'='*60}")

        for rate in ARRIVAL_RATES:
            count += 1
            print(f"\n[{count}/{total_experiments}] total_limit={total_limit}, lambda={rate}")
            run_single_experiment(rate, total_limit, output_dir)

    print("\n" + "=" * 60)
    print(f"所有 {total_experiments} 个实验完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
