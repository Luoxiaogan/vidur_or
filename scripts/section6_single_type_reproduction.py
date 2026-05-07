#!/usr/bin/env python3
"""Paper-facing Section 6 single-type p512d20 reproduction runner."""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "outputs" / "databases" / "section6_single_type_reproduction.db"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "single_type_reproduction"


@dataclass(frozen=True)
class RunSpec:
    run_tag: str
    arrival_rate: float
    policy: str
    config_name: str
    scheduler_type: str
    command: list[str]
    total_limit: int | None = None
    chunk_size: int | None = None
    batch_size_cap: int | None = None
    wait_cp_gate: str = "off"
    wait_gate: str = "off"
    seg_margin: float = 0.0


def comma_ints(text: str) -> list[int]:
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def comma_floats(text: str) -> list[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def slugify(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)


def prompt_types(rate: float, prefill: int, decode: int) -> list[dict]:
    return [{"type": "only", "prefill": prefill, "decode": decode, "arrival_rate": rate}]


def base_command(args: argparse.Namespace) -> list[str]:
    return [
        "python",
        "-m",
        "vidur.main",
        "--replica_config_device",
        args.device,
        "--replica_config_model_name",
        args.model_name,
        "--replica_config_memory_margin_fraction",
        str(args.memory_margin_fraction),
        "--cluster_config_num_replicas",
        "1",
        "--replica_config_tensor_parallel_size",
        "1",
        "--replica_config_num_pipeline_stages",
        "1",
        "--request_generator_config_type",
        "custom",
        "--no-metrics_config_store_plots",
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size",
        str(args.prediction_max_prefill_chunk_size),
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size",
        str(args.prediction_max_batch_size),
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request",
        str(args.prediction_max_tokens_per_request),
    ]


def build_specs(args: argparse.Namespace) -> list[RunSpec]:
    specs: list[RunSpec] = []
    common = base_command(args)
    rates = comma_floats(args.rates)
    tl_values = comma_ints(args.tl_values)
    chunk_sizes = comma_ints(args.wcp_chunk_sizes)
    max_tokens = args.prefill + args.decode

    for rate in rates:
        pts = json.dumps(prompt_types(rate, args.prefill, args.decode))
        request_args = [
            "--custom_request_generator_config_prompt_types",
            pts,
            "--custom_request_generator_config_max_tokens",
            str(max_tokens),
            "--custom_request_generator_config_num_requests",
            str(args.nreq),
        ]
        if args.seed is not None:
            request_args += ["--custom_request_generator_config_seed", str(args.seed)]
        if args.mode in {"all", "baselines"}:
            specs.append(
                RunSpec(
                    run_tag=args.run_tag,
                    arrival_rate=rate,
                    policy="Sarathi",
                    config_name="Sarathi512_cap256",
                    scheduler_type="sarathi",
                    command=common
                    + request_args
                    + [
                        "--replica_scheduler_config_type",
                        "sarathi",
                        "--sarathi_scheduler_config_chunk_size",
                        "512",
                        "--sarathi_scheduler_config_batch_size_cap",
                        str(args.sarathi_batch_size_cap),
                    ],
                    chunk_size=512,
                    batch_size_cap=args.sarathi_batch_size_cap,
                )
            )
            specs.append(
                RunSpec(
                    run_tag=args.run_tag,
                    arrival_rate=rate,
                    policy="vLLM",
                    config_name="vLLM",
                    scheduler_type="vllm",
                    command=common
                    + request_args
                    + [
                        "--replica_scheduler_config_type",
                        "vllm",
                    ],
                )
            )
        if args.mode in {"all", "wcp"}:
            for chunk_size in chunk_sizes:
                for tl in tl_values:
                    cmd = common + request_args + [
                        "--replica_scheduler_config_type",
                        "general_nested_chunked",
                        "--general_nested_chunked_scheduler_config_prompt_types",
                        pts,
                        "--general_nested_chunked_scheduler_config_total_limit",
                        str(tl),
                        "--general_nested_chunked_scheduler_config_total_num_requests",
                        str(args.nreq),
                        "--general_nested_chunked_scheduler_config_chunk_size",
                        str(chunk_size),
                        "--general_nested_chunked_scheduler_config_seg_margin",
                        str(args.seg_margin),
                        "--general_nested_chunked_scheduler_config_force_clear",
                        "--general_nested_chunked_scheduler_config_memory_cleanup",
                    ]
                    if not args.wait_gate:
                        cmd.append("--no-general_nested_chunked_scheduler_config_wait_gate")
                    specs.append(
                        RunSpec(
                            run_tag=args.run_tag,
                            arrival_rate=rate,
                            policy="WAIT",
                            config_name=f"WAIT_tl{tl}_cs{chunk_size}_wg{'ON' if args.wait_gate else 'OFF'}",
                            scheduler_type="general_nested_chunked",
                            command=cmd,
                            total_limit=tl,
                            chunk_size=chunk_size,
                            wait_cp_gate="on",
                            wait_gate="on" if args.wait_gate else "off",
                            seg_margin=args.seg_margin,
                        )
                    )
    return specs


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS single_type_runs (
          timestamp TEXT,
          run_tag TEXT,
          model_name TEXT,
          device TEXT,
          arrival_rate REAL,
          policy TEXT,
          config_name TEXT,
          scheduler_type TEXT,
          prefill INT,
          decode INT,
          nreq INT,
          total_limit INT,
          chunk_size INT,
          batch_size_cap INT,
          wait_cp_gate TEXT,
          wait_gate TEXT,
          seg_margin REAL,
          memory_margin_fraction REAL,
          prediction_max_prefill_chunk_size INT,
          prediction_max_batch_size INT,
          prediction_max_tokens_per_request INT,
          command_json TEXT,
          return_code INT,
          mean_latency REAL,
          p99_latency REAL,
          n_steady INT,
          n_completed INT,
          output_dir TEXT,
          stdout_path TEXT,
          stderr_path TEXT,
          metric_trim_head_frac REAL,
          metric_trim_tail_frac REAL,
          source_note TEXT
        );

        CREATE TABLE IF NOT EXISTS single_type_reproduction_configs (
          run_tag TEXT PRIMARY KEY,
          created_at TEXT,
          config_json TEXT,
          notes TEXT
        );

        CREATE TABLE IF NOT EXISTS single_type_selected_winners (
          selection_tag TEXT,
          selected_at TEXT,
          arrival_rate REAL,
          baseline_run_tag TEXT,
          baseline_mean_latency REAL,
          baseline_p99_latency REAL,
          wcp_run_tag TEXT,
          wcp_config_name TEXT,
          wcp_mean_latency REAL,
          wcp_p99_latency REAL,
          win_pct REAL,
          total_limit INT,
          chunk_size INT,
          wait_gate TEXT,
          command_json TEXT,
          PRIMARY KEY(selection_tag, arrival_rate)
        );
        """
    )
    conn.commit()


def already_done(conn: sqlite3.Connection, spec: RunSpec) -> bool:
    return (
        conn.execute(
            """
            SELECT 1 FROM single_type_runs
            WHERE run_tag=? AND arrival_rate=? AND config_name=? AND return_code=0
            LIMIT 1
            """,
            (spec.run_tag, spec.arrival_rate, spec.config_name),
        ).fetchone()
        is not None
    )


def collect_metrics(run_dir: Path, head_frac: float, tail_frac: float) -> tuple[float | None, float | None, int | None, int]:
    csvs = glob.glob(str(run_dir / "**" / "request_metrics_*.csv"), recursive=True)
    if not csvs:
        return None, None, None, 0
    df = pd.read_csv(csvs[0])
    completed = df[df.get("request_e2e_time").notna()] if "request_e2e_time" in df else df
    n_completed = int(len(completed))
    if completed.empty:
        return None, None, None, n_completed
    if "Request Id" in completed.columns:
        completed = completed.sort_values("Request Id")
    start = int(n_completed * head_frac)
    tail = int(n_completed * tail_frac)
    end = n_completed - tail if tail > 0 else n_completed
    if end <= start:
        return None, None, None, n_completed
    steady = completed.iloc[start:end]
    return (
        float(steady["request_e2e_time"].mean()),
        float(steady["request_e2e_time"].quantile(0.99)),
        int(len(steady)),
        n_completed,
    )


def run_one(conn: sqlite3.Connection, args: argparse.Namespace, spec: RunSpec) -> None:
    if not args.force and already_done(conn, spec):
        print(f"skip cached rate={spec.arrival_rate:g} {spec.config_name}", flush=True)
        return

    run_dir = args.output_root / spec.run_tag / f"rate_{spec.arrival_rate:g}" / slugify(spec.config_name)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    cmd = spec.command + ["--metrics_config_output_dir", str(run_dir)]
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = spec.wait_cp_gate
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        timeout=args.timeout,
        capture_output=True,
        text=True,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(result.stderr, encoding="utf-8", errors="replace")
    mean, p99, n_steady, n_completed = collect_metrics(run_dir, args.trim_head_frac, args.trim_tail_frac)
    conn.execute(
        """
        INSERT INTO single_type_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            datetime.now().isoformat(),
            spec.run_tag,
            args.model_name,
            args.device,
            spec.arrival_rate,
            spec.policy,
            spec.config_name,
            spec.scheduler_type,
            args.prefill,
            args.decode,
            args.nreq,
            spec.total_limit,
            spec.chunk_size,
            spec.batch_size_cap,
            spec.wait_cp_gate,
            spec.wait_gate,
            spec.seg_margin,
            args.memory_margin_fraction,
            args.prediction_max_prefill_chunk_size,
            args.prediction_max_batch_size,
            args.prediction_max_tokens_per_request,
            json.dumps(spec.command),
            result.returncode,
            mean,
            p99,
            n_steady,
            n_completed,
            str(run_dir),
            str(stdout_path),
            str(stderr_path),
            args.trim_head_frac,
            args.trim_tail_frac,
            "paper_facing_single_type_lamma2" if args.model_name.endswith("Llama-2-7b-hf") else "paper_facing_single_type",
        ),
    )
    conn.commit()
    status = "OK" if result.returncode == 0 and mean is not None else f"FAIL rc={result.returncode}"
    mean_text = f"{mean:.3f}s" if mean is not None else "-"
    print(f"{status:10s} rate={spec.arrival_rate:g} {spec.config_name} mean={mean_text}", flush=True)


