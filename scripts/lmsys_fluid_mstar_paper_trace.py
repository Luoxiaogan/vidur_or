#!/usr/bin/env python3
"""Compute the LMSYS fluid memory requirement from the paper trace.

This is a lightweight diagnostic. It reuses the Vidur-calibrated affine
coefficients already stored by scripts/fit_vidur_llama2_fluid_memory.py, but
rebuilds the LMSYS type distribution from the same filtered trace used by the
paper's distribution figure.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE = REPO_ROOT / "lmsys_chat_1m_dataset" / "output_trace" / "lmsys_chat_1m_dataset.csv"
DEFAULT_AFFINE = REPO_ROOT / "outputs" / "fluid_memory" / "lmsys_llama2_a100.json"
DEFAULT_OUT = REPO_ROOT / "outputs" / "fluid_memory" / "lmsys_paper_trace_mstar.csv"


def build_lmsys_bins(trace: Path, nbins: int) -> tuple[list[dict], dict]:
    df = pd.read_csv(trace)
    df = df[(df["question_length"] < 500) & (df["answer_length"] < 500)].copy()
    seg_size = max(1, 500 // nbins)
    bins: list[dict] = []
    for idx in range(nbins):
        lo = idx * seg_size + 1
        hi = 500 if idx == nbins - 1 else min(500, (idx + 1) * seg_size)
        sub = df[(df["answer_length"] >= lo) & (df["answer_length"] <= hi)]
        if sub.empty:
            continue
        bins.append(
            {
                "lo": lo,
                "hi": hi,
                "prefill_mean": float(sub["question_length"].mean()),
                "decode_representative": float(hi),
                "fraction": float(len(sub) / len(df)),
                "count": int(len(sub)),
            }
        )
    stats = {
        "filtered_requests": int(len(df)),
        "prefill_mean": float(df["question_length"].mean()),
        "prefill_median": float(df["question_length"].median()),
        "decode_mean": float(df["answer_length"].mean()),
        "decode_median": float(df["answer_length"].median()),
    }
    return bins, stats


def fluid_a_unit(bins: list[dict]) -> float:
    return sum(
        b["fraction"]
        * (b["decode_representative"] + 1.0)
        * (b["prefill_mean"] + b["decode_representative"] / 2.0)
        for b in bins
    )


def mstar(rate: float, a_unit: float, d0: float, d1: float) -> float:
    a = rate * a_unit
    denom = 1.0 - d1 * a
    if denom <= 0:
        return math.inf
    return d0 * a / denom


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--affine-json", type=Path, default=DEFAULT_AFFINE)
    parser.add_argument("--nbins", type=int, default=50)
    parser.add_argument("--rates", default="10,20,30,40,50,60,70,80,90,100,110,120,130,140,150")
    parser.add_argument("--capacity", type=float, default=137000.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    meta = json.loads(args.affine_json.read_text())
    d0 = float(meta["d0_s"])
    d1 = float(meta["d1_s_per_token"])
    bins, stats = build_lmsys_bins(args.trace, args.nbins)
    a_unit = fluid_a_unit(bins)
    critical_rate = 1.0 / (d1 * a_unit)

    lo, hi = 0.0, critical_rate * 0.999999
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if mstar(mid, a_unit, d0, d1) <= args.capacity:
            lo = mid
        else:
            hi = mid
    capacity_crossing = lo

    rows = []
    for rate in [float(x) for x in args.rates.split(",") if x]:
        memory = mstar(rate, a_unit, d0, d1)
        rows.append(
            {
                "rate_qps": rate,
                "A_unit": a_unit,
                "d0_s": d0,
                "d1_s_per_token": d1,
                "M_star_tokens": memory,
                "C_tokens": args.capacity,
                "M_star_over_C": memory / args.capacity if math.isfinite(memory) else math.inf,
                "inside_fluid_region": math.isfinite(memory) and memory <= args.capacity,
                "fluid_capacity_crossing_qps": capacity_crossing,
                "fluid_denominator_critical_qps": critical_rate,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        **stats,
        "nbins": args.nbins,
        "A_unit": a_unit,
        "d0_s": d0,
        "d1_s_per_token": d1,
        "capacity_tokens": args.capacity,
        "fluid_capacity_crossing_qps": capacity_crossing,
        "fluid_denominator_critical_qps": critical_rate,
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
