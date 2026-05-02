"""
Figure A (Appendix): Vidur simulator fidelity against real A100 GPU.

Scatter of real vs predicted iteration time for Llama-2-7B, using the
powers-of-two batch-size grid B in {1,2,4,...,256}, with prefill=256 and
decode=20.

Output:
    outputs/validation_database/figures/figure_A_sim_fidelity.pdf
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --- Style ----------------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["CMU Serif"],
    "mathtext.fontset": "cm",
    "font.size": 13,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 11,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
})

# --- Paths ----------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
DB = BASE / "outputs" / "validation_database" / "vidur_validation.db"
OUT = BASE / "outputs" / "validation_database" / "figures" / "figure_A_sim_fidelity.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

# --- Data -----------------------------------------------------------------
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute(
    """
    SELECT batch_size, real_ms, predicted_ms, abs_error_percent, region
    FROM comparison_results
    WHERE model = ?
      AND prefill_len = 256
      AND decode_len = 20
      AND batch_size IN (1, 2, 4, 8, 16, 32, 64, 128, 256)
    ORDER BY batch_size
    """,
    ("Llama-2-7B",),
)
rows = cur.fetchall()
conn.close()

batch = np.array([r[0] for r in rows])
real = np.array([r[1] for r in rows])
pred = np.array([r[2] for r in rows])
ape = np.array([r[3] for r in rows])
region = np.array([r[4] for r in rows])

mape = float(ape.mean())
ss_res = float(np.sum((real - pred) ** 2))
ss_tot = float(np.sum((real - real.mean()) ** 2))
r2 = 1.0 - ss_res / ss_tot
n = len(batch)

print(f"N = {n}, MAPE = {mape:.2f}%, R2 = {r2:.4f}")
print(f"Batch range: [{int(batch.min())}, {int(batch.max())}]")

# --- Plot -----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(5.2, 5.0))

lo = min(real.min(), pred.min())
hi = max(real.max(), pred.max())
pad = 0.05 * (hi - lo)
lims = (lo - pad, hi + pad)

# y = x reference line with in-line label
ax.plot(lims, lims, linestyle="--", color="gray", linewidth=1.0, zorder=1)
# Place "y = x" tag near the upper-left of the diagonal, slightly above it
tag_x = lims[0] + 0.08 * (lims[1] - lims[0])
tag_y = tag_x + 0.05 * (lims[1] - lims[0])
ax.text(tag_x, tag_y, r"$y = x$", fontsize=11, color="gray",
        ha="left", va="bottom", rotation=45,
        rotation_mode="anchor")

# Scatter points. Each point is one batch-size configuration; the coordinates
# compare the real measured iteration time with the simulator prediction.
ax.scatter(real, pred, s=44, color="#1f77b4", edgecolor="white",
           linewidth=0.7, zorder=3)

ax.set_xlim(lims)
ax.set_ylim(lims)
ax.set_aspect("equal", adjustable="box")

ax.set_xlabel("Measured iteration time on NVIDIA A100 (ms)")
ax.set_ylabel("Vidur simulator prediction (ms)")

# Annotation (lower-right): fidelity metrics for the plotted grid.
# Experimental setup (model, hardware, prefill/decode, batch range) goes in
# the caption, not on the figure itself.
ax.text(
    0.97, 0.05,
    f"$R^2 = {r2:.4f}$\nMAPE $= {mape:.2f}\\%$",
    transform=ax.transAxes,
    ha="right", va="bottom",
    fontsize=12,
    bbox=dict(boxstyle="round,pad=0.45", facecolor="white",
              edgecolor="#bbbbbb", linewidth=0.8),
)

ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.5)

fig.tight_layout()
fig.savefig(OUT, bbox_inches="tight")
print(f"Saved: {OUT}")
