from utils import copy_latest_csv

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/results_analysis/test10__long_decode_high_rate/sarathi"

# 设置 NUM_REQUESTS 变化范围
for batch_size in range(100, 2200, 100):
    cmd = [
        "python", "-m", "vidur.main",  # 通过 `-m` 方式运行模块
        "--replica_config_device", "a100",
        "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_num_requests", "10000",
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_batch_size_cap", str(batch_size),
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
    ]

    print(f"运行: batch_size ={batch_size}")
    
    # 启动进程并等待完成
    subprocess.run(cmd, check=True)
    
    print(f"完成: batch_size ={batch_size}\n")

    copy_latest_csv(destination_folder, add=f"batch_size_{batch_size}", find_batch_size=False)