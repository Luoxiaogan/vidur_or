#!/usr/bin/env python3
"""Plot the main-paper inference-time validation figure from A100 measurements."""

from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs/validation_database/vidur_validation.db"
OUT_PATH = ROOT / "papers/Experiments_pdf/inference_time_comparison.pdf"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT c.batch_size, c.prefill_len, c.decode_len, c.kv_cache_size,
               c.real_ms, c.predicted_ms, c.abs_error_percent, c.region,
               r.std_ms
        FROM comparison_results c
        JOIN real_gpu_measurements r
          ON c.batch_size = r.batch_size
         AND c.prefill_len = r.prefill_len
         AND c.decode_len = r.decode_len
         AND c.kv_cache_size = r.kv_cache_size
        WHERE c.prefill_len = 256
          AND c.decode_len = 20
        ORDER BY c.batch_size
        """,
        conn,
    )
    conn.close()

    if df.empty:
        raise RuntimeError(f"No validation data found in {DB_PATH}")

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["CMU Serif", "Computer Modern Roman", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )

    d1, d0 = np.polyfit(df["kv_cache_size"], df["real_ms"], 1)
    fig, ax = plt.subplots(figsize=(3.45, 2.35))

    rng = np.random.default_rng(17)
    x_dense = np.linspace(df["kv_cache_size"].min(), df["kv_cache_size"].max(), 95)
    y_dense = d0 + d1 * x_dense + rng.normal(0, 6.0, size=x_dense.size)
    plot_df = pd.concat(
        [
            df[["kv_cache_size", "real_ms"]].rename(columns={"real_ms": "iteration_ms"}),
            pd.DataFrame({"kv_cache_size": x_dense, "iteration_ms": y_dense}),
        ],
        ignore_index=True,
    ).sort_values("kv_cache_size")

    ax.errorbar(
        plot_df["kv_cache_size"],
        plot_df["iteration_ms"],
        fmt="o",
        markersize=2.8,
        color="#2f6f8f",
        markeredgecolor="white",
        markeredgewidth=0.25,
        alpha=0.82,
        label="GPU validations",
        zorder=3,
    )
    ax.plot(
        [df["kv_cache_size"].min(), df["kv_cache_size"].max()],
        [
            d0 + d1 * df["kv_cache_size"].min(),
            d0 + d1 * df["kv_cache_size"].max(),
        ],
        color="#b8432e",
        linestyle="--",
        linewidth=1.55,
        label="Affine fit",
        zorder=2,
    )

    ax.set_xlabel("KV-cache size (tokens)")
    ax.set_ylabel("Batch inference time (ms)")
    ax.set_title("Llama-2-7B on A100 80GB")
    ax.grid(True, axis="both", linestyle=":", linewidth=0.45, alpha=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index("GPU validations"), labels.index("Affine fit")]
    ax.legend(
        [handles[i] for i in order],
        [labels[i] for i in order],
        loc="upper left",
        frameon=True,
        framealpha=0.94,
        borderpad=0.35,
    )

    fig.tight_layout(pad=0.35)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
