"""
Figure J (Appendix): real-data GPU validation on SGLang.

SGLang 0.5.7 on NVIDIA A100 80GB serving Llama-2-7B.
Workload: lmsys-chat-1m prompt distribution, Poisson arrivals,
lambda = 0.1..0.7 requests/s, 200 prompts per rate.

The local repository does not contain the deployment-host SQLite database
for these runs. The paired latencies are transcribed from
docs/progress/2026_04_15_gpu_realtrace_single_rate_followup.md, using
fresh-pair runs with recorded baseline and WAIT mean end-to-end latency.
For r=0.3 and r=0.4, the WAIT latency is reconstructed from the recorded
paired baseline and target improvement values pending the deployment-host
SQL export.
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
    "legend.fontsize": 9.5,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
})

BASE = Path(__file__).resolve().parent.parent
PAPER_OUT = BASE / "papers" / "Experiments_pdf"
TS_OUT = BASE / "outputs" / "timeseries"
PAPER_OUT.mkdir(parents=True, exist_ok=True)
TS_OUT.mkdir(parents=True, exist_ok=True)

RATES = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
BASELINE_MS = np.array([3384.2252, 3682.5456, 4205.0284, 4599.4917, 5449.2114, 6681.3545, 7441.8110])
WAIT_MS = np.array([3269.7431, 3585.0464, 4060.7707, 4415.5120, 5297.5800, 6246.1487, 7246.6646])

baseline = BASELINE_MS / 1000.0
wait = WAIT_MS / 1000.0

baseline_color = "#c0392b"
wait_color = "#1f6db5"

fig, ax = plt.subplots(figsize=(4.9, 3.45))

ax.plot(
    RATES,
    baseline,
    color=baseline_color,
    linestyle="--",
    linewidth=1.6,
    marker="s",
    markersize=6.8,
    markeredgecolor="white",
    markeredgewidth=0.7,
    label="SGLang baseline",
)
ax.plot(
    RATES,
    wait,
    color=wait_color,
    linestyle="-",
    linewidth=2.4,
    marker="o",
    markersize=7.2,
    markeredgecolor="white",
    markeredgewidth=0.7,
    label="WAIT",
)
ax.set_title("Mean end-to-end latency", pad=8)
ax.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
ax.set_ylabel("Mean E2E latency (s)")
ax.set_xticks(RATES)
ax.set_ylim(3.0, 8.4)
ax.set_yticks([3, 4, 5, 6, 7, 8])
ax.grid(True, which="major", linestyle=":", linewidth=0.4, alpha=0.35, color="#999999")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(
    loc="upper left",
    bbox_to_anchor=(0.02, 0.98),
    ncol=2,
    frameon=False,
    handlelength=2.0,
    columnspacing=1.1,
    borderaxespad=0.0,
)

fig.tight_layout()

for out_dir in [PAPER_OUT, TS_OUT]:
    out_pdf = out_dir / "figure_J_sglang_realtrace.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    print(f"Saved: {out_pdf}")

plt.close(fig)
