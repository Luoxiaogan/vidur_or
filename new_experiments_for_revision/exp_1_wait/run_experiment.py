"""
实验 1: WAIT 算法 - Mean Latency vs Arrival Rate

运行脚本：遍历所有 threshold n × arrival rate λ 组合
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
from config import (
    GPU_TYPE, MODEL_NAME, PREFILL_TOKENS, DECODE_TOKENS,
    THRESHOLDS, ARRIVAL_RATES, NUM_REQUESTS, OUTPUT_DIR
)


def generate_folder_name(total_limit, arrival_rate, num_requests, prefill_tokens, decode_tokens):
    """生成结果文件夹名称"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"n{total_limit}_lambda{arrival_rate}_req{num_requests}_prefill{prefill_tokens}_decode{decode_tokens}_{timestamp}"


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


def run_single_experiment(arrival_rate, total_limit, num_requests, prefill_tokens, decode_tokens, output_dir):
    """运行单次实验"""
    prompt_types = [{
        "type": "type1",
        "prefill": prefill_tokens,
        "decode": decode_tokens,
        "arrival_rate": arrival_rate
    }]

    cmd = [
        "python", "-m", "vidur.main",
        "--replica_config_device", GPU_TYPE,
        "--replica_config_model_name", MODEL_NAME,
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
        "--custom_request_generator_config_num_requests", str(num_requests),
        "--replica_scheduler_config_type", "general_nested_booking_limit",
        "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_booking_limit_scheduler_config_total_limit", str(total_limit),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(num_requests),
        "--general_nested_booking_limit_scheduler_config_force_clear",
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
    ]

    print(f"运行: n={total_limit}, λ={arrival_rate}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(total_limit, arrival_rate, num_requests, prefill_tokens, decode_tokens)
    return copy_simulation_output(output_dir, folder_name)


def run_all_experiments():
    """运行所有 n × rate 组合的实验"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("实验 1: WAIT 算法 - n × λ 双重循环")
    print("=" * 60)
    print(f"THRESHOLDS (n): {THRESHOLDS}")
    print(f"ARRIVAL_RATES (λ): {ARRIVAL_RATES}")
    print(f"NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"PREFILL/DECODE: {PREFILL_TOKENS}/{DECODE_TOKENS}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print("=" * 60)

    total = len(THRESHOLDS) * len(ARRIVAL_RATES)
    count = 0

    for n in THRESHOLDS:
        for rate in ARRIVAL_RATES:
            count += 1
            print(f"\n[{count}/{total}] n={n}, λ={rate}")
            run_single_experiment(rate, n, NUM_REQUESTS, PREFILL_TOKENS, DECODE_TOKENS, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print(f"所有 {total} 个实验完成!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_experiments()
