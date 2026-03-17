#!/usr/bin/env python3
"""
sweep_draw.py - 针对 run_non_pd_sweep.py 结果的绘图脚本

自动发现 total_limit_* 目录，加载所有 WAIT + vLLM + Sarathi 数据并绘图。

目录结构:
    BASE_DIR/
    ├── total_limit_100/
    │   └── wait/
    ├── total_limit_200/
    │   └── wait/
    ├── vllm/
    └── sarathi/

使用方法：
    python sweep_draw.py
"""

import os
import re
import glob
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============ 调度器名称映射 (目录名 -> CSV 文件名后缀) ============
SCHEDULER_NAME_MAP = {
    "wait": "general_nested_booking_limit",
    "vllm": "vllm",
    "sarathi": "sarathi",
}

# ============ 颜色配置 ============
COLORS = [
    '#1f77b4',  # 蓝色
    '#ff7f0e',  # 橙色
    '#2ca02c',  # 绿色
    '#d62728',  # 红色
    '#9467bd',  # 紫色
    '#8c564b',  # 棕色
    '#e377c2',  # 粉色
    '#7f7f7f',  # 灰色
    '#bcbd22',  # 黄绿色
    '#17becf',  # 青色
]
MARKERS = ['o', 's', '^', 'D', 'v', 'p', 'h', '*', 'X', 'P']

# 固定的调度器颜色
SCHEDULER_COLORS = {
    "vllm": '#ff7f0e',      # 橙色
    "sarathi": '#2ca02c',   # 绿色
}
SCHEDULER_MARKERS = {
    "vllm": 's',
    "sarathi": '^',
}


def get_scheduler_style(scheduler: str, scheduler_index: int) -> Tuple[str, str]:
    """获取调度器的颜色和 marker"""
    color = SCHEDULER_COLORS.get(scheduler, COLORS[scheduler_index % len(COLORS)])
    marker = SCHEDULER_MARKERS.get(scheduler, MARKERS[scheduler_index % len(MARKERS)])
    return color, marker


