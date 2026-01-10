#!/usr/bin/env python3
"""
实验 1-1 分析脚本：Booking Limit (n) 参数敏感性分析

分析不同 booking limit n 和 arrival rate 对系统性能的影响
从 config.py 读取配置，无需命令行参数

使用方法：
    python analyze_exp_1_1.py
"""

import os
import re
import glob
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config import OUTPUT_DIR, ANALYSIS_OUTPUT_DIR, WARMUP_FRACTION


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class ExperimentConfig:
    """实验参数配置（从文件夹名解析）"""
    n: int
    lambda_rate: float
    num_requests: int
    prefill_tokens: int
    decode_tokens: int
    timestamp: str
    folder_path: str


@dataclass
class ExperimentData:
    """单个实验的所有数据"""
    config: ExperimentConfig
    request_metrics: pd.DataFrame
    throughput_series: pd.DataFrame
    batch_size_cdf: pd.DataFrame
    batch_tokens_cdf: pd.DataFrame
    memory_usage: Dict


@dataclass
class SteadyStateMetrics:
    """稳态指标汇总"""
    n: int
    lambda_rate: float
    steady_state_throughput: float
    mean_e2e_latency: float
    p50_e2e_latency: float
    p99_e2e_latency: float
    mean_scheduling_delay: float
    median_batch_size: float
    median_batch_tokens: float
    memory_usage_mean: float
    memory_usage_max: float
    total_time: float
    num_requests: int


# =============================================================================
# 数据加载
# =============================================================================

SCHEDULER_NAME = "general_nested_booking_limit"


def parse_folder_name(folder_path: str) -> Optional[ExperimentConfig]:
    """解析文件夹名，提取实验参数"""
    folder_name = os.path.basename(folder_path)
    pattern = r'n(\d+)_lambda([\d.]+)_req(\d+)_prefill(\d+)_decode(\d+)_(\d{8}_\d{6})'
    match = re.match(pattern, folder_name)
    if not match:
        print(f"警告: 无法解析文件夹名 {folder_name}")
        return None
    return ExperimentConfig(
        n=int(match.group(1)),
        lambda_rate=float(match.group(2)),
        num_requests=int(match.group(3)),
        prefill_tokens=int(match.group(4)),
        decode_tokens=int(match.group(5)),
        timestamp=match.group(6),
        folder_path=folder_path
    )


def load_experiment(folder_path: str) -> Optional[ExperimentData]:
    """加载单个实验的所有数据"""
    config = parse_folder_name(folder_path)
    if config is None:
        return None

    return ExperimentData(
        config=config,
        request_metrics=pd.read_csv(os.path.join(folder_path, f"request_metrics_{SCHEDULER_NAME}.csv")),
        throughput_series=pd.read_csv(os.path.join(folder_path, f"throughput_{SCHEDULER_NAME}.csv")),
        batch_size_cdf=pd.read_csv(os.path.join(folder_path, "plots", f"batch_size_{SCHEDULER_NAME}.csv")),
        batch_tokens_cdf=pd.read_csv(os.path.join(folder_path, "plots", f"batch_num_tokens_{SCHEDULER_NAME}.csv")),
        memory_usage=json.load(open(os.path.join(folder_path, "plots", "replica_1_memory_usage.json")))
    )


def load_all_experiments(results_dir: str) -> Dict[Tuple[int, float], ExperimentData]:
    """加载所有实验，按 (n, rate) 索引"""
    pattern = os.path.join(results_dir, "n*_lambda*")
    folders = sorted(glob.glob(pattern))
    experiments = {}

    for folder in folders:
        exp_data = load_experiment(folder)
        if exp_data is None:
            continue
        key = (exp_data.config.n, exp_data.config.lambda_rate)
        experiments[key] = exp_data

    return experiments


# =============================================================================
# 指标计算
# =============================================================================

