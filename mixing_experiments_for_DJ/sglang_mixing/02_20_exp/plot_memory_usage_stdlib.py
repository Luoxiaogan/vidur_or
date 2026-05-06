#!/usr/bin/env python3
"""
Plot GPU Memory Usage vs Batch Index for 02_20_exp experiments.
Uses only Python standard library (no pandas dependency).

Generates three separate PDFs:
- exp_single: Single type experiment
- exp_two: Two types (coprime) experiment
- exp_two_non_coprime: Two types (non-coprime) experiment

Usage:
    python plot_memory_usage_stdlib.py
"""

import csv
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "04_17_pdfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Matplotlib style settings
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["CMU Serif", "DejaVu Serif"],
    "font.size": 12,
    "axes.labelsize": 13,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "figure.dpi": 150,
})

# Experiment configurations
EXPERIMENTS = {
    "exp_single": {
        "title": "Single Type (prefill=6000, decode=5000)",
        "filename": "memory_usage_single_type.pdf",
    },
    "exp_two": {
        "title": "Two Types Coprime (6000 vs 6211)",
        "filename": "memory_usage_two_types_coprime.pdf",
    },
    "exp_two_non_coprime": {
        "title": "Two Types Non-Coprime (6000 vs 6200)",
        "filename": "memory_usage_two_types_non_coprime.pdf",
    },
}


def load_csv_data(csv_path: Path) -> dict:
    """Load CSV and extract relevant columns."""
    batch_ids = []
    memory_pcts = []

    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch_id = int(row['batch_id'])
            token_usage = float(row['token_usage'])
            memory_pct = token_usage * 100

            batch_ids.append(batch_id)
            memory_pcts.append(memory_pct)

    return {
        'batch_ids': batch_ids,
        'memory_pcts': memory_pcts,
    }


def filter_dummy_batches(data: dict, min_batch_id: int = 12) -> dict:
    """Filter out dummy batches and reset index."""
    filtered_ids = []
    filtered_memory = []

    for batch_id, memory in zip(data['batch_ids'], data['memory_pcts']):
        if batch_id >= min_batch_id:
            filtered_ids.append(batch_id)
            filtered_memory.append(memory)

    # Reset batch index to start from 0
    batch_index = list(range(len(filtered_ids)))

    return {
        'batch_index': batch_index,
        'batch_ids': filtered_ids,
        'memory_pcts': filtered_memory,
    }


def find_overflow_points(data: dict, threshold: float = 100.0) -> dict:
    """Find points where memory usage exceeds threshold."""
    overflow_index = []
    overflow_memory = []

    for idx, memory in zip(data['batch_index'], data['memory_pcts']):
        if memory > threshold:
            overflow_index.append(idx)
            overflow_memory.append(memory)

    return {
        'batch_index': overflow_index,
        'memory_pcts': overflow_memory,
    }


def calculate_stats(data: dict) -> dict:
    """Calculate statistics."""
    memory = data['memory_pcts']
    if not memory:
        return {}

    max_val = max(memory)
    min_val = min(memory)
    mean_val = sum(memory) / len(memory)

    # Count overflow points
    overflow_count = sum(1 for m in memory if m > 100.0)

    return {
        'count': len(memory),
        'max': max_val,
        'min': min_val,
        'mean': mean_val,
        'overflow_count': overflow_count,
    }


def plot_experiment(exp_name: str, config: dict):
    """Generate a single memory usage plot."""
    csv_path = BASE_DIR / exp_name / "batch_metrics_mix.csv"

    if not csv_path.exists():
        print(f"Warning: {csv_path} not found, skipping...")
        return

    print(f"Processing {exp_name}...")

    # Load and process data
    raw_data = load_csv_data(csv_path)
    data = filter_dummy_batches(raw_data)
    overflow = find_overflow_points(data)
    stats = calculate_stats(data)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot memory usage (blue line)
    ax.plot(
        data['batch_index'],
        data['memory_pcts'],
        color='#1f77b4',  # Blue
        linewidth=1.0,
        alpha=0.8,
        label='GPU Memory Usage'
    )

    # Add 100% reference line (red dashed)
    ax.axhline(
        y=100,
        color='#e74c3c',  # Red
        linestyle='--',
        linewidth=1.5,
        alpha=0.8,
        label='100% Capacity'
    )

    # Mark overflow points with red triangles
    if overflow['batch_index']:
        ax.scatter(
            overflow['batch_index'],
            overflow['memory_pcts'],
            color='#e74c3c',  # Red
            marker='^',  # Triangle up
            s=50,
            alpha=0.9,
            label=f'Overflow ({len(overflow["batch_index"])} points)',
            zorder=5
        )

    # Labels and title
    ax.set_xlabel("Batch Index", fontweight='bold')
    ax.set_ylabel("GPU Memory Usage (%)", fontweight='bold')
    ax.set_title(config['title'], fontweight='bold')

    # Y-axis limit (slightly above 100 to show overflow)
    max_memory = max(data['memory_pcts']) if data['memory_pcts'] else 105
    y_max = max(105, max_memory * 1.02)
    ax.set_ylim(0, y_max)

    # Grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Legend
    ax.legend(loc='lower right', framealpha=0.95)

    # Add statistics text box
    stats_text = (
        f"Batches: {stats['count']}\n"
        f"Max Usage: {stats['max']:.2f}%\n"
        f"Mean Usage: {stats['mean']:.2f}%\n"
        f"Overflow Points: {stats['overflow_count']}"
    )
    ax.text(
        0.02, 0.98, stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='left',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    )

    # Tight layout
    plt.tight_layout()

    # Save PDF
    output_path = OUTPUT_DIR / config['filename']
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"  Saved: {output_path}")
    print(f"  Stats: max={stats['max']:.2f}%, "
          f"mean={stats['mean']:.2f}%, "
          f"overflow={stats['overflow_count']}")


def main():
    """Generate all three memory usage plots."""
    print("=" * 60)
    print("GPU Memory Usage Plot Generation (Standard Library)")
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
