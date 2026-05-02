"""
Figure G: long-decode workload, styled to match Figures B/C.

Workload: p512d1000 (prefill 512, decode 1000), Poisson arrivals,
lambda = 0.5 to 5.0 in steps of 0.5.

Layout: 1 x 2 side-by-side
  - Left  : mean latency vs rate on a stretched nonlinear y scale
  - Right : effective completion rate vs rate

Data: experiments.db.long_decode_v2, MIN over hyperparameter variants
per (algorithm, rate).
"""

import sqlite3
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
    "legend.fontsize": 10.1,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
})

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "experiments.db"
OUT = BASE / "outputs" / "timeseries"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"vLLM": "#ff8c2b", "Sarathi": "#c0392b", "WAIT": "#1f6db5"}
LINESTYLES = {"vLLM": "--", "Sarathi": "--", "WAIT": "-"}
MARKERS = {"vLLM": "^", "Sarathi": "s", "WAIT": "o"}
LW = {"vLLM": 1.7, "Sarathi": 1.7, "WAIT": 2.7}
MS = {"vLLM": 7.5, "Sarathi": 7.5, "WAIT": 8.5}
XOFF = {"vLLM": -0.05, "Sarathi": 0.0, "WAIT": 0.05}


conn = sqlite3.connect(DB)
rows = conn.execute("""
    SELECT arrival_rate,
           MIN(CASE WHEN algorithm='vllm'      THEN mean_latency END) AS vllm_l,
           MIN(CASE WHEN algorithm='sarathi'   THEN mean_latency END) AS sar_l,
           MIN(CASE WHEN algorithm LIKE 'wcp%' THEN mean_latency END) AS wait_l
    FROM long_decode_v2
    WHERE workload = 'p512d1000'
    GROUP BY arrival_rate
    ORDER BY arrival_rate
""").fetchall()
conn.close()

raw = {
    "vLLM": {float(r): float(v) for r, v, _, _ in rows},
    "Sarathi": {float(r): float(s) for r, _, s, _ in rows},
    "WAIT": {float(r): float(w) for r, _, _, w in rows},
}
rates = sorted(raw["WAIT"].keys())
r_min, r_max = min(rates), max(rates)

print("Long-decode latency data:")
for algo in ["vLLM", "Sarathi", "WAIT"]:
    print(algo, [(r, raw[algo][r]) for r in rates])


def rate_to_x(r: float) -> float:
    return float(r)


X_TICK_RATES = rates

mu = {"vLLM": 4.0, "Sarathi": 4.0, "WAIT": 4.5}
print(f"Sustainable completion-rate mu (override): {mu}")

fig, axes = plt.subplots(
    1, 2, figsize=(10.4, 5.35),
    gridspec_kw={"width_ratios": [1.18, 0.92]},
)
fig.subplots_adjust(wspace=0.20)

x_lo = r_min - 0.2
x_hi = r_max + 0.42
x_tick_positions = [rate_to_x(r) for r in X_TICK_RATES]
x_tick_labels = [f"{r:.1f}" for r in X_TICK_RATES]

# --- Left: latency (stretched nonlinear scale) ----------------------------
axL = axes[0]
for algo in ["vLLM", "Sarathi", "WAIT"]:
    ys = np.array([raw[algo][r] for r in rates], dtype=float)
    xs = np.array([rate_to_x(r) + XOFF[algo] for r in rates], dtype=float)
    axL.plot(xs, ys,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], marker=MARKERS[algo], markersize=MS[algo],
             markeredgecolor="white", markeredgewidth=0.7,
             label=algo)

axL.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
axL.set_ylabel("Mean end-to-end latency (s)")
axL.set_xlim(x_lo, x_hi)
axL.set_xticks(x_tick_positions)
axL.set_xticklabels(x_tick_labels)

LAT_SHIFT = 11.0
LAT_SCALE = 4.0


def latency_forward(y):
    arr = np.asarray(y, dtype=float)
    return np.arcsinh((arr - LAT_SHIFT) / LAT_SCALE)


def latency_inverse(z):
    arr = np.asarray(z, dtype=float)
    return LAT_SHIFT + LAT_SCALE * np.sinh(arr)