def compute_steady_state_throughput(throughput_series: pd.DataFrame, warmup_fraction: float) -> float:
    """计算稳态吞吐量 (tokens/sec)"""
    df = throughput_series.copy()
    total_time = df['Time (sec)'].max()
    warmup_time = total_time * warmup_fraction
    steady_df = df[df['Time (sec)'] >= warmup_time]

    if len(steady_df) < 2:
        return 0.0

    start_count = steady_df.iloc[0]['throughput']
    end_count = steady_df.iloc[-1]['throughput']
    start_time = steady_df.iloc[0]['Time (sec)']
    end_time = steady_df.iloc[-1]['Time (sec)']

    if end_time <= start_time:
        return 0.0
    return (end_count - start_count) / (end_time - start_time)


def compute_latency_stats(request_metrics: pd.DataFrame, warmup_fraction: float) -> Dict[str, float]:
    """计算延迟统计量（去除 warm-up）"""
    cutoff = int(len(request_metrics) * warmup_fraction)
    steady_df = request_metrics.iloc[cutoff:]
    return {
        'mean_e2e_latency': steady_df['request_e2e_time'].mean(),
        'p50_e2e_latency': steady_df['request_e2e_time'].quantile(0.5),
        'p99_e2e_latency': steady_df['request_e2e_time'].quantile(0.99),
        'mean_scheduling_delay': steady_df['request_scheduling_delay'].mean()
    }


def compute_batch_stats(batch_size_cdf: pd.DataFrame, batch_tokens_cdf: pd.DataFrame) -> Dict[str, float]:
    """从 CDF 计算 batch 统计量（取中位数）"""
    size_median = batch_size_cdf[batch_size_cdf['cdf'] >= 0.5].iloc[0]['batch_size']
    tokens_median = batch_tokens_cdf[batch_tokens_cdf['cdf'] >= 0.5].iloc[0]['batch_num_tokens']
    return {'median_batch_size': size_median, 'median_batch_tokens': tokens_median}


def compute_all_metrics(exp_data: ExperimentData, warmup_fraction: float) -> SteadyStateMetrics:
    """计算单个实验的所有指标"""
    config = exp_data.config
    latency_stats = compute_latency_stats(exp_data.request_metrics, warmup_fraction)
    batch_stats = compute_batch_stats(exp_data.batch_size_cdf, exp_data.batch_tokens_cdf)
    memory = exp_data.memory_usage

    return SteadyStateMetrics(
        n=config.n,
        lambda_rate=config.lambda_rate,
        steady_state_throughput=compute_steady_state_throughput(exp_data.throughput_series, warmup_fraction),
        mean_e2e_latency=latency_stats['mean_e2e_latency'],
        p50_e2e_latency=latency_stats['p50_e2e_latency'],
        p99_e2e_latency=latency_stats['p99_e2e_latency'],
        mean_scheduling_delay=latency_stats['mean_scheduling_delay'],
        median_batch_size=batch_stats['median_batch_size'],
        median_batch_tokens=batch_stats['median_batch_tokens'],
        memory_usage_mean=memory.get('replica_1_memory_usage_weighted_mean', 0),
        memory_usage_max=memory.get('replica_1_memory_usage_max', 0),
        total_time=exp_data.throughput_series['Time (sec)'].max(),
        num_requests=config.num_requests
    )


# =============================================================================
# 绘图
# =============================================================================

def save_plot(fig, output_dir: str, filename: str, dpi: int = 150):
    """保存图表"""
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {filename}")


def plot_throughput_time_series(experiments: Dict[Tuple[int, float], ExperimentData], output_dir: str):
    """时间 vs 平均吞吐量（按 n 分组）"""
    fig, ax = plt.subplots(figsize=(12, 6))

    for (n, rate), exp_data in sorted(experiments.items()):
        df = exp_data.throughput_series.copy()
        df['instant_throughput'] = df['throughput'].diff().fillna(0)
        df['time_diff'] = df['Time (sec)'].diff().fillna(1)
        df['rate'] = df['instant_throughput'] / df['time_diff'].replace(0, 1)
        df['rate_smooth'] = df['rate'].rolling(window=10, min_periods=1).mean()
        ax.plot(df['Time (sec)'], df['rate_smooth'], label=f'n={n}, λ={rate}', linewidth=1.5)

    ax.set_xlabel('Time (sec)')
    ax.set_ylabel('Throughput (tokens/sec)')
    ax.set_title('Throughput Time Series')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'A1_throughput_time_series.png')


