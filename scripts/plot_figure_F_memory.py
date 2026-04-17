"""
Figure F: memory safeguard and eviction prevention near capacity.

Workload: long-decode (prefill 512, decode 1000), Poisson arrivals at
lambda = 4.0, with the KV-cache pool intentionally constrained to a
margin of 0.6 (i.e. capacity available to the scheduler is 60% of the
A100 80GB block pool). This is the "near-capacity" regime where the
distinction between scheduling policies becomes most stark.

Key story (single-source: nreq = 10000 run from CLAUDE.md log):
  - WAIT (tl=120):  31.3 s mean E2E latency, 0  restarts (evictions)
  - vLLM:           53.0 s mean E2E latency, 0  restarts
  - Sarathi:        78.1 s mean E2E latency, 3222 restarts (cascade!)

Three different mechanisms produce three different outcomes:
  - vLLM uses implicit admission control => no evictions, but
    over-conservative => latency 53 s.
  - Sarathi has no admission threshold and over-admits => triggers
    massive eviction cascade => latency 78 s.
  - WAIT uses an explicit total-limit budget => 0 evictions by
    construction AND lowest latency.

Layout: 1x2 side-by-side bar chart matching Figure B-E aesthetic.
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
    "xtick.labelsize": 11,
    "ytick.labelsize": 10.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
})

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "outputs" / "timeseries"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"vLLM": "#ff8c2b", "Sarathi": "#c0392b", "WAIT": "#1f6db5"}

POLICIES = ["vLLM", "Sarathi", "WAIT"]
LATENCY = {"vLLM": 53.0, "Sarathi": 78.1, "WAIT": 31.3}
EVICTIONS = {"vLLM": 0, "Sarathi": 3222, "WAIT": 0}

x = np.arange(len(POLICIES))
bar_kwargs = dict(width=0.55, edgecolor="white", linewidth=1.0)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
fig.subplots_adjust(wspace=0.32)

# --- Left: mean latency ---
axL = axes[0]
lat_vals = [LATENCY[p] for p in POLICIES]
bar_colors = [COLORS[p] for p in POLICIES]
bars_L = axL.bar(x, lat_vals, color=bar_colors, **bar_kwargs)
for rect, val in zip(bars_L, lat_vals):
    axL.text(rect.get_x() + rect.get_width() / 2,
             rect.get_height() + 1.5,
             f"{val:.1f}s",
             ha="center", va="bottom", fontsize=10.5,
             fontweight="semibold", color="#222")
axL.set_ylabel("Mean end-to-end latency (s)")
axL.set_xticks(x)
axL.set_xticklabels(POLICIES)
axL.set_ylim(0, max(lat_vals) * 1.18)
axL.grid(True, axis="y", linestyle=":", linewidth=0.4,
         alpha=0.35, color="#999999")
axL.set_axisbelow(True)
axL.set_title("(a) Mean latency", pad=8)

# --- Right: evictions (with broken-bar style label so 0 vs 3222 reads) ---
axR = axes[1]
ev_vals = [EVICTIONS[p] for p in POLICIES]
bars_R = axR.bar(x, ev_vals, color=bar_colors, **bar_kwargs)
for rect, val in zip(bars_R, ev_vals):
    if val == 0:
        axR.text(rect.get_x() + rect.get_width() / 2, 50,
                 "0",
                 ha="center", va="bottom", fontsize=10.5,
                 fontweight="semibold", color="#222")
    else:
        axR.text(rect.get_x() + rect.get_width() / 2,
                 rect.get_height() + 80,
                 f"{val:,}",
                 ha="center", va="bottom", fontsize=10.5,
                 fontweight="semibold", color="#222")
axR.set_ylabel("Number of evictions over simulation")
axR.set_xticks(x)
axR.set_xticklabels(POLICIES)
axR.set_ylim(0, max(ev_vals) * 1.18)
axR.grid(True, axis="y", linestyle=":", linewidth=0.4,
         alpha=0.35, color="#999999")
axR.set_axisbelow(True)
axR.set_title("(b) Evictions", pad=8)
axR.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{int(v):,}"))

fig.tight_layout()
out_pdf = OUT / "figure_F_memory_eviction.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
