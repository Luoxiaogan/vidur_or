"""Tune single-type WCP with and without the WAIT gate.

The comparison keeps the WCP admission limit, chunked-prefill budget, and
batch-token cap fixed within each configuration.  It only toggles the
segment-entry WAIT gate, so the resulting rows isolate full WAIT from the
threshold-only/no-wait variant.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT / "outputs" / "wait_vs_nowait_single_type_tune.db"

COMMON = [
    "python",
    "-m",
    "vidur.main",
    "--replica_config_device",
    "a100",
    "--replica_config_model_name",
    "meta-llama/Meta-Llama-3-8B",
    "--replica_config_memory_margin_fraction",
    "0.1",
    "--cluster_config_num_replicas",
    "1",
    "--replica_config_tensor_parallel_size",
    "1",
    "--replica_config_num_pipeline_stages",
    "1",
    "--request_generator_config_type",
    "custom",
    "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size",
    "1024",
    "--random_forrest_execution_time_predictor_config_prediction_max_batch_size",
    "128",
    "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request",
    "2048",
    "--random_forrest_execution_time_predictor_config_num_training_job_threads",
    "1",
    "--random_forrest_execution_time_predictor_config_num_estimators",
    "25",
    "--random_forrest_execution_time_predictor_config_max_depth",
    "8",
    "--random_forrest_execution_time_predictor_config_min_samples_split",
    "2",
    "--no-metrics_config_store_plots",
    "--log_level",
    "warning",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--nreq", type=int, default=1200)
    parser.add_argument("--prefill", type=int, default=512)
    parser.add_argument("--decode", type=int, default=20)
    parser.add_argument("--rates", type=float, nargs="+", default=[12, 18, 21, 22, 23, 24, 25])
    parser.add_argument("--total-limits", type=int, nargs="+", default=[20, 21, 22, 24])
    parser.add_argument("--chunk-sizes", type=int, nargs="+", default=[256, 384])
    parser.add_argument("--seg-margins", type=float, nargs="+", default=[0.0])
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--sim-time-limit", type=int, default=180)
    parser.add_argument("--rerun", action="store_true")
    return parser.parse_args()


def ensure_schema(cn: sqlite3.Connection) -> None:
    cn.execute(
        """CREATE TABLE IF NOT EXISTS runs (
            timestamp TEXT,
            arrival_rate REAL,
            prefill INT,
            decode INT,
            nreq INT,
            total_limit INT,
            chunk_size INT,
            seg_margin REAL,
            wait_gate INT,
            batch_gate TEXT,
            status TEXT,
            mean_latency REAL,
            p95_latency REAL,
            p99_latency REAL,
            scheduling_delay_mean REAL,
            execution_time_mean REAL,
            n_steady INT,
            stderr_tail TEXT
        )"""
    )
    cn.execute(
        """CREATE INDEX IF NOT EXISTS idx_runs_config
           ON runs(arrival_rate, prefill, decode, nreq, total_limit, chunk_size, seg_margin, wait_gate)"""
    )
    cn.commit()


def already_done(cn: sqlite3.Connection, args: argparse.Namespace, rate: float, tl: int, cs: int, sm: float, wg: bool) -> bool:
    row = cn.execute(
        """SELECT 1 FROM runs
           WHERE arrival_rate=? AND prefill=? AND decode=? AND nreq=?
             AND total_limit=? AND chunk_size=? AND seg_margin=? AND wait_gate=?
             AND status='ok'
           LIMIT 1""",
        (rate, args.prefill, args.decode, args.nreq, tl, cs, sm, 1 if wg else 0),
    ).fetchone()
    return row is not None


def prompt_types(args: argparse.Namespace, rate: float) -> list[dict]:
    return [
        {
            "type": "only",
            "prefill": args.prefill,
            "decode": args.decode,
            "arrival_rate": rate,
        }
    ]


def steady_slice(df: pd.DataFrame) -> pd.DataFrame:
    start = len(df) // 4
    end = max(start + 1, len(df) - 300)
    return df.iloc[start:end]


def run_one(args: argparse.Namespace, rate: float, tl: int, cs: int, sm: float, wait_gate: bool) -> tuple[str, dict]:
    tmpdir = tempfile.mkdtemp(prefix="vidur_wcp_wait_")
    pts = prompt_types(args, rate)
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on"

    cmd = COMMON + [
        "--custom_request_generator_config_prompt_types",
        json.dumps(pts),
        "--custom_request_generator_config_max_tokens",
        str(args.prefill + args.decode),
        "--custom_request_generator_config_num_requests",
        str(args.nreq),
        "--time_limit",
        str(args.sim_time_limit),
        "--metrics_config_output_dir",
        tmpdir,
        "--replica_scheduler_config_type",
        "general_nested_chunked",
        "--general_nested_chunked_scheduler_config_prompt_types",
        json.dumps(pts),
        "--general_nested_chunked_scheduler_config_total_limit",
        str(tl),
        "--general_nested_chunked_scheduler_config_total_num_requests",
        str(args.nreq),
        "--general_nested_chunked_scheduler_config_chunk_size",
        str(cs),
        "--general_nested_chunked_scheduler_config_seg_margin",
        str(sm),
        "--general_nested_chunked_scheduler_config_force_clear",
    ]
    if not wait_gate:
        cmd.append("--no-general_nested_chunked_scheduler_config_wait_gate")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=PROJECT,
            env=env,
            timeout=args.timeout,
        )
        if result.returncode != 0:
            return "failed", {"stderr_tail": None}
        csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
        if not csvs:
            return "missing_csv", {"stderr_tail": None}
        df = pd.read_csv(csvs[0])
        steady = steady_slice(df)
        return "ok", {
            "mean_latency": float(steady["request_e2e_time"].mean()),
            "p95_latency": float(steady["request_e2e_time"].quantile(0.95)),
            "p99_latency": float(steady["request_e2e_time"].quantile(0.99)),
            "scheduling_delay_mean": float(steady["request_scheduling_delay"].mean()),
            "execution_time_mean": float(steady["request_execution_time"].mean()),
            "n_steady": int(len(steady)),
            "stderr_tail": None,
        }
    except subprocess.TimeoutExpired as exc:
        return "timeout", {"stderr_tail": None}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def insert_run(
    cn: sqlite3.Connection,
    args: argparse.Namespace,
    rate: float,
    tl: int,
    cs: int,
    sm: float,
    wait_gate: bool,
    status: str,
    result: dict,
) -> None:
    cn.execute(
        """INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(),
            rate,
            args.prefill,
            args.decode,
            args.nreq,
            tl,
            cs,
            sm,
            1 if wait_gate else 0,
            "on",
            status,
            result.get("mean_latency"),
            result.get("p95_latency"),
            result.get("p99_latency"),
            result.get("scheduling_delay_mean"),
            result.get("execution_time_mean"),
            result.get("n_steady"),
            result.get("stderr_tail"),
        ),
    )
    cn.commit()


