#!/usr/bin/env python3
"""
analyze_latency_old_method.py - 滑动窗口 E2E Latency 分析（适配新实验结构）

基于 my_request_metrics_*.csv 计算 E2E latency (completed_at - arrived_at)
使用旧脚本的滑动窗口方法，但适配新实验目录结构

使用方法：
    python analyze_latency_old_method.py /home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402
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
LATENCY_WINDOW = 5.0
LATENCY_STEP = 0.5
LATENCY_START_TIME = 25.0
LATENCY_END_TIME = 100.0

# 调度器名称映射 (目录名前缀 -> CSV文件名后缀)
SCHEDULER_NAME_MAP = {
    "WCP": "general_nested_chunked",
    "vLLM": "vllm",
    "Sarathi": "sarathi",
}

# 颜色配置
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


# ============ 核心计算（完全保留旧脚本逻辑） ============
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
    """
    计算 [start_time, end_time] 大窗口内完成的请求的平均 E2E latency
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
def save_latency_data(scheduler: str, latency_data: Dict[int, Tuple[np.ndarray, np.ndarray]],
                      output_dir: Path, step: float):
    """保存 latency 数据到 CSV"""
    if not latency_data:
        return

    max_len = max(len(t) for t, _ in latency_data.values())
    data = {'time': np.arange(0, max_len * step, step)[:max_len]}

    for rate in sorted(latency_data.keys()):
        time_axis, latencies = latency_data[rate]
        padded = np.full(max_len, np.nan)
        padded[:len(latencies)] = latencies
        data[f'rate_{rate}'] = padded

    df = pd.DataFrame(data)
    csv_path = output_dir / f"latency_{scheduler}.csv"
    df.to_csv(csv_path, index=False)
    print(f"  已保存: {csv_path.name}")


# ============ 绘图（完全保留旧脚本逻辑） ============
def plot_latency_time_series(
    all_latency_data: Dict[str, Dict[int, Tuple[np.ndarray, np.ndarray]]],
    all_raw_data: Dict[str, Dict[int, pd.DataFrame]],
    output_dir: Path
):
    """
    绘制 1x3 的 latency 时间序列图
    """
    schedulers = ['WCP', 'Sarathi', 'vLLM']
    n_schedulers = sum(1 for s in schedulers if s in all_latency_data)

    if n_schedulers == 0:
        print("没有数据可绘制")
        return

    fig, axes = plt.subplots(1, n_schedulers, figsize=(6 * n_schedulers, 6))
    if n_schedulers == 1:
        axes = [axes]

    fig.suptitle(f"E2E Latency Time Series (window={LATENCY_WINDOW}s, step={LATENCY_STEP}s)",
                 fontsize=14, fontweight='bold')

    ax_idx = 0
    for scheduler in schedulers:
        if scheduler not in all_latency_data:
            continue

        ax = axes[ax_idx]
        ax_idx += 1

        ax.set_title(scheduler, fontsize=12, fontweight='bold')
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
            label = f'rate={rate}, avg={avg_latency:.3f}s' if not np.isnan(avg_latency) else f'rate={rate}'
            ax.plot(time_axis, latencies, color=color, alpha=0.8, linewidth=1.5, label=label)

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
    fig_path = output_dir / "latency_time_series_old_method.png"
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {fig_path.name}")


def plot_rate_vs_latency_summary(all_raw_data: Dict[str, Dict[int, pd.DataFrame]], output_dir: Path):
    """绘制 rate vs latency 汇总图"""
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
        latencies = []

        for rate in sorted(all_raw_data[scheduler].keys()):
            df = all_raw_data[scheduler][rate]
            lat = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)
            rates.append(rate)
            latencies.append(lat)

        color = scheduler_colors.get(scheduler, '#333333')
        marker = scheduler_markers.get(scheduler, 'o')

        ax.plot(rates, latencies, marker=marker, color=color, linewidth=2,
                markersize=8, label=scheduler)

    ax.set_xlabel('Arrival Rate (requests/s)')
    ax.set_ylabel('E2E Latency (sec)')
    ax.set_title(f'Latency vs Arrival Rate (Steady-state: [{LATENCY_START_TIME}, {LATENCY_END_TIME}]s)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig_path = output_dir / "rate_vs_latency_old_method.png"
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {fig_path.name}")


def save_summary_csv(all_raw_data: Dict[str, Dict[int, pd.DataFrame]], output_dir: Path):
    """保存汇总 CSV"""
    rows = []

    for scheduler in sorted(all_raw_data.keys()):
        for rate in sorted(all_raw_data[scheduler].keys()):
            df = all_raw_data[scheduler][rate]
            lat = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)

            # 计算其他统计量
            e2e_latency = df['completed_at'] - df['arrived_at']
            p50 = e2e_latency.median()
            p99 = e2e_latency.quantile(0.99)

            rows.append({
                "scheduler": scheduler,
                "rate": rate,
                "mean_latency": lat,
                "p50_latency": p50,
                "p99_latency": p99,
                "n_requests": len(df),
            })

    summary_df = pd.DataFrame(rows)
    csv_path = output_dir / "latency_summary_old_method.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"  已保存: {csv_path.name}")

    print("\nLatency Summary:")
    print(summary_df.to_string(index=False))


