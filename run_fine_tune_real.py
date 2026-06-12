import pandas as pd
import matplotlib.pyplot as plt
from utils import run_nested_real_data, run_sarathi_real_data, run_vllm_real_data
import subprocess
from itertools import combinations, chain, product
import shutil
import logging
import os

# 配置日志记录
logging.basicConfig(
    filename='error_log.txt',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 生成所有可能的 prompt_types 组合，强制包含 type5
all_prompt_types = ["type1", "type2", "type3", "type4", "type5"]

def generate_prompt_types_subset():
#     # 强制包含 type5
#     remaining_types = ["type1", "type2", "type3", "type4"]
#     subsets = []
#     # type5 单独存在
#     subsets.append(["type5"])
#     # 类型 2 到 5
#     for r in range(1, 5):  # 因为 type5 必须存在，所以最大长度是 5
#         for subset in combinations(remaining_types, r):
#             combined_subset = list(subset) + ["type5"]
#             subsets.append(combined_subset)
    # return subsets
    return [all_prompt_types]

prompt_type_combinations = generate_prompt_types_subset()
batch_size_list = [64]

# 生成所有可能的 arrival_rate 序列
def generate_possible_arrival_rates(k):
    possible_powers = [2**i for i in range(3, 7)]  # 2,4,8,16,32,64
    arrival_powers = []
    for rates in product(possible_powers, repeat=k):
        valid = True
        current = float('inf')
        for rate in rates:
            if rate > current:
                valid = False
                break
            current = rate
        if valid:
            arrival_powers.append(rates)
    return arrival_powers

# 遍历所有组合并运行代码
results = []

# 映射 type 到 decode 的值
decode_values = {
    "type1": 100,
    "type2": 200,
    "type3": 300,
    "type4": 400,
    "type5": 500
}

for prompt_types_subset in prompt_type_combinations:
    k = len(prompt_types_subset)
    arrival_rates_list = generate_possible_arrival_rates(k)
    
    for arrival_rates in arrival_rates_list:
        # 动态生成 prompt_types，确保 decode = t * 100 并维护 t 和 type 的对应关系
        prompt_types = []
        types_str = '_'.join(prompt_types_subset)
        ar_str = '_'.join(map(str, arrival_rates))
        filename = f"{types_str}_ar_{ar_str}.png"
        d = "./results_plot"
        
        for i, t in enumerate(prompt_types_subset):
            ar = arrival_rates[i]
            # decode 的值为 type 的序号乘以 100
            decode = decode_values.get(t, 0)
            prompt_types.append({
                "type": t,
                "prefill": 60,
                "decode": decode,
                "arrival_rate": ar
            })
        print(prompt_types)
        
        # 计算总 QPS
        # # 实际上这里的prompt_types已经没用了，因为我们是用真实数据
        qps = sum(prompt['arrival_rate'] for prompt in prompt_types)
        print(f"Total QPS: {qps}")

        destination_folder = "./results_analysis/test33/vllm"

        # 尝试运行 VLLM
        try:
            run_vllm_real_data(
                destination_folder=destination_folder,
                batchsize_start=500,
                batchsize_end=600,
                batchsize_interval=100,
                num_requests=4000,
                prompt_types=prompt_types,
                batch_size_list=batch_size_list,
                qps=qps,
                trace_file="./data/processed_traces/sample_2e5_input<200_output<500.csv"
            )
        except Exception as e:
            logging.error(f"Error in run_vllm_real_data with parameters {filename}: {e}")

        destination_folder = "./results_analysis/test33/sarathi"

        # 尝试运行 Sarathi
        try:
            run_sarathi_real_data(
                destination_folder=destination_folder,
                batchsize_start=500,
                batchsize_end=600,
                batchsize_interval=100,
                num_requests=4000,
                prompt_types=prompt_types,
                batch_size_list=batch_size_list,
                qps=qps,
                trace_file="./data/processed_traces/sample_2e5_input<200_output<500.csv"
            )
        except Exception as e:
            logging.error(f"Error in run_sarathi_real_data with parameters {filename}: {e}")

        destination_folder = "./results_analysis/test33/modified_nested"

        # 尝试运行 Modified Nested
        try:
            run_nested_real_data(
                destination_folder=destination_folder,
                limit_start=batch_size_list[0],
                limit_end=batch_size_list[0]+1,
                limit_interval=5,
                num_requests=4000,
                prompt_types=prompt_types,
                qps=qps,
                trace_file="./data/processed_traces/sample_2e5_input<200_output<500.csv"
            )
        except Exception as e:
            logging.error(f"Error in run_nested_real_data with parameters {filename}: {e}")
        
        # 定义文件路径
        # dir = "./results_analysis/test33"  # 假设所有结果文件都保存在这个目录下

        try:
            vllm_df = pd.read_csv(os.path.join(d, 'throughput_vllm.csv'))
            booking_df = pd.read_csv(os.path.join(d, 'throughput_general_nested_booking_limit.csv'))
            sarathi_df = pd.read_csv(os.path.join(d, 'throughput_sarathi.csv'))

            # 设置最大时间
            T = 1700
            vllm_subset = vllm_df[vllm_df['Time (sec)'] <= T].copy()
            sarathi_subset = sarathi_df[sarathi_df['Time (sec)'] <= T].copy()
            booking_subset = booking_df[booking_df['Time (sec)'] <= T].copy()

            # 计算 throughput / time
            vllm_subset['throughput_per_time'] = vllm_subset['throughput'] / vllm_subset['Time (sec)']
            sarathi_subset['throughput_per_time'] = sarathi_subset['throughput'] / sarathi_subset['Time (sec)']
            booking_subset['throughput_per_time'] = booking_subset['throughput'] / booking_subset['Time (sec)']

            # 画图
            plt.figure(figsize=(10, 6))
            plt.plot(vllm_subset['Time (sec)'], vllm_subset['throughput_per_time'], 
                     color='royalblue', linestyle='-', linewidth=1, alpha=0.9, label='vLLM, bs=128')
            plt.plot(sarathi_subset['Time (sec)'], sarathi_subset['throughput_per_time'], 
                     color='crimson', linestyle='-', linewidth=1, alpha=0.9, label='Sarathi, bs=128')
            plt.plot(booking_subset['Time (sec)'], booking_subset['throughput_per_time'], 
                     color='green', linestyle='-', linewidth=1, alpha=0.9, label='Nested, bs=128')
            plt.xlabel('Time (sec)', fontsize=14)
            plt.ylabel('Throughput / Time', fontsize=14)
            plt.legend(frameon=False, fontsize=12)
            plt.grid(True, linestyle=':', alpha=0.7)
            plt.ticklabel_format(axis='x', style='plain')  # 禁用科学计数法
            plt.tight_layout()
            
            # 保存图片并关闭当前图形
            # plt.savefig(os.path.join(dir, filename))
            plt.savefig(d+"/"+filename)
            plt.close()
        except Exception as e:
            logging.error(f"Error in plotting with parameters {filename}: {e}")
        
        # 清理模拟输出文件夹
        try:
            shutil.rmtree('./simulator_output')
        except Exception as e:
            logging.error(f"Error in removing simulator_output folder: {e}")