from utils import copy_latest_csv

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/results_analysis/test9__short_decode_high_rate/modified_booking_limit"

# 设置 NUM_REQUESTS 变化范围
for limit in range(420, 620, 20):
    cmd = [
        "python", "-m", "vidur.main",  # 通过 `-m` 方式运行模块
        "--replica_config_device", "a100",
        "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_num_requests", "10000",
        "--replica_scheduler_config_type", "modified_booking_limit",
        "--modified_booking_limit_scheduler_config_total_num_requests", "10000",
        "--modified_booking_limit_scheduler_config_total_limit", str(limit),
        "--modified_booking_limit_scheduler_config_force_clear",
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
    ]

    print(f"运行: limit={limit}")
    
    # 启动进程并等待完成
    subprocess.run(cmd, check=True)
    
    print(f"完成: limit={limit}\n")

    copy_latest_csv(destination_folder, add=f"limit_{limit}", find_batch_size=True)