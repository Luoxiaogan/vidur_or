#!/usr/bin/env python3
"""
draw_non_pd_with_cp.py - 绘制包含 WAIT+CP 的实验结果

支持四种调度器:
1. WAIT (GeneralNestedBookingLimit)
2. WAIT+CP (GeneralNestedChunked, chunk_size=512)
3. vLLM
4. Sarathi

所有配置硬编码在 main() 中
"""

import os
import re
import glob
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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

SCHEDULER_COLORS = {
    "wait": '#1f77b4',      # 蓝色
    "wait_cp": '#9467bd',   # 紫色 (新增)
    "vllm": '#ff7f0e',      # 橙色
    "sarathi": '#2ca02c',   # 绿色
}
SCHEDULER_MARKERS = {
    "wait": 'o',
    "wait_cp": 'D',  # 新增
    "vllm": 's',
    "sarathi": '^',
}
SCHEDULER_LABELS = {
    "wait": "WAIT",
    "wait_cp": "WAIT+CP (chunk=512)",
    "vllm": "vLLM",
    "sarathi": "Sarathi",
}


def get_scheduler_style(scheduler: str, scheduler_index: int) -> Tuple[str, str, str]:
    """获取调度器的颜色、marker 和 label"""
    color = SCHEDULER_COLORS.get(scheduler, COLORS[scheduler_index % len(COLORS)])
    marker = SCHEDULER_MARKERS.get(scheduler, MARKERS[scheduler_index % len(MARKERS)])
    label = SCHEDULER_LABELS.get(scheduler, scheduler.upper())
    return color, marker, label


