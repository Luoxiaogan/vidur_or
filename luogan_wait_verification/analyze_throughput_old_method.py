#!/usr/bin/env python3
"""
analyze_throughput_old_method.py - 滑动窗口吞吐量分析（适配新实验结构）

基于 my_request_metrics_*.csv 计算 decode tokens/sec
使用旧脚本的滑动窗口方法，但适配新实验目录结构

使用方法：
    python analyze_throughput_old_method.py /home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402
"""

import argparse
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# 全局配置变量（由命令行参数设置）
THROUGHPUT_WINDOW = 5.0
THROUGHPUT_STEP = 0.5
THROUGHPUT_START_TIME = 50.0
THROUGHPUT_END_TIME = 180.0

# 调度器名称映射 (目录名前缀 -> CSV文件名后缀)
SCHEDULER_NAME_MAP = {
    "WCP": "general_nested_chunked",
    "vLLM": "vllm",
    "Sarathi": "sarathi",
}

# 颜色配置
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


# ============ 核心计算（完全保留旧脚本逻辑） ============
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
    """
    计算 [start_time, end_time] 大窗口内的 throughput
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


# ============ 数据加载（适配新实验结构） ============
def parse_experiment_folder(folder_name: str) -> Optional[Tuple[str, int]]:
    """
    解析新实验文件夹名

    格式示例：
    - WCP_cs256_tl21_r12 -> ("WCP", 12)
    - Sarathi_cs512_r16 -> ("Sarathi", 16)
    - vLLM_r20 -> ("vLLM", 20)
    """
    match = re.match(r'(WCP|Sarathi|vLLM).*?_r(\d+)$', folder_name)
    if not match:
        return None

    scheduler = match.group(1)
    rate = int(match.group(2))
    return scheduler, rate


def find_my_request_metrics(exp_dir: Path) -> Optional[Path]:
    """递归查找 my_request_metrics_*.csv 文件"""
    pattern = exp_dir.rglob("my_request_metrics_*.csv")
    csv_files = list(pattern)

    if not csv_files:
        return None

    return csv_files[0]


def load_all_experiments(batch_dir: Path) -> Dict[str, Dict[int, pd.DataFrame]]:
    """
    加载 batch 目录下的所有实验

    Returns:
        {scheduler: {rate: DataFrame}}
    """
    experiments = {}

    print(f"扫描目录: {batch_dir}")
    print("-" * 60)

    for item in batch_dir.iterdir():
        if not item.is_dir():
            continue

        parsed = parse_experiment_folder(item.name)
        if not parsed:
            continue

        scheduler, rate = parsed
        csv_file = find_my_request_metrics(item)

        if csv_file is None:
            print(f"  [SKIP] {item.name}: 未找到 my_request_metrics CSV")
            continue

        try:
            df = pd.read_csv(csv_file)
            experiments.setdefault(scheduler, {})[rate] = df
            print(f"  [OK] {item.name}: {len(df)} 请求, CSV={csv_file.name}")
        except Exception as e:
            print(f"  [ERROR] {item.name}: {e}")

    print("-" * 60)
    total = sum(len(rates) for rates in experiments.values())
    print(f"加载了 {total} 个实验")

    for scheduler in sorted(experiments.keys()):
        print(f"  {scheduler}: {sorted(experiments[scheduler].keys())}")

    return experiments


# ============ 保存数据 ============
def save_throughput_data(scheduler: str, throughput_data: Dict[int, Tuple[np.ndarray, np.ndarray]],
                         output_dir: Path, step: float):
    """保存 throughput 数据到 CSV"""
    if not throughput_data:
        return

    max_len = max(len(t) for t, _ in throughput_data.values())
    data = {'time': np.arange(0, max_len * step, step)[:max_len]}

    for rate in sorted(throughput_data.keys()):
        time_axis, throughput = throughput_data[rate]
        padded = np.zeros(max_len)
        padded[:len(throughput)] = throughput
        data[f'rate_{rate}'] = padded

    df = pd.DataFrame(data)
    csv_path = output_dir / f"throughput_{scheduler}.csv"
    df.to_csv(csv_path, index=False)
    print(f"  已保存: {csv_path.name}")


# ============ 绘图（完全保留旧脚本逻辑） ============
def plot_throughput_time_series(
    all_throughput_data: Dict[str, Dict[int, Tuple[np.ndarray, np.ndarray]]],
    all_raw_data: Dict[str, Dict[int, pd.DataFrame]],
    output_dir: Path
):
    """
    绘制 1x3 的 throughput 时间序列图
    """
    schedulers = ['WCP', 'Sarathi', 'vLLM']
    n_schedulers = sum(1 for s in schedulers if s in all_throughput_data)

    if n_schedulers == 0:
        print("没有数据可绘制")
        return

    fig, axes = plt.subplots(1, n_schedulers, figsize=(6 * n_schedulers, 6))
    if n_schedulers == 1:
        axes = [axes]

    fig.suptitle(f"Throughput Time Series (window={THROUGHPUT_WINDOW}s, step={THROUGHPUT_STEP}s)",
                 fontsize=14, fontweight='bold')

    ax_idx = 0
    for scheduler in schedulers:
        if scheduler not in all_throughput_data:
            continue

        ax = axes[ax_idx]
        ax_idx += 1

        ax.set_title(scheduler, fontsize=12, fontweight='bold')
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
                    label=f'rate={rate}, avg={avg_throughput:.1f}')

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
    fig_path = output_dir / "throughput_time_series_old_method.png"
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {fig_path.name}")


def plot_rate_vs_throughput_summary(all_raw_data: Dict[str, Dict[int, pd.DataFrame]], output_dir: Path):
    """绘制 rate vs throughput 汇总图"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    scheduler_colors = {
        "WCP": '#1f77b4',
        "Sarathi": '#2ca02c',
        "vLLM": '#ff7f0e',
    }
    scheduler_markers = {
        "WCP": 'o',
        "Sarathi": '^',
        "vLLM": 's',
    }

    for scheduler in sorted(all_raw_data.keys()):
        rates = []
        throughputs = []

        for rate in sorted(all_raw_data[scheduler].keys()):
            df = all_raw_data[scheduler][rate]
            tp = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
            rates.append(rate)
            throughputs.append(tp)

        color = scheduler_colors.get(scheduler, '#333333')
        marker = scheduler_markers.get(scheduler, 'o')

        ax.plot(rates, throughputs, marker=marker, color=color, linewidth=2,
                markersize=8, label=scheduler)

    ax.set_xlabel('Arrival Rate (requests/s)')
    ax.set_ylabel('Throughput (tokens/sec)')
    ax.set_title(f'Throughput vs Arrival Rate (Steady-state: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}]s)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig_path = output_dir / "rate_vs_throughput_old_method.png"
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {fig_path.name}")


def save_summary_csv(all_raw_data: Dict[str, Dict[int, pd.DataFrame]], output_dir: Path):
    """保存汇总 CSV"""
    rows = []

    for scheduler in sorted(all_raw_data.keys()):
        for rate in sorted(all_raw_data[scheduler].keys()):
            df = all_raw_data[scheduler][rate]
            tp = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)

            rows.append({
                "scheduler": scheduler,
                "rate": rate,
                "throughput": tp,
                "n_requests": len(df),
            })

    summary_df = pd.DataFrame(rows)
    csv_path = output_dir / "throughput_summary_old_method.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"  已保存: {csv_path.name}")

    print("\nThroughput Summary:")
    print(summary_df.to_string(index=False))


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(
        description="使用旧脚本方法分析实验 throughput（基于 my_request_metrics.csv）"
    )
    parser.add_argument(
        "batch_dir",
        type=str,
        help="Batch 目录路径 (例如: /home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402)"
    )
    parser.add_argument(
        "--window", "-w",
        type=float,
        default=5.0,
        help="滑动窗口大小（秒），默认: 5.0"
    )
    parser.add_argument(
        "--step", "-s",
        type=float,
        default=0.5,
        help="滑动步长（秒），默认: 0.5"
    )
    parser.add_argument(
        "--start-time",
        type=float,
        default=50.0,
        help="稳态起始时间（秒），默认: 50.0"
    )
    parser.add_argument(
        "--end-time",
        type=float,
        default=180.0,
        help="稳态结束时间（秒），默认: 180.0"
    )

    args = parser.parse_args()

    # 设置全局配置
    global THROUGHPUT_WINDOW, THROUGHPUT_STEP, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME
    THROUGHPUT_WINDOW = args.window
    THROUGHPUT_STEP = args.step
    THROUGHPUT_START_TIME = args.start_time
    THROUGHPUT_END_TIME = args.end_time

    batch_dir = Path(args.batch_dir).resolve()
    output_dir = batch_dir / "analysis_old_method"
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("Throughput 分析（旧方法 - 基于 my_request_metrics.csv）")
    print("=" * 70)
    print(f"输入目录: {batch_dir}")
    print(f"输出目录: {output_dir}")
    print(f"滑动窗口: {THROUGHPUT_WINDOW}s, 步长: {THROUGHPUT_STEP}s")
    print(f"稳态区间: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}]s")
    print()

    # 加载数据
    experiments = load_all_experiments(batch_dir)

    if not experiments:
        print("未找到有效实验。退出。")
        return

    print()

    # 计算滑动窗口 throughput
    print("计算滑动窗口 throughput...")
    all_throughput_data = {}


if __name__ == "__main__":
    main()

