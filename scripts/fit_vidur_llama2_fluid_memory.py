#!/usr/bin/env python3
"""Fit a Vidur-calibrated affine model and compute fluid memory ratios.

This script is intentionally paper-facing: it uses the same model/device family
as Section 6 (Llama-2-7B on A100) and reports the fluid memory requirement
M*(lambda) relative to the experimental KV-cache cap.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

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
class PromptType:
    name: str
    prefill: int
    decode: int
    fraction: float


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
    generator_config = CustomRequestGeneratorConfig(max_tokens=args.prediction_max_tokens_per_request)
    Replica(replica_config, generator_config)
    scheduler_config = SarathiSchedulerConfig(chunk_size=args.chunk_size)
    return ExecutionTimePredictorRegistry.get(
        ExecutionTimePredictorType.RANDOM_FORREST,
        predictor_config=predictor_config,
        replica_config=replica_config,
        replica_scheduler_config=scheduler_config,
        metrics_config=MetricsConfig(),
    )


def make_prefill_request(req_id: int, prefill: int, decode: int) -> Request:
    req = Request(arrived_at=0.0, num_prefill_tokens=prefill, num_decode_tokens=decode)
    req._id = req_id
    req._num_processed_tokens = 0
    req._is_prefill_complete = False
    return req


def make_decode_request(req_id: int, prefill: int, decode: int, stage: int) -> Request:
    req = Request(arrived_at=0.0, num_prefill_tokens=prefill, num_decode_tokens=decode)
    req._id = req_id
    req._num_processed_tokens = prefill + max(1, stage)
    req._is_prefill_complete = True
    return req


def batch_time(
    predictor,
    prompt_type: PromptType,
    num_decode: int,
    decode_stage: int,
    prefill_chunk: int,
    req_start: int,
) -> tuple[float, int, int, int]:
    requests = []
    num_tokens = []
    rid = req_start
    for _ in range(num_decode):
        requests.append(make_decode_request(rid, prompt_type.prefill, prompt_type.decode, decode_stage))
        num_tokens.append(1)
        rid += 1
    if prefill_chunk > 0:
        requests.append(make_prefill_request(rid, prompt_type.prefill, prompt_type.decode))
        num_tokens.append(min(prefill_chunk, prompt_type.prefill))
    if not requests:
        return 0.0, 0, 0, req_start
    batch = Batch(replica_id=0, requests=requests, num_tokens=num_tokens)
    total_time = predictor.get_execution_time(batch, pipeline_stage=0).total_time
    kv_cache_tokens = sum(req.num_processed_tokens for req in requests)
    return total_time, kv_cache_tokens, sum(num_tokens), rid + 1


def parse_prompt_types(raw: str) -> list[PromptType]:
    out = []
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        name, prefill, decode, fraction = item.split(":")
        out.append(PromptType(name, int(prefill), int(decode), float(fraction)))
    total = sum(pt.fraction for pt in out)
    if not out or total <= 0:
        raise ValueError("prompt type fractions must be positive")
    return [PromptType(pt.name, pt.prefill, pt.decode, pt.fraction / total) for pt in out]


def lmsys_prompt_types(trace_file: Path, qps: float, nbins: int) -> list[PromptType]:
    df = pd.read_csv(trace_file)
    if "num_prefill_tokens" not in df.columns or "num_decode_tokens" not in df.columns:
        raise ValueError("trace file must have num_prefill_tokens and num_decode_tokens columns")
    df = df[(df.num_prefill_tokens < 500) & (df.num_decode_tokens < 500)].copy()
    seg_size = max(1, 500 // nbins)
    out = []
    for idx in range(nbins):
        lo = idx * seg_size + 1
        hi = 500 if idx == nbins - 1 else min(500, (idx + 1) * seg_size)
        sub = df[(df.num_decode_tokens >= lo) & (df.num_decode_tokens <= hi)]
        if len(sub) == 0:
            continue
        out.append(
            PromptType(
                name=f"d{hi}",
                prefill=max(1, int(round(sub.num_prefill_tokens.mean()))),
                decode=int(hi),
                fraction=len(sub) / len(df),
            )
        )
    return out


def fluid_A(prompt_types: list[PromptType], total_rate: float) -> float:
    return sum(
        total_rate * pt.fraction * (pt.decode + 1) * (pt.prefill + pt.decode / 2)
        for pt in prompt_types
    )


def fluid_memory(d0: float, d1: float, prompt_types: list[PromptType], total_rate: float) -> float:
    a = fluid_A(prompt_types, total_rate)
    denom = 1 - d1 * a
    if denom <= 0:
        return math.inf
    return d0 * a / denom


def sample_affine_data(args: argparse.Namespace, predictor, prompt_types: list[PromptType]) -> list[dict]:
    rows = []
    req_id = 0
    stages = args.decode_stages
    for pt in prompt_types:
        for n in args.decode_batch_sizes:
            for frac in stages:
                stage = max(1, min(pt.decode, int(round(pt.decode * frac))))
                t, kv, toks, req_id = batch_time(
                    predictor, pt, n, stage, 0, req_id
                )
                rows.append(
                    {
                        "prompt_type": pt.name,
                        "batch_kind": "decode",
                        "num_decode": n,
                        "decode_stage": stage,
                        "prefill_chunk": 0,
                        "kv_cache_tokens": kv,
                        "batch_tokens": toks,
                        "time_s": t,
                    }
                )
        for n in args.mixed_decode_batch_sizes:
            for prefill_chunk in args.prefill_chunks:
                stage = max(1, min(pt.decode, int(round(pt.decode * 0.5))))
                t, kv, toks, req_id = batch_time(
                    predictor, pt, n, stage, prefill_chunk, req_id
                )
                rows.append(
                    {
                        "prompt_type": pt.name,
                        "batch_kind": "mixed",
                        "num_decode": n,
                        "decode_stage": stage,
                        "prefill_chunk": min(prefill_chunk, pt.prefill),
                        "kv_cache_tokens": kv,
                        "batch_tokens": toks,
                        "time_s": t,
                    }
                )
    return rows


def fit_affine(rows: list[dict], fit_batch_kind: str) -> tuple[float, float, float, int]:
    if fit_batch_kind != "all":
        fit_rows = [r for r in rows if r["batch_kind"] == fit_batch_kind]
    else:
        fit_rows = rows
    if len(fit_rows) < 2:
        raise ValueError(f"not enough rows to fit batch_kind={fit_batch_kind}")
    x = np.array([r["kv_cache_tokens"] for r in fit_rows], dtype=float)
    y = np.array([r["time_s"] for r in fit_rows], dtype=float)
    design = np.column_stack([np.ones_like(x), x])
    d0, d1 = np.linalg.lstsq(design, y, rcond=None)[0]
    pred = d0 + d1 * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(d0), float(d1), r2, len(fit_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-name", default="meta-llama/Llama-2-7b-hf")
    parser.add_argument("--device", default="a100")
    parser.add_argument("--memory-margin-fraction", type=float, default=0.1)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--num-estimators", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=16)
    parser.add_argument("--min-samples-split", type=int, default=5)
    parser.add_argument("--k-fold-cv-splits", type=int, default=3)
    parser.add_argument("--num-training-job-threads", type=int, default=4)
    parser.add_argument("--prediction-max-prefill-chunk-size", type=int, default=512)
    parser.add_argument("--prediction-max-batch-size", type=int, default=64)
    parser.add_argument("--prediction-max-tokens-per-request", type=int, default=2048)
    parser.add_argument("--kv-capacity-tokens", type=float, default=1.37e5)
    parser.add_argument("--workload", choices=["single", "multi", "long", "lmsys"], default="single")
    parser.add_argument("--prompt-types", default="")
    parser.add_argument("--trace-file", type=Path, default=REPO_ROOT / "data" / "processed_traces" / "sample_2e5_input<200_output<500.csv")
    parser.add_argument("--lmsys-nbins", type=int, default=50)
    parser.add_argument("--rates", default="10,12,14,16,18,20,22,24")
    parser.add_argument("--decode-batch-sizes", type=lambda s: [int(x) for x in s.split(",") if x], default=[1, 2, 4, 8, 16, 32, 64, 96, 128])
    parser.add_argument("--mixed-decode-batch-sizes", type=lambda s: [int(x) for x in s.split(",") if x], default=[0, 4, 16, 64])
    parser.add_argument("--prefill-chunks", type=lambda s: [int(x) for x in s.split(",") if x], default=[256, 512])
    parser.add_argument("--decode-stages", type=lambda s: [float(x) for x in s.split(",") if x], default=[0.25, 0.5, 0.75, 1.0])
    parser.add_argument(
        "--fit-batch-kind",
        choices=["decode", "mixed", "all"],
        default="decode",
        help="Rows used for the affine KV-cache fit. Default decode matches the fluid memory model.",
    )
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "outputs" / "fluid_memory")
    return parser


def default_prompt_types(workload: str, prompt_types_raw: str, trace_file: Path) -> list[PromptType]:
    if prompt_types_raw:
        return parse_prompt_types(prompt_types_raw)
    if workload == "single":
        return [PromptType("p512d20", 512, 20, 1.0)]
    if workload == "multi":
        return [
            PromptType("p512d20", 512, 20, 0.7),
            PromptType("p512d50", 512, 50, 0.3),
        ]
    if workload == "long":
        return [PromptType("p512d1000", 512, 1000, 1.0)]
    raise ValueError("lmsys prompt types are built in main because qps-specific rates are reported separately")


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rates = [float(x) for x in args.rates.split(",") if x]

    if args.workload == "lmsys":
        # The type fractions are independent of rate, so use the first rate to
        # construct bins and normalize fractions.
        prompt_types = lmsys_prompt_types(args.trace_file, rates[0], args.lmsys_nbins)
    else:
        prompt_types = default_prompt_types(args.workload, args.prompt_types, args.trace_file)

    print("Creating Vidur Llama-2-7B/A100 predictor...", flush=True)
    predictor = make_predictor(args)
    print("Sampling batch compositions...", flush=True)
    rows = sample_affine_data(args, predictor, prompt_types)
    d0, d1, r2, fit_sample_count = fit_affine(rows, args.fit_batch_kind)

    prefix = args.output_dir / f"{args.workload}_llama2_a100"
    with open(prefix.with_suffix(".affine_samples.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = []
    for rate in rates:
        mstar = fluid_memory(d0, d1, prompt_types, rate)
        a = fluid_A(prompt_types, rate)
        summary_rows.append(
            {
                "workload": args.workload,
                "rate": rate,
                "A_lambda": a,
                "d0_s": d0,
                "d1_s_per_token": d1,
        "r2": r2,
        "fit_batch_kind": args.fit_batch_kind,
        "M_star_tokens": mstar,
                "C_tokens": args.kv_capacity_tokens,
                "M_star_over_C": mstar / args.kv_capacity_tokens if math.isfinite(mstar) else math.inf,
                "inside_fluid_region": math.isfinite(mstar) and mstar <= args.kv_capacity_tokens,
            }
        )
    with open(prefix.with_suffix(".mstar.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    metadata = {
        "model_name": args.model_name,
        "device": args.device,
        "workload": args.workload,
        "prompt_types": [pt.__dict__ for pt in prompt_types],
        "d0_s": d0,
        "d1_s_per_token": d1,
        "r2": r2,
        "fit_batch_kind": args.fit_batch_kind,
        "kv_capacity_tokens": args.kv_capacity_tokens,
        "fit_sample_count": fit_sample_count,
        "total_sample_count": len(rows),
    }
    prefix.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(metadata, indent=2), flush=True)
    print(f"Wrote {prefix.with_suffix('.affine_samples.csv')}", flush=True)
    print(f"Wrote {prefix.with_suffix('.mstar.csv')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
