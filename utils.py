import os
import glob
from datetime import datetime

def get_latest_simulation_folder(base_path="/Users/luogan/Code/vidur_or/simulator_output"):
    # 获取所有子目录
    subdirs = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d)]
    
    if not subdirs:
        return None  # 如果没有文件夹，返回 None

    def extract_timestamp(folder_path):
        """ 提取时间戳部分并转换为 datetime 对象 """
        folder_name = os.path.basename(folder_path)  # 获取文件夹名
        try:
            # 仅提取 YYYY-MM-DD_HH-MM-SS 部分
            timestamp_str = folder_name.rsplit("-", 1)[0]  # 去掉最后的 -XXXXXX
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
            return dt
        except ValueError:
            print(f"无法解析时间戳: {folder_name}")
            return None  # 解析失败返回 None

    # 解析所有文件夹的时间戳，并筛选有效的
    valid_folders = [(extract_timestamp(d), d) for d in subdirs]
    valid_folders = [(ts, d) for ts, d in valid_folders if ts is not None]

    if not valid_folders:
        return None  # 没有合法的文件夹

    # 按时间排序，选择最新的
    latest_folder = max(valid_folders, key=lambda x: x[0])[1]

    return latest_folder

import os
import glob
import shutil
import csv

def copy_throughput_csv(source_folder, destination_folder, add="", find_batch_size=False):
    """
    复制 source_folder 目录下以 'throughput' 开头的 CSV 文件到 destination_folder，
    并在目标文件名后面添加 add（如果提供）。如果 find_batch_size 为 True，
    则在 plots 文件夹中查找 batch_size 开头的 CSV 文件，读取最后一行的 batch_size 值，
    并将其添加到目标文件名中。

    :param source_folder: 源文件夹路径
    :param destination_folder: 目标文件夹路径
    :param add: 目标文件名后要追加的字符串（不包括扩展名），默认不添加
    :param find_batch_size: 是否查找 batch_size 文件并提取 batch_size 值，默认为 False
    """
    if not os.path.isdir(source_folder):
        print(f"源文件夹不存在: {source_folder}")
        return
    
    if not os.path.isdir(destination_folder):
        print(f"目标文件夹不存在，正在创建: {destination_folder}")
        os.makedirs(destination_folder)

    # 找到所有以 'throughput' 开头的 CSV 文件
    csv_files = glob.glob(os.path.join(source_folder, "throughput*.csv"))
    
    if not csv_files:
        print(f"未找到 throughput 开头的 CSV 文件于: {source_folder}")
        return

    # 由于只有一个符合条件的文件，直接复制
    src_file = csv_files[0]
    
    # 分离文件名和扩展名
    base_name, ext = os.path.splitext(os.path.basename(src_file))
    
    # 目标文件名（添加 _add）
    dst_file_name = f"{base_name}_{add}{ext}" if add else f"{base_name}{ext}"
    
    # 如果 find_batch_size 为 True，查找 batch_size 文件并提取 batch_size 值
    if find_batch_size:
        plots_folder = os.path.join(source_folder, "plots")
        batch_size_files = glob.glob(os.path.join(plots_folder, "batch_size*.csv"))
        
        if batch_size_files:
            batch_size_file = batch_size_files[0]
            with open(batch_size_file, 'r') as f:
                reader = csv.reader(f)
                last_row = None
                for row in reader:
                    last_row = row
                if last_row:
                    batch_size = int(float(last_row[-1]))  # 取最后一行的 batch_size 并转换为整数
                    dst_file_name = f"{base_name}_{add}_batch_size_{batch_size}{ext}" if add else f"{base_name}_batch_size_{batch_size}{ext}"
        else:
            print(f"未找到 batch_size 开头的 CSV 文件于: {plots_folder}")

    dst_file = os.path.join(destination_folder, dst_file_name)

    shutil.copy(src_file, dst_file)
    print(f"已复制到 {dst_file}")

# 示例调用
# copy_throughput_csv("source_folder", "destination_folder", add="example", find_batch_size=True)

def copy_complete_time_csv(source_folder, destination_folder, add=""):
    """
    复制 source_folder/plots 目录下以 'request_completion_time_series' 开头的 CSV 文件到 destination_folder，
    并在目标文件名后面添加 add

    :param source_folder: 源文件夹路径
    :param destination_folder: 目标文件夹路径
    :param add: 目标文件名后要追加的字符串（不包括扩展名），默认不添加
    """
    source_folder = source_folder + "/plots"
    
    if not os.path.isdir(source_folder):
        print(f"源文件夹不存在: {source_folder}")
        return
    
    if not os.path.isdir(destination_folder):
        print(f"目标文件夹不存在，正在创建: {destination_folder}")
        os.makedirs(destination_folder)

    # 找到所有以 'request_completion_time_series' 开头的 CSV 文件
    csv_files = glob.glob(os.path.join(source_folder, "request_completion_time_series*.csv"))
    
    if not csv_files:
        print(f"未找到 request_completion_time_series 开头的 CSV 文件于: {source_folder}")
        return

    # 由于只有一个符合条件的文件，直接复制
    src_file = csv_files[0]
    
    # 分离文件名和扩展名
    base_name, ext = os.path.splitext(os.path.basename(src_file))
    
    # 目标文件名（添加 _add）
    dst_file_name = f"{base_name}_{add}{ext}" if add else f"{base_name}{ext}"

    dst_file = os.path.join(destination_folder, dst_file_name)

    shutil.copy(src_file, dst_file)
    print(f"已复制到 {dst_file}")


