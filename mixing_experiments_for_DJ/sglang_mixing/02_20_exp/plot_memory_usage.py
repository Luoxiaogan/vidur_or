#!/usr/bin/env python3
"""
Plot GPU Memory Usage vs Batch Index for 02_20_exp experiments.

Generates three separate PDFs:
- exp_single: Single type experiment
- exp_two: Two types (coprime) experiment
- exp_two_non_coprime: Two types (non-coprime) experiment

Usage:
    python plot_memory_usage.py
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

# Experiment configurations
# Settings: P=5000 for all, D varies
EXPERIMENTS = {
    "exp_single": {
        "title": "Single Type (P=5000, D=1000)",
        "filename": "memory_usage_single_type",
    },
    "exp_two": {
        "title": "Two Types Coprime (P=5000, D=1000 vs 1211)",
        "filename": "memory_usage_two_types_coprime",
    },
    "exp_two_non_coprime": {
        "title": "Two Types Non-Coprime (P=5000, D=1000 vs 1200)",
        "filename": "memory_usage_two_types_non_coprime",
    },
}


def load_and_process(csv_path: Path) -> pd.DataFrame:
    """Load CSV and convert token_usage to percentage."""
    df = pd.read_csv(csv_path)
    df['memory_pct'] = df['token_usage'] * 100
    return df


def plot_experiment(exp_name: str, config: dict):
    """Generate a single memory usage plot."""
    csv_path = BASE_DIR / exp_name / "batch_metrics_mix.csv"

    if not csv_path.exists():
        print(f"Warning: {csv_path} not found, skipping...")
        return

    print(f"Processing {exp_name}...")

    # Load data
    df = load_and_process(csv_path)

    # Filter dummy batches (first few batches with very small token_usage)
    df_filtered = df[df['batch_id'] >= 12].copy()

    # Reset batch index to start from 0 for cleaner visualization
    df_filtered['batch_index'] = range(len(df_filtered))

    # Find overflow points (token_usage > 100%)
    overflow_mask = df_filtered['memory_pct'] > 100
    overflow_df = df_filtered[overflow_mask]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot memory usage (blue line)
    ax.plot(
        df_filtered['batch_index'],
        df_filtered['memory_pct'],
        color='#1f77b4',  # Blue
        linewidth=1.0,
        alpha=0.8,
        label='Memory Demand'
    )

    # Add 100% reference line (red dashed)
    ax.axhline(
        y=100,
        color='#e74c3c',  # Red
        linestyle='--',
        linewidth=1.5,
        alpha=0.8,
        label='Capacity M'
    )

    # Mark overflow points with red triangles
    if len(overflow_df) > 0:
        ax.scatter(
            overflow_df['batch_index'],
            overflow_df['memory_pct'],
            color='#e74c3c',  # Red
            marker='^',  # Triangle up
            s=50,
            alpha=0.9,
            label=f'Overflow ({len(overflow_df)} points)',
            zorder=5
        )

    # Labels and title
    ax.set_xlabel("Batch Index", fontweight='bold')
    ax.set_ylabel("GPU Memory Usage (%)", fontweight='bold')
    ax.set_title(config['title'], fontweight='bold')

    # Y-axis limit (slightly above 100 to show overflow)
    max_memory = df_filtered['memory_pct'].max()
    y_max = max(105, max_memory * 1.02)
    ax.set_ylim(0, y_max)

    # Grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Legend (upper right)
    ax.legend(loc='upper right', framealpha=0.95)

    # Tight layout
    plt.tight_layout()

    # Save PDF and PNG
    pdf_path = OUTPUT_DIR / f"{config['filename']}.pdf"
    png_path = OUTPUT_DIR / f"{config['filename']}.png"

    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    fig.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"  Saved: {pdf_path}")
    print(f"  Saved: {png_path}")


def main():
    """Generate all three memory usage plots."""
    print("=" * 60)
    print("GPU Memory Usage Plot Generation")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    for exp_name, config in EXPERIMENTS.items():
        plot_experiment(exp_name, config)
        print()

    print("=" * 60)
    print("All plots generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
