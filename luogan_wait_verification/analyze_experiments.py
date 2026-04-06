#!/usr/bin/env python3
"""
Analyze experiment results from batch directory.

Usage:
    python analyze_experiments.py /home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402
    python analyze_experiments.py ./single/batch_20260406_170402

Automatically detects experiment structure and generates:
- Latency time series plots (sliding window)
- Throughput analysis (using vidur's throughput.csv)
- Rate vs metrics summary
- Summary CSV with all statistics
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============ Configuration ============
# Sliding window parameters (request index based)
LATENCY_WINDOW = 100
LATENCY_STEP = 50

# Throughput analysis parameters (time based)
THROUGHPUT_TIME_WINDOW = 5.0  # 5-second window for averaging
THROUGHPUT_START_TIME = 25.0  # Start of steady-state period
THROUGHPUT_END_TIME = 100.0   # End of steady-state period

# Colors
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
SCHEDULER_COLORS = {
    "WCP": '#1f77b4',
    "Sarathi": '#2ca02c',
    "vLLM": '#ff7f0e',
}
SCHEDULER_MARKERS = {
    "WCP": 'o',
    "Sarathi": '^',
    "vLLM": 's',
}


# ============ Data Loading ============
def parse_experiment_folder(folder_name: str) -> Optional[Tuple[str, int]]:
    """
    Parse experiment folder name.

    Expected formats:
    - WCP_cs256_tl21_r12 -> ("WCP", 12)
    - Sarathi_cs512_r12 -> ("Sarathi", 12)
    - vLLM_r12 -> ("vLLM", 12)
    """
    match = re.match(r'(WCP|Sarathi|vLLM).*?_r(\d+)', folder_name)
    if not match:
        return None

    scheduler = match.group(1)
    rate = int(match.group(2))
    return scheduler, rate


def find_csv_files(exp_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Find request_metrics and throughput CSV files in experiment directory.

    Returns:
        (request_metrics_path, throughput_path)
    """
    # Find request_metrics CSV
    req_pattern = exp_dir.rglob("request_metrics_*.csv")
    req_files = list(req_pattern)
    req_csv = req_files[0] if req_files else None

    # Find throughput CSV
    tp_pattern = exp_dir.rglob("throughput_*.csv")
    tp_files = list(tp_pattern)
    tp_csv = tp_files[0] if tp_files else None

    return req_csv, tp_csv


def load_throughput_data(tp_csv: Path) -> pd.DataFrame:
    """
    Load and process throughput CSV from vidur.

    The throughput CSV contains:
    - Time (sec): timestamp
    - throughput: cumulative decode tokens

    Returns DataFrame with:
    - time: timestamp
    - cumulative_tokens: cumulative decode tokens
    - instant_throughput: instantaneous throughput (tokens/sec)
    """
    df = pd.read_csv(tp_csv)
    df.columns = ['time', 'cumulative_tokens']

    # Calculate instantaneous throughput using time differences
    df['dt'] = df['time'].diff()
    df['d_tokens'] = df['cumulative_tokens'].diff()

    # Instant throughput = delta tokens / delta time
    df['instant_throughput'] = df['d_tokens'] / df['dt']

    # Handle NaN in first row
    df.loc[0, 'instant_throughput'] = 0

    return df


