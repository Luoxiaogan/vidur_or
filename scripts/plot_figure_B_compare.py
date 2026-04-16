"""
Figure B: single-type mean latency + effective throughput vs arrival rate.

Workload: p512d20, Llama-3-8B on simulated A100 (Vidur).
Policies compared:
  - vLLM (no chunked prefill)
  - Sarathi (chunk_size = 512)
  - WAIT (ours; chunk_size = 256, total_limit = 21)

Data: experiments.db, nreq >= 5000; we take best (min) result per
(algorithm, rate) — consistent with a per-rate config selection rule.

Layout: 1 x 2 side-by-side
  - Left  : mean latency vs rate, log y
  - Right : effective throughput vs rate, linear
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
    "font.size": 13,
    "axes.labelsize": 14,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
})

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "experiments.db"
OUT = BASE / "outputs" / "timeseries"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"vLLM": "#ff7f0e", "Sarathi": "#d62728", "WAIT": "#1f77b4"}
LINESTYLES = {"vLLM": "--", "Sarathi": "-.", "WAIT": "-"}
MARKERS = {"vLLM": "^", "Sarathi": "s", "WAIT": "o"}
LW = {"vLLM": 1.8, "Sarathi": 1.8, "WAIT": 2.3}

# --- Data load ------------------------------------------------------------
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("""
    SELECT algorithm, arrival_rate, MIN(mean_latency)
    FROM experiments
    WHERE l0=512 AND l1=20 AND nreq>=5000
      AND ( (algorithm='sarathi' AND chunk_size=512)
         OR (algorithm='vllm')
         OR (algorithm='wait_cp' AND chunk_size=256 AND total_limit=21) )
    GROUP BY algorithm, arrival_rate
    ORDER BY algorithm, arrival_rate
""")
rows = cur.fetchall()
conn.close()

raw = {"vLLM": {}, "Sarathi": {}, "WAIT": {}}
alias = {"sarathi": "Sarathi", "vllm": "vLLM", "wait_cp": "WAIT"}
for algo_raw, r, lat in rows:
    raw[alias[algo_raw]][float(r)] = float(lat)

rates = sorted(set(r for d in raw.values() for r in d.keys()))
r_min, r_max = min(rates), max(rates)
print(f"Rates: {rates}")

# --- Sustainable throughput estimate --------------------------------------
# Knee = first rate where latency ratio to previous point exceeds 2.
def estimate_mu(d):
    keys = sorted(d.keys())
    vals = [d[k] for k in keys]
    for i in range(1, len(keys)):
        if vals[i] / max(vals[i - 1], 1e-9) > 2.0:
            return keys[i - 1]
    return keys[-1]

mu = {algo: estimate_mu(d) for algo, d in raw.items()}
print(f"Sustainable throughput mu: {mu}")


# --- Plot -----------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))

# Common x-axis range with padding
x_lo = r_min - 1.0
x_hi = r_max + 2.0
x_ticks = [r for r in range(int(r_min), int(r_max) + 1) if r % 2 == 0]

# --- Left: latency (log y) ---
axL = axes[0]
for algo in ["vLLM", "Sarathi", "WAIT"]:
    d = raw[algo]
    rs = sorted(d.keys())
    ys = [d[r] for r in rs]
    label = f"{algo}" + (" (ours)" if algo == "WAIT" else "")
    axL.plot(rs, ys,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], marker=MARKERS[algo], markersize=6.5,
             label=label)

axL.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
axL.set_ylabel("Mean end-to-end latency (s)")
axL.set_yscale("log")
axL.set_yticks([0.5, 1, 2, 5, 10, 20, 40])
axL.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
axL.set_xlim(x_lo, x_hi)
axL.set_xticks(x_ticks)
axL.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.6)
axL.legend(loc="upper left", frameon=False)

# --- Right: effective throughput (linear) ---
axR = axes[1]
r_grid = np.linspace(x_lo, x_hi, 400)

# Ideal y = lambda reference line (always stable, arrival = completion)
axR.plot(r_grid, r_grid, color="gray", linestyle=":", linewidth=1.2,
         label=r"Ideal ($\lambda = $ completion)", zorder=1)

for algo in ["vLLM", "Sarathi", "WAIT"]:
    m = mu[algo]
    ys = np.where(r_grid <= m, r_grid, m)
    # Use the observed rates as marker positions
    obs_rates = sorted(raw[algo].keys())
    obs_ys = [min(r, m) for r in obs_rates]
    label = f"{algo}" + (" (ours)" if algo == "WAIT" else "")
    axR.plot(r_grid, ys,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], zorder=2)
    axR.plot(obs_rates, obs_ys,
             color=COLORS[algo], marker=MARKERS[algo], markersize=6.5,
             linestyle="None", label=label, zorder=3)

axR.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
axR.set_ylabel("Effective throughput (requests/s)")
axR.set_xlim(x_lo, x_hi)
axR.set_xticks(x_ticks)
axR.set_ylim(x_lo, x_hi)
axR.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
axR.legend(loc="lower right", frameon=False)

fig.tight_layout()
out_pdf = OUT / "figure_B_single_type.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_pdf}")


# --- Cleanup exploratory variants ----------------------------------------
# B1 / B3 were exploration-only; keep the final B only.
for obsolete in [
    OUT / "figure_B1_logy_latency_only.pdf",
    OUT / "figure_B2_logy_latency_throughput.pdf",
    OUT / "figure_B3_brokeny_latency_throughput.pdf",
]:
    if obsolete.exists():
        obsolete.unlink()
        print(f"Removed exploratory: {obsolete.name}")
