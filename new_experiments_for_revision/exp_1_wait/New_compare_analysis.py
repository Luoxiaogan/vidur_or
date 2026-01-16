#!/usr/bin/env python3
"""
New_compare_analysis.py - 滑动窗口 Throughput & Latency 综合分析

基于 my_request_metrics_*.csv 计算:
- Throughput: decode tokens/sec
- Latency: E2E latency (completed_at - arrived_at)

输出到 new_analysis/ 子目录

使用方法：
    python New_compare_analysis.py
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
    THROUGHPUT_START_TIME, THROUGHPUT_END_TIME,
    LATENCY_WINDOW, LATENCY_STEP,
    LATENCY_START_TIME, LATENCY_END_TIME
)


# ============ 配置 ============
ANALYSIS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "new_analysis")

# 调度器名称映射 (目录名 -> 文件名后缀)
SCHEDULER_NAME_MAP = {
    "wait": "general_nested_booking_limit",
    "vllm": "vllm",
    "sarathi": "sarathi",
}

# 颜色配置
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
SCHEDULER_COLORS = {
    "wait": '#1f77b4',      # 蓝色
    "vllm": '#ff7f0e',      # 橙色
    "sarathi": '#2ca02c',   # 绿色
}
SCHEDULER_MARKERS = {
    "wait": 'o',
    "vllm": 's',
    "sarathi": '^',
}


# ============ Throughput 核心计算 ============
def compute_windowed_throughput(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    滑动窗口 throughput 计算

    对于时刻 t，计算 [t, t+window) 内完成的请求的 decode_tokens 之和 / actual_window
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
    """计算 [start_time, end_time] 大窗口内的 throughput"""
    completed_at = df['completed_at'].values
    decode_tokens = df['decode_tokens'].values
    max_time = completed_at.max()

    actual_end = min(end_time, max_time)
    actual_window = actual_end - start_time
    if actual_window <= 0:
        return 0.0

    mask = (completed_at >= start_time) & (completed_at < actual_end)
    tokens_in_window = decode_tokens[mask].sum()

    return tokens_in_window / actual_window


# ============ Latency 核心计算 ============
def compute_windowed_latency(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    滑动窗口 latency 计算

    对于时刻 t，计算 [t, t+window) 内完成的请求的平均 E2E latency
    """
    completed_at = df['completed_at'].values
    arrived_at = df['arrived_at'].values
    e2e_latency = completed_at - arrived_at

    max_time = completed_at.max()
    time_axis = np.arange(0, max_time + step, step)

    latencies = []
    for t in time_axis:
        window_end = min(t + window, max_time)
        mask = (completed_at >= t) & (completed_at < window_end)

        if mask.sum() > 0:
            latencies.append(e2e_latency[mask].mean())
        else:
            latencies.append(np.nan)

    return time_axis, np.array(latencies)


def compute_bigwindow_latency(df: pd.DataFrame, start_time: float, end_time: float) -> float:
    """计算 [start_time, end_time] 大窗口内完成的请求的平均 E2E latency"""
    completed_at = df['completed_at'].values
    arrived_at = df['arrived_at'].values
    e2e_latency = completed_at - arrived_at
    max_time = completed_at.max()

    actual_end = min(end_time, max_time)
    mask = (completed_at >= start_time) & (completed_at < actual_end)

    if mask.sum() > 0:
        return e2e_latency[mask].mean()
    return np.nan


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

    max_len = max(len(t) for t, _ in throughput_data.values())
    data = {'time': np.arange(0, max_len * THROUGHPUT_STEP, THROUGHPUT_STEP)[:max_len]}

    for rate in sorted(throughput_data.keys()):
        time_axis, throughput = throughput_data[rate]
        padded = np.zeros(max_len)
        padded[:len(throughput)] = throughput
        data[f'rate_{rate}'] = padded

    df = pd.DataFrame(data)
    csv_path = os.path.join(output_dir, f"throughput_{scheduler}.csv")
    df.to_csv(csv_path, index=False)
    print(f"    已保存: throughput_{scheduler}.csv")


