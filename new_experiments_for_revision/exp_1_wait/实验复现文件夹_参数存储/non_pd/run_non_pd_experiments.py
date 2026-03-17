#!/usr/bin/env python3
"""
非PD分离实验: WAIT (rate, total_limit) + vLLM + Sarathi

所有参数硬编码在 main() 中
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
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


def build_common_args(config):
    """构建公共命令行参数"""
    prompt_types = [{
        "type": "type1",
        "prefill": config["prefill_tokens"],
        "decode": config["decode_tokens"],
        "arrival_rate": config["arrival_rate"]
    }]

    return [
        "python", "-m", "vidur.main",
        "--replica_config_device", config["gpu_type"],
        "--replica_config_model_name", config["model_name"],
        "--replica_config_memory_margin_fraction", str(config["memory_margin_fraction"]),
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_max_tokens", str(config["max_tokens"]),
        "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
        "--custom_request_generator_config_num_requests", str(config["num_requests"]),
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
        "--metrics_config_keep_individual_batch_metrics"
    ], prompt_types


def run_wait_experiment(config, arrival_rate, total_limit, output_dir):
    """运行 WAIT 实验"""
    config["arrival_rate"] = arrival_rate
    common_args, prompt_types = build_common_args(config)

    scheduler_args = [
        "--replica_scheduler_config_type", "general_nested_booking_limit",
        "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_booking_limit_scheduler_config_total_limit", str(total_limit),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(config["num_requests"]),
        "--general_nested_booking_limit_scheduler_config_force_clear",
    ]

    cmd = common_args + scheduler_args
    print(f"  运行 WAIT: rate={arrival_rate}, total_limit={total_limit}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(arrival_rate, config["num_requests"], config["prefill_tokens"], config["decode_tokens"])
    return copy_simulation_output(output_dir, folder_name)


def run_vllm_experiment(config, arrival_rate, vllm_config, output_dir):
    """运行 vLLM 实验"""
    config["arrival_rate"] = arrival_rate
    common_args, _ = build_common_args(config)

    scheduler_args = [
        "--replica_scheduler_config_type", "vllm",
        "--vllm_scheduler_config_max_tokens_in_batch", str(vllm_config["max_tokens_in_batch"]),
        "--vllm_scheduler_config_batch_size_cap", str(vllm_config["batch_size_cap"]),
    ]

    cmd = common_args + scheduler_args
    print(f"  运行 vLLM: rate={arrival_rate}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(arrival_rate, config["num_requests"], config["prefill_tokens"], config["decode_tokens"])
    return copy_simulation_output(output_dir, folder_name)


def run_sarathi_experiment(config, arrival_rate, sarathi_config, output_dir):
    """运行 Sarathi 实验"""
    config["arrival_rate"] = arrival_rate
    common_args, _ = build_common_args(config)

    scheduler_args = [
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", str(sarathi_config["chunk_size"]),
        "--sarathi_scheduler_config_batch_size_cap", str(sarathi_config["batch_size_cap"]),
    ]

    cmd = common_args + scheduler_args
    print(f"  运行 Sarathi: rate={arrival_rate}")
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
        "num_requests": 60000,
    }

    # WAIT: (rate, total_limit) 组合
    WAIT_EXPERIMENTS = [
        (14, 20),
        (15, 20),
        (16, 40),
        (17, 100),
        (18, 525),
        (19, 725),
        (20, 725),
        (21, 725),
    ]

    # vLLM 配置
    # 注意: max_tokens_in_batch 不能超过 65536，否则执行时间预测器会报 KeyError
    VLLM_CONFIG = {
        "max_tokens_in_batch": 4096,
        "batch_size_cap": 128,
    }
    VLLM_RATES = [14, 15, 16, 17, 18, 19, 20, 21]

    # Sarathi 配置
    # 注意: chunk_size 不能超过 65536，否则执行时间预测器会报 KeyError
    SARATHI_CONFIG = {
        "chunk_size": 4096,
        "batch_size_cap": 128,
    }
    SARATHI_RATES = [14, 15, 16, 17, 18, 19, 20, 21]

    # 输出基础目录
    BASE_OUTPUT_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/non_PD分离_default_baseline_bigger_chunk_4096_sarathi"

    # ============================================================
    # ============ 配置区域结束 ============
    # ============================================================

    total_experiments = len(WAIT_EXPERIMENTS) + len(VLLM_RATES) + len(SARATHI_RATES)
    count = 0
    success_count = 0
    failed_experiments = []  # 记录失败的实验

    print("=" * 60)
    print("非PD分离实验：WAIT + vLLM + Sarathi")
    print("=" * 60)
    print(f"WAIT 实验: {len(WAIT_EXPERIMENTS)} 组")
    print(f"vLLM 实验: {len(VLLM_RATES)} 组")
    print(f"Sarathi 实验: {len(SARATHI_RATES)} 组")
    print(f"总计: {total_experiments} 个实验")
    print(f"输出目录: {BASE_OUTPUT_DIR}")
    print("=" * 60)

    # ============ WAIT 实验 ============
    print(f"\n{'='*60}")
    print("WAIT 实验")
    print(f"{'='*60}")

    for rate, total_limit in WAIT_EXPERIMENTS:
        count += 1
        # 每个 (rate, total_limit) 组合一个子文件夹
        output_dir = os.path.join(BASE_OUTPUT_DIR, "wait", f"rate_{rate}_total_limit_{total_limit}")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n[{count}/{total_experiments}] WAIT: rate={rate}, total_limit={total_limit}")
        try:
            run_wait_experiment(CONFIG.copy(), rate, total_limit, output_dir)
            success_count += 1
        except Exception as e:
            error_msg = f"WAIT(rate={rate}, total_limit={total_limit}): {type(e).__name__}: {e}"
            failed_experiments.append(error_msg)
            print(f"  [失败] {error_msg}")

    # ============ vLLM 实验 ============
    print(f"\n{'='*60}")
    print("vLLM 实验")
    print(f"{'='*60}")

    vllm_output_dir = os.path.join(BASE_OUTPUT_DIR, "vllm")
    os.makedirs(vllm_output_dir, exist_ok=True)

    for rate in VLLM_RATES:
        count += 1
        print(f"\n[{count}/{total_experiments}] vLLM: rate={rate}")
        try:
            run_vllm_experiment(CONFIG.copy(), rate, VLLM_CONFIG, vllm_output_dir)
            success_count += 1
        except Exception as e:
            error_msg = f"vLLM(rate={rate}): {type(e).__name__}: {e}"
            failed_experiments.append(error_msg)
            print(f"  [失败] {error_msg}")

    # ============ Sarathi 实验 ============
    print(f"\n{'='*60}")
    print("Sarathi 实验")
    print(f"{'='*60}")

    sarathi_output_dir = os.path.join(BASE_OUTPUT_DIR, "sarathi")
    os.makedirs(sarathi_output_dir, exist_ok=True)

    for rate in SARATHI_RATES:
        count += 1
        print(f"\n[{count}/{total_experiments}] Sarathi: rate={rate}")
        try:
            run_sarathi_experiment(CONFIG.copy(), rate, SARATHI_CONFIG, sarathi_output_dir)
            success_count += 1
        except Exception as e:
            error_msg = f"Sarathi(rate={rate}): {type(e).__name__}: {e}"
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


if __name__ == "__main__":
    main()