def print_best(cn: sqlite3.Connection, args: argparse.Namespace, rate: float) -> None:
    rows = cn.execute(
        """SELECT wait_gate, total_limit, chunk_size, seg_margin, mean_latency
           FROM runs
           WHERE arrival_rate=? AND prefill=? AND decode=? AND nreq=? AND status='ok'
           ORDER BY wait_gate, mean_latency ASC""",
        (rate, args.prefill, args.decode, args.nreq),
    ).fetchall()
    best = {}
    for wg, tl, cs, sm, mean in rows:
        best.setdefault(wg, (tl, cs, sm, mean))
    if 0 in best and 1 in best:
        off = best[0]
        on = best[1]
        delta = (on[3] - off[3]) / off[3] * 100
        print(
            f"BEST rate={rate:g}: off {off[3]:.3f}s TL={off[0]} CS={off[1]} "
            f"| on {on[3]:.3f}s TL={on[0]} CS={on[1]} | delta={delta:+.2f}%",
            flush=True,
        )


def main() -> None:
    args = parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    cn = sqlite3.connect(args.db)
    ensure_schema(cn)

    for rate in args.rates:
        print(f"\nRATE {rate:g}", flush=True)
        for tl in args.total_limits:
            for cs in args.chunk_sizes:
                for sm in args.seg_margins:
                    for wait_gate in (False, True):
                        if not args.rerun and already_done(cn, args, rate, tl, cs, sm, wait_gate):
                            continue
                        status, result = run_one(args, rate, tl, cs, sm, wait_gate)
                        insert_run(cn, args, rate, tl, cs, sm, wait_gate, status, result)
                        mean = result.get("mean_latency")
                        mean_text = f"{mean:.3f}s" if mean is not None else "-"
                        variant = "wait_on" if wait_gate else "wait_off"
                        print(
                            f"  {variant:8s} TL={tl:3d} CS={cs:3d} sm={sm:.2f} "
                            f"status={status:11s} mean={mean_text}",
                            flush=True,
                        )
        print_best(cn, args, rate)

    cn.close()
    print(f"\nWrote {args.db}", flush=True)


if __name__ == "__main__":
    main()