# ============ 核心计算函数 ============
def compute_windowed_throughput(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """滑动窗口 throughput 计算"""
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
    """计算大窗口内的 throughput"""
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


def compute_windowed_latency(df: pd.DataFrame, window: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """滑动窗口 latency 计算"""
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
    """计算大窗口内的平均 latency"""
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
def parse_lambda_folder_name(folder_name: str) -> Optional[float]:
    """解析 lambda 文件夹名，提取 rate"""
    pattern = r'lambda([\d.]+)_req\d+_prefill\d+_decode\d+_\d{8}_\d{6}'
    match = re.match(pattern, folder_name)
    if not match:
        return None
    return float(match.group(1))


def load_request_metrics(exp_dir: str, scheduler_type: str) -> Optional[pd.DataFrame]:
    """加载实验的 my_request_metrics CSV"""
    csv_path = os.path.join(exp_dir, f"my_request_metrics_{scheduler_type}.csv")
    if not os.path.exists(csv_path):
        return None
    return pd.read_csv(csv_path)


def load_wait_experiments(base_dir: str, wait_experiments: List[Tuple[int, int]],
                          subdir: str = "wait",
                          scheduler_type: str = "general_nested_booking_limit") -> Dict[float, pd.DataFrame]:
    """
    加载 WAIT 或 WAIT_CP 实验数据

    目录结构: base_dir/{subdir}/rate_{rate}_total_limit_{total_limit}/lambda.../
    """
    experiments = {}

    for rate, total_limit in wait_experiments:
        rate_dir = os.path.join(base_dir, subdir, f"rate_{rate}_total_limit_{total_limit}")
        if not os.path.exists(rate_dir):
            print(f"  警告: 目录不存在 {rate_dir}")
            continue

        # 找到 lambda 子目录
        lambda_folders = glob.glob(os.path.join(rate_dir, "lambda*"))
        if not lambda_folders:
            print(f"  警告: 没有找到 lambda 文件夹 in {rate_dir}")
            continue

        # 取第一个（应该只有一个）
        lambda_folder = lambda_folders[0]
        df = load_request_metrics(lambda_folder, scheduler_type)

        if df is not None:
            experiments[float(rate)] = df
            print(f"  加载: rate={rate}, total_limit={total_limit}")
        else:
            print(f"  警告: 缺少 CSV in {lambda_folder}")

    return experiments


def load_baseline_experiments(scheduler_dir: str, scheduler_type: str) -> Dict[float, pd.DataFrame]:
    """
    加载 vLLM/Sarathi 实验数据

    目录结构: scheduler_dir/lambda.../
    """
    if not os.path.exists(scheduler_dir):
        print(f"  警告: 目录不存在 {scheduler_dir}")
        return {}

    pattern = os.path.join(scheduler_dir, "lambda*")
    folders = sorted(glob.glob(pattern))

    experiments = {}
    for folder in folders:
        folder_name = os.path.basename(folder)
        rate = parse_lambda_folder_name(folder_name)
        if rate is None:
            print(f"  警告: 无法解析文件夹名 {folder_name}")
            continue

        df = load_request_metrics(folder, scheduler_type)
        if df is not None:
            experiments[rate] = df
        else:
            print(f"  警告: 缺少 CSV in {folder}")

    return experiments


# ============ 保存数据 ============
def save_throughput_data(scheduler: str, throughput_data: Dict[float, Tuple[np.ndarray, np.ndarray]],
                         output_dir: str, step: float):
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
    csv_path = os.path.join(output_dir, f"throughput_{scheduler}.csv")
    df.to_csv(csv_path, index=False)
    print(f"    已保存: throughput_{scheduler}.csv")


def save_latency_data(scheduler: str, latency_data: Dict[float, Tuple[np.ndarray, np.ndarray]],
                      output_dir: str, step: float):
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
    csv_path = os.path.join(output_dir, f"latency_{scheduler}.csv")
    df.to_csv(csv_path, index=False)
    print(f"    已保存: latency_{scheduler}.csv")


# ============ 绘图 ============
def plot_time_series_2xN(
    all_throughput_data: Dict[str, Dict[float, Tuple[np.ndarray, np.ndarray]]],
    all_latency_data: Dict[str, Dict[float, Tuple[np.ndarray, np.ndarray]]],
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    schedulers: List[str],
    output_dir: str,
    throughput_window: float,
    throughput_start_time: float,
    throughput_end_time: float,
    latency_window: float,
    latency_start_time: float,
    latency_end_time: float,
):
    """绘制 2xN 的时间序列图"""
    n_schedulers = len(schedulers)

    fig, axes = plt.subplots(2, n_schedulers, figsize=(6 * n_schedulers, 10))

    if n_schedulers == 1:
        axes = axes.reshape(2, 1)

    fig.suptitle(f"Time Series Analysis\n(window={throughput_window}s)",
                 fontsize=14, fontweight='bold')

    # 第1行: Throughput
    for idx, scheduler in enumerate(schedulers):
        ax = axes[0, idx]
        _, _, label = get_scheduler_style(scheduler, idx)
        ax.set_title(f"{label} - Throughput", fontsize=11, fontweight='bold')

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
                    raw_data[rate], throughput_start_time, throughput_end_time
                )

            ax.plot(time_axis, throughput, color=color, alpha=0.8, linewidth=1.5,
                    label=f'rate={rate:.0f}, avg={avg_throughput:.2f}')
            ax.axhline(y=avg_throughput, color=color, linestyle='--', alpha=0.6, linewidth=1)

        ax.axvline(x=throughput_start_time, color='black', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=throughput_end_time, color='black', linestyle='--', alpha=0.7, linewidth=1)

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Throughput (tokens/sec)')
        ax.legend(fontsize=7, loc='best')
        ax.grid(True, alpha=0.3)

    # 第2行: Latency
    for idx, scheduler in enumerate(schedulers):
        ax = axes[1, idx]
        _, _, label = get_scheduler_style(scheduler, idx)
        ax.set_title(f"{label} - Latency", fontsize=11, fontweight='bold')

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
                    raw_data[rate], latency_start_time, latency_end_time
                )

            ax.plot(time_axis, latencies, color=color, alpha=0.8, linewidth=1.5,
                    label=f'rate={rate:.0f}, avg={avg_latency:.2f}s')

            if not np.isnan(avg_latency):
                ax.axhline(y=avg_latency, color=color, linestyle='--', alpha=0.6, linewidth=1)

        ax.axvline(x=latency_start_time, color='black', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=latency_end_time, color='black', linestyle='--', alpha=0.7, linewidth=1)

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
    schedulers: List[str],
    output_dir: str,
    throughput_start_time: float,
    throughput_end_time: float,
    latency_start_time: float,
    latency_end_time: float,
):
    """绘制 rate vs metrics 图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Rate vs Metrics (BigWindow: [{throughput_start_time}, {throughput_end_time}] sec)",
                 fontsize=14, fontweight='bold')

    for idx, scheduler in enumerate(schedulers):
        if scheduler not in all_raw_data or not all_raw_data[scheduler]:
            continue

        raw_data = all_raw_data[scheduler]
        rates = sorted(raw_data.keys())

        throughputs = []
        latencies = []

        for rate in rates:
            df = raw_data[rate]
            throughputs.append(compute_bigwindow_throughput(df, throughput_start_time, throughput_end_time))
            latencies.append(compute_bigwindow_latency(df, latency_start_time, latency_end_time))

        color, marker, label = get_scheduler_style(scheduler, idx)

        axes[0].plot(rates, throughputs, marker=marker, color=color, linewidth=2,
                     markersize=8, label=label)
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


def save_summary_csv(
    all_raw_data: Dict[str, Dict[float, pd.DataFrame]],
    schedulers: List[str],
    output_dir: str,
    throughput_start_time: float,
    throughput_end_time: float,
    latency_start_time: float,
    latency_end_time: float,
):
    """保存汇总数据到 CSV"""
    rows = []

    for scheduler in schedulers:
        if scheduler not in all_raw_data:
            continue

        raw_data = all_raw_data[scheduler]
        _, _, label = get_scheduler_style(scheduler, 0)

        for rate in sorted(raw_data.keys()):
            df = raw_data[rate]
            throughput = compute_bigwindow_throughput(df, throughput_start_time, throughput_end_time)
            latency = compute_bigwindow_latency(df, latency_start_time, latency_end_time)

            rows.append({
                'scheduler': label,
                'rate': rate,
                'throughput': throughput,
                'latency': latency,
            })

    summary_df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, "summary.csv")
    summary_df.to_csv(csv_path, index=False)
    print(f"  已保存: summary.csv")


# ============ 主程序 ============
def main():
    # ============================================================
    # ============ 硬编码配置区域 - 修改这里 ============
    # ============================================================

    # 基础目录
    BASE_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/non_PD分离_default_baseline_bigger_chunk_4096_sarathi"

    # 输出目录 (新的)
    OUTPUT_DIR = "/home/lg/vidur_or/new_experiments_for_revision/exp_1_wait/non_PD分离_default_baseline_bigger_chunk_4096_sarathi/new_分析结果"

    # WAIT 实验: (rate, total_limit) 组合
    WAIT_EXPERIMENTS = [
        (14, 20),
        (15, 20),
        (16, 40),
        (17, 100),
        (18, 525),
        (19, 725),
        (20, 725),
        (21, 725),
    ]

    # 是否加载各调度器
    LOAD_WAIT = True
    LOAD_WAIT_CP = True  # 新增
    LOAD_VLLM = True
    LOAD_SARATHI = True

    # 分析配置
    THROUGHPUT_WINDOW = 60       # 滑动窗口大小（秒）
    THROUGHPUT_STEP = 10         # 滑动步长（秒）
    THROUGHPUT_START_TIME = 120  # 大窗口起始时刻（秒）
    THROUGHPUT_END_TIME = 1500   # 大窗口结束时刻（秒）

    LATENCY_WINDOW = THROUGHPUT_WINDOW
    LATENCY_STEP = THROUGHPUT_STEP
    LATENCY_START_TIME = THROUGHPUT_START_TIME
    LATENCY_END_TIME = THROUGHPUT_END_TIME

    # ============================================================
    # ============ 配置区域结束 ============
    # ============================================================

    print("=" * 60)
    print("draw_non_pd_with_cp.py - 绘图脚本 (包含 WAIT+CP)")
    print("=" * 60)
    print(f"基础目录: {BASE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"WAIT 实验: {len(WAIT_EXPERIMENTS)} 组")
    print(f"大窗口范围: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}] 秒")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_throughput_data = {}
    all_latency_data = {}
    all_raw_data = {}
    schedulers = []

    # ============ 加载 WAIT 数据 ============
    if LOAD_WAIT:
        print("\n加载 WAIT 数据...")
        wait_experiments = load_wait_experiments(
            BASE_DIR, WAIT_EXPERIMENTS,
            subdir="wait",
            scheduler_type="general_nested_booking_limit"
        )
        print(f"  共加载 {len(wait_experiments)} 个实验")

        if wait_experiments:
            schedulers.append("wait")
            throughput_data = {}
            latency_data = {}

            for rate, df in sorted(wait_experiments.items()):
                time_axis_t, throughput = compute_windowed_throughput(df, THROUGHPUT_WINDOW, THROUGHPUT_STEP)
                throughput_data[rate] = (time_axis_t, throughput)

                time_axis_l, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
                latency_data[rate] = (time_axis_l, latencies)

                avg_t = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
                avg_l = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)
                print(f"    rate={rate}: throughput={avg_t:.2f} tokens/s, latency={avg_l:.2f}s")

            all_throughput_data["wait"] = throughput_data
            all_latency_data["wait"] = latency_data
            all_raw_data["wait"] = wait_experiments

            save_throughput_data("wait", throughput_data, OUTPUT_DIR, THROUGHPUT_STEP)
            save_latency_data("wait", latency_data, OUTPUT_DIR, LATENCY_STEP)

    # ============ 加载 WAIT+CP 数据 (新增) ============
    if LOAD_WAIT_CP:
        print("\n加载 WAIT+CP 数据...")
        wait_cp_experiments = load_wait_experiments(
            BASE_DIR, WAIT_EXPERIMENTS,
            subdir="wait_cp",  # 新目录
            scheduler_type="general_nested_chunked"  # 新调度器类型
        )
        print(f"  共加载 {len(wait_cp_experiments)} 个实验")

        if wait_cp_experiments:
            schedulers.append("wait_cp")
            throughput_data = {}
            latency_data = {}

            for rate, df in sorted(wait_cp_experiments.items()):
                time_axis_t, throughput = compute_windowed_throughput(df, THROUGHPUT_WINDOW, THROUGHPUT_STEP)
                throughput_data[rate] = (time_axis_t, throughput)

                time_axis_l, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
                latency_data[rate] = (time_axis_l, latencies)

                avg_t = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
                avg_l = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)
                print(f"    rate={rate}: throughput={avg_t:.2f} tokens/s, latency={avg_l:.2f}s")

            all_throughput_data["wait_cp"] = throughput_data
            all_latency_data["wait_cp"] = latency_data
            all_raw_data["wait_cp"] = wait_cp_experiments

            save_throughput_data("wait_cp", throughput_data, OUTPUT_DIR, THROUGHPUT_STEP)
            save_latency_data("wait_cp", latency_data, OUTPUT_DIR, LATENCY_STEP)

    # ============ 加载 vLLM 数据 ============
    if LOAD_VLLM:
        print("\n加载 vLLM 数据...")
        vllm_dir = os.path.join(BASE_DIR, "vllm")
        vllm_experiments = load_baseline_experiments(vllm_dir, "vllm")
        print(f"  共加载 {len(vllm_experiments)} 个实验")

        if vllm_experiments:
            schedulers.append("vllm")
            throughput_data = {}
            latency_data = {}

            for rate, df in sorted(vllm_experiments.items()):
                time_axis_t, throughput = compute_windowed_throughput(df, THROUGHPUT_WINDOW, THROUGHPUT_STEP)
                throughput_data[rate] = (time_axis_t, throughput)

                time_axis_l, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
                latency_data[rate] = (time_axis_l, latencies)

                avg_t = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
                avg_l = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)
                print(f"    rate={rate}: throughput={avg_t:.2f} tokens/s, latency={avg_l:.2f}s")

            all_throughput_data["vllm"] = throughput_data
            all_latency_data["vllm"] = latency_data
            all_raw_data["vllm"] = vllm_experiments

            save_throughput_data("vllm", throughput_data, OUTPUT_DIR, THROUGHPUT_STEP)
            save_latency_data("vllm", latency_data, OUTPUT_DIR, LATENCY_STEP)

    # ============ 加载 Sarathi 数据 ============
    if LOAD_SARATHI:
        print("\n加载 Sarathi 数据...")
        sarathi_dir = os.path.join(BASE_DIR, "sarathi")
        sarathi_experiments = load_baseline_experiments(sarathi_dir, "sarathi")
        print(f"  共加载 {len(sarathi_experiments)} 个实验")

        if sarathi_experiments:
            schedulers.append("sarathi")
            throughput_data = {}
            latency_data = {}

            for rate, df in sorted(sarathi_experiments.items()):
                time_axis_t, throughput = compute_windowed_throughput(df, THROUGHPUT_WINDOW, THROUGHPUT_STEP)
                throughput_data[rate] = (time_axis_t, throughput)

                time_axis_l, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
                latency_data[rate] = (time_axis_l, latencies)

                avg_t = compute_bigwindow_throughput(df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
                avg_l = compute_bigwindow_latency(df, LATENCY_START_TIME, LATENCY_END_TIME)
                print(f"    rate={rate}: throughput={avg_t:.2f} tokens/s, latency={avg_l:.2f}s")

            all_throughput_data["sarathi"] = throughput_data
            all_latency_data["sarathi"] = latency_data
            all_raw_data["sarathi"] = sarathi_experiments

            save_throughput_data("sarathi", throughput_data, OUTPUT_DIR, THROUGHPUT_STEP)
            save_latency_data("sarathi", latency_data, OUTPUT_DIR, LATENCY_STEP)

    # ============ 绘图 ============
    if schedulers:
        print("\n绘制图表...")
        plot_time_series_2xN(
            all_throughput_data, all_latency_data, all_raw_data,
            schedulers, OUTPUT_DIR,
            THROUGHPUT_WINDOW, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME,
            LATENCY_WINDOW, LATENCY_START_TIME, LATENCY_END_TIME,
        )
        plot_rate_vs_metrics(
            all_raw_data, schedulers, OUTPUT_DIR,
            THROUGHPUT_START_TIME, THROUGHPUT_END_TIME,
            LATENCY_START_TIME, LATENCY_END_TIME,
        )
        save_summary_csv(
            all_raw_data, schedulers, OUTPUT_DIR,
            THROUGHPUT_START_TIME, THROUGHPUT_END_TIME,
            LATENCY_START_TIME, LATENCY_END_TIME,
        )
    else:
        print("\n警告: 没有加载到任何数据，无法绘图")

    print(f"\n所有结果已保存到: {OUTPUT_DIR}")
    print("完成!")


if __name__ == "__main__":
    main()
