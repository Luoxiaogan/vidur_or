"""Plot filtered LMSYS prompt/decode length distributions for Section 6.

The paper-facing workload population keeps requests whose prompt (prefill)
and response (decode) lengths are both below 500 tokens. This script regenerates
the distribution figure from the raw length trace so the caption, figure labels,
and text statistics use the same filter.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["CMU Serif", "Computer Modern Roman", "DejaVu Serif"],
    "mathtext.fontset": "cm",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.linewidth": 0.8,
})

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "lmsys_chat_1m_dataset" / "output_trace" / "lmsys_chat_1m_dataset.csv"
OUT = ROOT / "papers" / "Experiments_pdf" / "question_answer_lengths_distribution.pdf"


def summarize(values: pd.Series) -> tuple[float, float]:
    return float(values.mean()), float(values.median())


def plot_panel(ax: plt.Axes, values: pd.Series, title: str, xlabel: str, color: str) -> None:
    mean, median = summarize(values)
    bins = np.arange(0, 501, 10)
    ax.hist(values, bins=bins, color=color, alpha=0.82, edgecolor="white", linewidth=0.25)
    ax.axvline(mean, color="#7f1d1d", linestyle="--", linewidth=1.2, label=f"Mean: {mean:.1f}")
    ax.axvline(median, color="#1f4e79", linestyle=":", linewidth=1.4, label=f"Median: {median:.0f}")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Number of requests")
    ax.set_xlim(0, 500)
    ax.set_yscale("log")
    ax.grid(True, which="major", linestyle=":", linewidth=0.35, alpha=0.35)
    ax.legend(frameon=False, loc="upper right", handlelength=2.3)


def main() -> None:
    df = pd.read_csv(TRACE)
    filtered = df[(df["question_length"] < 500) & (df["answer_length"] < 500)].copy()
    prefill_mean, prefill_median = summarize(filtered["question_length"])
    decode_mean, decode_median = summarize(filtered["answer_length"])
    short_decode = float((filtered["answer_length"] <= 50).mean())
    long_decode = float((filtered["answer_length"] > 300).mean())

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1), sharey=True)
    plot_panel(axes[0], filtered["question_length"], "Prefill length", "Tokens", "#4c78a8")
    plot_panel(axes[1], filtered["answer_length"], "Decode length", "Tokens", "#f58518")
    axes[1].set_ylabel("")
    fig.tight_layout(w_pad=1.6)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {OUT}")
    print(f"Filtered requests: {len(filtered)}")
    print(f"Prefill mean/median: {prefill_mean:.3f}/{prefill_median:.0f}")
    print(f"Decode mean/median: {decode_mean:.3f}/{decode_median:.0f}")
    print(f"Decode <= 50: {100 * short_decode:.2f}%")
    print(f"Decode > 300: {100 * long_decode:.2f}%")


if __name__ == "__main__":
    main()
