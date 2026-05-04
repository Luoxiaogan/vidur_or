#!/usr/bin/env python3
"""Vidur-calibrated fluid memory diagnostic for the p512d20 workload.

This diagnostic computes the memory scale of the balanced WAIT composition
used in the single-type Section 6 experiment.  It does not fit a global affine
model.  Instead, for each per-stage scale n, it constructs the balanced
chunked-prefill/decode pipeline batch, queries Vidur's Llama-2-7B/A100
execution-time predictor for that exact batch, and finds the smallest n whose
fluid completion rate covers a requested arrival rate.

The output is intended as an audit artifact for the C versus M* discussion:
M* is reported in KV-cache tokens under both the continuous token count and
Vidur's block-rounded memory accounting.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vidur.config.config import (  # noqa: E402
    CustomRequestGeneratorConfig,
    MetricsConfig,
    RandomForrestExecutionTimePredictorConfig,
    ReplicaConfig,
    SarathiSchedulerConfig,
)
from vidur.entities.batch import Batch  # noqa: E402
from vidur.entities.replica import Replica  # noqa: E402
from vidur.entities.request import Request  # noqa: E402
from vidur.execution_time_predictor import ExecutionTimePredictorRegistry  # noqa: E402
from vidur.types import ExecutionTimePredictorType  # noqa: E402


@dataclass(frozen=True)
class BalancedPoint:
    n: int
    batch_size: int
    batch_new_tokens: int
    continuous_kv_tokens: int
    block_kv_tokens: int
    iteration_time_s: float

    @property
    def completion_rate(self) -> float:
        return self.n / self.iteration_time_s


def make_predictor(args: argparse.Namespace):
    replica_config = ReplicaConfig(
        model_name=args.model_name,
        device=args.device,
        memory_margin_fraction=args.memory_margin_fraction,
        tensor_parallel_size=1,
        num_pipeline_stages=1,
    )
    predictor_config = RandomForrestExecutionTimePredictorConfig(
        num_estimators=[args.num_estimators],
        max_depth=[args.max_depth],
        min_samples_split=[args.min_samples_split],
        k_fold_cv_splits=args.k_fold_cv_splits,
        num_training_job_threads=args.num_training_job_threads,
        prediction_max_prefill_chunk_size=args.prediction_max_prefill_chunk_size,
        prediction_max_batch_size=args.prediction_max_batch_size,
        prediction_max_tokens_per_request=args.prediction_max_tokens_per_request,
    )
    generator_config = CustomRequestGeneratorConfig(
        max_tokens=args.prefill_len + args.decode_len + 50
    )
    Replica(replica_config, generator_config)
    scheduler_config = SarathiSchedulerConfig(chunk_size=args.chunk_size)
    return ExecutionTimePredictorRegistry.get(
        ExecutionTimePredictorType.RANDOM_FORREST,
        predictor_config=predictor_config,
        replica_config=replica_config,
        replica_scheduler_config=scheduler_config,
        metrics_config=MetricsConfig(),
    )


def _request(req_id: int, prefill: int, decode: int, processed: int, prefill_complete: bool) -> Request:
    req = Request(arrived_at=0.0, num_prefill_tokens=prefill, num_decode_tokens=decode)
    req._id = req_id
    req._num_processed_tokens = processed
    req._is_prefill_complete = prefill_complete
    return req


def _round_blocks(tokens: int, block_size: int) -> int:
    return int(math.ceil(tokens / block_size) * block_size)


def balanced_batch_point(args: argparse.Namespace, predictor, n: int) -> BalancedPoint:
    requests: list[Request] = []
    num_tokens: list[int] = []
    req_id = 0

    k_prefill = int(math.ceil(args.prefill_len / args.chunk_size))

    # Chunked prefill stages. Vidur allocates the full prefill KV blocks when a
    # request is admitted, so the block-rounded memory count uses prefill_len
    # for each in-progress prefill request.
    for chunk_idx in range(k_prefill):
        processed = min(chunk_idx * args.chunk_size, args.prefill_len)
        remaining = args.prefill_len - processed
        chunk = min(args.chunk_size, remaining)
        for _ in range(n):
            requests.append(
                _request(
                    req_id,
                    args.prefill_len,
                    args.decode_len,
                    processed,
                    prefill_complete=False,
                )
            )
            num_tokens.append(chunk)
            req_id += 1

    # Decode stages. A stage-s prompt has already materialized prefill+s KV
    # tokens and receives one new decode token in this iteration.
    for stage in range(1, args.decode_len + 1):
        processed = args.prefill_len + stage
        for _ in range(n):
            requests.append(
                _request(
                    req_id,
                    args.prefill_len,
                    args.decode_len,
                    processed,
                    prefill_complete=True,
                )
            )
            num_tokens.append(1)
            req_id += 1

    batch = Batch(replica_id=0, requests=requests, num_tokens=num_tokens)
    iteration_time = predictor.get_execution_time(batch, pipeline_stage=0).total_time

    continuous_kv_tokens = 0
    block_kv_tokens = 0
    for req in requests:
        if req.is_prefill_complete:
            continuous_kv_tokens += req.num_processed_tokens
            block_kv_tokens += _round_blocks(req.num_processed_tokens, args.block_size)
        else:
            continuous_kv_tokens += req.num_processed_tokens
            block_kv_tokens += _round_blocks(args.prefill_len, args.block_size)

    return BalancedPoint(
        n=n,
        batch_size=batch.size,
        batch_new_tokens=batch.total_num_tokens,
        continuous_kv_tokens=continuous_kv_tokens,
        block_kv_tokens=block_kv_tokens,
        iteration_time_s=float(iteration_time),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-name", default="meta-llama/Llama-2-7b-hf")
    parser.add_argument("--device", default="a100")
    parser.add_argument("--memory-margin-fraction", type=float, default=0.1)
    parser.add_argument("--prefill-len", type=int, default=512)
    parser.add_argument("--decode-len", type=int, default=20)
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--block-size", type=int, default=16)
    parser.add_argument("--kv-capacity-tokens", type=float, default=1.37e5)
    parser.add_argument("--rates", default="12,14,16,18,20,22,23,24")
    parser.add_argument(
        "--max-n",
        type=int,
        default=5,
        help="Default keeps the balanced batch size (22n for p512d20/cs256) within B<=128.",
    )
    parser.add_argument("--num-estimators", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=16)
    parser.add_argument("--min-samples-split", type=int, default=5)
    parser.add_argument("--k-fold-cv-splits", type=int, default=3)
    parser.add_argument("--num-training-job-threads", type=int, default=4)
    parser.add_argument("--prediction-max-prefill-chunk-size", type=int, default=1024)
    parser.add_argument(
        "--prediction-max-batch-size",
        type=int,
        default=128,
        help="Keep at 128 to stay within the raw Llama-2-7B/A100 profiling range.",
    )
    parser.add_argument("--prediction-max-tokens-per-request", type=int, default=65536)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "fluid_memory" / "single_type_vidur_balanced_mstar.csv",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rates = [float(x) for x in args.rates.split(",") if x]

    print("Creating Vidur Llama-2-7B/A100 predictor...", flush=True)
    predictor = make_predictor(args)

    points = [balanced_batch_point(args, predictor, n) for n in range(1, args.max_n + 1)]
    rows = []
    for rate in rates:
        feasible = [p for p in points if p.completion_rate >= rate]
        chosen = feasible[0] if feasible else points[-1]
        rows.append(
            {
                "workload": f"p{args.prefill_len}d{args.decode_len}",
                "rate": rate,
                "n_star_vidur": chosen.n,
                "covers_rate": chosen.completion_rate >= rate,
                "completion_rate_req_s": chosen.completion_rate,
                "iteration_time_s": chosen.iteration_time_s,
                "batch_size_requests": chosen.batch_size,
                "batch_new_tokens": chosen.batch_new_tokens,
                "M_star_continuous_kv_tokens": chosen.continuous_kv_tokens,
                "M_star_block_kv_tokens": chosen.block_kv_tokens,
                "C_tokens": args.kv_capacity_tokens,
                "M_star_block_over_C": chosen.block_kv_tokens / args.kv_capacity_tokens,
                "chunk_size": args.chunk_size,
                "block_size": args.block_size,
                "prediction_max_batch_size": args.prediction_max_batch_size,
            }
        )

    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    grid_output = args.output.with_name(args.output.stem + "_grid.csv")
    with grid_output.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "n",
                "completion_rate_req_s",
                "iteration_time_s",
                "batch_size_requests",
                "batch_new_tokens",
                "continuous_kv_tokens",
                "block_kv_tokens",
                "block_kv_over_C",
            ],
        )
        writer.writeheader()
        for p in points:
            writer.writerow(
                {
                    "n": p.n,
                    "completion_rate_req_s": p.completion_rate,
                    "iteration_time_s": p.iteration_time_s,
                    "batch_size_requests": p.batch_size,
                    "batch_new_tokens": p.batch_new_tokens,
                    "continuous_kv_tokens": p.continuous_kv_tokens,
                    "block_kv_tokens": p.block_kv_tokens,
                    "block_kv_over_C": p.block_kv_tokens / args.kv_capacity_tokens,
                }
            )

    metadata = {
        "model_name": args.model_name,
        "device": args.device,
        "prefill_len": args.prefill_len,
        "decode_len": args.decode_len,
        "chunk_size": args.chunk_size,
        "block_size": args.block_size,
        "kv_capacity_tokens": args.kv_capacity_tokens,
        "prediction_max_batch_size": args.prediction_max_batch_size,
        "output": str(args.output),
        "grid_output": str(grid_output),
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Wrote {args.output}", flush=True)
    print(f"Wrote {grid_output}", flush=True)
    for row in rows:
        print(
            f"rate={row['rate']:>4.1f} n={row['n_star_vidur']} "
            f"mu={row['completion_rate_req_s']:.2f}/s "
            f"M_block/C={row['M_star_block_over_C']:.3f}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
