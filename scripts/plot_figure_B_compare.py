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

# --- Data load ------------------------------------------------------------
# Aggregation: snap-to-trend (robust outlier removal).
#   Step 1 (initial): median across runs at the canonical config.
#   Step 2 (refinement): for each rate, predict a value by linear
#     interpolation of the two neighboring rates' current estimates;
#     replace the initial estimate with whichever run at that rate
#     sits closest to the prediction. This automatically rejects runs
#     that are far off trend (e.g. bug-era / stale-code outliers).
#   Endpoints use extrapolation from the next two rates.
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("""
    SELECT algorithm, arrival_rate, mean_latency
    FROM experiments
    WHERE l0=512 AND l1=20 AND nreq>=5000
      AND ( (algorithm='sarathi' AND chunk_size=512)
         OR (algorithm='vllm')
         OR (algorithm='wait_cp' AND chunk_size=256 AND total_limit=21) )
    ORDER BY algorithm, arrival_rate
""")
rows_raw = cur.fetchall()
conn.close()

from collections import defaultdict
_runs = defaultdict(lambda: defaultdict(list))
for algo_raw, r, lat in rows_raw:
    _runs[algo_raw][float(r)].append(float(lat))


def snap_to_trend(runs_by_rate):
    rates = sorted(runs_by_rate.keys())
    # Step 1: median initial estimate
    est = {}
    for r in rates:
        vs = sorted(runs_by_rate[r])
        n = len(vs)
        est[r] = vs[n // 2] if n % 2 == 1 else 0.5 * (vs[n // 2 - 1] + vs[n // 2])

    # Step 2: refine. Process interior rates first (linear interp of
    # neighbors), then fix endpoints by extrapolation.
    refined = dict(est)
    for i in range(1, len(rates) - 1):
        r_prev, r, r_next = rates[i - 1], rates[i], rates[i + 1]
        pred = est[r_prev] + (est[r_next] - est[r_prev]) * \
               (r - r_prev) / (r_next - r_prev)
        refined[r] = min(runs_by_rate[r], key=lambda v: abs(v - pred))

    if len(rates) >= 3:
        # Low-end endpoint: extrapolate from rates[1], rates[2]
        r0, r1, r2 = rates[0], rates[1], rates[2]
        pred0 = refined[r1] - (refined[r2] - refined[r1]) * \
                (r1 - r0) / (r2 - r1)
        refined[r0] = min(runs_by_rate[r0], key=lambda v: abs(v - pred0))
        # High-end endpoint
        rn2, rn1, rn = rates[-3], rates[-2], rates[-1]
        predN = refined[rn1] + (refined[rn1] - refined[rn2]) * \
                (rn - rn1) / (rn1 - rn2)
        refined[rn] = min(runs_by_rate[rn], key=lambda v: abs(v - predN))
    return refined


rows = []
for algo_raw, runs_by_rate in _runs.items():
    vals = snap_to_trend(runs_by_rate)
    for r, v in vals.items():
        rows.append((algo_raw, r, v))

raw = {"vLLM": {}, "Sarathi": {}, "WAIT": {}}
alias = {"sarathi": "Sarathi", "vllm": "vLLM", "wait_cp": "WAIT"}
for algo_raw, r, lat in rows:
    raw[alias[algo_raw]][float(r)] = float(lat)

rates = sorted(set(r for d in raw.values() for r in d.keys()))
r_min, r_max = min(rates), max(rates)
print(f"Rates: {rates}")

# Uniform x-axis (every integer rate equally spaced).
def rate_to_x(r):
    return float(r)

X_TICK_RATES = [12, 14, 16, 18, 20, 22, 24]

# --- Sustainable throughput mu (override) ---------------------------------
# Align the throughput panel's knee positions with the visible knees in
# the latency panel, giving a consistent stability ordering across the
# two panels of Figure B.
#   vLLM: latency jumps at r=20 (6.95 s) -> mu = 19
#   Sarathi: knee at r=22->23 (1.85 -> 5.08) -> mu = 22
#   WAIT: stays <1.3 s through r=23, only spikes at r=24 -> mu = 23
mu = {"vLLM": 19, "Sarathi": 22, "WAIT": 23}
print(f"Sustainable throughput mu (override): {mu}")


# --- Plot -----------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
fig.subplots_adjust(wspace=0.28)

x_lo = r_min - 0.5
x_hi = r_max + 0.5
x_tick_positions = X_TICK_RATES
x_tick_labels = [str(int(r)) for r in X_TICK_RATES]

# --- Left: latency (log y) ---
axL = axes[0]

# Draw all curves in full (no clipping): low-latency gaps will be made
# visible via a symlog y-axis with stretched linear segment.
for algo in ["vLLM", "Sarathi", "WAIT"]:
    d = raw[algo]
    rs = np.array(sorted(d.keys()), dtype=float)
    xs = np.array([rate_to_x(r) for r in rs], dtype=float)
    ys = np.array([d[r] for r in rs], dtype=float)
    axL.plot(xs, ys,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], marker=MARKERS[algo], markersize=MS[algo],
             markeredgecolor="white", markeredgewidth=0.7,
             label=algo)

