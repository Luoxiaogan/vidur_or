#!/usr/bin/env python3
"""
New_Compare_latency.py - 滑动窗口 E2E Latency 分析

基于 my_request_metrics_*.csv 计算 E2E latency (completed_at - arrived_at)
输出到 latency_analysis/ 子目录

使用方法：
    python New_Compare_latency.py
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
    LATENCY_WINDOW, LATENCY_STEP,
    LATENCY_START_TIME, LATENCY_END_TIME
)


# ============ 配置 ============
ANALYSIS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "latency_analysis")

# 调度器名称映射 (目录名 -> 文件名后缀)
SCHEDULER_NAME_MAP = {
    "wait": "general_nested_booking_limit",
    "vllm": "vllm",
    "sarathi": "sarathi",
}

# 颜色配置
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


# ============ 核心计算 ============
def compute_windowed_latency(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    滑动窗口 latency 计算

    对于时刻 t，计算 [t, t+window) 内完成的请求的平均 E2E latency

    Args:
        df: 包含 completed_at, arrived_at 的 DataFrame
        window: 窗口大小（秒）
        step: 步长（秒）

    Returns:
        time_axis: 时间点数组
        latencies: 对应的平均 latency 数组 (秒)，无请求时为 np.nan
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
    """
    计算 [start_time, end_time] 大窗口内完成的请求的平均 E2E latency

    Args:
        df: 包含 completed_at, arrived_at 的 DataFrame
        start_time: 大窗口起始时刻
        end_time: 大窗口结束时刻

    Returns:
        latency: 平均 E2E latency (秒)，无请求时为 np.nan
    """
    completed_at = df['completed_at'].values
    arrived_at = df['arrived_at'].values
    e2e_latency = completed_at - arrived_at
    max_time = completed_at.max()

    # 边界处理
    actual_end = min(end_time, max_time)
    if actual_end < end_time:
        print(f"    Warning: end_time({end_time}) > max_time({max_time:.2f}), using {actual_end:.2f}")

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
def save_latency_data(scheduler: str, latency_data: Dict[float, Tuple[np.ndarray, np.ndarray]], output_dir: str):
    """保存 latency 数据到 CSV"""
    if not latency_data:
        return

    # 找到最长的时间轴
    max_len = max(len(t) for t, _ in latency_data.values())

    # 构建 DataFrame
    data = {'time': np.arange(0, max_len * LATENCY_STEP, LATENCY_STEP)[:max_len]}

    for rate in sorted(latency_data.keys()):
        time_axis, latencies = latency_data[rate]
        # 填充到相同长度
        padded = np.full(max_len, np.nan)
        padded[:len(latencies)] = latencies
        data[f'rate_{rate}'] = padded

    df = pd.DataFrame(data)
    csv_path = os.path.join(output_dir, f"latency_{scheduler}.csv")
    df.to_csv(csv_path, index=False)
    print(f"  已保存: latency_{scheduler}.csv")


# ============ 绘图 ============
def plot_latency_time_series(
    all_latency_data: Dict[str, Dict[float, Tuple[np.ndarray, np.ndarray]]],
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    output_dir: str
):
    """
    绘制 1x3 的 latency 时间序列图

    Args:
        all_latency_data: 滑动窗口 latency 数据 {scheduler: {rate: (time_axis, latencies)}}
        all_raw_data: 原始 DataFrame 数据 {scheduler: {rate: df}}
        output_dir: 输出目录
    """
    schedulers = SCHEDULERS_TO_COMPARE
    n_schedulers = len(schedulers)

    fig, axes = plt.subplots(1, n_schedulers, figsize=(6 * n_schedulers, 6))
    if n_schedulers == 1:
        axes = [axes]

    fig.suptitle(f"E2E Latency Time Series (window={LATENCY_WINDOW}s, step={LATENCY_STEP}s)",
                 fontsize=14, fontweight='bold')

    for idx, scheduler in enumerate(schedulers):
        ax = axes[idx]
        scheduler_display = scheduler.upper() if scheduler != "wait" else "WAIT"
        ax.set_title(scheduler_display, fontsize=12, fontweight='bold')

        if scheduler not in all_latency_data or not all_latency_data[scheduler]:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            continue

        latency_data = all_latency_data[scheduler]
        raw_data = all_raw_data.get(scheduler, {})
        rates = sorted(latency_data.keys())

        for i, rate in enumerate(rates):
            time_axis, latencies = latency_data[rate]
            color = COLORS[i % len(COLORS)]

            # 计算大窗口 latency
            avg_latency = np.nan
            if rate in raw_data:
                avg_latency = compute_bigwindow_latency(
                    raw_data[rate], LATENCY_START_TIME, LATENCY_END_TIME
                )

            # 绘制时间序列（实线）
            ax.plot(time_axis, latencies, color=color, alpha=0.8, linewidth=1.5,
                    label=f'rate={rate}, avg={avg_latency:.2f}s')

            # 绘制横虚线（avg）
            if not np.isnan(avg_latency):
                ax.axhline(y=avg_latency, color=color, linestyle='--', alpha=0.6, linewidth=1)

        # 绘制黑色虚线竖线（start_time 和 end_time）
        ax.axvline(x=LATENCY_START_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=LATENCY_END_TIME, color='black', linestyle='--', alpha=0.7, linewidth=1)

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('E2E Latency (sec)')
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存图片
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, "latency_time_series.png")
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: latency_time_series.png")


# ============ 主程序 ============
def main():
    print("=" * 60)
    print("New_Compare_latency.py - 滑动窗口 E2E Latency 分析")
    print("=" * 60)
    print(f"结果目录: {OUTPUT_DIR}")
    print(f"输出目录: {ANALYSIS_OUTPUT_DIR}")
    print(f"窗口大小: {LATENCY_WINDOW} 秒")
    print(f"滑动步长: {LATENCY_STEP} 秒")
    print(f"大窗口范围: [{LATENCY_START_TIME}, {LATENCY_END_TIME}] 秒")
    print(f"调度器列表: {SCHEDULERS_TO_COMPARE}")

    os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)

    # 加载并计算所有数据
    all_latency_data = {}
    all_raw_data = {}  # 保存原始 DataFrame 用于计算大窗口 latency

    for scheduler in SCHEDULERS_TO_COMPARE:
        print(f"\n处理 {scheduler}...")
        experiments = load_all_experiments_for_scheduler(scheduler, OUTPUT_DIR)
        print(f"  找到 {len(experiments)} 个实验")

        latency_data = {}
        for rate, df in sorted(experiments.items()):
            time_axis, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
            latency_data[rate] = (time_axis, latencies)
            # 计算有效的 latency 统计（忽略 NaN）
            valid_latencies = latencies[~np.isnan(latencies)]
            if len(valid_latencies) > 0:
                print(f"    rate={rate}: {len(time_axis)} 个时间点, max_latency={valid_latencies.max():.2f}s, min_latency={valid_latencies.min():.2f}s")
            else:
                print(f"    rate={rate}: {len(time_axis)} 个时间点, 无有效数据")

        all_latency_data[scheduler] = latency_data
        all_raw_data[scheduler] = experiments  # 保存原始数据

        # 保存中间数据
        save_latency_data(scheduler, latency_data, ANALYSIS_OUTPUT_DIR)

    # 绘制图表
    print("\n绘制图表...")
    plot_latency_time_series(all_latency_data, all_raw_data, ANALYSIS_OUTPUT_DIR)

    print(f"\n所有结果已保存到: {ANALYSIS_OUTPUT_DIR}")
    print("完成!")


if __name__ == "__main__":
    main()