# ============ 核心计算函数 ============
def compute_windowed_throughput(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
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
        throughput.append(tokens_in_window / actual_window if actual_window > 0 else 0)

    return time_axis, np.array(throughput)


def compute_bigwindow_throughput(df: pd.DataFrame, start_time: float, end_time: float) -> float:
    completed_at = df['completed_at'].values
    decode_tokens = df['decode_tokens'].values
    max_time = completed_at.max()
    actual_end = min(end_time, max_time)
    actual_window = actual_end - start_time
    if actual_window <= 0:
        return 0.0
    mask = (completed_at >= start_time) & (completed_at < actual_end)
    return decode_tokens[mask].sum() / actual_window


def compute_windowed_latency(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    completed_at = df['completed_at'].values
    arrived_at = df['arrived_at'].values
    e2e_latency = completed_at - arrived_at
    max_time = completed_at.max()
    time_axis = np.arange(0, max_time + step, step)

    latencies = []
    for t in time_axis:
        window_end = min(t + window, max_time)
        mask = (completed_at >= t) & (completed_at < window_end)
        latencies.append(e2e_latency[mask].mean() if mask.sum() > 0 else np.nan)

    return time_axis, np.array(latencies)


def compute_bigwindow_latency(df: pd.DataFrame, start_time: float, end_time: float) -> float:
    completed_at = df['completed_at'].values
    arrived_at = df['arrived_at'].values
    e2e_latency = completed_at - arrived_at
    max_time = completed_at.max()
    actual_end = min(end_time, max_time)
    mask = (completed_at >= start_time) & (completed_at < actual_end)
    return e2e_latency[mask].mean() if mask.sum() > 0 else np.nan


# ============ 数据加载 ============
def parse_folder_name(folder_name: str) -> Optional[float]:
    pattern = r'lambda([\d.]+)_req\d+_prefill\d+_decode\d+_\d{8}_\d{6}'
    match = re.match(pattern, folder_name)
    return float(match.group(1)) if match else None


def load_my_request_metrics(exp_dir: str, scheduler: str) -> Optional[pd.DataFrame]:
    scheduler_csv_name = SCHEDULER_NAME_MAP.get(scheduler, "general_nested_booking_limit")
    csv_path = os.path.join(exp_dir, f"my_request_metrics_{scheduler_csv_name}.csv")
    return pd.read_csv(csv_path) if os.path.exists(csv_path) else None


def load_all_experiments_for_scheduler(scheduler: str, scheduler_dir: str) -> Dict[float, pd.DataFrame]:
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
            continue
        df = load_my_request_metrics(folder, scheduler)
        if df is not None:
            experiments[rate] = df

    return experiments


def discover_total_limits(base_dir: str) -> List[int]:
    """自动发现所有 total_limit_* 目录"""
    pattern = os.path.join(base_dir, "total_limit_*")
    folders = glob.glob(pattern)
    limits = []
    for folder in folders:
        match = re.search(r'total_limit_(\d+)', folder)
        if match:
            limits.append(int(match.group(1)))
    return sorted(limits)


# ============ 绘图函数 ============
def plot_rate_vs_metrics(
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    schedulers: List[str],
    output_dir: str,
    start_time: float,
    end_time: float,
    filename: str = "rate_vs_metrics.png",
):
    """绘制 rate vs throughput/latency"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Rate vs Metrics (Window: [{start_time}, {end_time}] sec)", fontsize=14, fontweight='bold')

    for idx, scheduler in enumerate(schedulers):
        if scheduler not in all_raw_data or not all_raw_data[scheduler]:
            continue

        raw_data = all_raw_data[scheduler]
        rates = sorted(raw_data.keys())
        throughputs = [compute_bigwindow_throughput(raw_data[r], start_time, end_time) for r in rates]
        latencies = [compute_bigwindow_latency(raw_data[r], start_time, end_time) for r in rates]

        color, marker = get_scheduler_style(scheduler, idx)
        label = scheduler.upper() if "wait" not in scheduler.lower() else scheduler

        axes[0].plot(rates, throughputs, marker=marker, color=color, linewidth=2, markersize=6, label=label)
        axes[1].plot(rates, latencies, marker=marker, color=color, linewidth=2, markersize=6, label=label)

    axes[0].set_xlabel('Arrival Rate')
    axes[0].set_ylabel('Throughput (tokens/sec)')
    axes[0].set_title('Throughput vs Arrival Rate')
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Arrival Rate')
    axes[1].set_ylabel('E2E Latency (sec)')
    axes[1].set_title('Latency vs Arrival Rate')
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, filename)
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {filename}")


def plot_time_series_grid(
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    schedulers: List[str],
    output_dir: str,
    window: float,
    step: float,
    start_time: float,
    end_time: float,
    filename: str = "time_series.png",
):
    """绘制 2xN 时间序列图"""
    n_schedulers = len(schedulers)
    if n_schedulers == 0:
        return

    fig, axes = plt.subplots(2, n_schedulers, figsize=(5 * n_schedulers, 8))
    if n_schedulers == 1:
        axes = axes.reshape(2, 1)

    fig.suptitle(f"Time Series (window={window}s)", fontsize=14, fontweight='bold')

    for idx, scheduler in enumerate(schedulers):
        if scheduler not in all_raw_data or not all_raw_data[scheduler]:
            axes[0, idx].text(0.5, 0.5, 'No Data', ha='center', va='center', transform=axes[0, idx].transAxes)
            axes[1, idx].text(0.5, 0.5, 'No Data', ha='center', va='center', transform=axes[1, idx].transAxes)
            continue

        raw_data = all_raw_data[scheduler]
        rates = sorted(raw_data.keys())
        label = scheduler.upper() if "wait" not in scheduler.lower() else scheduler

        # Throughput
        ax = axes[0, idx]
        ax.set_title(f"{label} - Throughput", fontsize=10, fontweight='bold')
        for i, rate in enumerate(rates):
            time_axis, throughput = compute_windowed_throughput(raw_data[rate], window, step)
            ax.plot(time_axis, throughput, color=COLORS[i % len(COLORS)], alpha=0.8, linewidth=1, label=f'r={int(rate)}')
        ax.axvline(x=start_time, color='black', linestyle='--', alpha=0.5)
        ax.axvline(x=end_time, color='black', linestyle='--', alpha=0.5)
        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Throughput')
        ax.legend(fontsize=6, loc='best', ncol=2)
        ax.grid(True, alpha=0.3)

        # Latency
        ax = axes[1, idx]
        ax.set_title(f"{label} - Latency", fontsize=10, fontweight='bold')
        for i, rate in enumerate(rates):
            time_axis, latencies = compute_windowed_latency(raw_data[rate], window, step)
            ax.plot(time_axis, latencies, color=COLORS[i % len(COLORS)], alpha=0.8, linewidth=1, label=f'r={int(rate)}')
        ax.axvline(x=start_time, color='black', linestyle='--', alpha=0.5)
        ax.axvline(x=end_time, color='black', linestyle='--', alpha=0.5)
        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Latency (sec)')
        ax.legend(fontsize=6, loc='best', ncol=2)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, filename)
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {filename}")


def plot_limit_comparison(
    wait_data_by_limit: Dict[int, Dict[float, pd.DataFrame]],
    vllm_data: Dict[float, pd.DataFrame],
    sarathi_data: Dict[float, pd.DataFrame],
    output_dir: str,
    start_time: float,
    end_time: float,
):
    """绘制不同 total_limit 的对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"WAIT (different limits) vs vLLM vs Sarathi\n(Window: [{start_time}, {end_time}] sec)",
                 fontsize=14, fontweight='bold')

    # 绘制 vLLM
    if vllm_data:
        rates = sorted(vllm_data.keys())
        throughputs = [compute_bigwindow_throughput(vllm_data[r], start_time, end_time) for r in rates]
        latencies = [compute_bigwindow_latency(vllm_data[r], start_time, end_time) for r in rates]
        axes[0].plot(rates, throughputs, marker='s', color='#ff7f0e', linewidth=2.5, markersize=8, label='vLLM')
        axes[1].plot(rates, latencies, marker='s', color='#ff7f0e', linewidth=2.5, markersize=8, label='vLLM')

    # 绘制 Sarathi
    if sarathi_data:
        rates = sorted(sarathi_data.keys())
        throughputs = [compute_bigwindow_throughput(sarathi_data[r], start_time, end_time) for r in rates]
        latencies = [compute_bigwindow_latency(sarathi_data[r], start_time, end_time) for r in rates]
        axes[0].plot(rates, throughputs, marker='^', color='#2ca02c', linewidth=2.5, markersize=8, label='Sarathi')
        axes[1].plot(rates, latencies, marker='^', color='#2ca02c', linewidth=2.5, markersize=8, label='Sarathi')

    # 绘制各个 WAIT limit
    limits = sorted(wait_data_by_limit.keys())
    for i, limit in enumerate(limits):
        data = wait_data_by_limit[limit]
        if not data:
            continue
        rates = sorted(data.keys())
        throughputs = [compute_bigwindow_throughput(data[r], start_time, end_time) for r in rates]
        latencies = [compute_bigwindow_latency(data[r], start_time, end_time) for r in rates]

        color = COLORS[(i + 3) % len(COLORS)]  # 跳过 vLLM 和 Sarathi 的颜色
        marker = MARKERS[(i + 2) % len(MARKERS)]
        axes[0].plot(rates, throughputs, marker=marker, color=color, linewidth=1.5, markersize=5,
                     alpha=0.8, label=f'WAIT(L={limit})')
        axes[1].plot(rates, latencies, marker=marker, color=color, linewidth=1.5, markersize=5,
                     alpha=0.8, label=f'WAIT(L={limit})')

    axes[0].set_xlabel('Arrival Rate')
    axes[0].set_ylabel('Throughput (tokens/sec)')
    axes[0].set_title('Throughput vs Arrival Rate')
    axes[0].legend(fontsize=8, loc='best')
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Arrival Rate')
    axes[1].set_ylabel('E2E Latency (sec)')
    axes[1].set_title('Latency vs Arrival Rate')
    axes[1].legend(fontsize=8, loc='best')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "limit_comparison.png")
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: limit_comparison.png")


