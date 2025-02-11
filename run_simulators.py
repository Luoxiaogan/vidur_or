import subprocess

def run_test(scheduler_type, num_requests, force_clear=None):
    """ 运行单个调度器的测试 """
    command = [
        "python", "-m", "vidur.main",
        "--replica_config_device", "a100",
        "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
        "--cluster_config_num_replicas", "1",
        "--replica_config_tensor_parallel_size", "1",
        "--replica_config_num_pipeline_stages", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_num_requests", str(num_requests),
        "--replica_scheduler_config_type", scheduler_type,
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
    ]

    if scheduler_type == "booking_limit":
        command.extend([
            "--booking_limit_scheduler_config_total_num_requests", str(num_requests),
            "--booking_limit_scheduler_config_force_clear" if force_clear else ""
        ])
    elif scheduler_type == "general_nested_booking_limit":
        command.extend([
            "--general_nested_booking_limit_scheduler_config_total_num_requests", str(num_requests),
            "--general_nested_booking_limit_scheduler_config_force_clear" if force_clear else ""
        ])
    elif scheduler_type == "vllm":
        pass  # vllm 没有额外参数
    elif scheduler_type == "sarathi":
        pass  # sarathi 没有额外参数

    # 打印并运行命令
    print(f"Running command:\n{' '.join(command)}")
    try:
        subprocess.run(command, check=True)
        print(f"Successfully completed test for {scheduler_type}")
    except subprocess.CalledProcessError as e:
        print(f"Error running command for {scheduler_type}: {e}")

def main():
    # 定义测试配置
    num_requests = 1000

    test_configs = [
        {
            "run_test": False,
            "scheduler_type": "booking_limit",
            "num_requests": num_requests,
            "force_clear": True
        },
        {
            "run_test": True,
            "scheduler_type": "vllm",
            "num_requests": num_requests
        },
        {
            "run_test": True,
            "scheduler_type": "sarathi",
            "num_requests": num_requests
        },
        {
            "run_test": True,
            "scheduler_type": "general_nested_booking_limit",
            "num_requests": num_requests,
            "force_clear": True
        }
    ]

    # 依次运行测试
    for config in test_configs:
        if config["run_test"]:
            print("执行模拟, scheduler_type: ", config["scheduler_type"])
            del config["run_test"]
            run_test(**config)
            print("模拟结束\n\n")

if __name__ == "__main__":
    main()