def copy_latest_csv(destination_folder, add="", find_batch_size=False):
    """
    复制最新的模拟结果文件夹中的 throughput CSV 文件到目标文件夹，
    并在目标文件名后面添加 add。
    
    :param destination_folder: 目标文件夹路径
    :param add: 目标文件名后要追加的字符串（不包括扩展名），默认不添加
    """
    # 获取最新的模拟结果文件夹
    latest_folder = get_latest_simulation_folder()
    
    if latest_folder is None:
        print("未找到最新的模拟结果文件夹")
        return
    
    # 复制 throughput CSV 文件
    copy_throughput_csv(latest_folder, destination_folder, add=add, find_batch_size=find_batch_size)
    copy_complete_time_csv(latest_folder, destination_folder, add=add)

import subprocess

import subprocess
import json

def run_modified(destination_folder, limit_start, limit_end, limit_interval, num_requests, prompt_types=None):
    if prompt_types is None:
        prompt_types = [
            {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000},
            {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000},
            {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 8000}
        ]

    for limit in range(limit_start, limit_end, limit_interval):
        cmd = [
            "python", "-m", "vidur.main",  # 通过 `-m` 方式运行模块
            "--replica_config_device", "a100",
            "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
            "--cluster_config_num_replicas", "1",
            "--replica_config_tensor_parallel_size", "1",
            "--replica_config_num_pipeline_stages", "1",
            "--request_generator_config_type", "custom",
            "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
            "--custom_request_generator_config_num_requests", str(num_requests),
            "--replica_scheduler_config_type", "modified_booking_limit",
            "--modified_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
            "--modified_booking_limit_scheduler_config_total_num_requests", str(num_requests),
            "--modified_booking_limit_scheduler_config_total_limit", str(limit),
            "--modified_booking_limit_scheduler_config_force_clear",
            "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
            "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
            "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
        ]
        print(f"运行modified: limit={limit}")
        subprocess.run(cmd, check=True)
        print(f"完成modified: limit={limit}\n")
        copy_latest_csv(destination_folder, add=f"limit_{limit}", find_batch_size=True)

def run_nested(destination_folder, limit_start, limit_end, limit_interval, num_requests, prompt_types=None):
    if prompt_types is None:
        prompt_types = [
            {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000},
            {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000},
            {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 8000}
        ]

    for limit in range(limit_start, limit_end, limit_interval):
        cmd = [
            "python", "-m", "vidur.main",  # 通过 `-m` 方式运行模块
            "--replica_config_device", "a100",
            "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
            "--cluster_config_num_replicas", "1",
            "--replica_config_tensor_parallel_size", "1",
            "--replica_config_num_pipeline_stages", "1",
            "--request_generator_config_type", "custom",
            "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
            "--custom_request_generator_config_num_requests", str(num_requests),
            "--replica_scheduler_config_type", "general_nested_booking_limit",
            "--general_nested_booking_limit_scheduler_config_prompt_types", json.dumps(prompt_types),
            "--general_nested_booking_limit_scheduler_config_total_num_requests", str(num_requests),
            "--general_nested_booking_limit_scheduler_config_total_limit", str(limit),
            "--general_nested_booking_limit_scheduler_config_force_clear",
            "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
            "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
            "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
        ]
        print(f"运行nested: limit={limit}")
        subprocess.run(cmd, check=True)
        print(f"完成nested: limit={limit}\n")
        copy_latest_csv(destination_folder, add=f"limit_{limit}", find_batch_size=True)

def run_vllm(destination_folder, batchsize_start, batchsize_end, batchsize_interval, num_requests, prompt_types=None):
    if prompt_types is None:
        prompt_types = [
            {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000},
            {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000},
            {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 8000}
        ]

    for batch_size in range(batchsize_start, batchsize_end, batchsize_interval):
        cmd = [
            "python", "-m", "vidur.main",  # 通过 `-m` 方式运行模块
            "--replica_config_device", "a100",
            "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
            "--cluster_config_num_replicas", "1",
            "--replica_config_tensor_parallel_size", "1",
            "--replica_config_num_pipeline_stages", "1",
            "--request_generator_config_type", "custom",
            "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
            "--custom_request_generator_config_num_requests", str(num_requests),
            "--replica_scheduler_config_type", "vllm",
            "--vllm_scheduler_config_batch_size_cap", str(batch_size),
            "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
            "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
            "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
        ]
        print(f"运行vllm: batch_size ={batch_size}")
        # 启动进程并等待完成
        subprocess.run(cmd, check=True)
        print(f"完成vllm: batch_size ={batch_size}\n")
        copy_latest_csv(destination_folder, add=f"batch_size_{batch_size}", find_batch_size=False)

def run_sarathi(destination_folder, batchsize_start, batchsize_end, batchsize_interval, num_requests, prompt_types=None):
    if prompt_types is None:
        prompt_types = [
            {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000},
            {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000},
            {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 8000}
        ]

    for batch_size in range(batchsize_start, batchsize_end, batchsize_interval):
        cmd = [
            "python", "-m", "vidur.main",  # 通过 `-m` 方式运行模块
            "--replica_config_device", "a100",
            "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
            "--cluster_config_num_replicas", "1",
            "--replica_config_tensor_parallel_size", "1",
            "--replica_config_num_pipeline_stages", "1",
            "--request_generator_config_type", "custom",
            "--custom_request_generator_config_prompt_types", json.dumps(prompt_types),
            "--custom_request_generator_config_num_requests", str(num_requests),
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_batch_size_cap", str(batch_size),
            "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
            "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
            "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "16384"
        ]
        print(f"运行sarathi: batch_size ={batch_size}")
        # 启动进程并等待完成
        subprocess.run(cmd, check=True)
        print(f"完成sarathi: batch_size ={batch_size}\n")
        copy_latest_csv(destination_folder, add=f"batch_size_{batch_size}", find_batch_size=False)