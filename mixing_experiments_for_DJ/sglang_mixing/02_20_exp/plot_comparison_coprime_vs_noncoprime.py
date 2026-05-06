#!/usr/bin/env python3
"""
Plot comparison between Coprime and Non-Coprime experiments.

Generates two comparison plots:
- Memory Usage: coprime (green) vs non-coprime (orange)
- Admission: coprime (green) vs non-coprime (orange)

Usage:
    python plot_comparison_coprime_vs_noncoprime.py
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "04_17_pdfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Matplotlib style settings
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.labelsize": 13,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "figure.dpi": 150,
})

# Colors
COLOR_COPRIME = '#2ca02c'      # Green
COLOR_NON_COPRIME = '#ff7f0e'  # Orange


def load_and_process(csv_path: Path) -> pd.DataFrame:
    """Load CSV and process."""
    df = pd.read_csv(csv_path)
    df['memory_pct'] = df['token_usage'] * 100
    return df


def plot_memory_comparison():
    """Plot Memory Usage comparison: Coprime vs Non-Coprime."""
    print("Processing Memory Usage comparison...")

    # Load data
    df_coprime = load_and_process(BASE_DIR / "exp_two" / "batch_metrics_mix.csv")
    df_non_coprime = load_and_process(BASE_DIR / "exp_two_non_coprime" / "batch_metrics_mix.csv")

    # Filter dummy batches
    df_coprime = df_coprime[df_coprime['batch_id'] >= 12].copy()
    df_non_coprime = df_non_coprime[df_non_coprime['batch_id'] >= 12].copy()

    # Reset batch index
    df_coprime['batch_index'] = range(len(df_coprime))
    df_non_coprime['batch_index'] = range(len(df_non_coprime))

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot coprime (green)
    ax.plot(
        df_coprime['batch_index'],
        df_coprime['memory_pct'],
        color=COLOR_COPRIME,
        linewidth=1.0,
        alpha=0.8,
        label='Coprime (D=1000 vs 1211)'
    )

    # Plot non-coprime (orange)
    ax.plot(
        df_non_coprime['batch_index'],
        df_non_coprime['memory_pct'],
        color=COLOR_NON_COPRIME,
        linewidth=1.0,
        alpha=0.8,
        label='Non-Coprime (D=1000 vs 1200)'
    )

    # Add 100% reference line (red dashed)
    ax.axhline(
        y=100,
        color='#e74c3c',
        linestyle='--',
        linewidth=1.5,
        alpha=0.8,
        label='Capacity M'
    )

    # Labels and title
    ax.set_xlabel("Batch Index", fontweight='bold')
    ax.set_ylabel("GPU Memory Usage (%)", fontweight='bold')
    ax.set_title("Memory Usage: Coprime vs Non-Coprime (P=5000)", fontweight='bold')

    # Y-axis limit
    y_max = max(df_coprime['memory_pct'].max(), df_non_coprime['memory_pct'].max())
    ax.set_ylim(0, max(105, y_max * 1.02))

    # Grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Legend (upper right)
    ax.legend(loc='upper right', framealpha=0.95)

    # Tight layout
    plt.tight_layout()

    # Save
    pdf_path = OUTPUT_DIR / "comparison_memory_coprime_vs_noncoprime.pdf"
    png_path = OUTPUT_DIR / "comparison_memory_coprime_vs_noncoprime.png"

    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    fig.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"  Saved: {pdf_path}")
    print(f"  Saved: {png_path}")


def plot_admission_comparison():
    """Plot Admission comparison: Coprime vs Non-Coprime."""
    print("Processing Admission comparison...")

    # Load data
    df_coprime = load_and_process(BASE_DIR / "exp_two" / "batch_metrics_mix.csv")
    df_non_coprime = load_and_process(BASE_DIR / "exp_two_non_coprime" / "batch_metrics_mix.csv")

    # Filter dummy batches
    df_coprime = df_coprime[df_coprime['batch_id'] >= 12].copy()
    df_non_coprime = df_non_coprime[df_non_coprime['batch_id'] >= 12].copy()

    # Reset batch index
    df_coprime['batch_index'] = range(len(df_coprime))
    df_non_coprime['batch_index'] = range(len(df_non_coprime))

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot coprime (green)
    ax.plot(
        df_coprime['batch_index'],
        df_coprime['num_new_seqs'],
        color=COLOR_COPRIME,
        linewidth=1.0,
        alpha=0.8,
        label='Coprime (D=1000 vs 1211)'
    )

    # Plot non-coprime (orange)
    ax.plot(
        df_non_coprime['batch_index'],
        df_non_coprime['num_new_seqs'],
        color=COLOR_NON_COPRIME,
        linewidth=1.0,
        alpha=0.8,
        label='Non-Coprime (D=1000 vs 1200)'
    )

    # Labels and title
    ax.set_xlabel("Batch Index", fontweight='bold')
    ax.set_ylabel("Number of New Reqs", fontweight='bold')
    ax.set_title("Admission: Coprime vs Non-Coprime (P=5000)", fontweight='bold')

    # Y-axis
    y_max = max(df_coprime['num_new_seqs'].max(), df_non_coprime['num_new_seqs'].max())
    ax.set_ylim(0, max(y_max * 1.05, 10))

    # Grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Legend (upper right)
    ax.legend(loc='upper right', framealpha=0.95)

    # Tight layout
    plt.tight_layout()

    # Save
    pdf_path = OUTPUT_DIR / "comparison_admission_coprime_vs_noncoprime.pdf"
    png_path = OUTPUT_DIR / "comparison_admission_coprime_vs_noncoprime.png"

    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    fig.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"  Saved: {pdf_path}")
    print(f"  Saved: {png_path}")


def main():
    """Generate comparison plots."""
    print("=" * 60)
    print("Coprime vs Non-Coprime Comparison Plot Generation")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    plot_memory_comparison()
    print()
    plot_admission_comparison()
    print()

    print("=" * 60)
    print("All comparison plots generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