def plot_cumulative_completed(experiments: Dict[Tuple[int, float], ExperimentData], output_dir: str):
    """时间 vs 累计完成 tokens"""
    fig, ax = plt.subplots(figsize=(12, 6))

    for (n, rate), exp_data in sorted(experiments.items()):
        df = exp_data.throughput_series
        ax.plot(df['Time (sec)'], df['throughput'], label=f'n={n}, λ={rate}', linewidth=1.5)

    ax.set_xlabel('Time (sec)')
    ax.set_ylabel('Cumulative Completed Tokens')
    ax.set_title('Cumulative Completed Tokens')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'A2_cumulative_completed.png')


def plot_latency_time_series(experiments: Dict[Tuple[int, float], ExperimentData], output_dir: str):
    """时间 vs 平均延迟"""
    fig, ax = plt.subplots(figsize=(12, 6))

    for (n, rate), exp_data in sorted(experiments.items()):
        df = exp_data.request_metrics.copy().sort_values('Request Id')
        df['cumsum_latency'] = df['request_e2e_time'].cumsum()
        df['count'] = range(1, len(df) + 1)
        df['avg_latency'] = df['cumsum_latency'] / df['count']
        ax.plot(df['Request Id'], df['avg_latency'], label=f'n={n}, λ={rate}', linewidth=1.5)

    ax.set_xlabel('Request ID (Time Order)')
    ax.set_ylabel('Average E2E Latency (sec)')
    ax.set_title('Average Latency Over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'A3_latency_time_series.png')


def plot_n_vs_metrics(summary_df: pd.DataFrame, output_dir: str):
    """n vs 各项指标（按 lambda 分组画多条曲线）"""
    lambda_values = summary_df['lambda'].unique()

    # B1: n vs throughput
    fig, ax = plt.subplots(figsize=(10, 6))
    for lam in sorted(lambda_values):
        df = summary_df[summary_df['lambda'] == lam].sort_values('n')
        ax.plot(df['n'], df['steady_state_throughput'], marker='o', linewidth=2, label=f'λ={lam}')
    ax.set_xlabel('Booking Limit (n)')
    ax.set_ylabel('Steady-State Throughput (tokens/sec)')
    ax.set_title('Effect of Booking Limit on Throughput')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'B1_n_vs_throughput.png')

    # B2: n vs latency
    fig, ax = plt.subplots(figsize=(10, 6))
    for lam in sorted(lambda_values):
        df = summary_df[summary_df['lambda'] == lam].sort_values('n')
        ax.plot(df['n'], df['mean_e2e_latency'], marker='o', linewidth=2, label=f'λ={lam}')
    ax.set_xlabel('Booking Limit (n)')
    ax.set_ylabel('Mean E2E Latency (sec)')
    ax.set_title('Effect of Booking Limit on Latency')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'B2_n_vs_latency.png')

    # B3: n vs batch size
    fig, ax = plt.subplots(figsize=(10, 6))
    for lam in sorted(lambda_values):
        df = summary_df[summary_df['lambda'] == lam].sort_values('n')
        ax.plot(df['n'], df['median_batch_size'], marker='o', linewidth=2, label=f'λ={lam}')
    ax.set_xlabel('Booking Limit (n)')
    ax.set_ylabel('Median Batch Size')
    ax.set_title('Effect of Booking Limit on Batch Size')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'B3_n_vs_batch_size.png')

    # B4: n vs memory
    fig, ax = plt.subplots(figsize=(10, 6))
    for lam in sorted(lambda_values):
        df = summary_df[summary_df['lambda'] == lam].sort_values('n')
        ax.plot(df['n'], df['memory_usage_mean'], marker='o', linewidth=2, label=f'λ={lam}')
    ax.set_xlabel('Booking Limit (n)')
    ax.set_ylabel('Memory Usage (%)')
    ax.set_title('Effect of Booking Limit on Memory Usage')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'B4_n_vs_memory.png')


