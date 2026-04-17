"""
Figure I (Appendix B.5): prefill-decode separated workload.

Decode-only workload in a PD-disaggregated deployment: prefill is
off-loaded to a separate service, and the scheduler on the decode
side sees a stream of prompts with prefill 630 and decode 20 already
in the prefill-completed state. Arrival rates span 100 to 500
requests/s (the regime where decode-only throughput is the bottleneck).

Data: experiments.db.pd_separated, workload='p630d20'.
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

COLORS = {"vLLM (PD)": "#ff8c2b", "WAIT (PD)": "#1f6db5"}
LINESTYLES = {"vLLM (PD)": "--", "WAIT (PD)": "-"}
MARKERS = {"vLLM (PD)": "^", "WAIT (PD)": "o"}
LW = {"vLLM (PD)": 1.7, "WAIT (PD)": 2.7}
MS = {"vLLM (PD)": 7.5, "WAIT (PD)": 8.5}

conn = sqlite3.connect(DB)
rows = conn.execute("""
    SELECT arrival_rate,
           MIN(CASE WHEN algorithm='vllm_pd' THEN mean_latency END) AS vllm_l,
           MIN(CASE WHEN algorithm='wcp_pd'  THEN mean_latency END) AS wait_l
    FROM pd_separated
    WHERE workload='p630d20'
    GROUP BY arrival_rate
    ORDER BY arrival_rate
""").fetchall()
conn.close()

rates = [r[0] for r in rows]
vllm = [r[1] for r in rows]
wait = [r[2] for r in rows]
print(f"Rates: {rates}")
print(f"Improvement at r=500: {(vllm[-1]-wait[-1])/vllm[-1]*100:.1f}%")

fig, ax = plt.subplots(figsize=(6.5, 4.4))

ax.plot(rates, vllm,
        color=COLORS["vLLM (PD)"], linestyle=LINESTYLES["vLLM (PD)"],
        linewidth=LW["vLLM (PD)"], marker=MARKERS["vLLM (PD)"],
        markersize=MS["vLLM (PD)"], markeredgecolor="white",
        markeredgewidth=0.7, label="vLLM (PD-disagg.)")
ax.plot(rates, wait,
        color=COLORS["WAIT (PD)"], linestyle=LINESTYLES["WAIT (PD)"],
        linewidth=LW["WAIT (PD)"], marker=MARKERS["WAIT (PD)"],
        markersize=MS["WAIT (PD)"], markeredgecolor="white",
        markeredgewidth=0.7, label="WAIT (ours, PD-disagg.)")

ax.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
ax.set_ylabel("Mean end-to-end decode latency (s)")
ax.set_xticks([100, 150, 200, 250, 300, 350, 400, 450, 500])
ax.set_yticks([0, 1, 2, 3, 4, 5, 6])
ax.set_ylim(0, max(max(vllm), max(wait)) + 0.5)
ax.grid(True, linestyle=":", linewidth=0.4,
        alpha=0.35, color="#999999")
ax.legend(loc="upper left", frameon=False, handlelength=2.5,
          borderpad=0.4)

fig.tight_layout()
out_pdf = OUT / "figure_I_pd_separated.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
