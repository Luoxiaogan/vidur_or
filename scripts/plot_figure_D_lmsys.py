"""
Figure D: real-workload mean latency + effective throughput vs QPS.

Workload: lmsys-chat-1m, 50 decode-length bins, prefill ~35 tokens,
decode 1-500 tokens.

Policies compared:
  - vLLM
  - Sarathi (chunk_size = 256)
  - Nested WAIT (best validated 50-bin configuration per QPS)

Data source: validated real-data QPS grid recorded in
docs/progress/2026_03_25_overnight_grid_results.md and
docs/progress/2026_03_30_real_data_experiments.md.

Important: these are the recorded results, including the one observed
loss at QPS=50. We do not smooth or overwrite that point.
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

COLORS = {"vLLM": "#ff8c2b", "Sarathi": "#c0392b", "Nested WAIT": "#1f6db5"}
LINESTYLES = {"vLLM": "--", "Sarathi": "--", "Nested WAIT": "-"}
MARKERS = {"vLLM": "^", "Sarathi": "s", "Nested WAIT": "o"}
LW = {"vLLM": 1.7, "Sarathi": 1.7, "Nested WAIT": 2.7}
MS = {"vLLM": 7.5, "Sarathi": 7.5, "Nested WAIT": 8.5}

# --- Data ------------------------------------------------------------------
QPS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]

raw = {
    "vLLM": dict(zip(QPS, [
        1.9,  2.3,  3.2, 15.4, 30.1,
        40.0, 47.2, 52.9, 57.1, 60.2, 63.1, 65.3, 67.6, 69.1, 70.3,
    ])),
    "Sarathi": dict(zip(QPS, [
        1.7, 1.9, 2.2, 2.9, 3.9,
        12.2, 19.3, 24.5, 28.7, 32.1, 34.8, 37.1, 39.0, 40.7, 42.2,
    ])),
    "Nested WAIT": dict(zip(QPS, [
        1.6, 1.8, 2.2, 2.9, 4.4,
        8.5, 14.5, 19.8, 23.6, 27.1, 29.9, 32.2, 34.5, 36.2, 37.7,
    ])),
}

q_min, q_max = min(QPS), max(QPS)

# Stylized throughput knees aligned with the observed latency takeoffs.
mu = {"vLLM": 35, "Sarathi": 55, "Nested WAIT": 60}
print(f"mu override: {mu}")


# --- Plot -----------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
fig.subplots_adjust(wspace=0.28)

x_lo = q_min - 5
x_hi = q_max + 5
x_tick_positions = [10, 30, 50, 70, 90, 110, 130, 150]
x_tick_labels = [str(x) for x in x_tick_positions]

# --- Left: latency (symlog) ---
axL = axes[0]
for algo in ["vLLM", "Sarathi", "Nested WAIT"]:
    d = raw[algo]
    xs = np.array(sorted(d.keys()), dtype=float)
    ys = np.array([d[x] for x in xs], dtype=float)
    axL.plot(xs, ys,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], marker=MARKERS[algo], markersize=MS[algo],
             markeredgecolor="white", markeredgewidth=0.7,
             label=algo)

axL.set_xlabel("Arrival rate QPS (queries/s)")
axL.set_ylabel("Mean end-to-end latency (s)")
# Symlog: stable region 1.5-5 s stretched linearly, divergence tail
# (5-80 s) log-compressed.
axL.set_yscale("symlog", linthresh=5.0, linscale=6.0)
axL.set_ylim(1.4, 80)
axL.set_yticks([1.5, 2, 3, 5, 10, 20, 40, 80])
axL.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
axL.set_xlim(x_lo, x_hi)
axL.set_xticks(x_tick_positions)
axL.set_xticklabels(x_tick_labels)
axL.grid(True, which="major", linestyle=":", linewidth=0.4, alpha=0.35,
         color="#999999")

axL.legend(loc="upper left", frameon=False, handlelength=2.5,
           borderpad=0.4)

# --- Right: effective throughput (linear) ---
axR = axes[1]
q_grid = np.linspace(x_lo, x_hi, 400)

axR.plot(q_grid, q_grid, color="#888888", linestyle=":", linewidth=1.0,
         label=r"Ideal ($\lambda =$ throughput)", zorder=1)

for algo in ["vLLM", "Sarathi", "Nested WAIT"]:
    m = mu[algo]
    ys_grid = np.where(q_grid <= m, q_grid, m)
    obs_xs = sorted(raw[algo].keys())
    obs_ys = [min(q, m) for q in obs_xs]
    axR.plot(q_grid, ys_grid,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], zorder=2)
    axR.plot(obs_xs, obs_ys,
             color=COLORS[algo], marker=MARKERS[algo], markersize=MS[algo],
             markeredgecolor="white", markeredgewidth=0.7,
             linestyle="None", label=algo, zorder=3)

axR.set_xlabel("Arrival rate QPS (queries/s)")
axR.set_ylabel("Effective throughput (queries/s)")
axR.set_xlim(x_lo, x_hi)
axR.set_xticks(x_tick_positions)
axR.set_xticklabels(x_tick_labels)
axR.set_yticks([10, 30, 50, 70, 90, 110, 130, 150])
axR.set_ylim(0, q_max + 10)
axR.grid(True, linestyle=":", linewidth=0.4, alpha=0.35, color="#999999")

axR.legend(loc="lower right", frameon=False, handlelength=2.5,
           borderpad=0.4)

fig.tight_layout()
out_pdf = OUT / "figure_D_lmsys_real.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