def save_summary_csv(
    wait_data_by_limit: Dict[int, Dict[float, pd.DataFrame]],
    vllm_data: Dict[float, pd.DataFrame],
    sarathi_data: Dict[float, pd.DataFrame],
    output_dir: str,
    start_time: float,
    end_time: float,
):
    """保存汇总 CSV"""
    rows = []

    # vLLM
    for rate, df in sorted(vllm_data.items()):
        rows.append({
            'scheduler': 'vllm',
            'total_limit': None,
            'rate': rate,
            'throughput': compute_bigwindow_throughput(df, start_time, end_time),
            'latency': compute_bigwindow_latency(df, start_time, end_time),
        })

    # Sarathi
    for rate, df in sorted(sarathi_data.items()):
        rows.append({
            'scheduler': 'sarathi',
            'total_limit': None,
            'rate': rate,
            'throughput': compute_bigwindow_throughput(df, start_time, end_time),
            'latency': compute_bigwindow_latency(df, start_time, end_time),
        })

    # WAIT
    for limit in sorted(wait_data_by_limit.keys()):
        for rate, df in sorted(wait_data_by_limit[limit].items()):
            rows.append({
                'scheduler': 'wait',
                'total_limit': limit,
                'rate': rate,
                'throughput': compute_bigwindow_throughput(df, start_time, end_time),
                'latency': compute_bigwindow_latency(df, start_time, end_time),
            })

    summary_df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, "summary.csv")
    summary_df.to_csv(csv_path, index=False)
    print(f"  已保存: summary.csv")


