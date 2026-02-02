#!/usr/bin/env python3
"""
WAIT 实验 - total_limit=21
复制原有 比较测试_3_1_baseline_use_defaults/wait 的配置，仅修改 total_limit
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

# ============ 配置 ============
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
PREFILL_TOKENS = 630
DECODE_TOKENS = 20
MAX_TOKENS = PREFILL_TOKENS + DECODE_TOKENS  # 650
MEMORY_MARGIN_FRACTION = 0.1
NUM_REQUESTS = 10000

# 关键修改：total_limit = 21
TOTAL_LIMIT = 21

ARRIVAL_RATES = [14, 15, 16, 17, 18, 19, 20]

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "比较测试_3_1_baseline_use_defaults/wait_small_limit")


def generate_folder_name(arrival_rate):
    """生成结果文件夹名称"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"lambda{arrival_rate}_req{NUM_REQUESTS}_prefill{PREFILL_TOKENS}_decode{DECODE_TOKENS}_{timestamp}"


def copy_simulation_output(output_dir, folder_name):
    """复制最新的 simulator_output 文件夹到指定目录"""
    latest_folder = get_latest_simulation_folder()
    if latest_folder is None:
        print("未找到最新的模拟结果文件夹")
        return None

    os.makedirs(output_dir, exist_ok=True)
    dest_path = os.path.join(output_dir, folder_name)

    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    shutil.copytree(latest_folder, dest_path)
    print(f"已复制结果到: {dest_path}")
    return dest_path


def run_single_experiment(arrival_rate):
    """运行单次实验"""
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
        "--general_nested_booking_limit_scheduler_config_total_limit", str(TOTAL_LIMIT),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(NUM_REQUESTS),
        "--general_nested_booking_limit_scheduler_config_force_clear",
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
        "--metrics_config_keep_individual_batch_metrics"
    ]

    print(f"运行: total_limit={TOTAL_LIMIT}, lambda={arrival_rate}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(arrival_rate)
    return copy_simulation_output(OUTPUT_DIR, folder_name)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("WAIT 实验 - total_limit=21")
    print("=" * 60)
    print(f"TOTAL_LIMIT: {TOTAL_LIMIT}")
    print(f"ARRIVAL_RATES: {ARRIVAL_RATES}")
    print(f"NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"PREFILL/DECODE: {PREFILL_TOKENS}/{DECODE_TOKENS}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print("=" * 60)

    total = len(ARRIVAL_RATES)
    for i, rate in enumerate(ARRIVAL_RATES, 1):
        print(f"\n[{i}/{total}] lambda={rate}")
        run_single_experiment(rate)

    print("\n" + "=" * 60)
    print(f"所有 {total} 个实验完成!")
    print(f"结果保存在: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
