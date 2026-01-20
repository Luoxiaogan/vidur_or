"""
vLLM PD 分离调度器实验（多 Type）

运行脚本：测试 VLLMPDSeparatedReplicaScheduler 调度器
- 无 Watermark
- restart 时保持 is_prefill_complete=True
- 多 type 请求混合
"""

import json
import os
import sys
import shutil
import subprocess
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from utils import get_latest_simulation_folder
from config import (
    GPU_TYPE, MODEL_NAME, NUM_REQUESTS, OUTPUT_DIR,
    MAX_TOKENS, MEMORY_MARGIN_FRACTION, BATCH_SIZE_CAP,
    BLOCK_SIZE, WATERMARK_BLOCKS_FRACTION, MAX_TOKENS_IN_BATCH,
    PROMPT_TYPES, SEED
)
from plot_batch_scheduling import plot_batch_scheduling_metrics


def generate_folder_name():
    """生成结果文件夹名称"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    types_str = "_".join([f"{pt['type']}_p{pt['prefill']}_d{pt['decode']}" for pt in PROMPT_TYPES])
    return f"vllm_pd_multi_{types_str}_req{NUM_REQUESTS}_{timestamp}"


def copy_simulation_output(folder_name):
    """复制最新的 simulator_output 文件夹到指定目录"""
    latest_folder = get_latest_simulation_folder()
    if latest_folder is None:
        print("未找到最新的模拟结果文件夹")
        return None

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dest_path = os.path.join(OUTPUT_DIR, folder_name)

    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    shutil.copytree(latest_folder, dest_path)
    print(f"已复制结果到: {dest_path}")
    return dest_path


def run_experiment():
    """运行 vLLM PD 分离调度器实验"""
    cmd = [
        "python", "-m", "vidur.main",
        "--replica_config_device", GPU_TYPE,
        "--replica_config_model_name", MODEL_NAME,
        "--replica_config_memory_margin_fraction", str(MEMORY_MARGIN_FRACTION),
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "pd_separated",
        "--p_d_separated_request_generator_config_num_requests", str(NUM_REQUESTS),
        "--p_d_separated_request_generator_config_prompt_types", json.dumps(PROMPT_TYPES),
        "--p_d_separated_request_generator_config_seed", str(SEED),
        "--replica_scheduler_config_type", "vllm_pd_separated",
        "--vllm_p_d_separated_scheduler_config_batch_size_cap", str(BATCH_SIZE_CAP),
        "--vllm_p_d_separated_scheduler_config_block_size", str(BLOCK_SIZE),
        "--vllm_p_d_separated_scheduler_config_watermark_blocks_fraction", str(WATERMARK_BLOCKS_FRACTION),
        "--vllm_p_d_separated_scheduler_config_max_tokens_in_batch", str(MAX_TOKENS_IN_BATCH),
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384",
        "--metrics_config_keep_individual_batch_metrics"
    ]

    print("=" * 60)
    print("vLLM PD 分离调度器实验（多 Type）")
    print("=" * 60)
    print(f"PROMPT_TYPES: {PROMPT_TYPES}")
    print(f"NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"BATCH_SIZE_CAP: {BATCH_SIZE_CAP}")
    print(f"WATERMARK_BLOCKS_FRACTION: {WATERMARK_BLOCKS_FRACTION}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print("=" * 60)

    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    folder_name = generate_folder_name()
    result_path = copy_simulation_output(folder_name)

    # 绘制 batch scheduling metrics 图表
    if result_path:
        plot_batch_scheduling_metrics(result_path)

    print("\n" + "=" * 60)
    print("实验完成!")
    if result_path:
        print(f"结果保存在: {result_path}")
    print("=" * 60)

    return result_path


if __name__ == "__main__":
    run_experiment()
