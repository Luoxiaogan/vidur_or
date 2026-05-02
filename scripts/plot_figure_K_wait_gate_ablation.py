"""Figure K: waiting ablation on the single-type p512d20 Vidur workload.

The data compare full WAIT with a threshold-only no-wait variant.  For
each arrival rate, both policies use the same parameter setting; only
the waiting condition is toggled.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["CMU Serif"],
    "mathtext.fontset": "cm",
    "font.size": 11.5,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "legend.fontsize": 9.4,
    "xtick.labelsize": 9.8,
    "ytick.labelsize": 9.8,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
})

BASE = Path(__file__).resolve().parent.parent
PAPER_OUT = BASE / "papers" / "Experiments_pdf"
TS_OUT = BASE / "outputs" / "timeseries"
PAPER_OUT.mkdir(parents=True, exist_ok=True)
TS_OUT.mkdir(parents=True, exist_ok=True)

RATES = np.array([8, 10, 12, 14, 15, 16, 18, 19, 20, 21, 22, 23], dtype=float)
TOTAL_LIMIT = np.array([4, 6, 6, 7, 9, 10, 10, 11, 14, 12, 14, 14], dtype=int)
CHUNK_SIZE = np.array([128, 160, 224, 352, 160, 224, 224, 224, 224, 320, 192, 192], dtype=int)
NO_WAIT = np.array([0.507, 0.514, 0.563, 0.612, 0.630, 0.883, 1.630, 1.717, 2.049, 2.276, 2.654, 3.843])
WAIT = np.array([0.554, 0.590, 0.618, 0.653, 0.681, 0.866, 1.539, 1.594, 1.959, 2.257, 2.654, 3.843])

improvement = 100.0 * (NO_WAIT - WAIT) / NO_WAIT

baseline_color = "#c0392b"
wait_color = "#1f6db5"
bar_colors = np.where(improvement >= 0, wait_color, "#b35c1e")

fig, axes = plt.subplots(
    1,
    2,
    figsize=(9.4, 3.65),
    gridspec_kw={"width_ratios": [1.28, 0.92]},
)
fig.subplots_adjust(wspace=0.24)

ax = axes[0]
ax.plot(
    RATES,
    NO_WAIT,
    color=baseline_color,
    linestyle="--",
    linewidth=1.7,
    marker="s",
    markersize=6.4,
    markeredgecolor="white",
    markeredgewidth=0.7,
    label="Threshold only",
)
ax.plot(
    RATES,
    WAIT,
    color=wait_color,
    linestyle="-",
    linewidth=2.4,
    marker="o",
    markersize=6.8,
    markeredgecolor="white",
    markeredgewidth=0.7,
    label="WAIT",
)
ax.set_title("Mean end-to-end latency", pad=7)
ax.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
ax.set_ylabel("Mean E2E latency (s)")
ax.set_xlim(7.3, 23.7)
ax.set_ylim(0.35, 4.15)
ax.set_xticks(RATES)
ax.set_yticks([0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4])
ax.grid(True, which="major", linestyle=":", linewidth=0.4, alpha=0.36, color="#999999")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(
    loc="upper left",
    bbox_to_anchor=(0.02, 0.98),
    frameon=False,
    handlelength=2.2,
    borderaxespad=0.0,
)

ax2 = axes[1]
ax2.axhline(0, color="#555555", linewidth=0.9)
ax2.bar(RATES, improvement, color=bar_colors, width=0.58, alpha=0.88)
ax2.set_title("Effect of waiting", pad=7)
ax2.set_xlabel(r"Arrival rate $\lambda$")
ax2.set_ylabel("WAIT change in latency (%)")
ax2.set_xlim(7.3, 23.7)
ax2.set_ylim(-17.5, 9)
ax2.set_xticks(RATES)
ax2.set_yticks([-15, -10, -5, 0, 5])
ax2.grid(True, axis="y", linestyle=":", linewidth=0.4, alpha=0.36, color="#999999")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.text(
    0.50,
    0.10,
    "same threshold\nparameters",
    transform=ax2.transAxes,
    ha="center",
    va="center",
    fontsize=9.2,
    color="#333333",
    bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#999999", linewidth=0.7),
)

fig.tight_layout()

for out_dir in [PAPER_OUT, TS_OUT]:
    out_pdf = out_dir / "figure_K_wait_gate_ablation.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    print(f"Saved: {out_pdf}")

plt.close(fig)
