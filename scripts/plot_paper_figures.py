"""
Plot publication-quality figures from timeseries CSV data.

Generates:
1. Mean Latency vs Arrival Rate (2 subplots: single-type, multi-type)
2. Time-series at critical rates (2x2 grid with rolling averages)

Usage:
    python scripts/plot_paper_figures.py
"""

import os
import glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# Use CMU Serif for publication quality
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["CMU Serif"],
    "mathtext.fontset": "cm",
    "font.size": 13,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 11,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
})

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
TS_DIR = BASE_DIR / "outputs" / "timeseries"

RATES = list(range(12, 27))  # 12-26

# Colors and styles
COLORS = {
    "Sarathi": "#d62728",
    "vLLM":    "#ff7f0e",
    "WCP":     "#1f77b4",
}
LINESTYLES = {
    "Sarathi": "-",
    "vLLM":    "--",
    "WCP":     "-",
}
LINEWIDTHS = {
    "Sarathi": 1.8,
    "vLLM":    1.8,
    "WCP":     2.5,
}
MARKERS = {
    "Sarathi": "s",
    "vLLM":    "^",
    "WCP":     "o",
}

# Multi-type WCP: best config varies by rate
# rates 12-19: cs192_tl20, rate 20: cs192_tl26, rates 21-26: cs128_tl30
MT_WCP_CONFIG = {}
for r in range(12, 20):
    MT_WCP_CONFIG[r] = "cs192_tl20"
MT_WCP_CONFIG[20] = "cs192_tl26"
for r in range(21, 27):
    MT_WCP_CONFIG[r] = "cs128_tl30"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_csv(path):
    """Load a CSV and return the DataFrame, or None if file missing."""
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def trimmed_mean(series, trim_frac=0.25):
    """Compute mean of the middle 50% of a series (skip first 25%, last 25%)."""
    n = len(series)
    lo = int(n * trim_frac)
    hi = n - int(n * trim_frac)
    if hi <= lo:
        return np.nan
    return series.iloc[lo:hi].mean()


def get_st_path(algo, rate):
    """Return path for single-type CSV."""
    if algo == "Sarathi":
        return TS_DIR / f"ST_Sarathi_r{rate}.csv"
    elif algo == "vLLM":
        return TS_DIR / f"ST_vLLM_r{rate}.csv"
    elif algo == "WCP":
        return TS_DIR / f"ST_WCP_cs256_tl21_r{rate}.csv"


def get_mt_path(algo, rate):
    """Return path for multi-type CSV."""
    if algo == "Sarathi":
        return TS_DIR / f"MT_Sarathi_r{rate}.csv"
    elif algo == "vLLM":
        return TS_DIR / f"MT_vLLM_r{rate}.csv"
    elif algo == "WCP":
        cfg = MT_WCP_CONFIG.get(rate)
        if cfg is None:
            return None
        return TS_DIR / f"MT_WCP_{cfg}_r{rate}.csv"


def compute_mean_latencies(get_path_fn, algos, rates):
    """Compute trimmed mean latency for each algorithm at each rate."""
    results = {algo: {} for algo in algos}
    for rate in rates:
        for algo in algos:
            path = get_path_fn(algo, rate)
            if path is None:
                continue
            df = load_csv(str(path))
            if df is not None and "request_e2e_time" in df.columns:
                val = trimmed_mean(df["request_e2e_time"])
                if not np.isnan(val):
                    results[algo][rate] = val
    return results


