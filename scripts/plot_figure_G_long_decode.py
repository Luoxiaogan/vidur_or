"""
Figure G (Appendix B.1): long-decode workload.

Workload: p512d1000 (prefill 512, decode 1000), Poisson arrivals,
lambda = 0.5 to 5.0 in steps of 0.5.

Responds to Reviewer 2's Comment on "how the algorithm behaves when the
output length exceeds 1000 tokens".

Data: experiments.db.long_decode_v2, MIN over hyperparameter variants
per (algo, rate).
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

COLORS = {"vLLM": "#ff8c2b", "Sarathi": "#c0392b", "WAIT": "#1f6db5"}
LINESTYLES = {"vLLM": "--", "Sarathi": "--", "WAIT": "-"}
MARKERS = {"vLLM": "^", "Sarathi": "s", "WAIT": "o"}
LW = {"vLLM": 1.7, "Sarathi": 1.7, "WAIT": 2.7}
MS = {"vLLM": 7.5, "Sarathi": 7.5, "WAIT": 8.5}

conn = sqlite3.connect(DB)
rows = conn.execute("""
    SELECT arrival_rate,
           MIN(CASE WHEN algorithm='vllm'      THEN mean_latency END) vllm_l,
           MIN(CASE WHEN algorithm='sarathi'   THEN mean_latency END) sar_l,
           MIN(CASE WHEN algorithm LIKE 'wcp%' THEN mean_latency END) wait_l
    FROM long_decode_v2
    WHERE workload = 'p512d1000'
    GROUP BY arrival_rate
    ORDER BY arrival_rate
""").fetchall()
conn.close()

rates = [r[0] for r in rows]
vllm = [r[1] for r in rows]
sar = [r[2] for r in rows]
wait = [r[3] for r in rows]
print(f"Rates: {rates}")
print(f"WAIT vs Sarathi at r=4.5: {wait[8]:.2f} vs {sar[8]:.2f}")

fig, ax = plt.subplots(figsize=(6.5, 4.4))

for algo, ys in [("vLLM", vllm), ("Sarathi", sar), ("WAIT", wait)]:
    ax.plot(rates, ys,
            color=COLORS[algo], linestyle=LINESTYLES[algo],
            linewidth=LW[algo], marker=MARKERS[algo],
            markersize=MS[algo], markeredgecolor="white",
            markeredgewidth=0.7, label=algo)

ax.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
ax.set_ylabel("Mean end-to-end latency (s)")
ax.set_xticks(rates)
ax.set_xticklabels([f"{r:.1f}" for r in rates])
ax.set_yscale("log")
ax.set_yticks([12, 15, 20, 30, 50, 75])
ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
ax.set_ylim(10.5, 80)
ax.grid(True, which="major", linestyle=":", linewidth=0.4,
        alpha=0.35, color="#999999")
ax.legend(loc="upper left", frameon=False, handlelength=2.5,
          borderpad=0.4)

fig.tight_layout()
out_pdf = OUT / "figure_G_long_decode.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")