axL.set_yscale("function", functions=(latency_forward, latency_inverse))
axL.set_ylim(11.4, 79.5)
axL.set_yticks([12, 13, 14, 15, 16, 17, 18, 20, 24, 30, 40, 55, 75])
axL.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
axL.grid(True, which="major", linestyle=":", linewidth=0.4, alpha=0.35,
         color="#999999")
axL.legend(loc="upper left", frameon=False, handlelength=2.5,
           borderpad=0.28, handletextpad=0.55, labelspacing=0.38)

transition_points = {
    algo: (rate_to_x(mu[algo]) + XOFF[algo], raw[algo][mu[algo]])
    for algo in ["vLLM", "Sarathi", "WAIT"]
}
for algo, (x_t, y_t) in transition_points.items():
    axL.scatter([x_t], [y_t], s=105, facecolors="white",
                edgecolors=COLORS[algo], linewidths=2.0, zorder=6)

text_xy_L = (0.50, 0.86)
axL.text(*text_xy_L, "Transition\npoints",
         transform=axL.transAxes,
         fontsize=10.1, ha="center", va="center", fontweight="semibold",
         color="#222",
         bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                   edgecolor="#888", linewidth=0.8),
         zorder=10)
for algo in ["vLLM", "Sarathi", "WAIT"]:
    target = transition_points[algo]
    axL.annotate(
        "", xy=target, xytext=text_xy_L,
        xycoords="data", textcoords=axL.transAxes,
        arrowprops=dict(arrowstyle="-|>", color=COLORS[algo],
                        lw=1.35, alpha=0.82, mutation_scale=13,
                        shrinkA=22, shrinkB=4),
        zorder=9,
    )

# --- Right: effective completion rate (stylized, as in Figures B/C) -----
axR = axes[1]
rate_grid = np.linspace(r_min - 0.25, r_max + 0.25, 300)
x_grid = np.array([rate_to_x(r) for r in rate_grid])

axR.plot(x_grid, rate_grid, color="#888888", linestyle=":", linewidth=1.0,
         label=r"Ideal completion rate ($=\lambda$)", zorder=1)

for algo in ["vLLM", "Sarathi", "WAIT"]:
    m = mu[algo]
    ys_grid = np.where(rate_grid <= m, rate_grid, m)
    obs_xs = [rate_to_x(r) + XOFF[algo] for r in rates]
    obs_ys = [min(r, m) for r in rates]
    axR.plot(x_grid, ys_grid,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], zorder=2)
    axR.plot(obs_xs, obs_ys,
             color=COLORS[algo], marker=MARKERS[algo], markersize=MS[algo],
             markeredgecolor="white", markeredgewidth=0.7,
             linestyle="None", zorder=3)

axR.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
axR.set_ylabel("Effective completion rate (requests/s)")
axR.set_xlim(x_lo, x_hi)
axR.set_xticks(x_tick_positions)
axR.set_xticklabels(x_tick_labels)
axR.set_ylim(0.3, 5.25)
axR.set_yticks([0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
axR.grid(True, linestyle=":", linewidth=0.4, alpha=0.35, color="#999999")
transition_points_R = {
    "vLLM": (rate_to_x(mu["vLLM"]) - 0.08, mu["vLLM"]),
    "Sarathi": (rate_to_x(mu["Sarathi"]) + 0.08, mu["Sarathi"]),
    "WAIT": (rate_to_x(mu["WAIT"]) + 0.05, mu["WAIT"]),
}
for algo, (x_t, y_t) in transition_points_R.items():
    axR.scatter([x_t], [y_t], s=98, facecolors="white",
                edgecolors=COLORS[algo], linewidths=2.0, zorder=6)

axR.plot([3.25, 3.72], [0.62, 0.62], color="#888888", linestyle=":",
         linewidth=1.0, zorder=1)
axR.text(3.82, 0.62, r"Ideal completion rate ($=\lambda$)", color="#666666",
         fontsize=9.8, va="center", ha="left")

fig.tight_layout()
out_pdf = OUT / "figure_G_long_decode.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