def load_experiments(batch_dir: Path) -> Tuple[Dict, Dict]:
    """
    Load all experiments from batch directory.

    Returns:
        (request_metrics_data, throughput_data)
        where each is {scheduler: {rate: DataFrame}}
    """
    req_data = {}
    tp_data = {}

    if not batch_dir.exists():
        print(f"Error: Directory does not exist: {batch_dir}")
        sys.exit(1)

    print(f"Scanning directory: {batch_dir}")
    print("-" * 60)

    for item in batch_dir.iterdir():
        if not item.is_dir():
            continue

        parsed = parse_experiment_folder(item.name)
        if not parsed:
            continue

        scheduler, rate = parsed
        req_csv, tp_csv = find_csv_files(item)

        if req_csv is None:
            print(f"  [SKIP] {item.name}: No request_metrics CSV found")
            continue

        try:
            # Load request metrics
            req_df = pd.read_csv(req_csv)

            # Load throughput data if available
            if tp_csv:
                tp_df = load_throughput_data(tp_csv)
                tp_data.setdefault(scheduler, {})[rate] = tp_df
                tp_status = f"+throughput ({len(tp_df)} points)"
            else:
                tp_status = "no throughput"

            req_data.setdefault(scheduler, {})[rate] = req_df
            print(f"  [OK] {item.name}: {len(req_df)} requests, {tp_status}")

        except Exception as e:
            print(f"  [ERROR] {item.name}: {e}")

    print("-" * 60)
    total_req = sum(len(rates) for rates in req_data.values())
    total_tp = sum(len(rates) for rates in tp_data.values())
    print(f"Loaded {total_req} experiments ({total_tp} with throughput)")

    for scheduler in sorted(req_data.keys()):
        rates = sorted(req_data[scheduler].keys())
        has_tp = scheduler in tp_data
        print(f"  {scheduler}: {rates} {'(+TP)' if has_tp else ''}")

    return req_data, tp_data