# ============ 主程序 ============
def main():
    # ============================================================
    # ============ 硬编码配置区域 ============
    # ============================================================

    # 输入目录 (run_non_pd_sweep.py 的输出目录)
    BASE_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/non_PD分离_sweep_default"

    # 输出目录
    OUTPUT_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/non_PD分离_sweep_default/分析结果"

    # 分析窗口配置
    WINDOW = 60              # 滑动窗口大小（秒）
    STEP = 10                # 滑动步长（秒）
    START_TIME = 300         # 大窗口起始时刻（秒）
    END_TIME = 800           # 大窗口结束时刻（秒）

    # ============================================================
    # ============ 配置区域结束 ============
    # ============================================================

    print("=" * 60)
    print("sweep_draw.py - Sweep 实验绘图脚本")
    print("=" * 60)
    print(f"输入目录: {BASE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"分析窗口: [{START_TIME}, {END_TIME}] 秒")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 自动发现 total_limit 目录
    total_limits = discover_total_limits(BASE_DIR)
    print(f"\n发现 total_limits: {total_limits}")

    # 加载 WAIT 数据 (按 limit 分组)
    wait_data_by_limit = {}
    for limit in total_limits:
        wait_dir = os.path.join(BASE_DIR, f"total_limit_{limit}", "wait")
        print(f"\n加载 WAIT (limit={limit})...")
        print(f"  目录: {wait_dir}")
        data = load_all_experiments_for_scheduler("wait", wait_dir)
        print(f"  找到 {len(data)} 个实验")
        wait_data_by_limit[limit] = data

        # 打印摘要
        for rate, df in sorted(data.items()):
            tp = compute_bigwindow_throughput(df, START_TIME, END_TIME)
            lt = compute_bigwindow_latency(df, START_TIME, END_TIME)
            print(f"    rate={rate}: throughput={tp:.2f}, latency={lt:.2f}s")

    # 加载 vLLM 数据
    vllm_dir = os.path.join(BASE_DIR, "vllm")
    print(f"\n加载 vLLM...")
    print(f"  目录: {vllm_dir}")
    vllm_data = load_all_experiments_for_scheduler("vllm", vllm_dir)
    print(f"  找到 {len(vllm_data)} 个实验")
    for rate, df in sorted(vllm_data.items()):
        tp = compute_bigwindow_throughput(df, START_TIME, END_TIME)
        lt = compute_bigwindow_latency(df, START_TIME, END_TIME)
        print(f"    rate={rate}: throughput={tp:.2f}, latency={lt:.2f}s")

    # 加载 Sarathi 数据
    sarathi_dir = os.path.join(BASE_DIR, "sarathi")
    print(f"\n加载 Sarathi...")
    print(f"  目录: {sarathi_dir}")
    sarathi_data = load_all_experiments_for_scheduler("sarathi", sarathi_dir)
    print(f"  找到 {len(sarathi_data)} 个实验")
    for rate, df in sorted(sarathi_data.items()):
        tp = compute_bigwindow_throughput(df, START_TIME, END_TIME)
        lt = compute_bigwindow_latency(df, START_TIME, END_TIME)
        print(f"    rate={rate}: throughput={tp:.2f}, latency={lt:.2f}s")

    # 绘图
    print("\n" + "=" * 60)
    print("绘制图表...")
    print("=" * 60)

    # 1. 总对比图 (所有 WAIT limits + vLLM + Sarathi)
    plot_limit_comparison(wait_data_by_limit, vllm_data, sarathi_data, OUTPUT_DIR, START_TIME, END_TIME)

    # 2. 为每个 limit 单独绘制 time series
    for limit in total_limits:
        all_data = {
            f"WAIT(L={limit})": wait_data_by_limit[limit],
            "vllm": vllm_data,
            "sarathi": sarathi_data,
        }
        plot_time_series_grid(all_data, list(all_data.keys()), OUTPUT_DIR, WINDOW, STEP, START_TIME, END_TIME,
                              filename=f"time_series_limit_{limit}.png")

    # 3. 保存汇总 CSV
    save_summary_csv(wait_data_by_limit, vllm_data, sarathi_data, OUTPUT_DIR, START_TIME, END_TIME)

    print(f"\n所有结果已保存到: {OUTPUT_DIR}")
    print("完成!")


if __name__ == "__main__":
    main()
