import os
import json
from utils import run_modified, run_vllm, run_sarathi  # 假设 utils.py 中包含了这些函数

# 定义可变的 arrival_rate 值
arrival_rates = [2000, 4000, 6000, 8000]

# 遍历所有可能的 prompt_types 组合
for i, (ar1, ar2, ar3) in enumerate(zip(arrival_rates, arrival_rates, arrival_rates), start=1):
    # 创建主文件夹路径
    main_folder = os.path.join("/Users/luogan/Code/vidur_or/results_analysis/search_long_decode", f"test{i}")
    os.makedirs(main_folder, exist_ok=True)
    
    # 创建子文件夹
    subfolders = ["modified_booking_limit", "vllm", "sarathi"]
    for subfolder in subfolders:
        os.makedirs(os.path.join(main_folder, subfolder), exist_ok=True)
    
    # 定义当前 prompt_types
    prompt_types = [
        {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": ar1},
        {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": ar2},
        {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": ar3}
    ]

    print(f"\n\nRunning test {i}")
    
    # 保存 prompt_types 到 config.py 中
    config_file_path = os.path.join(main_folder, "config.py")
    with open(config_file_path, 'w') as config_file:
        config_file.write(f"# Configuration file\nprompt_types = {json.dumps(prompt_types)}\n")
    
    # 调用 run_modified
    modified_folder = os.path.join(main_folder, "modified_booking_limit")
    run_modified(
        destination_folder=modified_folder,
        limit_start=100,
        limit_end=2100,
        limit_interval=100,
        num_requests=5000,
        prompt_types=prompt_types
    )
    
    # 调用 run_vllm
    vllm_folder = os.path.join(main_folder, "vllm")
    run_vllm(
        destination_folder=vllm_folder,
        batchsize_start=100,
        batchsize_end=2100,
        batchsize_interval=100,
        num_requests=5000,
        prompt_types=prompt_types
    )
    
    # 调用 run_sarathi
    sarathi_folder = os.path.join(main_folder, "sarathi")
    run_sarathi(
        destination_folder=sarathi_folder,
        batchsize_start=100,
        batchsize_end=2100,
        batchsize_interval=100,
        num_requests=5000,
        prompt_types=prompt_types
    )