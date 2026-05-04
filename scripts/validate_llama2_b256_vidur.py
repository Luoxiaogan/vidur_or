#!/usr/bin/env python3
"""Validate the Llama-2-7B B=256 point used in the GPU/Vidur figure.

This script makes the validation path explicit:

1. Check the raw Vidur profiling coverage for Llama-2-7B on A100.
2. Load the recorded A100 measurement from the validation SQLite database.
3. Refit the linear validation model on the profiling-supported region
   (ACCURATE and ACCURATE_PLUS, i.e., B <= 128 in the current database).
4. Predict the requested batch size and report the error against the recorded
   A100 measurement.
5. Optionally, construct a Vidur Batch and query the random-forest execution
   time predictor directly. This can be slow because the predictor trains
   component models on first use.

The default mode is intentionally lightweight and reproducible on non-GPU
machines. Re-running the physical A100 measurement requires a GPU VM and the
separate measurement scripts.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "outputs/validation_database/vidur_validation.db"
DEFAULT_ATTENTION = (
    PROJECT_ROOT
    / "data/profiling/compute/a100/meta-llama/Llama-2-7b-hf/attention.csv"
)


@dataclass
class ValidationPoint:
    batch_size: int
    prefill_len: int
    decode_len: int
    kv_cache_size: int
    real_ms: float
    predicted_ms: float
    abs_error_percent: float
    region: str


def load_measurement(
    db_path: Path,
    batch_size: int,
    prefill_len: int,
    decode_len: int,
) -> ValidationPoint:
    conn = sqlite3.connect(db_path)
    row = pd.read_sql_query(
        """
        SELECT batch_size, prefill_len, decode_len, kv_cache_size, real_ms,
               predicted_ms, abs_error_percent, region
        FROM comparison_results
        WHERE model='Llama-2-7B'
          AND batch_size=?
          AND prefill_len=?
          AND decode_len=?
        """,
        conn,
        params=(batch_size, prefill_len, decode_len),
    )
    conn.close()

    if row.empty:
        raise RuntimeError(
            "No comparison_results row for "
            f"B={batch_size}, prefill={prefill_len}, decode={decode_len}."
        )

    r = row.iloc[0]
    return ValidationPoint(
        batch_size=int(r.batch_size),
        prefill_len=int(r.prefill_len),
        decode_len=int(r.decode_len),
        kv_cache_size=int(r.kv_cache_size),
        real_ms=float(r.real_ms),
        predicted_ms=float(r.predicted_ms),
        abs_error_percent=float(r.abs_error_percent),
        region=str(r.region),
    )


def print_profiling_coverage(attention_csv: Path, batch_size: int) -> None:
    df = pd.read_csv(attention_csv)
    unique_batches = sorted(df["batch_size"].unique())
    print("Raw Vidur attention profiling coverage")
    print(f"  file: {attention_csv.relative_to(PROJECT_ROOT)}")
    print(f"  rows: {len(df)}")
    print(f"  batch_size min/max: {min(unique_batches)} / {max(unique_batches)}")
    print(f"  contains B={batch_size}: {batch_size in set(unique_batches)}")
    print()


def refit_linear_validation_model(
    db_path: Path,
    batch_size: int,
    prefill_len: int,
    decode_len: int,
) -> tuple[float, float, float, float, int, int]:
    """Fit real_ms = d0 + d1 * kv_cache_size on ACCURATE(_PLUS) rows."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT batch_size, kv_cache_size, mean_ms, region
        FROM real_gpu_measurements
        WHERE model='Llama-2-7B'
          AND prefill_len=?
          AND decode_len=?
        ORDER BY batch_size
        """,
        conn,
        params=(prefill_len, decode_len),
    )
    conn.close()

    train = df[df["region"].isin(["ACCURATE", "ACCURATE_PLUS"])].copy()
    if train.empty:
        raise RuntimeError("No ACCURATE/ACCURATE_PLUS rows available for fitting.")

    d1, d0 = np.polyfit(train["kv_cache_size"], train["mean_ms"], 1)
    kv_cache_size = batch_size * (prefill_len + decode_len)
    predicted_ms = d0 + d1 * kv_cache_size
    return (
        float(d0),
        float(d1),
        float(predicted_ms),
        float(kv_cache_size),
        int(len(train)),
        int(train["batch_size"].max()),
    )


def run_vidur_predictor(
    batch_size: int,
    prefill_len: int,
    decode_len: int,
    prediction_max_batch_size: int,
    prediction_max_tokens_per_request: int,
    prediction_max_prefill_chunk_size: int,
    include_prefill: bool,
) -> None:
    """Query Vidur's random-forest predictor on constructed batch states."""
    from vidur.config.config import (
        CustomRequestGeneratorConfig,
        MetricsConfig,
        RandomForrestExecutionTimePredictorConfig,
        ReplicaConfig,
        SarathiSchedulerConfig,
    )
    from vidur.entities.batch import Batch
    from vidur.entities.replica import Replica
    from vidur.entities.request import Request
    from vidur.execution_time_predictor import ExecutionTimePredictorRegistry
    from vidur.types import ExecutionTimePredictorType

    replica_config = ReplicaConfig(
        model_name="meta-llama/Llama-2-7b-hf",
        device="a100",
        memory_margin_fraction=0.1,
        tensor_parallel_size=1,
        num_pipeline_stages=1,
    )
    predictor_config = RandomForrestExecutionTimePredictorConfig(
        prediction_max_prefill_chunk_size=prediction_max_prefill_chunk_size,
        prediction_max_batch_size=prediction_max_batch_size,
        prediction_max_tokens_per_request=prediction_max_tokens_per_request,
    )
    scheduler_config = SarathiSchedulerConfig(chunk_size=512)
    _ = Replica(
        replica_config,
        CustomRequestGeneratorConfig(max_tokens=prefill_len + decode_len + 50),
    )
    predictor = ExecutionTimePredictorRegistry.get(
        ExecutionTimePredictorType.RANDOM_FORREST,
        predictor_config=predictor_config,
        replica_config=replica_config,
        replica_scheduler_config=scheduler_config,
        metrics_config=MetricsConfig(),
    )

    def decode_request(req_id: int, processed: int) -> Request:
        req = Request(
            arrived_at=0.0,
            num_prefill_tokens=prefill_len,
            num_decode_tokens=decode_len,
        )
        req._id = req_id
        req._num_processed_tokens = processed
        req._is_prefill_complete = True
        return req

    def prefill_request(req_id: int) -> Request:
        req = Request(
            arrived_at=0.0,
            num_prefill_tokens=prefill_len,
            num_decode_tokens=decode_len,
        )
        req._id = req_id
        req._num_processed_tokens = 0
        req._is_prefill_complete = False
        return req

    print("Direct Vidur random-forest predictor")
    print("  note: this is component-model prediction, not physical GPU measurement")

    decode_processed = prefill_len + decode_len
    decode_batch = Batch(
        replica_id=0,
        requests=[decode_request(i, decode_processed) for i in range(batch_size)],
        num_tokens=[1] * batch_size,
    )
    decode_time = predictor.get_execution_time(decode_batch, pipeline_stage=0)
    print(
        "  pure decode batch: "
        f"B={batch_size}, avg cached tokens/request={decode_processed}, "
        f"time={decode_time.total_time * 1000:.3f} ms"
    )

    if include_prefill:
        prefill_batch = Batch(
            replica_id=0,
            requests=[prefill_request(i) for i in range(batch_size)],
            num_tokens=[prefill_len] * batch_size,
        )
        prefill_time = predictor.get_execution_time(prefill_batch, pipeline_stage=0)
        print(
            "  full prefill batch: "
            f"B={batch_size}, chunk={prefill_len}, "
            f"time={prefill_time.total_time * 1000:.3f} ms"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--prefill-len", type=int, default=256)
    parser.add_argument("--decode-len", type=int, default=20)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--attention-csv", type=Path, default=DEFAULT_ATTENTION)
    parser.add_argument(
        "--run-vidur-predictor",
        action="store_true",
        help="Also query Vidur's random-forest execution-time predictor.",
    )
    parser.add_argument(
        "--prediction-max-batch-size",
        type=int,
        default=None,
        help="Max batch size for Vidur predictor table generation.",
    )
    parser.add_argument(
        "--prediction-max-tokens-per-request",
        type=int,
        default=None,
        help=(
            "Max tokens/request for Vidur predictor table generation. "
            "Default rounds prefill+decode up to Vidur's 64-token decode bucket."
        ),
    )
    parser.add_argument(
        "--prediction-max-prefill-chunk-size",
        type=int,
        default=None,
        help="Max prefill chunk size for Vidur predictor table generation.",
    )
    parser.add_argument(
        "--include-prefill-predictor",
        action="store_true",
        help="Also query the predictor on a full-prefill B batch.",
    )
    args = parser.parse_args()

    print_profiling_coverage(args.attention_csv, args.batch_size)

    point = load_measurement(
        args.db, args.batch_size, args.prefill_len, args.decode_len
    )
    print("Recorded validation database comparison")
    print(f"  db: {args.db.relative_to(PROJECT_ROOT)}")
    print(f"  B={point.batch_size}, prefill={point.prefill_len}, decode={point.decode_len}")
    print(f"  kv_cache_size={point.kv_cache_size}")
    print(f"  recorded A100 measurement={point.real_ms:.6f} ms")
    print(f"  recorded prediction={point.predicted_ms:.6f} ms")
    print(f"  abs_error={point.abs_error_percent:.4f}%")
    print(f"  region={point.region}")
    print()

    d0, d1, pred, kv, train_n, train_max_b = refit_linear_validation_model(
        args.db, args.batch_size, args.prefill_len, args.decode_len
    )
    err = abs((point.real_ms - pred) / point.real_ms * 100)
    print("Recomputed linear validation fit")
    print(f"  training rows={train_n}, max training B={train_max_b}")
    print(f"  model: time_ms = {d0:.6f} + {d1:.9f} * kv_cache_tokens")
    print(f"  recomputed prediction at B={args.batch_size}: {pred:.6f} ms")
    print(f"  recomputed abs_error: {err:.4f}%")
    print()

    if args.run_vidur_predictor:
        run_vidur_predictor(
            args.batch_size,
            args.prefill_len,
            args.decode_len,
            prediction_max_batch_size=(
                args.prediction_max_batch_size or args.batch_size
            ),
            prediction_max_tokens_per_request=(
                args.prediction_max_tokens_per_request
                or int(ceil((args.prefill_len + args.decode_len) / 64) * 64)
            ),
            prediction_max_prefill_chunk_size=(
                args.prediction_max_prefill_chunk_size or args.prefill_len
            ),
            include_prefill=args.include_prefill_predictor,
        )


if __name__ == "__main__":
    main()