def plot_throughput_vs_latency(summary_df: pd.DataFrame, output_dir: str):
    """Throughput vs Latency (Pareto 曲线)"""
    fig, ax = plt.subplots(figsize=(10, 8))
    lambda_values = summary_df['lambda'].unique()

    for lam in sorted(lambda_values):
        df = summary_df[summary_df['lambda'] == lam].sort_values('n')
        ax.scatter(df['steady_state_throughput'], df['mean_e2e_latency'], s=100, alpha=0.7, label=f'λ={lam}')
        ax.plot(df['steady_state_throughput'], df['mean_e2e_latency'], '--', linewidth=1, alpha=0.5)

        for _, row in df.iterrows():
            ax.annotate(f"n={int(row['n'])}", (row['steady_state_throughput'], row['mean_e2e_latency']),
                       textcoords="offset points", xytext=(5, 5), fontsize=8)

    ax.set_xlabel('Throughput (tokens/sec)')
    ax.set_ylabel('Mean E2E Latency (sec)')
    ax.set_title('Throughput-Latency Trade-off')
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(fig, output_dir, 'C1_throughput_vs_latency.png')


def generate_all_plots(experiments: Dict[Tuple[int, float], ExperimentData], summary_df: pd.DataFrame, output_dir: str):
    """生成所有图表"""
    print("\n生成图表...")
    plot_throughput_time_series(experiments, output_dir)
    plot_cumulative_completed(experiments, output_dir)
    plot_latency_time_series(experiments, output_dir)
    plot_n_vs_metrics(summary_df, output_dir)
    plot_throughput_vs_latency(summary_df, output_dir)


# =============================================================================
# 主程序
# =============================================================================

def main():
    results_dir = OUTPUT_DIR
    output_dir = ANALYSIS_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("实验 1-1 分析: Booking Limit (n) × Arrival Rate (λ)")
    print("=" * 60)
    print(f"结果目录: {results_dir}")
    print(f"输出目录: {output_dir}")
    print(f"Warm-up 比例: {WARMUP_FRACTION}")

    # 加载数据
    print("\n加载实验数据...")
    experiments = load_all_experiments(results_dir)

    if not experiments:
        print("错误: 未找到任何实验数据")
        return

    keys = sorted(experiments.keys())
    n_values = sorted(set(k[0] for k in keys))
    lambda_values = sorted(set(k[1] for k in keys))
    print(f"已加载 {len(experiments)} 个实验")
    print(f"  n 值: {n_values}")
    print(f"  λ 值: {lambda_values}")

    # 计算指标
    print("\n计算稳态指标...")
    summary_rows = []
    for key in sorted(experiments.keys()):
        exp_data = experiments[key]
        metrics = compute_all_metrics(exp_data, WARMUP_FRACTION)
        summary_rows.append({
            'n': metrics.n,
            'lambda': metrics.lambda_rate,
            'num_requests': metrics.num_requests,
            'steady_state_throughput': metrics.steady_state_throughput,
            'mean_e2e_latency': metrics.mean_e2e_latency,
            'p50_e2e_latency': metrics.p50_e2e_latency,
            'p99_e2e_latency': metrics.p99_e2e_latency,
            'mean_scheduling_delay': metrics.mean_scheduling_delay,
            'median_batch_size': metrics.median_batch_size,
            'median_batch_tokens': metrics.median_batch_tokens,
            'memory_usage_mean': metrics.memory_usage_mean,
            'memory_usage_max': metrics.memory_usage_max,
            'total_time': metrics.total_time
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(['lambda', 'n'])

    # 生成图表
    generate_all_plots(experiments, summary_df, output_dir)

    # 保存汇总表
    summary_path = os.path.join(output_dir, 'summary.csv')
    summary_df.to_csv(summary_path, index=False)
    print(f"\n汇总表已保存: {summary_path}")

    # 打印汇总
    print("\n" + "=" * 60)
    print("汇总统计")
    print("=" * 60)
    print(summary_df.to_string(index=False))
    print("=" * 60)
    print(f"\n所有图表已保存到: {output_dir}")


if __name__ == "__main__":
    main()