def save_latency_data(scheduler: str, latency_data: Dict[float, Tuple[np.ndarray, np.ndarray]], output_dir: str):
    """保存 latency 数据到 CSV"""
    if not latency_data:
        return

    max_len = max(len(t) for t, _ in latency_data.values())
    data = {'time': np.arange(0, max_len * LATENCY_STEP, LATENCY_STEP)[:max_len]}

    for rate in sorted(latency_data.keys()):
        time_axis, latencies = latency_data[rate]
        padded = np.full(max_len, np.nan)
        padded[:len(latencies)] = latencies
        data[f'rate_{rate}'] = padded

    df = pd.DataFrame(data)
    csv_path = os.path.join(output_dir, f"latency_{scheduler}.csv")
    df.to_csv(csv_path, index=False)
    print(f"    已保存: latency_{scheduler}.csv")


# ============ 绘图 ============
def plot_time_series_2x3(
    all_throughput_data: Dict[str, Dict[float, Tuple[np.ndarray, np.ndarray]]],
    all_latency_data: Dict[str, Dict[float, Tuple[np.ndarray, np.ndarray]]],
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    output_dir: str
):
    """
    绘制 2x3 的时间序列图
    第1行: throughput (wait, vllm, sarathi)
    第2行: latency (wait, vllm, sarathi)
    """
    schedulers = SCHEDULERS_TO_COMPARE
    n_schedulers = len(schedulers)

    fig, axes = plt.subplots(2, n_schedulers, figsize=(6 * n_schedulers, 10))

    fig.suptitle(f"Time Series Analysis\n(throughput: window={THROUGHPUT_WINDOW}s, latency: window={LATENCY_WINDOW}s)",
                 fontsize=14, fontweight='bold')

    # 第1行: Throughput
    for idx, scheduler in enumerate(schedulers):
        ax = axes[0, idx]
        scheduler_display = scheduler.upper() if scheduler != "wait" else "WAIT"
        ax.set_title(f"{scheduler_display} - Throughput", fontsize=11, fontweight='bold')

        if scheduler not in all_throughput_data or not all_throughput_data[scheduler]:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            continue

        throughput_data = all_throughput_data[scheduler]
        raw_data = all_raw_data.get(scheduler, {})
        rates = sorted(throughput_data.keys())

        for i, rate in enumerate(rates):
            time_axis, throughput = throughput_data[rate]
            color = COLORS[i % len(COLORS)]

            avg_throughput = 0.0
            if rate in raw_data:
                avg_throughput = compute_bigwindow_throughput(
                    raw_data[rate], THROUGHPUT_START_TIME, THROUGHPUT_END_TIME
                )

            ax.plot(time_axis, throughput, color=color, alpha=0.8, linewidth=1.5,
                    label=f'rate={rate}, avg={avg_throughput:.2f}')
            ax.axhline(y=avg_throughput, color=color, linestyle='--', alpha=0.6, linewidth=1)

        ax.axvline(x=THROUGHPUT_START_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=THROUGHPUT_END_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Throughput (tokens/sec)')
        ax.legend(fontsize=7, loc='best')
        ax.grid(True, alpha=0.3)

    # 第2行: Latency
    for idx, scheduler in enumerate(schedulers):
        ax = axes[1, idx]
        scheduler_display = scheduler.upper() if scheduler != "wait" else "WAIT"
        ax.set_title(f"{scheduler_display} - Latency", fontsize=11, fontweight='bold')

        if scheduler not in all_latency_data or not all_latency_data[scheduler]:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            continue

        latency_data = all_latency_data[scheduler]
        raw_data = all_raw_data.get(scheduler, {})
        rates = sorted(latency_data.keys())

        for i, rate in enumerate(rates):
            time_axis, latencies = latency_data[rate]
            color = COLORS[i % len(COLORS)]

            avg_latency = np.nan
            if rate in raw_data:
                avg_latency = compute_bigwindow_latency(
                    raw_data[rate], LATENCY_START_TIME, LATENCY_END_TIME
                )

            ax.plot(time_axis, latencies, color=color, alpha=0.8, linewidth=1.5,
                    label=f'rate={rate}, avg={avg_latency:.2f}s')

            if not np.isnan(avg_latency):
                ax.axhline(y=avg_latency, color=color, linestyle='--', alpha=0.6, linewidth=1)

        ax.axvline(x=LATENCY_START_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=LATENCY_END_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('E2E Latency (sec)')
        ax.legend(fontsize=7, loc='best')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, "time_series.png")
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: time_series.png")


def plot_rate_vs_metrics(
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    output_dir: str
):
    """
    绘制 1x2 的 rate vs 大窗口均值图
    子图1: rate vs throughput
    子图2: rate vs latency
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Rate vs Metrics (BigWindow: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}] sec)",
                 fontsize=14, fontweight='bold')

    # 收集所有调度器的数据
    for scheduler in SCHEDULERS_TO_COMPARE:
        if scheduler not in all_raw_data or not all_raw_data[scheduler]:
            continue

        raw_data = all_raw_data[scheduler]
        rates = sorted(raw_data.keys())

        throughputs = []
        latencies = []

        for rate in rates:
            df = raw_data[rate]
            throughputs.append(compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME))
            latencies.append(compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME))

        color = SCHEDULER_COLORS.get(scheduler, '#333333')
        marker = SCHEDULER_MARKERS.get(scheduler, 'o')
        label = scheduler.upper() if scheduler != "wait" else "WAIT"

        # 子图1: Rate vs Throughput
        axes[0].plot(rates, throughputs, marker=marker, color=color, linewidth=2,
                     markersize=8, label=label)

        # 子图2: Rate vs Latency
        axes[1].plot(rates, latencies, marker=marker, color=color, linewidth=2,
                     markersize=8, label=label)

    axes[0].set_xlabel('Arrival Rate')
    axes[0].set_ylabel('Throughput (tokens/sec)')
    axes[0].set_title('Throughput vs Arrival Rate')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Arrival Rate')
    axes[1].set_ylabel('E2E Latency (sec)')
    axes[1].set_title('Latency vs Arrival Rate')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    fig_path = os.path.join(output_dir, "rate_vs_metrics.png")
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: rate_vs_metrics.png")


# ============ 主程序 ============
def main():
    print("=" * 60)
    print("New_compare_analysis.py - Throughput & Latency 综合分析")
    print("=" * 60)
    print(f"结果目录: {OUTPUT_DIR}")
    print(f"输出目录: {ANALYSIS_OUTPUT_DIR}")
    print(f"Throughput - 窗口: {THROUGHPUT_WINDOW}s, 步长: {THROUGHPUT_STEP}s")
    print(f"Latency    - 窗口: {LATENCY_WINDOW}s, 步长: {LATENCY_STEP}s")
    print(f"大窗口范围: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}] 秒")
    print(f"调度器列表: {SCHEDULERS_TO_COMPARE}")

    os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)

    # 加载并计算所有数据
    all_throughput_data = {}
    all_latency_data = {}
    all_raw_data = {}

    for scheduler in SCHEDULERS_TO_COMPARE:
        print(f"\n处理 {scheduler}...")
        experiments = load_all_experiments_for_scheduler(scheduler, OUTPUT_DIR)
        print(f"  找到 {len(experiments)} 个实验")

        throughput_data = {}
        latency_data = {}

        for rate, df in sorted(experiments.items()):
            # Throughput
            time_axis_t, throughput = compute_windowed_throughput(df, THROUGHPUT_WINDOW, THROUGHPUT_STEP)
            throughput_data[rate] = (time_axis_t, throughput)

            # Latency
            time_axis_l, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
            latency_data[rate] = (time_axis_l, latencies)

            # 打印摘要
            avg_t = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
            avg_l = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)
            print(f"    rate={rate}: throughput={avg_t:.2f} tokens/s, latency={avg_l:.2f}s")

        all_throughput_data[scheduler] = throughput_data
        all_latency_data[scheduler] = latency_data
        all_raw_data[scheduler] = experiments

        # 保存 CSV
        save_throughput_data(scheduler, throughput_data, ANALYSIS_OUTPUT_DIR)
        save_latency_data(scheduler, latency_data, ANALYSIS_OUTPUT_DIR)

    # 绘制图表
    print("\n绘制图表...")
    plot_time_series_2x3(all_throughput_data, all_latency_data, all_raw_data, ANALYSIS_OUTPUT_DIR)
    plot_rate_vs_metrics(all_raw_data, ANALYSIS_OUTPUT_DIR)

    print(f"\n所有结果已保存到: {ANALYSIS_OUTPUT_DIR}")
    print("完成!")


if __name__ == "__main__":
    main()
