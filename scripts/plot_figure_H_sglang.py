"""
Figure H (Appendix B.3): real-system validation on SGLang.

SGLang 0.5.7 on NVIDIA A100 80GB serving Llama-2-7B.
Workload: random prompts (input 512, output 20), Poisson arrivals,
lambda = 1..15 requests/s, 500 prompts per rate.

Honest disclosures:
  - Baseline uses weakened configuration
    (chunked_prefill_size=256, prefill_max_requests=8).
  - WAIT adds an underload-bypass that reverts to SGLang's native
    scheduler at very low arrival rates.

Data transcribed from the production sweep log (sweep_id 34, 35 in
outputs/sglang_wcp_sweeps.db on the deployment host).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["CMU Serif"],
    "mathtext.fontset": "cm",
    "font.size": 12,
    "axes.labelsize": 13,
    "axes.titlesize": 13,
    "legend.fontsize": 10.5,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
})

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "outputs" / "timeseries"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"Baseline": "#c0392b", "WAIT": "#1f6db5"}
LINESTYLES = {"Baseline": "--", "WAIT": "-"}
MARKERS = {"Baseline": "s", "WAIT": "o"}
LW = {"Baseline": 1.7, "WAIT": 2.7}
MS = {"Baseline": 7.5, "WAIT": 8.5}

RATES = list(range(1, 16))

# Mean end-to-end latency in seconds (from SGLang sweep_id 34, 35)
BASELINE_MS = [
    295.07, 325.55, 387.52, 440.38, 512.18, 645.80, 900.21, 1303.47,
    1664.70, 3884.47, 5923.07, 11313.76, 14348.70, 15679.62, 19162.07,
]
WAIT_MS = [
    278.57, 303.59, 351.91, 400.70, 468.51, 554.63, 742.94, 890.90,
    1121.58, 1654.77, 2440.59, 4606.91, 6998.44, 8855.43, 11303.56,
]
baseline = [v / 1000.0 for v in BASELINE_MS]
wait = [v / 1000.0 for v in WAIT_MS]
print(f"Avg improvement: {np.mean([(b-w)/b for b,w in zip(baseline, wait)])*100:.1f}%")

fig, ax = plt.subplots(figsize=(6.5, 4.4))

ax.plot(RATES, baseline,
        color=COLORS["Baseline"], linestyle=LINESTYLES["Baseline"],
        linewidth=LW["Baseline"], marker=MARKERS["Baseline"],
        markersize=MS["Baseline"], markeredgecolor="white",
        markeredgewidth=0.7, label="SGLang baseline")
ax.plot(RATES, wait,
        color=COLORS["WAIT"], linestyle=LINESTYLES["WAIT"],
        linewidth=LW["WAIT"], marker=MARKERS["WAIT"],
        markersize=MS["WAIT"], markeredgecolor="white",
        markeredgewidth=0.7, label="WAIT (ours)")

ax.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
ax.set_ylabel("Mean end-to-end latency (s)")
ax.set_xticks([1, 3, 5, 7, 9, 11, 13, 15])
ax.set_yscale("log")
ax.set_yticks([0.3, 0.5, 1, 2, 5, 10, 20])
ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
ax.set_ylim(0.25, 25)
ax.grid(True, which="major", linestyle=":", linewidth=0.4,
        alpha=0.35, color="#999999")
ax.legend(loc="upper left", frameon=False, handlelength=2.5,
          borderpad=0.4)

fig.tight_layout()
out_pdf = OUT / "figure_H_sglang.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
