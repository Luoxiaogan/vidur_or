#!/usr/bin/env python3
"""
PD分离 WAIT 实验: 遍历 (rates, total_limits) 组合

使用 pd_separated 请求生成器，模拟已完成 Prefill 的请求

目录结构:
    BASE_OUTPUT_DIR/
    └── total_limit_{limit}/
        └── wait/
            └── lambda{rate}_req{num}_prefill{prefill}_decode{decode}_{timestamp}/

这样可以直接用 draw_copy_pd.py 画图，只需修改 SCHEDULER_DIRS:
    SCHEDULER_DIRS = {
        "wait_BS=20": ".../total_limit_20/wait",
        "wait_BS=40": ".../total_limit_40/wait",
    }
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


def generate_folder_name(arrival_rate, num_requests, prefill_tokens, decode_tokens):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"lambda{arrival_rate}_req{num_requests}_prefill{prefill_tokens}_decode{decode_tokens}_{timestamp}"


def copy_simulation_output(output_dir, folder_name):
    latest_folder = get_latest_simulation_folder()
    if latest_folder is None:
        print("  未找到最新的模拟结果文件夹")
        return None

    os.makedirs(output_dir, exist_ok=True)
    dest_path = os.path.join(output_dir, folder_name)

    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    shutil.copytree(latest_folder, dest_path)
    print(f"  已复制结果到: {dest_path}")
    return dest_path


def run_wait_experiment(config, arrival_rate, total_limit, output_dir):
    """运行 WAIT 实验 (PD 分离)"""
    prompt_types = [{
        "type": "type1",
        "prefill": config["prefill_tokens"],
        "decode": config["decode_tokens"],
        "arrival_rate": arrival_rate
    }]

    cmd = [
        "python", "-m", "vidur.main",
        # GPU 和模型配置
        "--replica_config_device", config["gpu_type"],
        "--replica_config_model_name", config["model_name"],
        "--replica_config_memory_margin_fraction", str(config["memory_margin_fraction"]),
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        # PD 分离请求生成器（关键差异）
        "--request_generator_config_type", "pd_separated",
        "--p_d_separated_request_generator_config_num_requests", str(config["num_requests"]),
        "--p_d_separated_request_generator_config_prefill_tokens", str(config["prefill_tokens"]),
        "--p_d_separated_request_generator_config_decode_tokens", str(config["decode_tokens"]),
        "--p_d_separated_request_generator_config_arrival_rate", str(arrival_rate),
        "--p_d_separated_request_generator_config_seed", str(config["random_seed"]),
        # WAIT 调度器配置
        "--replica_scheduler_config_type", "general_nested_booking_limit",
        "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_booking_limit_scheduler_config_total_limit", str(total_limit),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(config["num_requests"]),
        "--general_nested_booking_limit_scheduler_config_force_clear",
        # 执行时间预测器配置
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
        "--metrics_config_keep_individual_batch_metrics"
    ]

    print(f"  运行 WAIT: rate={arrival_rate}, total_limit={total_limit}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(arrival_rate, config["num_requests"], config["prefill_tokens"], config["decode_tokens"])
    return copy_simulation_output(output_dir, folder_name)


def main():
    # ============================================================
    # ============ 硬编码配置区域 ============
    # ============================================================

    # 公共配置
    CONFIG = {
        "gpu_type": "a100",
        "model_name": "meta-llama/Meta-Llama-3-8B",
        "prefill_tokens": 630,
        "decode_tokens": 20,
        "max_tokens": 650,
        "memory_margin_fraction": 0.1,
        "num_requests": 50000,
        "random_seed": 42,
    }

    # 要遍历的 arrival rates
    ARRIVAL_RATES = [50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 360, 370, 380, 390, 400, 410, 420]

    # 要遍历的 total_limit
    TOTAL_LIMITS = [20, 40, 60, 80, 100, 150, 200, 300, 400, 500]

    # 输出基础目录
    BASE_OUTPUT_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/PD分离实验3_统一测试_vllm_default"

    # ============================================================
    # ============ 配置区域结束 ============
    # ============================================================

    total_experiments = len(TOTAL_LIMITS) * len(ARRIVAL_RATES)
    count = 0
    success_count = 0
    failed_experiments = []  # 记录失败的实验

    print("=" * 60)
    print("PD分离 WAIT 实验: (rates × total_limits) 遍历")
    print("=" * 60)
    print(f"请求生成器: pd_separated (已完成 Prefill)")
    print(f"ARRIVAL_RATES: {ARRIVAL_RATES}")
    print(f"TOTAL_LIMITS: {TOTAL_LIMITS}")
    print(f"NUM_REQUESTS: {CONFIG['num_requests']}")
    print(f"PREFILL/DECODE: {CONFIG['prefill_tokens']}/{CONFIG['decode_tokens']}")
    print(f"总计: {total_experiments} 个实验")
    print(f"输出目录: {BASE_OUTPUT_DIR}")
    print("=" * 60)

    for total_limit in TOTAL_LIMITS:
        # 每个 total_limit 一个子文件夹
        limit_dir = os.path.join(BASE_OUTPUT_DIR, f"total_limit_{total_limit}")
        wait_output_dir = os.path.join(limit_dir, "wait")
        os.makedirs(wait_output_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"total_limit = {total_limit}")
        print(f"输出目录: {wait_output_dir}")
        print(f"{'='*60}")

        for rate in ARRIVAL_RATES:
            count += 1
            print(f"\n[{count}/{total_experiments}] total_limit={total_limit}, rate={rate}")
            try:
                run_wait_experiment(CONFIG.copy(), rate, total_limit, wait_output_dir)
                success_count += 1
            except Exception as e:
                error_msg = f"WAIT(rate={rate}, total_limit={total_limit}): {type(e).__name__}: {e}"
                failed_experiments.append(error_msg)
                print(f"  [失败] {error_msg}")

    # ============ 总结 ============
    print("\n" + "=" * 60)
    print("实验总结")
    print("=" * 60)
    print(f"总计: {total_experiments} 个实验")
    print(f"成功: {success_count} 个")
    print(f"失败: {len(failed_experiments)} 个")
    print(f"结果保存在: {BASE_OUTPUT_DIR}")

    if failed_experiments:
        print("\n" + "-" * 60)
        print("失败实验列表:")
        print("-" * 60)
        for i, err in enumerate(failed_experiments, 1):
            print(f"  {i}. {err}")
        print("-" * 60)
    else:
        print("\n所有实验成功完成!")

    print("=" * 60)
    print("\n使用 draw_copy_pd.py 画图时，修改 SCHEDULER_DIRS:")
    print("  SCHEDULER_DIRS = {")
    for limit in TOTAL_LIMITS:
        print(f'      "wait_BS={limit}": "{BASE_OUTPUT_DIR}/total_limit_{limit}/wait",')
    print("  }")


if __name__ == "__main__":
    main()