def record_config(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    payload = {
        "run_tag": args.run_tag,
        "model_name": args.model_name,
        "device": args.device,
        "memory_margin_fraction": args.memory_margin_fraction,
        "prediction_max_prefill_chunk_size": args.prediction_max_prefill_chunk_size,
        "prediction_max_batch_size": args.prediction_max_batch_size,
        "prediction_max_tokens_per_request": args.prediction_max_tokens_per_request,
        "rates": args.rates,
        "prefill": args.prefill,
        "decode": args.decode,
        "nreq": args.nreq,
        "sarathi_chunk_size": 512,
        "sarathi_batch_size_cap": args.sarathi_batch_size_cap,
        "wcp_chunk_sizes": args.wcp_chunk_sizes,
        "tl_values": args.tl_values,
        "wait_cp_gate": "on",
        "wait_gate": "on" if args.wait_gate else "off",
        "seg_margin": args.seg_margin,
        "metric": f"middle {100 * (1 - args.trim_head_frac - args.trim_tail_frac):.0f}% request_e2e_time",
    }
    conn.execute(
        "INSERT OR REPLACE INTO single_type_reproduction_configs VALUES (?,?,?,?)",
        (
            args.run_tag,
            datetime.now().isoformat(),
            json.dumps(payload, sort_keys=True),
            "Paper-facing single-type reproduction under current manuscript model/baseline口径.",
        ),
    )
    conn.commit()


def select_winners(conn: sqlite3.Connection, selection_tag: str, baseline_run_tag: str) -> None:
    conn.execute("DELETE FROM single_type_selected_winners WHERE selection_tag=?", (selection_tag,))
    rates = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT arrival_rate FROM single_type_runs WHERE run_tag=? ORDER BY arrival_rate",
            (baseline_run_tag,),
        )
    ]
    now = datetime.now().isoformat()
    for rate in rates:
        base = conn.execute(
            """
            SELECT mean_latency, p99_latency FROM single_type_runs
            WHERE run_tag=? AND arrival_rate=? AND policy='Sarathi' AND return_code=0
            ORDER BY mean_latency LIMIT 1
            """,
            (baseline_run_tag, rate),
        ).fetchone()
        wcp = conn.execute(
            """
            SELECT run_tag, config_name, mean_latency, p99_latency, total_limit, chunk_size, wait_gate, command_json
            FROM single_type_runs
            WHERE run_tag=? AND arrival_rate=? AND policy='WAIT' AND wait_gate='on'
              AND return_code=0 AND mean_latency IS NOT NULL
              AND model_name='meta-llama/Llama-2-7b-hf'
            ORDER BY mean_latency LIMIT 1
            """,
            (baseline_run_tag, rate),
        ).fetchone()
        if not base or not wcp:
            continue
        win = (base[0] - wcp[2]) / base[0] * 100.0
        conn.execute(
            "INSERT OR REPLACE INTO single_type_selected_winners VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                selection_tag,
                now,
                rate,
                baseline_run_tag,
                base[0],
                base[1],
                wcp[0],
                wcp[1],
                wcp[2],
                wcp[3],
                win,
                wcp[4],
                wcp[5],
                wcp[6],
                wcp[7],
            ),
        )
    conn.commit()


