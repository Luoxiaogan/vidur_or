#!/usr/bin/env python3
"""
Compare_analysis.py - WAIT vs vLLM vs Sarathi 性能分析

从 Compare_config.py 读取配置，分析 OUTPUT_DIR 中的实验结果

输出:
- Part 1: 单算法时间序列图 (wait/vllm/sarathi)_time_series.png
- Part 2: 跨算法对比图 scheduler_comparison.png
"""

import os
import re
import glob
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from Compare_config import (
    OUTPUT_DIR, ARRIVAL_RATES, SCHEDULERS_TO_COMPARE,
    PREFILL_TOKENS, DECODE_TOKENS, NUM_REQUESTS, WARMUP_FRACTION
)


# ============ 配置 ============
ANALYSIS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "analysis")

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


# ============ 数据类定义 ============
@dataclass
class ExperimentData:
    """单个实验的所有数据"""
    scheduler: str
    rate: float
    folder_path: str
    request_metrics: pd.DataFrame
    throughput: pd.DataFrame
    batch_size: pd.DataFrame
    batch_num_tokens: pd.DataFrame
    batch_memory_usage: pd.DataFrame
    batch_kv_tokens_percent: pd.DataFrame
    batch_execution_time: pd.DataFrame


# ============ 数据加载 ============
def parse_folder_name(folder_name: str) -> Optional[float]:
    """解析文件夹名，提取 rate"""
    pattern = r'lambda([\d.]+)_req\d+_prefill\d+_decode\d+_\d{8}_\d{6}'
    match = re.match(pattern, folder_name)
    if not match:
        return None
    return float(match.group(1))


def load_experiment_data(exp_dir: str, scheduler: str) -> Optional[ExperimentData]:
    """加载单个实验的所有数据"""
    folder_name = os.path.basename(exp_dir)
    rate = parse_folder_name(folder_name)
    if rate is None:
        print(f"  警告: 无法解析文件夹名 {folder_name}")
        return None

    scheduler_name = SCHEDULER_NAME_MAP[scheduler]
    plots_dir = os.path.join(exp_dir, "plots")

    # 检查必要文件是否存在
    request_metrics_file = os.path.join(exp_dir, f"request_metrics_{scheduler_name}.csv")
    throughput_file = os.path.join(exp_dir, f"throughput_{scheduler_name}.csv")

    if not os.path.exists(request_metrics_file) or not os.path.exists(throughput_file):
        print(f"  警告: 缺少必要文件 in {exp_dir}")
        return None

    return ExperimentData(
        scheduler=scheduler,
        rate=rate,
        folder_path=exp_dir,
        request_metrics=pd.read_csv(request_metrics_file),
        throughput=pd.read_csv(throughput_file),
        batch_size=pd.read_csv(os.path.join(plots_dir, "batch_size_per_batch.csv")),
        batch_num_tokens=pd.read_csv(os.path.join(plots_dir, "batch_num_tokens_per_batch.csv")),
        batch_memory_usage=pd.read_csv(os.path.join(plots_dir, "batch_memory_usage_percent_per_batch.csv")),
        batch_kv_tokens_percent=pd.read_csv(os.path.join(plots_dir, "batch_kv_tokens_percent_per_batch.csv")),
        batch_execution_time=pd.read_csv(os.path.join(plots_dir, "batch_execution_time_per_batch.csv")),
    )


def load_all_experiments_for_scheduler(scheduler: str, results_dir: str) -> Dict[float, ExperimentData]:
    """加载指定调度器的所有实验数据，按 rate 索引"""
    scheduler_dir = os.path.join(results_dir, scheduler)
    if not os.path.exists(scheduler_dir):
        print(f"  警告: 目录不存在 {scheduler_dir}")
        return {}

    pattern = os.path.join(scheduler_dir, "lambda*")
    folders = sorted(glob.glob(pattern))

    experiments = {}
    for folder in folders:
        exp_data = load_experiment_data(folder, scheduler)
        if exp_data is not None:
            experiments[exp_data.rate] = exp_data

    return experiments


# ============ 指标计算 ============
def compute_batch_time_axis(batch_execution_time_df: pd.DataFrame) -> np.ndarray:
    """计算每个 batch 结束时的累计时间"""
    times = batch_execution_time_df['batch_execution_time'].cumsum()
    return times.values