# ---------------------------------------------------------------------------
# Figure 1: Mean Latency vs Arrival Rate
# ---------------------------------------------------------------------------
def plot_mean_latency_vs_rate():
    """Two subplots side-by-side: single-type (left), multi-type (right)."""
    algos = ["Sarathi", "vLLM", "WCP"]

    st_data = compute_mean_latencies(get_st_path, algos, RATES)
    mt_data = compute_mean_latencies(get_mt_path, algos, RATES)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)

    for ax, data, title in [
        (axes[0], st_data, "Single-type (p512d20)"),
        (axes[1], mt_data, "Multi-type (p512d20 + p512d50)"),
    ]:
        for algo in algos:
            rates_present = sorted(data[algo].keys())
            means = [data[algo][r] for r in rates_present]
            if not rates_present:
                continue
            label = algo if algo != "WCP" else "WCP (ours)"
            ax.plot(
                rates_present, means,
                color=COLORS[algo],
                linestyle=LINESTYLES[algo],
                linewidth=LINEWIDTHS[algo],
                marker=MARKERS[algo],
                markersize=6,
                label=label,
            )

        ax.set_xlabel("Arrival Rate (requests/s)", fontsize=13)
        ax.set_ylabel("Mean E2E Latency (s)", fontsize=13)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_yscale("log")
        ax.tick_params(axis="both", labelsize=11)
        ax.legend(fontsize=11, loc="upper left")
        ax.grid(True, which="both", alpha=0.3, linewidth=0.5)
        ax.set_xticks([r for r in RATES if r % 2 == 0])

    fig.tight_layout(pad=2.0)

    out_pdf = TS_DIR / "paper_mean_latency_vs_rate.pdf"
    out_png = TS_DIR / "paper_mean_latency_vs_rate.png"
    fig.savefig(str(out_pdf), dpi=300, bbox_inches="tight")
    fig.savefig(str(out_png), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_pdf}")
    print(f"Saved: {out_png}")


# ---------------------------------------------------------------------------
# Figure 2: Time-series at Critical Rates (2x2 grid)
# ---------------------------------------------------------------------------
def plot_timeseries_critical():
    """
    2x2 grid:
      Top-left:    ST r=22    Top-right:   ST r=23
      Bottom-left: MT r=21    Bottom-right: MT r=22
    Each subplot shows rolling-average e2e_time for 3 algorithms.
    """
    panels = [
        ("Single-type, rate=22", get_st_path, 22),
        ("Single-type, rate=23", get_st_path, 23),
        ("Multi-type, rate=21",  get_mt_path, 21),
        ("Multi-type, rate=22",  get_mt_path, 22),
    ]
    algos = ["Sarathi", "vLLM", "WCP"]
    window = 200  # rolling window size

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    axes_flat = axes.flatten()

    for idx, (title, get_path_fn, rate) in enumerate(panels):
        ax = axes_flat[idx]
        for algo in algos:
            path = get_path_fn(algo, rate)
            if path is None:
                continue
            df = load_csv(str(path))
            if df is None or "request_e2e_time" not in df.columns:
                continue
            e2e = df["request_e2e_time"]
            rolling = e2e.rolling(window=window, min_periods=1).mean()
            label = algo if algo != "WCP" else "WCP (ours)"
            ax.plot(
                range(len(rolling)), rolling,
                color=COLORS[algo],
                linestyle=LINESTYLES[algo],
                linewidth=LINEWIDTHS[algo],
                label=label,
                alpha=0.9,
            )

        ax.set_xlabel("Request Index", fontsize=12)
        ax.set_ylabel("E2E Latency (s, rolling avg)", fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.tick_params(axis="both", labelsize=10)
        ax.legend(fontsize=10, loc="upper left")
        ax.grid(True, alpha=0.3, linewidth=0.5)

    fig.tight_layout(pad=2.5)

    out_pdf = TS_DIR / "paper_timeseries_critical.pdf"
    out_png = TS_DIR / "paper_timeseries_critical.png"
    fig.savefig(str(out_pdf), dpi=300, bbox_inches="tight")
    fig.savefig(str(out_png), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_pdf}")
    print(f"Saved: {out_png}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Reading CSVs from: {TS_DIR}")
    print()

    print("=" * 60)
    print("Figure 1: Mean Latency vs Arrival Rate")
    print("=" * 60)
    plot_mean_latency_vs_rate()
    print()

    print("=" * 60)
    print("Figure 2: Time-series at Critical Rates")
    print("=" * 60)
    plot_timeseries_critical()
    print()

    print("Done. All figures saved.")