def refresh_metrics_from_outputs(conn: sqlite3.Connection, run_tag: str, head_frac: float, tail_frac: float) -> None:
    rows = conn.execute(
        """
        SELECT run_tag, arrival_rate, config_name, output_dir
        FROM single_type_runs
        WHERE run_tag=?
        ORDER BY arrival_rate, config_name
        """,
        (run_tag,),
    ).fetchall()
    now = datetime.now().isoformat()
    refreshed = 0
    for row_run_tag, rate, config_name, output_dir in rows:
        mean, p99, n_steady, n_completed = collect_metrics(Path(output_dir), head_frac, tail_frac)
        conn.execute(
            """
            UPDATE single_type_runs
            SET timestamp=?, mean_latency=?, p99_latency=?, n_steady=?, n_completed=?,
                metric_trim_head_frac=?, metric_trim_tail_frac=?
            WHERE run_tag=? AND arrival_rate=? AND config_name=?
            """,
            (
                now,
                mean,
                p99,
                n_steady,
                n_completed,
                head_frac,
                tail_frac,
                row_run_tag,
                rate,
                config_name,
            ),
        )
        refreshed += 1
    conn.commit()
    print(f"refreshed {refreshed} rows for run_tag={run_tag} trim=({head_frac},{tail_frac})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", default=f"section6_single_type_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--mode", choices=["all", "baselines", "wcp"], default="all")
    parser.add_argument("--rates", default="12,13,14,15,16,17,18,19,20,21,22,23,24")
    parser.add_argument("--prefill", type=int, default=512)
    parser.add_argument("--decode", type=int, default=20)
    parser.add_argument("--nreq", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--model-name", default="meta-llama/Llama-2-7b-hf")
    parser.add_argument("--device", default="a100")
    parser.add_argument("--memory-margin-fraction", type=float, default=0.01)
    parser.add_argument("--prediction-max-prefill-chunk-size", type=int, default=16384)
    parser.add_argument("--prediction-max-batch-size", type=int, default=2048)
    parser.add_argument("--prediction-max-tokens-per-request", type=int, default=65536)
    parser.add_argument("--sarathi-batch-size-cap", type=int, default=256)
    parser.add_argument("--wcp-chunk-sizes", default="256")
    parser.add_argument("--tl-values", default="20,25,30,35,40,45,50")
    parser.add_argument("--seg-margin", type=float, default=0.0)
    parser.add_argument("--wait-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--trim-head-frac", type=float, default=0.0)
    parser.add_argument("--trim-tail-frac", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--select-winners", action="store_true")
    parser.add_argument("--refresh-metrics-from-outputs", action="store_true")
    parser.add_argument("--selection-tag", default="section6_single_type_l2_cap256_winners_20260507")
    parser.add_argument("--baseline-run-tag", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.output_root.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        ensure_schema(conn)
        if args.refresh_metrics_from_outputs:
            refresh_metrics_from_outputs(conn, args.run_tag, args.trim_head_frac, args.trim_tail_frac)
            return 0
        if args.select_winners:
            select_winners(conn, args.selection_tag, args.baseline_run_tag or args.run_tag)
            return 0
        record_config(conn, args)
        specs = build_specs(args)
        if args.limit is not None:
            specs = specs[: args.limit]
        print(f"run_tag={args.run_tag}")
        print(f"model_name={args.model_name}")
        print(f"mode={args.mode}")
        print(f"rates={args.rates}")
        print(f"tl_values={args.tl_values}")
        print(f"wcp_chunk_sizes={args.wcp_chunk_sizes}")
        print(f"sarathi_batch_size_cap={args.sarathi_batch_size_cap}")
        print(f"wait_gate={'on' if args.wait_gate else 'off'}")
        print(f"spec_count={len(specs)}")
        if args.print_plan:
            for spec in specs:
                print(f"{spec.arrival_rate:g} | {spec.policy} | {spec.config_name}")
            return 0
        for index, spec in enumerate(specs, start=1):
            print(f"[{index:03d}/{len(specs):03d}]", end=" ", flush=True)
            run_one(conn, args, spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