def print_comparison_table(all_raw_data: Dict[str, Dict[int, pd.DataFrame]]):
    """打印 WCP vs Sarathi 对比表"""
    print("\n" + "=" * 80)
    print("Comparison: WCP vs Sarathi (Gap calculation)")
    print("=" * 80)
    print(f"{'Rate':>6} | {'WCP (s)':>10} | {'Sarathi (s)':>12} | {'Gap':>10} | {'Status':>8}")
    print("-" * 80)

    if "WCP" not in all_raw_data or "Sarathi" not in all_raw_data:
        print("需要 WCP 和 Sarathi 数据才能对比")
        return

    for rate in sorted(all_raw_data["WCP"].keys()):
        if rate not in all_raw_data["Sarathi"]:
            continue

        wcp_lat = compute_bigwindow_latency(all_raw_data["WCP"][rate], LATENCY_START_TIME, LATENCY_END_TIME)
        sar_lat = compute_bigwindow_latency(all_raw_data["Sarathi"][rate], LATENCY_START_TIME, LATENCY_END_TIME)

        if not np.isnan(wcp_lat) and not np.isnan(sar_lat):
            gap_pct = (wcp_lat - sar_lat) / sar_lat * 100
            status = "WIN" if gap_pct < -1 else "LOSE"
            print(f"{rate:>6} | {wcp_lat:>10.3f} | {sar_lat:>12.3f} | {gap_pct:>+9.1f}% | {status:>8}")


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(
        description="使用旧脚本方法分析实验 latency（基于 my_request_metrics.csv）"
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
        default=25.0,
        help="稳态起始时间（秒），默认: 25.0"
    )
    parser.add_argument(
        "--end-time",
        type=float,
        default=100.0,
        help="稳态结束时间（秒），默认: 100.0"
    )

    args = parser.parse_args()

    # 设置全局配置
    global LATENCY_WINDOW, LATENCY_STEP, LATENCY_START_TIME, LATENCY_END_TIME
    LATENCY_WINDOW = args.window
    LATENCY_STEP = args.step
    LATENCY_START_TIME = args.start_time
    LATENCY_END_TIME = args.end_time

    batch_dir = Path(args.batch_dir).resolve()
    output_dir = batch_dir / "analysis_old_method"
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("Latency 分析（旧方法 - 基于 my_request_metrics.csv）")
    print("=" * 70)
    print(f"输入目录: {batch_dir}")
    print(f"输出目录: {output_dir}")
    print(f"滑动窗口: {LATENCY_WINDOW}s, 步长: {LATENCY_STEP}s")
    print(f"稳态区间: [{LATENCY_START_TIME}, {LATENCY_END_TIME}]s")
    print()

    # 加载数据
    experiments = load_all_experiments(batch_dir)

    if not experiments:
        print("未找到有效实验。退出。")
        return

    print()

    # 计算滑动窗口 latency
    print("计算滑动窗口 latency...")
    all_latency_data = {}

    for scheduler in sorted(experiments.keys()):
        latency_data = {}
        for rate, df in sorted(experiments[scheduler].items()):
            time_axis, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
            latency_data[rate] = (time_axis, latencies)
            valid_latencies = latencies[~np.isnan(latencies)]
            if len(valid_latencies) > 0:
                print(f"  {scheduler} rate={rate}: {len(time_axis)} 时间点, max={valid_latencies.max():.3f}s")
            else:
                print(f"  {scheduler} rate={rate}: {len(time_axis)} 时间点, 无有效数据")

        all_latency_data[scheduler] = latency_data
        save_latency_data(scheduler, latency_data, output_dir, LATENCY_STEP)

    print()

    # 绘图
    print("生成图表...")
    plot_latency_time_series(all_latency_data, experiments, output_dir)
    plot_rate_vs_latency_summary(experiments, output_dir)

    # 保存汇总
    print()
    print("保存汇总...")
    save_summary_csv(experiments, output_dir)

    # 打印对比
    print_comparison_table(experiments)

    print()
    print("=" * 70)
    print(f"分析完成! 结果保存在: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
