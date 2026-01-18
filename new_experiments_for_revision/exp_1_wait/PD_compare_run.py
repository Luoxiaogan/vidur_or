"""
PD 分离场景下 WAIT vs vLLM vs Sarathi 公平比较实验

运行脚本：使用 pd_separated 请求生成器，模拟已完成 Prefill 的请求
"""

import os
import sys
import json
import shutil
import subprocess
import importlib.util
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from utils import get_latest_simulation_folder
from PD_compare_config import (
    GPU_TYPE, MODEL_NAME, PREFILL_TOKENS, DECODE_TOKENS,
    ARRIVAL_RATES, NUM_REQUESTS, OUTPUT_DIR,
    MAX_TOKENS, MEMORY_MARGIN_FRACTION, RANDOM_SEED,
    WAIT_CONFIG, VLLM_CONFIG, SARATHI_CONFIG,
    SCHEDULERS_TO_COMPARE
)


def generate_folder_name(scheduler_name, arrival_rate, num_requests, prefill_tokens, decode_tokens):
    """生成结果文件夹名称"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"lambda{arrival_rate}_req{num_requests}_prefill{prefill_tokens}_decode{decode_tokens}_{timestamp}"


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


def build_common_args(arrival_rate, num_requests):
    """构建公共命令行参数 - 使用 pd_separated 生成器"""
    # prompt_types 仅用于 WAIT 调度器（与 generator 参数保持一致）
    prompt_types = [{
        "type": "type1",
        "prefill": PREFILL_TOKENS,
        "decode": DECODE_TOKENS,
        "arrival_rate": arrival_rate
    }]

    return [
        "python", "-m", "vidur.main",
        "--replica_config_device", GPU_TYPE,
        "--replica_config_model_name", MODEL_NAME,
        "--replica_config_memory_margin_fraction", str(MEMORY_MARGIN_FRACTION),
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        # PD 分离请求生成器（关键差异）
        "--request_generator_config_type", "pd_separated",
        "--p_d_separated_request_generator_config_num_requests", str(num_requests),
        "--p_d_separated_request_generator_config_prefill_tokens", str(PREFILL_TOKENS),
        "--p_d_separated_request_generator_config_decode_tokens", str(DECODE_TOKENS),
        "--p_d_separated_request_generator_config_arrival_rate", str(arrival_rate),
        "--p_d_separated_request_generator_config_seed", str(RANDOM_SEED),
        # 执行时间预测器配置
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
        "--metrics_config_keep_individual_batch_metrics"
    ], prompt_types


def build_wait_args(prompt_types, num_requests):
    """构建 WAIT 调度器参数"""
    return [
        "--replica_scheduler_config_type", "general_nested_booking_limit",
        "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
        "--general_nested_booking_limit_scheduler_config_total_limit", str(WAIT_CONFIG["total_limit"]),
        "--general_nested_booking_limit_scheduler_config_total_num_requests", str(num_requests),
        "--general_nested_booking_limit_scheduler_config_force_clear",
    ]


def build_vllm_args():
    """构建 vLLM 调度器参数"""
    return [
        "--replica_scheduler_config_type", "vllm",
        "--vllm_scheduler_config_max_tokens_in_batch", str(VLLM_CONFIG["max_tokens_in_batch"]),
        "--vllm_scheduler_config_batch_size_cap", str(VLLM_CONFIG["batch_size_cap"]),
    ]


def build_sarathi_args():
    """构建 Sarathi 调度器参数"""
    return [
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", str(SARATHI_CONFIG["chunk_size"]),
        "--sarathi_scheduler_config_batch_size_cap", str(SARATHI_CONFIG["batch_size_cap"]),
    ]


def run_single_experiment(scheduler_name, arrival_rate, num_requests, output_dir):
    """运行单次实验"""
    common_args, prompt_types = build_common_args(arrival_rate, num_requests)

    if scheduler_name == "wait":
        scheduler_args = build_wait_args(prompt_types, num_requests)
    elif scheduler_name == "vllm":
        scheduler_args = build_vllm_args()
    elif scheduler_name == "sarathi":
        scheduler_args = build_sarathi_args()
    else:
        raise ValueError(f"未知的调度器类型: {scheduler_name}")

    cmd = common_args + scheduler_args

    print(f"运行: scheduler={scheduler_name}, lambda={arrival_rate}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    scheduler_output_dir = os.path.join(output_dir, scheduler_name)
    folder_name = generate_folder_name(scheduler_name, arrival_rate, num_requests, PREFILL_TOKENS, DECODE_TOKENS)
    return copy_simulation_output(scheduler_output_dir, folder_name)


def run_comparison():
    """运行所有 scheduler x rate 组合的比较实验"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("PD 分离: WAIT vs vLLM vs Sarathi 公平比较实验")
    print("=" * 60)
    print(f"请求生成器: pd_separated (已完成 Prefill)")
    print(f"SCHEDULERS: {SCHEDULERS_TO_COMPARE}")
    print(f"ARRIVAL_RATES: {ARRIVAL_RATES}")
    print(f"NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"PREFILL/DECODE: {PREFILL_TOKENS}/{DECODE_TOKENS}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print("-" * 60)
    print("调度器配置:")
    print(f"  WAIT: total_limit={WAIT_CONFIG['total_limit']}")
    print(f"  vLLM: max_tokens_in_batch={VLLM_CONFIG['max_tokens_in_batch']}, batch_size_cap={VLLM_CONFIG['batch_size_cap']}")
    print(f"  Sarathi: chunk_size={SARATHI_CONFIG['chunk_size']}, batch_size_cap={SARATHI_CONFIG['batch_size_cap']}")
    print("=" * 60)

    total = len(SCHEDULERS_TO_COMPARE) * len(ARRIVAL_RATES)
    count = 0

    for scheduler in SCHEDULERS_TO_COMPARE:
        print(f"\n{'='*60}")
        print(f"调度器: {scheduler.upper()}")
        print(f"{'='*60}")

        for rate in ARRIVAL_RATES:
            count += 1
            print(f"\n[{count}/{total}] scheduler={scheduler}, lambda={rate}")
            run_single_experiment(scheduler, rate, NUM_REQUESTS, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print(f"所有 {total} 个实验完成!")
    print(f"结果保存在: {OUTPUT_DIR}")
    print("=" * 60)


def run_single_scheduler(scheduler_name):
    """只运行单个调度器的所有实验"""
    if scheduler_name not in SCHEDULERS_TO_COMPARE:
        print(f"未知的调度器: {scheduler_name}")
        print(f"可用的调度器: {SCHEDULERS_TO_COMPARE}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print(f"PD 分离 - 单调度器实验: {scheduler_name.upper()}")
    print("=" * 60)

    total = len(ARRIVAL_RATES)
    for i, rate in enumerate(ARRIVAL_RATES, 1):
        print(f"\n[{i}/{total}] scheduler={scheduler_name}, lambda={rate}")
        run_single_experiment(scheduler_name, rate, NUM_REQUESTS, OUTPUT_DIR)

    print(f"\n{scheduler_name} 的 {total} 个实验完成!")


def load_config_from_file(config_path):
    """动态加载外部配置文件"""
    spec = importlib.util.spec_from_file_location("external_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PD 分离: WAIT vs vLLM vs Sarathi 公平比较实验")
    parser.add_argument("config_file", type=str, nargs="?", default=None,
                        help="外部配置文件路径（可选），覆盖默认配置")
    parser.add_argument("--scheduler", type=str, default=None,
                        help="只运行指定的调度器 (wait/vllm/sarathi)，默认运行所有")
    parser.add_argument("--rate", type=float, default=None,
                        help="只运行指定的 arrival rate，默认运行所有")

    args = parser.parse_args()

    # 如果提供了外部配置文件，覆盖默认配置
    if args.config_file:
        print(f"加载外部配置文件: {args.config_file}")
        ext_cfg = load_config_from_file(args.config_file)
        CONFIG_VARS = [
            "GPU_TYPE", "MODEL_NAME", "PREFILL_TOKENS", "DECODE_TOKENS",
            "ARRIVAL_RATES", "NUM_REQUESTS", "OUTPUT_DIR", "MAX_TOKENS",
            "MEMORY_MARGIN_FRACTION", "RANDOM_SEED",
            "WAIT_CONFIG", "VLLM_CONFIG", "SARATHI_CONFIG", "SCHEDULERS_TO_COMPARE"
        ]
        for var_name in CONFIG_VARS:
            if hasattr(ext_cfg, var_name):
                globals()[var_name] = getattr(ext_cfg, var_name)
        print(f"配置已覆盖: OUTPUT_DIR={OUTPUT_DIR}")

    if args.scheduler and args.rate:
        print(f"运行单个实验: scheduler={args.scheduler}, rate={args.rate}")
        run_single_experiment(args.scheduler, args.rate, NUM_REQUESTS, OUTPUT_DIR)
    elif args.scheduler:
        run_single_scheduler(args.scheduler)
    else:
        run_comparison()
