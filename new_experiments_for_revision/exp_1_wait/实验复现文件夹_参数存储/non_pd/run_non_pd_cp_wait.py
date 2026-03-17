#!/usr/bin/env python3
"""
非PD分离实验: WAIT + Chunked Prefill (GeneralNestedChunked)

只跑 general_nested_chunked 调度器，chunk_size=512
与 run_non_pd_experiments.py 的设置完全相同
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


def run_wait_chunked_experiment(config, arrival_rate, total_limit, chunk_size, output_dir):
    """运行 WAIT + Chunked Prefill 实验 (GeneralNestedChunked)"""
    config["arrival_rate"] = arrival_rate
    common_args, prompt_types = build_common_args(config)

    scheduler_args = [
        "--replica_scheduler_config_type", "general_nested_chunked",
        "--general_nested_chunked_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_chunked_scheduler_config_total_limit", str(total_limit),
        "--general_nested_chunked_scheduler_config_total_num_requests", str(config["num_requests"]),
        "--general_nested_chunked_scheduler_config_chunk_size", str(chunk_size),
        "--general_nested_chunked_scheduler_config_force_clear",
    ]

    cmd = common_args + scheduler_args
    print(f"  运行 WAIT+CP: rate={arrival_rate}, total_limit={total_limit}, chunk_size={chunk_size}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name(arrival_rate, config["num_requests"], config["prefill_tokens"], config["decode_tokens"])
    return copy_simulation_output(output_dir, folder_name)


def main():
    # ============================================================
    # ============ 硬编码配置区域 ============
    # ============================================================

    # 公共配置 (与 run_non_pd_experiments.py 完全相同)
    CONFIG = {
        "gpu_type": "a100",
        "model_name": "meta-llama/Meta-Llama-3-8B",
        "prefill_tokens": 630,
        "decode_tokens": 20,
        "max_tokens": 650,
        "memory_margin_fraction": 0.1,
        "num_requests": 60000,
    }

    # WAIT + Chunked Prefill: (rate, total_limit) 组合 (与 run_non_pd_experiments.py 相同)
    WAIT_CP_EXPERIMENTS = [
        (14, 20),
        (15, 20),
        (16, 40),
        (17, 100),
        (18, 525),
        (19, 725),
        (20, 725),
        (21, 725),
    ]

    # Chunked Prefill 配置
    CHUNK_SIZE = 512

    # 输出基础目录
    BASE_OUTPUT_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/non_PD分离_wait_chunked_prefill"

    # ============================================================
    # ============ 配置区域结束 ============
    # ============================================================

    total_experiments = len(WAIT_CP_EXPERIMENTS)
    count = 0
    success_count = 0
    failed_experiments = []  # 记录失败的实验

    print("=" * 60)
    print("非PD分离实验：WAIT + Chunked Prefill (GeneralNestedChunked)")
    print("=" * 60)
    print(f"WAIT+CP 实验: {len(WAIT_CP_EXPERIMENTS)} 组")
    print(f"Chunk Size: {CHUNK_SIZE}")
    print(f"总计: {total_experiments} 个实验")
    print(f"输出目录: {BASE_OUTPUT_DIR}")
    print("=" * 60)

    # ============ WAIT + Chunked Prefill 实验 ============
    print(f"\n{'='*60}")
    print("WAIT + Chunked Prefill 实验")
    print(f"{'='*60}")

    for rate, total_limit in WAIT_CP_EXPERIMENTS:
        count += 1
        # 每个 (rate, total_limit) 组合一个子文件夹
        output_dir = os.path.join(BASE_OUTPUT_DIR, "wait_cp", f"rate_{rate}_total_limit_{total_limit}")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n[{count}/{total_experiments}] WAIT+CP: rate={rate}, total_limit={total_limit}, chunk_size={CHUNK_SIZE}")
        try:
            run_wait_chunked_experiment(CONFIG.copy(), rate, total_limit, CHUNK_SIZE, output_dir)
            success_count += 1
        except Exception as e:
            error_msg = f"WAIT+CP(rate={rate}, total_limit={total_limit}): {type(e).__name__}: {e}"
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