# ============ Latency Analysis ============
def compute_windowed_latency(df: pd.DataFrame, window: int, step: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute sliding window latency based on request index.
    """
    n = len(df)
    indices = []
    latencies = []

    for i in range(0, n - window + 1, step):
        window_data = df.iloc[i:i+window]
        avg_latency = window_data['request_e2e_time'].mean()
        center = i + window // 2
        indices.append(center)
        latencies.append(avg_latency)

    return np.array(indices), np.array(latencies)


def compute_latency_stats(df: pd.DataFrame) -> Dict[str, float]:
    """Compute latency statistics."""
    return {
        "mean_latency": df['request_e2e_time'].mean(),
        "p50_latency": df['request_e2e_time'].median(),
        "p99_latency": df['request_e2e_time'].quantile(0.99),
        "n_requests": len(df),
    }


# ============ Throughput Analysis ============
def compute_throughput_stats(tp_df: pd.DataFrame, start_time: float, end_time: float) -> Dict[str, float]:
    """
    Compute throughput statistics from vidur throughput data.

    Uses the steady-state period [start_time, end_time].
    """
    # Filter data in the time window
    mask = (tp_df['time'] >= start_time) & (tp_df['time'] <= end_time)
    window_data = tp_df[mask]

    if len(window_data) < 2:
        return {
            "mean_throughput": 0.0,
            "p99_throughput": 0.0,
            "total_tokens": 0.0,
        }

    # Method 1: Average of instantaneous throughputs
    mean_tp = window_data['instant_throughput'].mean()
    p99_tp = window_data['instant_throughput'].quantile(0.99)

    # Method 2: Total tokens / time span (more accurate for overall throughput)
    time_span = window_data['time'].iloc[-1] - window_data['time'].iloc[0]
    tokens_in_window = window_data['cumulative_tokens'].iloc[-1] - window_data['cumulative_tokens'].iloc[0]
    overall_tp = tokens_in_window / time_span if time_span > 0 else 0

    return {
        "mean_throughput": mean_tp,
        "overall_throughput": overall_tp,
        "p99_throughput": p99_tp,
        "total_tokens": window_data['cumulative_tokens'].iloc[-1],
        "time_span": time_span,
    }


def compute_windowed_throughput_from_vidur(tp_df: pd.DataFrame, window_size: float, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute sliding window throughput from vidur throughput data.

    Uses time-based windows on the instantaneous throughput.
    """
    max_time = tp_df['time'].max()
    time_axis = np.arange(0, max_time, step)
    throughputs = []

    for t in time_axis:
        window_end = min(t + window_size, max_time)
        mask = (tp_df['time'] >= t) & (tp_df['time'] < window_end)

        if mask.sum() > 0:
            avg_tp = tp_df.loc[mask, 'instant_throughput'].mean()
            throughputs.append(avg_tp)
        else:
            throughputs.append(0)

    return time_axis, np.array(throughputs)


# ============ Plotting ============
def plot_latency_time_series(req_data: Dict, output_dir: Path):
    """Plot latency time series for all schedulers."""
    schedulers = ['WCP', 'Sarathi', 'vLLM']
    n_schedulers = sum(1 for s in schedulers if s in req_data)

    if n_schedulers == 0:
        print("No data to plot for latency time series")
        return

    fig, axes = plt.subplots(1, n_schedulers, figsize=(6 * n_schedulers, 6))
    if n_schedulers == 1:
        axes = [axes]

    fig.suptitle(f"E2E Latency Time Series (window={LATENCY_WINDOW} requests)",
                 fontsize=14, fontweight='bold')

    ax_idx = 0
    for scheduler in schedulers:
        if scheduler not in req_data:
            continue

        ax = axes[ax_idx]
        ax_idx += 1

        for i, rate in enumerate(sorted(req_data[scheduler].keys())):
            df = req_data[scheduler][rate]
            indices, latencies = compute_windowed_latency(df, LATENCY_WINDOW, LATENCY_STEP)
            color = COLORS[i % len(COLORS)]
            ax.plot(indices, latencies, label=f'rate={rate}', color=color, linewidth=1.5)

        ax.set_xlabel('Request Index')
        ax.set_ylabel('E2E Latency (sec)')
        ax.set_title(f'{scheduler}', fontsize=12, fontweight='bold')
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = output_dir / 'latency_time_series.png'
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {fig_path}")


def plot_throughput_time_series(tp_data: Dict, output_dir: Path):
    """Plot throughput time series for all schedulers."""
    schedulers = ['WCP', 'Sarathi', 'vLLM']
    n_schedulers = sum(1 for s in schedulers if s in tp_data)

    if n_schedulers == 0:
        print("No throughput data to plot")
        return

    fig, axes = plt.subplots(1, n_schedulers, figsize=(6 * n_schedulers, 6))
    if n_schedulers == 1:
        axes = [axes]

    fig.suptitle(f"Throughput Time Series (window={THROUGHPUT_TIME_WINDOW}s)",
                 fontsize=14, fontweight='bold')

    ax_idx = 0
    for scheduler in schedulers:
        if scheduler not in tp_data:
            continue

        ax = axes[ax_idx]
        ax_idx += 1

        for i, rate in enumerate(sorted(tp_data[scheduler].keys())):
            tp_df = tp_data[scheduler][rate]
            time_axis, throughputs = compute_windowed_throughput_from_vidur(
                tp_df, THROUGHPUT_TIME_WINDOW, 1.0
            )
            color = COLORS[i % len(COLORS)]
            ax.plot(time_axis, throughputs, label=f'rate={rate}', color=color, linewidth=1.5)

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Throughput (tokens/sec)')
        ax.set_title(f'{scheduler}', fontsize=12, fontweight='bold')
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = output_dir / 'throughput_time_series.png'
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {fig_path}")


def plot_rate_vs_metrics(req_data: Dict, tp_data: Dict, output_dir: Path):
    """Plot rate vs mean latency and rate vs mean throughput."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Rate vs Metrics (Steady-state: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}]s)",
                 fontsize=14, fontweight='bold')

    for scheduler in sorted(req_data.keys()):
        rates = []
        mean_latencies = []
        mean_throughputs = []

        for rate in sorted(req_data[scheduler].keys()):
            # Latency stats
            req_df = req_data[scheduler][rate]
            lat_stats = compute_latency_stats(req_df)

            # Throughput stats (if available)
            if scheduler in tp_data and rate in tp_data[scheduler]:
                tp_df = tp_data[scheduler][rate]
                tp_stats = compute_throughput_stats(tp_df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
                mean_throughputs.append(tp_stats["overall_throughput"])
            else:
                mean_throughputs.append(0)

            rates.append(rate)
            mean_latencies.append(lat_stats["mean_latency"])

        color = SCHEDULER_COLORS.get(scheduler, '#333333')
        marker = SCHEDULER_MARKERS.get(scheduler, 'o')

        axes[0].plot(rates, mean_latencies, marker=marker, color=color, linewidth=2,
                     markersize=8, label=scheduler)
        axes[1].plot(rates, mean_throughputs, marker=marker, color=color, linewidth=2,
                     markersize=8, label=scheduler)

    axes[0].set_xlabel('Arrival Rate (requests/s)')
    axes[0].set_ylabel('Mean E2E Latency (sec)')
    axes[0].set_title('Latency vs Arrival Rate')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Arrival Rate (requests/s)')
    axes[1].set_ylabel('Throughput (tokens/sec)')
    axes[1].set_title('Throughput vs Arrival Rate')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = output_dir / 'rate_vs_metrics.png'
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {fig_path}")


# ============ Summary ============
def save_summary_csv(req_data: Dict, tp_data: Dict, output_dir: Path):
    """Save summary statistics to CSV."""
    rows = []

    for scheduler in sorted(req_data.keys()):
        for rate in sorted(req_data[scheduler].keys()):
            req_df = req_data[scheduler][rate]
            lat_stats = compute_latency_stats(req_df)

            row = {
                "scheduler": scheduler,
                "rate": rate,
                "mean_latency": lat_stats["mean_latency"],
                "p50_latency": lat_stats["p50_latency"],
                "p99_latency": lat_stats["p99_latency"],
                "n_requests": lat_stats["n_requests"],
            }

            # Add throughput if available
            if scheduler in tp_data and rate in tp_data[scheduler]:
                tp_df = tp_data[scheduler][rate]
                tp_stats = compute_throughput_stats(tp_df, THROUGHPUT_START_TIME, THROUGHPUT_END_TIME)
                row["mean_throughput"] = tp_stats["mean_throughput"]
                row["overall_throughput"] = tp_stats["overall_throughput"]
                row["p99_throughput"] = tp_stats["p99_throughput"]
            else:
                row["mean_throughput"] = None
                row["overall_throughput"] = None
                row["p99_throughput"] = None

            rows.append(row)

    summary_df = pd.DataFrame(rows)
    csv_path = output_dir / 'summary.csv'
    summary_df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")

    print("\nSummary Table:")
    print(summary_df.to_string(index=False))


def print_comparison_table(req_data: Dict):
    """Print comparison table with gaps."""
    print("\n" + "=" * 80)
    print("Comparison: WCP vs Sarathi (Gap calculation)")
    print("=" * 80)
    print(f"{'Rate':>6} | {'WCP (s)':>10} | {'Sarathi (s)':>12} | {'Gap':>10} | {'Status':>8}")
    print("-" * 80)

    if "WCP" not in req_data or "Sarathi" not in req_data:
        print("Need both WCP and Sarathi data for comparison")
        return

    for rate in sorted(req_data["WCP"].keys()):
        if rate not in req_data["Sarathi"]:
            continue

        wcp_mean = req_data["WCP"][rate]['request_e2e_time'].mean()
        sar_mean = req_data["Sarathi"][rate]['request_e2e_time'].mean()
        gap_pct = (wcp_mean - sar_mean) / sar_mean * 100
        status = "WIN" if gap_pct < -1 else "LOSE"

        print(f"{rate:>6} | {wcp_mean:>10.3f} | {sar_mean:>12.3f} | {gap_pct:>+9.1f}% | {status:>8}")


# ============ Main ============
def main():
    parser = argparse.ArgumentParser(
        description="Analyze experiment results from batch directory"
    )
    parser.add_argument(
        "batch_dir",
        type=str,
        help="Path to batch directory (e.g., /home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402)"
    )

    args = parser.parse_args()

    batch_dir = Path(args.batch_dir).resolve()
    output_dir = batch_dir / "analysis"
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("Experiment Analysis Tool (with correct throughput)")
    print("=" * 80)
    print(f"Input directory: {batch_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Steady-state period: [{THROUGHPUT_START_TIME}, {THROUGHPUT_END_TIME}]s")
    print()

    # Load data
    req_data, tp_data = load_experiments(batch_dir)

    if not req_data:
        print("No valid experiments found. Exiting.")
        sys.exit(1)

    print()

    # Generate plots
    print("Generating plots...")
    plot_latency_time_series(req_data, output_dir)
    plot_throughput_time_series(tp_data, output_dir)
    plot_rate_vs_metrics(req_data, tp_data, output_dir)

    # Save summary
    print("\nGenerating summary...")
    save_summary_csv(req_data, tp_data, output_dir)

    # Print comparison
    print_comparison_table(req_data)

    print("\n" + "=" * 80)
    print(f"Analysis complete! All results saved to: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
