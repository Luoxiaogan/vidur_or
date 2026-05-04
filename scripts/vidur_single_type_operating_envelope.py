#!/usr/bin/env python3
"""Operational-capacity diagnostic for Section 6 p512d20.

The single-type experiment uses a system-wide cap ``tl``.  This script computes
the memory envelope induced by that configured policy and the service rate of a
rotating balanced batch composition under Vidur's Llama-2-7B/A100 predictor.
The intent is to distinguish the physical GPU capacity from the smaller
operating envelope used in a specific experiment.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.vidur_single_type_fluid_memory_diagnostic import (  # noqa: E402
    _request,
    _round_blocks,
    make_predictor,
)
from vidur.entities.batch import Batch  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-name", default="meta-llama/Llama-2-7b-hf")
    parser.add_argument("--device", default="a100")
    parser.add_argument("--memory-margin-fraction", type=float, default=0.1)
    parser.add_argument("--prefill-len", type=int, default=512)
    parser.add_argument("--decode-len", type=int, default=20)
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--block-size", type=int, default=16)
    parser.add_argument("--tl", type=int, default=21)
    parser.add_argument("--physical-kv-capacity-tokens", type=float, default=1.37e5)
    parser.add_argument("--num-estimators", type=int, default=12)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--min-samples-split", type=int, default=5)
    parser.add_argument("--k-fold-cv-splits", type=int, default=2)
    parser.add_argument("--num-training-job-threads", type=int, default=2)
    parser.add_argument("--prediction-max-prefill-chunk-size", type=int, default=1024)
    parser.add_argument("--prediction-max-batch-size", type=int, default=128)
    parser.add_argument("--prediction-max-tokens-per-request", type=int, default=65536)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "fluid_memory" / "single_type_tl21_operating_envelope.csv",
    )
    return parser


def stage_specs(args: argparse.Namespace):
    specs = []
    k_prefill = int(math.ceil(args.prefill_len / args.chunk_size))
    for chunk_idx in range(k_prefill):
        processed = min(chunk_idx * args.chunk_size, args.prefill_len)
        remaining = args.prefill_len - processed
        chunk = min(args.chunk_size, remaining)
        specs.append(
            {
                "kind": "prefill",
                "stage": chunk_idx,
                "processed": processed,
                "num_tokens": chunk,
                "block_kv": _round_blocks(args.prefill_len, args.block_size),
                "continuous_kv": processed,
                "prefill_complete": False,
            }
        )
    for stage in range(1, args.decode_len + 1):
        processed = args.prefill_len + stage
        specs.append(
            {
                "kind": "decode",
                "stage": stage,
                "processed": processed,
                "num_tokens": 1,
                "block_kv": _round_blocks(processed, args.block_size),
                "continuous_kv": processed,
                "prefill_complete": True,
            }
        )
    return specs


def make_batch(args: argparse.Namespace, specs_with_counts):
    requests = []
    num_tokens = []
    req_id = 0
    for spec, count in specs_with_counts:
        for _ in range(count):
            requests.append(
                _request(
                    req_id,
                    args.prefill_len,
                    args.decode_len,
                    spec["processed"],
                    spec["prefill_complete"],
                )
            )
            num_tokens.append(spec["num_tokens"])
            req_id += 1
    return Batch(replica_id=0, requests=requests, num_tokens=num_tokens)


def rotation_counts(total_limit: int, depth: int, rotation: int) -> list[int]:
    base = total_limit // depth
    remainder = total_limit % depth
    return [
        base + (1 if ((idx - rotation) % depth) < remainder else 0)
        for idx in range(depth)
    ]


def main() -> int:
    args = build_parser().parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    predictor = make_predictor(args)
    specs = stage_specs(args)
    depth = len(specs)
    p = args.tl / depth

    full_block_sum = sum(s["block_kv"] for s in specs)
    full_continuous_sum = sum(s["continuous_kv"] for s in specs)
    m_fluid_block = p * full_block_sum
    m_fluid_continuous = p * full_continuous_sum
    c_op_worst_block = args.tl * _round_blocks(args.prefill_len + args.decode_len, args.block_size)

    rows = []
    for rotation in range(depth):
        counts = rotation_counts(args.tl, depth, rotation)
        specs_with_counts = [
            (spec, count) for spec, count in zip(specs, counts) if count > 0
        ]
        batch = make_batch(args, specs_with_counts)
        exec_time = float(predictor.get_execution_time(batch, pipeline_stage=0).total_time)
        block_tokens = sum(s["block_kv"] * count for s, count in zip(specs, counts))
        continuous_tokens = sum(
            s["continuous_kv"] * count for s, count in zip(specs, counts)
        )
        completions = counts[-1]
        rows.append(
            {
                "rotation": rotation,
                "terminal_stage_count": completions,
                "tl": args.tl,
                "pipeline_depth": depth,
                "fluid_per_stage_P": p,
                "batch_size_requests": batch.size,
                "batch_new_tokens": batch.total_num_tokens,
                "representative_block_kv_tokens": block_tokens,
                "representative_continuous_kv_tokens": continuous_tokens,
                "iteration_time_s": exec_time,
                "fluid_completion_boundary_req_s": completions / exec_time,
                "C_op_worst_block_tokens": c_op_worst_block,
                "M_fluid_block_tokens": m_fluid_block,
                "M_fluid_continuous_tokens": m_fluid_continuous,
                "M_fluid_over_C_op_worst": m_fluid_block / c_op_worst_block,
                "C_op_worst_over_C_phys": c_op_worst_block / args.physical_kv_capacity_tokens,
                "C_phys_tokens": args.physical_kv_capacity_tokens,
            }
        )

    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    cycle_time = sum(r["iteration_time_s"] for r in rows)
    cycle_completions = sum(r["terminal_stage_count"] for r in rows)
    cycle_completion_rate = cycle_completions / cycle_time
    summary = {
        "tl": args.tl,
        "pipeline_depth": depth,
        "fluid_per_stage_P": p,
        "C_op_worst_block_tokens": c_op_worst_block,
        "M_fluid_block_tokens": m_fluid_block,
        "M_fluid_continuous_tokens": m_fluid_continuous,
        "M_fluid_over_C_op_worst": m_fluid_block / c_op_worst_block,
        "C_op_worst_over_C_phys": c_op_worst_block / args.physical_kv_capacity_tokens,
        "cycle_time_s": cycle_time,
        "cycle_completions": cycle_completions,
        "cycle_completion_boundary_req_s": cycle_completion_rate,
        "service_boundary_min_req_s": min(r["fluid_completion_boundary_req_s"] for r in rows),
        "service_boundary_mean_req_s": sum(r["fluid_completion_boundary_req_s"] for r in rows) / len(rows),
        "service_boundary_max_req_s": max(r["fluid_completion_boundary_req_s"] for r in rows),
        "output": str(args.output),
    }
    args.output.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