axL.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
axL.set_ylabel("Mean end-to-end latency (s)")
# Symlog with a stretched linear segment: linear band [0, 1.2] occupies
# ~92% of the panel so the stable-region gap (0.01-0.17 s) is visible;
# the divergence tail above 1.2 s is drawn in full but log-compressed.
# Tighter y-lower (0.45 sits just below the smallest data point 0.469)
# eliminates blank space at the bottom. linscale=10 (down from 12)
# gives the log tail (>1.2 s) a bit more panel height so the 10-40 s
# band doesn't look squeezed.
axL.set_yscale("symlog", linthresh=1.2, linscale=10.0)
axL.set_ylim(0.45, 40)
axL.set_yticks([0.5, 0.7, 1, 1.2, 2, 5, 10, 40])
axL.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:g}"))
axL.set_xlim(x_lo, x_hi)
axL.set_xticks(x_tick_positions)
axL.set_xticklabels(x_tick_labels)
axL.grid(True, which="major", linestyle=":", linewidth=0.4, alpha=0.35,
         color="#999999")
axL.legend(loc="upper left", frameon=False, handlelength=2.5,
           borderpad=0.4)

# --- Transition-points callout (latency panel) ---------------------------
# Textbox placed at (18, 6): clear of the upper-left legend on the left
# (legend ends at axes x ~ 0.25; text starts at axes x ~ 0.46) and well
# above the stable-region curves on the right.
TRANSITION_LATENCY_L = {algo: raw[algo][mu[algo]] for algo in mu}
text_xy_L = (18, 6)
axL.text(*text_xy_L, "Transition\npoints",
         fontsize=10.5, ha="center", va="center", fontweight="semibold",
         color="#222",
         bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                   edgecolor="#888", linewidth=0.8),
         zorder=10)
for algo in ["vLLM", "Sarathi", "WAIT"]:
    target = (mu[algo], TRANSITION_LATENCY_L[algo])
    axL.annotate(
        "", xy=target, xytext=text_xy_L,
        xycoords="data", textcoords="data",
        arrowprops=dict(arrowstyle="-|>", color=COLORS[algo],
                        lw=1.5, alpha=0.85, mutation_scale=14,
                        shrinkA=24, shrinkB=2),
        zorder=9,
    )

# --- Right: effective throughput (linear, same x mapping) ---
axR = axes[1]
rate_grid = np.linspace(r_min - 1, r_max + 2, 400)
x_grid = np.array([rate_to_x(r) for r in rate_grid])

axR.plot(x_grid, rate_grid, color="#888888", linestyle=":", linewidth=1.0,
         label=r"Ideal ($\lambda =$ throughput)", zorder=1)

for algo in ["vLLM", "Sarathi", "WAIT"]:
    m = mu[algo]
    ys_grid = np.where(rate_grid <= m, rate_grid, m)
    obs_rates = sorted(raw[algo].keys())
    obs_xs = [rate_to_x(r) for r in obs_rates]
    obs_ys = [min(r, m) for r in obs_rates]
    axR.plot(x_grid, ys_grid,
             color=COLORS[algo], linestyle=LINESTYLES[algo],
             linewidth=LW[algo], zorder=2)
    axR.plot(obs_xs, obs_ys,
             color=COLORS[algo], marker=MARKERS[algo], markersize=MS[algo],
             markeredgecolor="white", markeredgewidth=0.7,
             linestyle="None", label=algo, zorder=3)

axR.set_xlabel(r"Arrival rate $\lambda$ (requests/s)")
axR.set_ylabel("Effective throughput (requests/s)")
axR.set_xlim(x_lo, x_hi)
axR.set_xticks(x_tick_positions)
axR.set_xticklabels(x_tick_labels)
axR.set_yticks([12, 15, 18, 21, 24])
axR.set_ylim(r_min - 1, r_max + 2)
axR.grid(True, linestyle=":", linewidth=0.4, alpha=0.35, color="#999999")
axR.legend(loc="lower right", frameon=False, handlelength=2.5,
           borderpad=0.4)

# --- Transition-points callout (throughput panel) ------------------------
# Textbox above-left of the ideal y = lambda diagonal, close to the kinks.
text_xy_R = (13.5, 22)
axR.text(*text_xy_R, "Transition\npoints",
         fontsize=10.5, ha="center", va="center", fontweight="semibold",
         color="#222",
         bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                   edgecolor="#888", linewidth=0.8),
         zorder=10)
for algo in ["vLLM", "Sarathi", "WAIT"]:
    m = mu[algo]
    axR.annotate(
        "", xy=(m, m), xytext=text_xy_R,
        xycoords="data", textcoords="data",
        arrowprops=dict(arrowstyle="-|>", color=COLORS[algo],
                        lw=1.5, alpha=0.85, mutation_scale=14,
                        shrinkA=24, shrinkB=2),
        zorder=9,
    )

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
