#!/usr/bin/env python3
"""
New_Compare_throughput.py - 滑动窗口吞吐量分析

基于 my_request_metrics_*.csv 计算 decode tokens/sec
输出到 throughput_analysis/ 子目录

使用方法：
    python New_Compare_throughput.py
"""

import os
import re
import glob
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from Compare_config import (
    OUTPUT_DIR, SCHEDULERS_TO_COMPARE,
    THROUGHPUT_WINDOW, THROUGHPUT_STEP,
    THROUGHPUT_START_TIME, THROUGHPUT_END_TIME
)


# ============ 配置 ============
ANALYSIS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "throughput_analysis")

# 调度器名称映射 (目录名 -> 文件名后缀)
SCHEDULER_NAME_MAP = {
    "wait": "general_nested_booking_limit",
    "vllm": "vllm",
    "sarathi": "sarathi",
}

# 颜色配置
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


# ============ 核心计算 ============
def compute_windowed_throughput(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    滑动窗口 throughput 计算

    对于时刻 t，计算 [t, t+window) 内完成的请求的 decode_tokens 之和 / actual_window

    Args:
        df: 包含 completed_at, decode_tokens 的 DataFrame
        window: 窗口大小（秒）
        step: 步长（秒）

    Returns:
        time_axis: 时间点数组
        throughput: 对应的 throughput 数组 (tokens/sec)
    """
    completed_at = df['completed_at'].values
    decode_tokens = df['decode_tokens'].values

    max_time = completed_at.max()
    time_axis = np.arange(0, max_time + step, step)

    throughput = []
    for t in time_axis:
        window_end = min(t + window, max_time)
        actual_window = window_end - t

        mask = (completed_at >= t) & (completed_at < window_end)
        tokens_in_window = decode_tokens[mask].sum()

        if actual_window > 0:
            throughput.append(tokens_in_window / actual_window)
        else:
            throughput.append(0)

    return time_axis, np.array(throughput)


def compute_bigwindow_throughput(df: pd.DataFrame, start_time: float, end_time: float) -> float:
    """
    计算 [start_time, end_time] 大窗口内的 throughput

    Args:
        df: 包含 completed_at, decode_tokens 的 DataFrame
        start_time: 大窗口起始时刻
        end_time: 大窗口结束时刻

    Returns:
        throughput: decode_tokens 之和 / actual_window (tokens/sec)
    """
    completed_at = df['completed_at'].values
    decode_tokens = df['decode_tokens'].values
    max_time = completed_at.max()

    # 边界处理
    actual_end = min(end_time, max_time)
    if actual_end < end_time:
        print(f"    Warning: end_time({end_time}) > max_time({max_time:.2f}), using {actual_end:.2f}")

    actual_window = actual_end - start_time
    if actual_window <= 0:
        return 0.0

    mask = (completed_at >= start_time) & (completed_at < actual_end)
    tokens_in_window = decode_tokens[mask].sum()

    return tokens_in_window / actual_window


# ============ 数据加载 ============
def parse_folder_name(folder_name: str) -> Optional[float]:
    """解析文件夹名，提取 rate"""
    pattern = r'lambda([\d.]+)_req\d+_prefill\d+_decode\d+_\d{8}_\d{6}'
    match = re.match(pattern, folder_name)
    if not match:
        return None
    return float(match.group(1))


def load_my_request_metrics(exp_dir: str, scheduler: str) -> Optional[pd.DataFrame]:
    """加载单个实验的 my_request_metrics CSV"""
    scheduler_name = SCHEDULER_NAME_MAP[scheduler]
    csv_path = os.path.join(exp_dir, f"my_request_metrics_{scheduler_name}.csv")

    if not os.path.exists(csv_path):
        return None

    return pd.read_csv(csv_path)


def load_all_experiments_for_scheduler(scheduler: str, results_dir: str) -> Dict[float, pd.DataFrame]:
    """加载指定调度器的所有实验数据，按 rate 索引"""
    scheduler_dir = os.path.join(results_dir, scheduler)
    if not os.path.exists(scheduler_dir):
        print(f"  警告: 目录不存在 {scheduler_dir}")
        return {}

    pattern = os.path.join(scheduler_dir, "lambda*")
    folders = sorted(glob.glob(pattern))

    experiments = {}
    for folder in folders:
        folder_name = os.path.basename(folder)
        rate = parse_folder_name(folder_name)
        if rate is None:
            print(f"  警告: 无法解析文件夹名 {folder_name}")
            continue

        df = load_my_request_metrics(folder, scheduler)
        if df is not None:
            experiments[rate] = df
        else:
            print(f"  警告: 缺少 my_request_metrics CSV in {folder}")

    return experiments


# ============ 保存数据 ============
def save_throughput_data(scheduler: str, throughput_data: Dict[float, Tuple[np.ndarray, np.ndarray]], output_dir: str):
    """保存 throughput 数据到 CSV"""
    if not throughput_data:
        return

    # 找到最长的时间轴
    max_len = max(len(t) for t, _ in throughput_data.values())

    # 构建 DataFrame
    data = {'time': np.arange(0, max_len * THROUGHPUT_STEP, THROUGHPUT_STEP)[:max_len]}

    for rate in sorted(throughput_data.keys()):
        time_axis, throughput = throughput_data[rate]
        # 填充到相同长度
        padded = np.zeros(max_len)
        padded[:len(throughput)] = throughput
        data[f'rate_{rate}'] = padded

    df = pd.DataFrame(data)
    csv_path = os.path.join(output_dir, f"throughput_{scheduler}.csv")
    df.to_csv(csv_path, index=False)
    print(f"  已保存: throughput_{scheduler}.csv")


# ============ 绘图 ============
def plot_throughput_time_series(
    all_throughput_data: Dict[str, Dict[float, Tuple[np.ndarray, np.ndarray]]],
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    output_dir: str
):
    """
    绘制 1x3 的 throughput 时间序列图

    Args:
        all_throughput_data: 滑动窗口 throughput 数据 {scheduler: {rate: (time_axis, throughput)}}
        all_raw_data: 原始 DataFrame 数据 {scheduler: {rate: df}}
        output_dir: 输出目录
    """
    schedulers = SCHEDULERS_TO_COMPARE
    n_schedulers = len(schedulers)

    fig, axes = plt.subplots(1, n_schedulers, figsize=(6 * n_schedulers, 6))
    if n_schedulers == 1:
        axes = [axes]

    fig.suptitle(f"Throughput Time Series (window={THROUGHPUT_WINDOW}s, step={THROUGHPUT_STEP}s)",
                 fontsize=14, fontweight='bold')

    for idx, scheduler in enumerate(schedulers):
        ax = axes[idx]
        scheduler_display = scheduler.upper() if scheduler != "wait" else "WAIT"
        ax.set_title(scheduler_display, fontsize=12, fontweight='bold')

        if scheduler not in all_throughput_data or not all_throughput_data[scheduler]:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            continue

        throughput_data = all_throughput_data[scheduler]
        raw_data = all_raw_data.get(scheduler, {})
        rates = sorted(throughput_data.keys())

        for i, rate in enumerate(rates):
            time_axis, throughput = throughput_data[rate]
            color = COLORS[i % len(COLORS)]

            # 计算大窗口 throughput
            avg_throughput = 0.0
            if rate in raw_data:
                avg_throughput = compute_bigwindow_throughput(
                    raw_data[rate], THROUGHPUT_START_TIME, THROUGHPUT_END_TIME
                )

            # 绘制时间序列（实线）
            ax.plot(time_axis, throughput, color=color, alpha=0.8, linewidth=1.5,
                    label=f'rate={rate}, avg={avg_throughput:.3f}')

            # 绘制横虚线（avg）
            ax.axhline(y=avg_throughput, color=color, linestyle='--', alpha=0.6, linewidth=1)

        # 绘制黑色虚线竖线（start_time 和 end_time）
        ax.axvline(x=THROUGHPUT_START_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=THROUGHPUT_END_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Throughput (tokens/sec)')
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存图片
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, "throughput_time_series.png")
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: throughput_time_series.png")


# ============ 主程序 ============
def main():
    print("=" * 60)
    print("New_Compare_throughput.py - 滑动窗口吞吐量分析")
    print("=" * 60)
    print(f"结果目录: {OUTPUT_DIR}")
    print(f"输出目录: {ANALYSIS_OUTPUT_DIR}")
    print(f"窗口大小: {THROUGHPUT_WINDOW} 秒")
    print(f"滑动步长: {THROUGHPUT_STEP} 秒")
    print(f"大窗口范围: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}] 秒")
    print(f"调度器列表: {SCHEDULERS_TO_COMPARE}")

    os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)

    # 加载并计算所有数据
    all_throughput_data = {}
    all_raw_data = {}  # 保存原始 DataFrame 用于计算大窗口 throughput

    for scheduler in SCHEDULERS_TO_COMPARE:
        print(f"\n处理 {scheduler}...")
        experiments = load_all_experiments_for_scheduler(scheduler, OUTPUT_DIR)
        print(f"  找到 {len(experiments)} 个实验")

        throughput_data = {}
        for rate, df in sorted(experiments.items()):
            time_axis, throughput = compute_windowed_throughput(df, THROUGHPUT_WINDOW, THROUGHPUT_STEP)
            throughput_data[rate] = (time_axis, throughput)
            print(f"    rate={rate}: {len(time_axis)} 个时间点, max_throughput={throughput.max():.2f}")

        all_throughput_data[scheduler] = throughput_data
        all_raw_data[scheduler] = experiments  # 保存原始数据

        # 保存中间数据
        save_throughput_data(scheduler, throughput_data, ANALYSIS_OUTPUT_DIR)

    # 绘制图表
    print("\n绘制图表...")
    plot_throughput_time_series(all_throughput_data, all_raw_data, ANALYSIS_OUTPUT_DIR)

    print(f"\n所有结果已保存到: {ANALYSIS_OUTPUT_DIR}")
    print("完成!")


if __name__ == "__main__":
    main()
