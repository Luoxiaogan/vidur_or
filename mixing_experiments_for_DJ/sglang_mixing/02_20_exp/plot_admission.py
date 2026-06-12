#!/usr/bin/env python3
"""
Plot Admission (Number of New Sequences per Batch) vs Batch Index for 02_20_exp experiments.

Generates three separate PDFs and PNGs:
- exp_single: Single type experiment
- exp_two: Two types (coprime) experiment
- exp_two_non_coprime: Two types (non-coprime) experiment

Usage:
    python plot_admission.py
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
        "filename": "admission_single_type",
    },
    "exp_two": {
        "title": "Two Types Coprime (P=5000, D=1000 vs 1211)",
        "filename": "admission_two_types_coprime",
    },
    "exp_two_non_coprime": {
        "title": "Two Types Non-Coprime (P=5000, D=1000 vs 1200)",
        "filename": "admission_two_types_non_coprime",
    },
}


def load_and_process(csv_path: Path) -> pd.DataFrame:
    """Load CSV."""
    df = pd.read_csv(csv_path)
    return df


def plot_experiment(exp_name: str, config: dict):
    """Generate a single admission plot."""
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

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot admission (num_new_seqs) with green line
    ax.plot(
        df_filtered['batch_index'],
        df_filtered['num_new_seqs'],
        color='#2ca02c',  # Green
        linewidth=1.0,
        alpha=0.8,
        label='Admission'
    )

    # Labels and title
    ax.set_xlabel("Batch Index", fontweight='bold')
    ax.set_ylabel("Number of New Reqs", fontweight='bold')
    ax.set_title(config['title'], fontweight='bold')

    # Y-axis start from 0
    ax.set_ylim(0, max(df_filtered['num_new_seqs'].max() * 1.05, 10))

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
    """Generate all three admission plots."""
    print("=" * 60)
    print("Admission Plot Generation")
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