def compute_avg_throughput(throughput_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """计算平均吞吐量 (completed/T) over time"""
    time = throughput_df['Time (sec)'].values
    cumulative = throughput_df['throughput'].values
    mask = time > 0
    avg_throughput = np.zeros_like(cumulative, dtype=float)
    avg_throughput[mask] = cumulative[mask] / time[mask]
    return time[mask], avg_throughput[mask]


def compute_avg_latency_over_time(request_metrics_df: pd.DataFrame,
                                   throughput_df: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """计算累计平均延迟 over time"""
    latencies = request_metrics_df['request_e2e_time'].values
    cumsum_latency = np.cumsum(latencies)
    cumavg_latency = cumsum_latency / np.arange(1, len(latencies) + 1)

    # Map to time axis using throughput data
    time = throughput_df['Time (sec)'].values
    cumulative = throughput_df['throughput'].values

    time_points, latency_points = [], []
    for t, completed in zip(time, cumulative):
        idx = int(completed)
        if 0 < idx <= len(cumavg_latency):
            time_points.append(t)
            latency_points.append(cumavg_latency[idx - 1])

    return time_points, latency_points


def compute_steady_state_metrics(exp_data: ExperimentData,
                                  warmup_fraction: float) -> Tuple[float, float]:
    """计算稳态吞吐量和延迟"""
    throughput_df = exp_data.throughput
    request_metrics_df = exp_data.request_metrics

    total_time = throughput_df['Time (sec)'].max()
    warmup_time = total_time * warmup_fraction

    # Steady-state throughput
    steady_df = throughput_df[throughput_df['Time (sec)'] >= warmup_time]
    steady_throughput = 0.0
    if len(steady_df) >= 2:
        delta_completed = steady_df.iloc[-1]['throughput'] - steady_df.iloc[0]['throughput']
        delta_time = steady_df.iloc[-1]['Time (sec)'] - steady_df.iloc[0]['Time (sec)']
        if delta_time > 0:
            steady_throughput = delta_completed / delta_time

    # Steady-state latency
    cutoff = int(len(request_metrics_df) * warmup_fraction)
    steady_latency = request_metrics_df.iloc[cutoff:]['request_e2e_time'].mean()

    return steady_throughput, steady_latency


# ============ 绘图 ============
def save_plot(fig, output_dir: str, filename: str, dpi: int = 150):
    """保存图表"""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {filename}")


def plot_single_scheduler_time_series(scheduler: str,
                                       experiments: Dict[float, ExperimentData],
                                       output_dir: str):
    """绘制单个调度器的时间序列图 (6 subplots)"""
    if not experiments:
        print(f"  跳过 {scheduler}: 无数据")
        return

    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    scheduler_display = scheduler.upper() if scheduler != "wait" else "WAIT"
    fig.suptitle(f"{scheduler_display} Time Series Analysis", fontsize=14, fontweight='bold')

    rates = sorted(experiments.keys())

    for i, rate in enumerate(rates):
        exp_data = experiments[rate]
        color = COLORS[i % len(COLORS)]
        label = f'rate={rate}'

        # 计算 batch 时间轴
        batch_time = compute_batch_time_axis(exp_data.batch_execution_time)

        # (0,0) Throughput
        ax = axes[0, 0]
        time, throughput = compute_avg_throughput(exp_data.throughput)
        ax.plot(time, throughput, label=label, color=color, alpha=0.8, linewidth=1.5)

        # (0,1) Avg E2E Latency
        ax = axes[0, 1]
        time_pts, latency_pts = compute_avg_latency_over_time(exp_data.request_metrics, exp_data.throughput)
        ax.plot(time_pts, latency_pts, label=label, color=color, alpha=0.8, linewidth=1.5)

        # (1,0) Batch Num Tokens
        ax = axes[1, 0]
        ax.plot(batch_time, exp_data.batch_num_tokens['batch_num_tokens'].values,
                label=label, color=color, alpha=0.7, linewidth=1)

        # (1,1) Batch Size
        ax = axes[1, 1]
        ax.plot(batch_time, exp_data.batch_size['batch_size'].values,
                label=label, color=color, alpha=0.7, linewidth=1)

        # (2,0) Memory Usage
        ax = axes[2, 0]
        ax.plot(batch_time, exp_data.batch_memory_usage['batch_memory_usage_percent'].values,
                label=label, color=color, alpha=0.7, linewidth=1)

        # (2,1) KV Tokens Percent
        ax = axes[2, 1]
        ax.plot(batch_time, exp_data.batch_kv_tokens_percent['batch_kv_tokens_percent'].values,
                label=label, color=color, alpha=0.7, linewidth=1)

    # 设置子图标题和标签
    axes[0, 0].set_xlabel('Time (sec)')
    axes[0, 0].set_ylabel('Throughput (tokens/sec)')
    axes[0, 0].set_title('Average Throughput over Time')
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].set_xlabel('Time (sec)')
    axes[0, 1].set_ylabel('Avg E2E Latency (sec)')
    axes[0, 1].set_title('Cumulative Avg E2E Latency over Time')
    axes[0, 1].legend(fontsize=8)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].set_xlabel('Time (sec)')
    axes[1, 0].set_ylabel('Num Tokens')
    axes[1, 0].set_title('Batch Num Tokens over Time')
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].set_xlabel('Time (sec)')
    axes[1, 1].set_ylabel('Batch Size (# requests)')
    axes[1, 1].set_title('Batch Size over Time')
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(True, alpha=0.3)

    axes[2, 0].set_xlabel('Time (sec)')
    axes[2, 0].set_ylabel('Memory Usage (%)')
    axes[2, 0].set_title('Memory Usage over Time')
    axes[2, 0].legend(fontsize=8)
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].set_ylim(0, 105)

    axes[2, 1].set_xlabel('Time (sec)')
    axes[2, 1].set_ylabel('KV Tokens Percent (%)')
    axes[2, 1].set_title('KV Tokens Percent over Time')
    axes[2, 1].legend(fontsize=8)
    axes[2, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    save_plot(fig, output_dir, f"{scheduler}_time_series.png")


def plot_scheduler_comparison(all_experiments: Dict[str, Dict[float, ExperimentData]],
                               output_dir: str):
    """绘制跨调度器对比图 (2 subplots: rate vs throughput, rate vs latency)"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Scheduler Comparison (Steady-State, warmup={WARMUP_FRACTION*100:.0f}%)",
                 fontsize=14, fontweight='bold')

    for scheduler, experiments in all_experiments.items():
        if not experiments:
            continue

        rates = []
        throughputs = []
        latencies = []

        for rate in sorted(experiments.keys()):
            exp_data = experiments[rate]
            steady_throughput, steady_latency = compute_steady_state_metrics(exp_data, WARMUP_FRACTION)
            rates.append(rate)
            throughputs.append(steady_throughput)
            latencies.append(steady_latency)

        color = SCHEDULER_COLORS.get(scheduler, '#333333')
        marker = SCHEDULER_MARKERS.get(scheduler, 'o')
        label = scheduler.upper() if scheduler != "wait" else "WAIT"

        # (0) Rate vs Throughput
        axes[0].plot(rates, throughputs, marker=marker, color=color, linewidth=2,
                     markersize=8, label=label)

        # (1) Rate vs Latency
        axes[1].plot(rates, latencies, marker=marker, color=color, linewidth=2,
                     markersize=8, label=label)

    axes[0].set_xlabel('Arrival Rate')
    axes[0].set_ylabel('Steady-State Throughput (tokens/sec)')
    axes[0].set_title('Throughput vs Arrival Rate')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Arrival Rate')
    axes[1].set_ylabel('Steady-State Avg E2E Latency (sec)')
    axes[1].set_title('Latency vs Arrival Rate')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    save_plot(fig, output_dir, "scheduler_comparison.png")


def print_summary(all_experiments: Dict[str, Dict[float, ExperimentData]]):
    """打印汇总统计"""
    print("\n" + "=" * 80)
    print("Steady-State Metrics Summary")
    print("=" * 80)

    rows = []
    for scheduler, experiments in all_experiments.items():
        for rate in sorted(experiments.keys()):
            exp_data = experiments[rate]
            steady_throughput, steady_latency = compute_steady_state_metrics(exp_data, WARMUP_FRACTION)
            rows.append({
                'Scheduler': scheduler,
                'Rate': rate,
                'Throughput (tokens/sec)': f"{steady_throughput:.2f}",
                'Latency (sec)': f"{steady_latency:.2f}",
            })

    if rows:
        df = pd.DataFrame(rows)
        print(df.to_string(index=False))
    print("=" * 80)


# ============ 主程序 ============
def main():
    print("=" * 60)
    print("Compare_analysis.py - WAIT vs vLLM vs Sarathi 性能分析")
    print("=" * 60)
    print(f"结果目录: {OUTPUT_DIR}")
    print(f"输出目录: {ANALYSIS_OUTPUT_DIR}")
    print(f"Warmup 比例: {WARMUP_FRACTION}")
    print(f"调度器列表: {SCHEDULERS_TO_COMPARE}")

    # 加载所有实验数据
    print("\n加载实验数据...")
    all_experiments = {}
    for scheduler in SCHEDULERS_TO_COMPARE:
        print(f"  加载 {scheduler}...")
        experiments = load_all_experiments_for_scheduler(scheduler, OUTPUT_DIR)
        all_experiments[scheduler] = experiments
        print(f"    找到 {len(experiments)} 个实验")

    # Part 1: 单算法时间序列图
    print("\n生成单算法时间序列图...")
    for scheduler in SCHEDULERS_TO_COMPARE:
        print(f"  绘制 {scheduler}...")
        plot_single_scheduler_time_series(scheduler, all_experiments[scheduler], ANALYSIS_OUTPUT_DIR)

    # Part 2: 跨算法对比图
    print("\n生成跨算法对比图...")
    plot_scheduler_comparison(all_experiments, ANALYSIS_OUTPUT_DIR)

    # 打印汇总
    print_summary(all_experiments)

    print(f"\n所有图表已保存到: {ANALYSIS_OUTPUT_DIR}")
    print("完成!")


if __name__ == "__main__":
    main()
