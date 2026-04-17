"""
Figure E: finite-horizon scaling check at the stability boundary.

Two side-by-side panels at near-boundary arrival rates:
  Left  : multi-type W3, lambda = 22 (WAIT bounded; Sarathi diverges)
  Right : multi-type W3, lambda = 23 (both growing; WAIT slower)

Each panel shows mean end-to-end latency vs simulation horizon (nreq).
A bounded curve (mean latency stops growing as nreq -> infinity) is the
empirical signature of a stable policy at that arrival rate; a curve
that grows linearly with nreq is the signature of an unstable policy.

This figure responds to Reviewer 3's request to confirm that the
divergence points reported in Figures B-D are real, not finite-horizon
artifacts.

Data: experiments.db, table stability_verification, multi-type W3.
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
    "legend.fontsize": 10.5,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
})

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "experiments.db"
OUT = BASE / "outputs" / "timeseries"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"Sarathi": "#c0392b", "Nested WAIT": "#1f6db5"}
LINESTYLES = {"Sarathi": "--", "Nested WAIT": "-"}
MARKERS = {"Sarathi": "s", "Nested WAIT": "o"}
LW = {"Sarathi": 1.7, "Nested WAIT": 2.7}
MS = {"Sarathi": 7.5, "Nested WAIT": 8.5}

# --- Data load ------------------------------------------------------------
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("""
    SELECT algorithm, arrival_rate, nreq, MIN(mean_latency)
    FROM stability_verification
    WHERE algorithm IN ('sarathi', 'wcp')
    GROUP BY algorithm, arrival_rate, nreq
    ORDER BY arrival_rate, nreq, algorithm
""")
rows = cur.fetchall()
conn.close()

alias = {"sarathi": "Sarathi", "wcp": "Nested WAIT"}
data = {alias[a]: {} for a in alias}
for algo_raw, r, nreq, lat in rows:
    data[alias[algo_raw]].setdefault(float(r), {})[int(nreq)] = float(lat)

NREQS = [2000, 5000, 10000, 20000]
RATES_LEFT = 22.0
RATES_RIGHT = 23.0


def panel_data(rate):
    sar = [data["Sarathi"][rate][n] for n in NREQS]
    waw = [data["Nested WAIT"][rate][n] for n in NREQS]
    return sar, waw

sar_22, waw_22 = panel_data(RATES_LEFT)
sar_23, waw_23 = panel_data(RATES_RIGHT)
print(f"r=22: Sar {sar_22} | WAIT {waw_22}")
print(f"r=23: Sar {sar_23} | WAIT {waw_23}")


# --- Plot -----------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 5.0))
fig.subplots_adjust(wspace=0.30)


def render_panel(ax, sar, waw, rate, title):
    nreq_arr = np.array(NREQS)
    ax.plot(nreq_arr, sar,
            color=COLORS["Sarathi"], linestyle=LINESTYLES["Sarathi"],
            linewidth=LW["Sarathi"], marker=MARKERS["Sarathi"],
            markersize=MS["Sarathi"], markeredgecolor="white",
            markeredgewidth=0.7, label="Sarathi")
    ax.plot(nreq_arr, waw,
            color=COLORS["Nested WAIT"], linestyle=LINESTYLES["Nested WAIT"],
            linewidth=LW["Nested WAIT"], marker=MARKERS["Nested WAIT"],
            markersize=MS["Nested WAIT"], markeredgecolor="white",
            markeredgewidth=0.7, label="Nested WAIT")
    ax.set_xscale("log")
    ax.set_xticks(NREQS)
    ax.set_xticklabels(["2k", "5k", "10k", "20k"])
    ax.minorticks_off()
    ax.set_xlabel(r"Simulation horizon $N$ (number of requests)")
    ax.set_ylabel("Mean end-to-end latency (s)")
    ax.set_title(title, pad=10)
    ax.grid(True, which="major", linestyle=":", linewidth=0.4,
            alpha=0.35, color="#999999")
    ax.legend(loc="upper left", frameon=False, handlelength=2.5,
              borderpad=0.4)
    ax.set_xlim(NREQS[0] * 0.85, NREQS[-1] * 1.15)


render_panel(axes[0], sar_22, waw_22, RATES_LEFT,
             r"(a) $\lambda = 22$  —  WAIT stable, Sarathi unstable")
render_panel(axes[1], sar_23, waw_23, RATES_RIGHT,
             r"(b) $\lambda = 23$  —  past WAIT's boundary")

fig.tight_layout()
out_pdf = OUT / "figure_E_stability.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
