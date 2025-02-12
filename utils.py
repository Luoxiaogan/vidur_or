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
import shutil
import glob

def copy_throughput_csv(source_folder, destination_folder, add=""):
    """
    复制 source_folder 目录下以 'throughput' 开头的 CSV 文件到 destination_folder，
    并在目标文件名后面添加 add（如果提供）。
    
    :param source_folder: 源文件夹路径
    :param destination_folder: 目标文件夹路径
    :param add: 目标文件名后要追加的字符串（不包括扩展名），默认不添加
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
    dst_file = os.path.join(destination_folder, dst_file_name)

    shutil.copy(src_file, dst_file)
    print(f"已复制")

def copy_latest_csv(destination_folder, add=""):
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
    copy_throughput_csv(latest_folder, destination_folder, add=add)