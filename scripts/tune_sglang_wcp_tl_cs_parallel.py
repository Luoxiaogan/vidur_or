#!/usr/bin/env python3
"""Parallel TL/CS tuning: baseline once, then WCP configs on two GPUs."""

from __future__ import annotations

import argparse
import json
import queue
import sqlite3
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "outputs" / "sglang_wcp_sweeps.db"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "sglang_wcp_parallel_tuning"


@dataclass(frozen=True)
class WorkerSlot:
    name: str
    gpu_id: int
    port: int


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def init_tables() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sglang_parallel_tuning_trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tuning_batch TEXT NOT NULL,
            baseline_sweep_id INTEGER NOT NULL,
            wcp_sweep_id INTEGER NOT NULL,
            exp_name TEXT NOT NULL,
            gpu_id INTEGER NOT NULL,
            tl INTEGER NOT NULL,
            cs INTEGER NOT NULL,
            underload_threshold INTEGER,
            num_prompts INTEGER NOT NULL,
            rates_json TEXT NOT NULL,
            avg_improvement_pct REAL,
            win_count INTEGER NOT NULL,
            loss_count INTEGER NOT NULL,
            nonnegative_count INTEGER NOT NULL,
            best_improvement_pct REAL,
            worst_improvement_pct REAL,
            created_at TEXT NOT NULL,
            notes TEXT
        )
        """
    )
    existing = {row[1] for row in cur.execute("PRAGMA table_info(sglang_parallel_tuning_trials)")}
    if "underload_threshold" not in existing:
        cur.execute(
            "ALTER TABLE sglang_parallel_tuning_trials ADD COLUMN underload_threshold INTEGER"
        )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sglang_parallel_tuning_rate_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id INTEGER NOT NULL,
            rate REAL NOT NULL,
            baseline_mean_e2e_latency_ms REAL NOT NULL,
            wcp_mean_e2e_latency_ms REAL NOT NULL,
            baseline_request_throughput REAL,
            wcp_request_throughput REAL,
            improvement_pct_mean_e2e REAL NOT NULL,
            wcp_won_mean_e2e INTEGER NOT NULL,
            FOREIGN KEY (trial_id) REFERENCES sglang_parallel_tuning_trials(id)
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_sweep_id(exp_name: str) -> int:
    conn = connect()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id FROM sglang_sweeps WHERE exp_name = ? ORDER BY id DESC LIMIT 1",
        (exp_name,),
    ).fetchone()
    conn.close()
    if row is None:
        raise RuntimeError(f"sweep for exp_name={exp_name} not found")
    return int(row[0])


def fetch_runs_by_rate(sweep_id: int, scheduler: str) -> Dict[float, Dict]:
    conn = connect()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT rate, mean_e2e_latency_ms, request_throughput, status, completed
        FROM sglang_run_results
        WHERE sweep_id = ? AND scheduler = ?
        """,
        (sweep_id, scheduler),
    ).fetchall()
    conn.close()
    return {float(row[0]): dict(zip(["rate", "mean_e2e_latency_ms", "request_throughput", "status", "completed"], row)) for row in rows}


def validate_baseline_reference(
    sweep_id: int,
    rates: Sequence[float],
    num_prompts: int,
) -> None:
    baseline = fetch_runs_by_rate(sweep_id, "baseline")
    missing = [float(rate) for rate in rates if float(rate) not in baseline]
    if missing:
        raise RuntimeError(
            f"baseline sweep_id={sweep_id} missing rates: {missing}"
        )

    incomplete = []
    for rate in rates:
        row = baseline[float(rate)]
        if row["status"] != "ok" or int(row["completed"] or 0) != num_prompts:
            incomplete.append(
                (
                    float(rate),
                    row["status"],
                    int(row["completed"] or 0),
                )
            )
    if incomplete:
        raise RuntimeError(
            f"baseline sweep_id={sweep_id} has incomplete runs: {incomplete}"
        )


def insert_trial(
    tuning_batch: str,
    baseline_sweep_id: int,
    wcp_sweep_id: int,
    exp_name: str,
    gpu_id: int,
    tl: int,
    cs: int,
    underload_threshold: int | None,
    num_prompts: int,
    rates: Sequence[float],
    notes: str | None,
    per_rate_rows: List[Dict],
) -> None:
    improvements = [row["improvement_pct_mean_e2e"] for row in per_rate_rows]
    win_count = sum(1 for row in per_rate_rows if row["wcp_won_mean_e2e"])
    loss_count = len(per_rate_rows) - win_count
    nonnegative_count = sum(1 for value in improvements if value >= 0)

    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sglang_parallel_tuning_trials (
            tuning_batch, baseline_sweep_id, wcp_sweep_id, exp_name, gpu_id,
            tl, cs, underload_threshold, num_prompts, rates_json, avg_improvement_pct, win_count,
            loss_count, nonnegative_count, best_improvement_pct,
            worst_improvement_pct, created_at, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tuning_batch,
            baseline_sweep_id,
            wcp_sweep_id,
            exp_name,
            gpu_id,
            tl,
            cs,
            underload_threshold,
            num_prompts,
            json.dumps(list(rates)),
            sum(improvements) / len(improvements),
            win_count,
            loss_count,
            nonnegative_count,
            max(improvements),
            min(improvements),
            datetime.now(timezone.utc).isoformat(),
            notes,
        ),
    )
    trial_id = cur.lastrowid

    for row in per_rate_rows:
        cur.execute(
            """
            INSERT INTO sglang_parallel_tuning_rate_results (
                trial_id, rate, baseline_mean_e2e_latency_ms,
                wcp_mean_e2e_latency_ms, baseline_request_throughput,
                wcp_request_throughput, improvement_pct_mean_e2e,
                wcp_won_mean_e2e
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trial_id,
                row["rate"],
                row["baseline_mean_e2e_latency_ms"],
                row["wcp_mean_e2e_latency_ms"],
                row["baseline_request_throughput"],
                row["wcp_request_throughput"],
                row["improvement_pct_mean_e2e"],
                row["wcp_won_mean_e2e"],
            ),
        )

    conn.commit()
    conn.close()


def build_sweep_cmd(
    exp_name: str,
    schedulers: Sequence[str],
    rates: Sequence[float],
    num_prompts: int,
    tl: int,
    cs: int,
    baseline_gpu_id: int,
    wcp_gpu_id: int,
    baseline_port: int,
    wcp_port: int,
    baseline_chunked_prefill_size: int = 512,
    baseline_prefill_max_requests: int = 32,
    underload_threshold: int | None = None,
    notes: str | None = None,
) -> List[str]:
    cmd = [
        "python3",
        "-u",
        "scripts/sglang_wcp_rate_sweep_sql.py",
        "--exp-name",
        exp_name,
        "--num-prompts",
        str(num_prompts),
        "--baseline-gpu-id",
        str(baseline_gpu_id),
        "--wcp-gpu-id",
        str(wcp_gpu_id),
        "--baseline-port",
        str(baseline_port),
        "--wcp-port",
        str(wcp_port),
        "--baseline-chunked-prefill-size",
        str(baseline_chunked_prefill_size),
        "--baseline-prefill-max-requests",
        str(baseline_prefill_max_requests),
        "--wcp-total-limit",
        str(tl),
        "--wcp-chunk-size",
        str(cs),
        "--benchmark-timeout-s",
        "5400",
        "--schedulers",
        *list(schedulers),
        "--rates",
        *[str(rate) for rate in rates],
    ]
    if underload_threshold is not None:
        cmd.extend(["--wcp-underload-threshold", str(underload_threshold)])
    if notes:
        cmd.extend(["--notes", notes])
    return cmd


def run_subprocess(cmd: List[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log_file:
        log_file.write(("CMD: " + " ".join(cmd) + "\n").encode())
        result = subprocess.run(cmd, cwd=REPO_ROOT, stdout=log_file, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(cmd)}")


def compute_external_comparison(
    baseline_sweep_id: int,
    wcp_sweep_id: int,
    rates: Sequence[float],
    num_prompts: int,
) -> List[Dict]:
    baseline = fetch_runs_by_rate(baseline_sweep_id, "baseline")
    wcp = fetch_runs_by_rate(wcp_sweep_id, "wcp")
    rows = []
    for rate in rates:
        base = baseline[float(rate)]
        cur = wcp[float(rate)]
        if int(base["completed"] or 0) != num_prompts or int(cur["completed"] or 0) != num_prompts:
            raise RuntimeError(f"incomplete run at rate={rate}")
        base_mean = float(base["mean_e2e_latency_ms"])
        wcp_mean = float(cur["mean_e2e_latency_ms"])
        improvement = ((base_mean - wcp_mean) / base_mean) * 100.0
        rows.append(
            {
                "rate": float(rate),
                "baseline_mean_e2e_latency_ms": base_mean,
                "wcp_mean_e2e_latency_ms": wcp_mean,
                "baseline_request_throughput": float(base["request_throughput"]),
                "wcp_request_throughput": float(cur["request_throughput"]),
                "improvement_pct_mean_e2e": improvement,
                "wcp_won_mean_e2e": int(wcp_mean < base_mean),
            }
        )
    return rows


def run_baseline_reference(
    batch_name: str,
    rates: Sequence[float],
    num_prompts: int,
    gpu_id: int,
    port: int,
    baseline_chunked_prefill_size: int,
    baseline_prefill_max_requests: int,
    notes: str | None,
) -> int:
    exp_name = f"{batch_name}_baseline_ref"
    log_path = OUTPUT_ROOT / batch_name / f"{exp_name}.log"
    cmd = build_sweep_cmd(
        exp_name=exp_name,
        schedulers=["baseline"],
        rates=rates,
        num_prompts=num_prompts,
        tl=21,
        cs=256,
        baseline_gpu_id=gpu_id,
        wcp_gpu_id=1,
        baseline_port=port,
        wcp_port=port + 100,
        baseline_chunked_prefill_size=baseline_chunked_prefill_size,
        baseline_prefill_max_requests=baseline_prefill_max_requests,
        notes=notes or "baseline reference for parallel WCP tuning",
    )
    run_subprocess(cmd, log_path)
    return fetch_sweep_id(exp_name)


def worker_loop(
    slot: WorkerSlot,
    task_queue: "queue.Queue[Tuple[int, int, int | None] | None]",
    batch_name: str,
    baseline_sweep_id: int,
    rates: Sequence[float],
    num_prompts: int,
    baseline_chunked_prefill_size: int,
    baseline_prefill_max_requests: int,
    notes: str | None,
) -> None:
    while True:
        item = task_queue.get()
        if item is None:
            task_queue.task_done()
            return

        tl, cs, underload_threshold = item
        exp_name = f"{batch_name}_wcp_gpu{slot.gpu_id}_tl{tl}_cs{cs}"
        if underload_threshold is not None:
            exp_name += f"_ub{underload_threshold}"
        log_path = OUTPUT_ROOT / batch_name / f"{exp_name}.log"
        try:
            cmd = build_sweep_cmd(
                exp_name=exp_name,
                schedulers=["wcp"],
                rates=rates,
                num_prompts=num_prompts,
                tl=tl,
                cs=cs,
                underload_threshold=underload_threshold,
                baseline_gpu_id=slot.gpu_id,
                wcp_gpu_id=slot.gpu_id,
                baseline_port=slot.port - 100,
                wcp_port=slot.port,
                baseline_chunked_prefill_size=baseline_chunked_prefill_size,
                baseline_prefill_max_requests=baseline_prefill_max_requests,
                notes=notes or f"parallel WCP tuning tl={tl} cs={cs}",
            )
            run_subprocess(cmd, log_path)
            sweep_id = fetch_sweep_id(exp_name)
            per_rate_rows = compute_external_comparison(
                baseline_sweep_id=baseline_sweep_id,
                wcp_sweep_id=sweep_id,
                rates=rates,
                num_prompts=num_prompts,
            )
            insert_trial(
                tuning_batch=batch_name,
                baseline_sweep_id=baseline_sweep_id,
                wcp_sweep_id=sweep_id,
                exp_name=exp_name,
                gpu_id=slot.gpu_id,
                tl=tl,
                cs=cs,
                underload_threshold=underload_threshold,
                num_prompts=num_prompts,
                rates=rates,
                notes=notes,
                per_rate_rows=per_rate_rows,
            )
            avg_imp = sum(row["improvement_pct_mean_e2e"] for row in per_rate_rows) / len(per_rate_rows)
            wins = sum(row["wcp_won_mean_e2e"] for row in per_rate_rows)
            print(
                f"[gpu{slot.gpu_id}] sweep_id={sweep_id} tl={tl} cs={cs} "
                f"ub={underload_threshold} "
                f"avg={avg_imp:.3f} wins={wins}/{len(per_rate_rows)}"
            )
        finally:
            task_queue.task_done()


def print_ranking(batch_name: str) -> None:
    conn = connect()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT wcp_sweep_id, gpu_id, tl, cs, underload_threshold, avg_improvement_pct,
               win_count, loss_count, best_improvement_pct, worst_improvement_pct
        FROM sglang_parallel_tuning_trials
        WHERE tuning_batch = ?
        ORDER BY avg_improvement_pct DESC, win_count DESC
        """,
        (batch_name,),
    ).fetchall()
    conn.close()

    print("\n=== Parallel Tuning Ranking ===")
    for row in rows:
        print(
            f"sweep_id={row[0]} gpu={row[1]} tl={row[2]} cs={row[3]} "
            f"ub={row[4]} avg={row[5]:.3f} wins={row[6]} losses={row[7]} "
            f"best={row[8]:.3f} worst={row[9]:.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tuning-batch",
        default=f"parallel_tlcs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
    )
    parser.add_argument("--rates", type=float, nargs="+", default=[8, 9, 10, 11, 12, 13])
    parser.add_argument("--num-prompts", type=int, default=300)
    parser.add_argument("--tl-values", type=int, nargs="+", default=[21, 24, 28])
    parser.add_argument("--cs-values", type=int, nargs="+", default=[256, 384, 512])
    parser.add_argument(
        "--underload-threshold-values",
        type=int,
        nargs="+",
        default=None,
        help="Optional underload-bypass thresholds to sweep for WCP launches.",
    )
    parser.add_argument(
        "--baseline-sweep-id",
        type=int,
        default=None,
        help="Reuse an existing baseline-only sweep instead of rerunning it.",
    )
    parser.add_argument("--baseline-gpu-id", type=int, default=0)
    parser.add_argument("--baseline-port", type=int, default=30000)
    parser.add_argument("--baseline-chunked-prefill-size", type=int, default=512)
    parser.add_argument("--baseline-prefill-max-requests", type=int, default=32)
    parser.add_argument("--wcp-gpu-ids", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--wcp-ports", type=int, nargs="+", default=[31000, 31001])
    parser.add_argument("--notes")
    args = parser.parse_args()

    if len(args.wcp_gpu_ids) != len(args.wcp_ports):
        raise SystemExit("--wcp-gpu-ids and --wcp-ports must have the same length")

    init_tables()
    batch_dir = OUTPUT_ROOT / args.tuning_batch
    batch_dir.mkdir(parents=True, exist_ok=True)

    if args.baseline_sweep_id is not None:
        baseline_sweep_id = args.baseline_sweep_id
        print(f"=== Reusing baseline reference sweep_id={baseline_sweep_id} ===")
        validate_baseline_reference(
            sweep_id=baseline_sweep_id,
            rates=args.rates,
            num_prompts=args.num_prompts,
        )
    else:
        print("=== Running baseline reference once ===")
        baseline_sweep_id = run_baseline_reference(
            batch_name=args.tuning_batch,
            rates=args.rates,
            num_prompts=args.num_prompts,
            gpu_id=args.baseline_gpu_id,
            port=args.baseline_port,
            baseline_chunked_prefill_size=args.baseline_chunked_prefill_size,
            baseline_prefill_max_requests=args.baseline_prefill_max_requests,
            notes=args.notes,
        )
        validate_baseline_reference(
            sweep_id=baseline_sweep_id,
            rates=args.rates,
            num_prompts=args.num_prompts,
        )
        print(f"Baseline sweep_id={baseline_sweep_id}")

    task_queue: "queue.Queue[Tuple[int, int, int | None] | None]" = queue.Queue()
    slots = [
        WorkerSlot(name=f"gpu{gpu_id}", gpu_id=gpu_id, port=port)
        for gpu_id, port in zip(args.wcp_gpu_ids, args.wcp_ports)
    ]

    threads = [
        threading.Thread(
            target=worker_loop,
            args=(
                slot,
                task_queue,
                args.tuning_batch,
                baseline_sweep_id,
                args.rates,
                args.num_prompts,
                args.baseline_chunked_prefill_size,
                args.baseline_prefill_max_requests,
                args.notes,
            ),
            daemon=True,
        )
        for slot in slots
    ]

    for thread in threads:
        thread.start()

    underload_thresholds = args.underload_threshold_values or [None]
    for tl in args.tl_values:
        for cs in args.cs_values:
            for underload_threshold in underload_thresholds:
                task_queue.put((tl, cs, underload_threshold))

    for _ in threads:
        task_queue.put(None)

    task_queue.join()
    for thread in threads:
        thread.join()

    print_ranking(args.tuning_batch)
    print(f"SQLite DB: {DB_PATH}")
    print(f"Tuning batch: {args.tuning_batch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
