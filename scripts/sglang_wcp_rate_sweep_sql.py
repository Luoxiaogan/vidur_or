#!/usr/bin/env python3
"""
Rate sweep for baseline SGLang vs WCP-patched SGLang with SQLite recording.

This runner is designed for the current A100 environment where the default
flashinfer path cannot be used because `/usr/local/cuda/bin/nvcc` is missing.
It therefore launches both baseline and WCP with the same non-JIT backend
stack so the comparison stays fair:

- `--attention-backend torch_native`
- `--sampling-backend pytorch`
- `--disable-cuda-graph`

All benchmark summaries, launch commands, and per-rate comparisons are written
to SQLite for later querying and reproduction.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shlex
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "outputs" / "sglang_wcp_sweeps.db"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "sglang_wcp_sweeps"
DEFAULT_MINIFORGE_ACTIVATE = "/data/miniforge3/bin/activate"
DEFAULT_SGLANG_ROOT = "/persistent/miniforge3/lib/python3.11/site-packages"
DEFAULT_MODEL = "models/modelscope/Llama-2-7b-ms"


@dataclass(frozen=True)
class LaunchSpec:
    scheduler: str
    host: str
    port: int
    gpu_id: int
    command: str
    wcp_total_limit: Optional[int]
    wcp_chunk_size: Optional[int]


@dataclass(frozen=True)
class SweepConfig:
    exp_name: str
    db_path: Path
    output_root: Path
    model_path: str
    sglang_root: str
    rates: List[float]
    host: str
    baseline_port: int
    wcp_port: int
    baseline_gpu_id: int
    wcp_gpu_id: int
    baseline_chunked_prefill_size: int
    baseline_prefill_max_requests: int
    num_prompts: int
    random_input_len: int
    random_output_len: int
    mem_fraction_static: float
    attention_backend: str
    sampling_backend: str
    disable_cuda_graph: bool
    disable_radix_cache: bool
    tensor_parallel_size: int
    warmup_requests: int
    request_timeout_s: int
    server_start_timeout_s: int
    benchmark_timeout_s: int
    wcp_total_limit: int
    wcp_chunk_size: int
    wcp_prompt_type: str
    wcp_enable_underload_bypass: bool
    wcp_underload_threshold: Optional[int]
    schedulers: List[str]
    notes: Optional[str]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _shell_join(parts: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _sqlite_connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path, timeout=60)


def _base_server_args(cfg: SweepConfig, port: int, gpu_id: int) -> List[str]:
    args = [
        "--model-path",
        cfg.model_path,
        "--host",
        cfg.host,
        "--port",
        str(port),
        "--tensor-parallel-size",
        str(cfg.tensor_parallel_size),
        "--base-gpu-id",
        str(gpu_id),
        "--mem-fraction-static",
        str(cfg.mem_fraction_static),
        "--attention-backend",
        cfg.attention_backend,
        "--sampling-backend",
        cfg.sampling_backend,
    ]
    if cfg.disable_cuda_graph:
        args.append("--disable-cuda-graph")
    if cfg.disable_radix_cache:
        args.append("--disable-radix-cache")
    return args


def build_launch_spec(cfg: SweepConfig, scheduler: str) -> LaunchSpec:
    if scheduler == "baseline":
        port = cfg.baseline_port
        gpu_id = cfg.baseline_gpu_id
        server_args = [
            "python",
            "-u",
            "-m",
            "sglang.launch_server",
            *_base_server_args(cfg, port, gpu_id),
            "--chunked-prefill-size",
            str(cfg.baseline_chunked_prefill_size),
            "--prefill-max-requests",
            str(cfg.baseline_prefill_max_requests),
        ]
        cmd = (
            f"source {shlex.quote(DEFAULT_MINIFORGE_ACTIVATE)} base && "
            f"{_shell_join(server_args)}"
        )
        return LaunchSpec(
            scheduler="baseline",
            host=cfg.host,
            port=port,
            gpu_id=gpu_id,
            command=cmd,
            wcp_total_limit=None,
            wcp_chunk_size=None,
        )

    if scheduler == "wcp":
        port = cfg.wcp_port
        gpu_id = cfg.wcp_gpu_id
        server_args = _base_server_args(cfg, port, gpu_id)
        wrapper_args = [
            "python",
            "-u",
            "scripts/launch_sglang_wcp.py",
            "--sglang-root",
            cfg.sglang_root,
            "--wcp-total-limit",
            str(cfg.wcp_total_limit),
            "--wcp-chunk-size",
            str(cfg.wcp_chunk_size),
            "--wcp-prompt-type",
            cfg.wcp_prompt_type,
        ]
        if not cfg.wcp_enable_underload_bypass:
            wrapper_args.append("--disable-wcp-underload-bypass")
        if cfg.wcp_underload_threshold is not None:
            wrapper_args.extend(
                ["--wcp-underload-threshold", str(cfg.wcp_underload_threshold)]
            )
        wrapper_args.extend(["--", *server_args])
        cmd = (
            f"source {shlex.quote(DEFAULT_MINIFORGE_ACTIVATE)} base && "
            f"{_shell_join(wrapper_args)}"
        )
        return LaunchSpec(
            scheduler="wcp",
            host=cfg.host,
            port=port,
            gpu_id=gpu_id,
            command=cmd,
            wcp_total_limit=cfg.wcp_total_limit,
            wcp_chunk_size=cfg.wcp_chunk_size,
        )

    raise ValueError(f"unknown scheduler: {scheduler}")


def build_bench_command(cfg: SweepConfig, port: int, rate: float, output_path: Path) -> str:
    args = [
        "python",
        "-u",
        "-m",
        "sglang.bench_serving",
        "--backend",
        "sglang",
        "--host",
        cfg.host,
        "--port",
        str(port),
        "--dataset-name",
        "random",
        "--num-prompts",
        str(cfg.num_prompts),
        "--random-input-len",
        str(cfg.random_input_len),
        "--random-output-len",
        str(cfg.random_output_len),
        "--request-rate",
        str(rate),
        "--disable-stream",
        "--disable-tqdm",
        "--tokenize-prompt",
        "--warmup-requests",
        str(cfg.warmup_requests),
        "--output-file",
        str(output_path),
    ]
    return (
        f"source {shlex.quote(DEFAULT_MINIFORGE_ACTIVATE)} base && "
        f"{_shell_join(args)}"
    )


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _sqlite_connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sglang_sweeps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exp_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            model_path TEXT NOT NULL,
            sglang_root TEXT NOT NULL,
            host TEXT NOT NULL,
            baseline_port INTEGER NOT NULL,
            wcp_port INTEGER NOT NULL,
            baseline_chunked_prefill_size INTEGER NOT NULL DEFAULT 512,
            baseline_prefill_max_requests INTEGER NOT NULL DEFAULT 32,
            num_prompts INTEGER NOT NULL,
            random_input_len INTEGER NOT NULL,
            random_output_len INTEGER NOT NULL,
            rates_json TEXT NOT NULL,
            mem_fraction_static REAL NOT NULL,
            attention_backend TEXT NOT NULL,
            sampling_backend TEXT NOT NULL,
            disable_cuda_graph INTEGER NOT NULL,
            disable_radix_cache INTEGER NOT NULL,
            tensor_parallel_size INTEGER NOT NULL,
            warmup_requests INTEGER NOT NULL,
            wcp_total_limit INTEGER NOT NULL,
            wcp_chunk_size INTEGER NOT NULL,
            wcp_prompt_type TEXT NOT NULL,
            wcp_enable_underload_bypass INTEGER NOT NULL DEFAULT 1,
            wcp_underload_threshold INTEGER,
            output_dir TEXT NOT NULL,
            notes TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sglang_run_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sweep_id INTEGER NOT NULL,
            scheduler TEXT NOT NULL,
            rate REAL NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            launch_cmd TEXT NOT NULL,
            bench_cmd TEXT NOT NULL,
            launch_log_path TEXT NOT NULL,
            bench_log_path TEXT NOT NULL,
            benchmark_output_path TEXT NOT NULL,
            completed INTEGER,
            duration_s REAL,
            request_throughput REAL,
            input_throughput REAL,
            output_throughput REAL,
            total_throughput REAL,
            mean_e2e_latency_ms REAL,
            median_e2e_latency_ms REAL,
            p99_e2e_latency_ms REAL,
            mean_ttft_ms REAL,
            p99_ttft_ms REAL,
            concurrency REAL,
            max_concurrent_requests INTEGER,
            chunked_prefill_size INTEGER,
            prefill_max_requests INTEGER,
            wcp_total_limit INTEGER,
            wcp_chunk_size INTEGER,
            server_info_json TEXT,
            summary_json TEXT,
            error_text TEXT,
            FOREIGN KEY (sweep_id) REFERENCES sglang_sweeps(id)
        )
        """
    )

    existing = {row[1] for row in cur.execute("PRAGMA table_info(sglang_sweeps)")}
    if "wcp_enable_underload_bypass" not in existing:
        try:
            cur.execute(
                "ALTER TABLE sglang_sweeps ADD COLUMN wcp_enable_underload_bypass INTEGER NOT NULL DEFAULT 1"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    if "baseline_chunked_prefill_size" not in existing:
        try:
            cur.execute(
                "ALTER TABLE sglang_sweeps ADD COLUMN baseline_chunked_prefill_size INTEGER NOT NULL DEFAULT 512"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    if "baseline_prefill_max_requests" not in existing:
        try:
            cur.execute(
                "ALTER TABLE sglang_sweeps ADD COLUMN baseline_prefill_max_requests INTEGER NOT NULL DEFAULT 32"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    if "wcp_underload_threshold" not in existing:
        try:
            cur.execute(
                "ALTER TABLE sglang_sweeps ADD COLUMN wcp_underload_threshold INTEGER"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sglang_rate_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sweep_id INTEGER NOT NULL,
            rate REAL NOT NULL,
            baseline_run_id INTEGER,
            wcp_run_id INTEGER,
            baseline_stable INTEGER NOT NULL,
            wcp_stable INTEGER NOT NULL,
            both_stable INTEGER NOT NULL,
            wcp_won_mean_e2e INTEGER NOT NULL,
            baseline_mean_e2e_latency_ms REAL,
            wcp_mean_e2e_latency_ms REAL,
            improvement_pct_mean_e2e REAL,
            baseline_request_throughput REAL,
            wcp_request_throughput REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sweep_id) REFERENCES sglang_sweeps(id),
            FOREIGN KEY (baseline_run_id) REFERENCES sglang_run_results(id),
            FOREIGN KEY (wcp_run_id) REFERENCES sglang_run_results(id)
        )
        """
    )

    conn.commit()
    conn.close()


def insert_sweep(cfg: SweepConfig, output_dir: Path) -> int:
    conn = _sqlite_connect(cfg.db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sglang_sweeps (
            exp_name, created_at, model_path, sglang_root, host,
            baseline_port, wcp_port, baseline_chunked_prefill_size,
            baseline_prefill_max_requests, num_prompts, random_input_len,
            random_output_len, rates_json, mem_fraction_static,
            attention_backend, sampling_backend, disable_cuda_graph,
            disable_radix_cache, tensor_parallel_size, warmup_requests,
            wcp_total_limit, wcp_chunk_size, wcp_prompt_type,
            wcp_enable_underload_bypass, wcp_underload_threshold,
            output_dir, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cfg.exp_name,
            datetime.now(timezone.utc).isoformat(),
            cfg.model_path,
            cfg.sglang_root,
            cfg.host,
            cfg.baseline_port,
            cfg.wcp_port,
            cfg.baseline_chunked_prefill_size,
            cfg.baseline_prefill_max_requests,
            cfg.num_prompts,
            cfg.random_input_len,
            cfg.random_output_len,
            json.dumps(cfg.rates),
            cfg.mem_fraction_static,
            cfg.attention_backend,
            cfg.sampling_backend,
            int(cfg.disable_cuda_graph),
            int(cfg.disable_radix_cache),
            cfg.tensor_parallel_size,
            cfg.warmup_requests,
            cfg.wcp_total_limit,
            cfg.wcp_chunk_size,
            cfg.wcp_prompt_type,
            int(cfg.wcp_enable_underload_bypass),
            cfg.wcp_underload_threshold,
            str(output_dir),
            cfg.notes,
        ),
    )
    sweep_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(sweep_id)


def insert_run_result(db_path: Path, payload: Dict[str, object]) -> int:
    conn = _sqlite_connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sglang_run_results (
            sweep_id, scheduler, rate, status, started_at, finished_at,
            launch_cmd, bench_cmd, launch_log_path, bench_log_path,
            benchmark_output_path, completed, duration_s, request_throughput,
            input_throughput, output_throughput, total_throughput,
            mean_e2e_latency_ms, median_e2e_latency_ms, p99_e2e_latency_ms,
            mean_ttft_ms, p99_ttft_ms, concurrency, max_concurrent_requests,
            chunked_prefill_size, prefill_max_requests, wcp_total_limit,
            wcp_chunk_size, server_info_json, summary_json, error_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["sweep_id"],
            payload["scheduler"],
            payload["rate"],
            payload["status"],
            payload["started_at"],
            payload["finished_at"],
            payload["launch_cmd"],
            payload["bench_cmd"],
            payload["launch_log_path"],
            payload["bench_log_path"],
            payload["benchmark_output_path"],
            payload.get("completed"),
            payload.get("duration_s"),
            payload.get("request_throughput"),
            payload.get("input_throughput"),
            payload.get("output_throughput"),
            payload.get("total_throughput"),
            payload.get("mean_e2e_latency_ms"),
            payload.get("median_e2e_latency_ms"),
            payload.get("p99_e2e_latency_ms"),
            payload.get("mean_ttft_ms"),
            payload.get("p99_ttft_ms"),
            payload.get("concurrency"),
            payload.get("max_concurrent_requests"),
            payload.get("chunked_prefill_size"),
            payload.get("prefill_max_requests"),
            payload.get("wcp_total_limit"),
            payload.get("wcp_chunk_size"),
            payload.get("server_info_json"),
            payload.get("summary_json"),
            payload.get("error_text"),
        ),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(run_id)


def insert_comparison(db_path: Path, payload: Dict[str, object]) -> None:
    conn = _sqlite_connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sglang_rate_comparisons (
            sweep_id, rate, baseline_run_id, wcp_run_id, baseline_stable,
            wcp_stable, both_stable, wcp_won_mean_e2e,
            baseline_mean_e2e_latency_ms, wcp_mean_e2e_latency_ms,
            improvement_pct_mean_e2e, baseline_request_throughput,
            wcp_request_throughput, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["sweep_id"],
            payload["rate"],
            payload.get("baseline_run_id"),
            payload.get("wcp_run_id"),
            payload["baseline_stable"],
            payload["wcp_stable"],
            payload["both_stable"],
            payload["wcp_won_mean_e2e"],
            payload.get("baseline_mean_e2e_latency_ms"),
            payload.get("wcp_mean_e2e_latency_ms"),
            payload.get("improvement_pct_mean_e2e"),
            payload.get("baseline_request_throughput"),
            payload.get("wcp_request_throughput"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def parse_summary_file(path: Path) -> Dict[str, object]:
    with path.open() as f:
        line = f.readline().strip()
    if not line:
        raise RuntimeError(f"empty benchmark output: {path}")
    return json.loads(line)


def wait_for_server(host: str, port: int, timeout_s: int) -> bool:
    url = f"http://{host}:{port}/v1/models"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(1)
    return False


def stop_process_tree(proc: subprocess.Popen[bytes], grace_s: int = 10) -> None:
    if proc.poll() is not None:
        return

    try:
        os.killpg(proc.pid, signal.SIGINT)
    except ProcessLookupError:
        return

    deadline = time.time() + grace_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.5)

    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.time() + grace_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.5)

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def launch_server(spec: LaunchSpec, log_path: Path) -> subprocess.Popen[bytes]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as f:
        header = f"\n[{datetime.now(timezone.utc).isoformat()}] CMD: {spec.command}\n".encode()
        f.write(header)
    log_file = log_path.open("ab")
    return subprocess.Popen(
        ["bash", "-lc", spec.command],
        cwd=REPO_ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def run_benchmark_command(command: str, log_path: Path, timeout_s: int) -> Tuple[int, Optional[str]]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as f:
        header = f"\n[{datetime.now(timezone.utc).isoformat()}] CMD: {command}\n".encode()
        f.write(header)
    with log_path.open("ab") as log_file:
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=REPO_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            timeout=timeout_s,
        )
    return proc.returncode, None


def benchmark_one_rate(
    cfg: SweepConfig,
    sweep_id: int,
    spec: LaunchSpec,
    scheduler_output_dir: Path,
    rate: float,
    launch_log_path: Path,
) -> int:
    rate_slug = str(rate).replace(".", "p")
    bench_jsonl = scheduler_output_dir / f"{spec.scheduler}_rate_{rate_slug}.jsonl"
    bench_log = scheduler_output_dir / f"{spec.scheduler}_rate_{rate_slug}.log"
    bench_cmd = build_bench_command(cfg, spec.port, rate, bench_jsonl)
    started_at = datetime.now(timezone.utc).isoformat()

    status = "ok"
    error_text = None
    summary = None
    returncode = None

    try:
        returncode, _ = run_benchmark_command(bench_cmd, bench_log, cfg.benchmark_timeout_s)
        if returncode != 0:
            status = "benchmark_failed"
            error_text = f"benchmark exited with code {returncode}"
        elif not bench_jsonl.exists():
            status = "missing_output"
            error_text = f"benchmark output not found: {bench_jsonl}"
        else:
            summary = parse_summary_file(bench_jsonl)
    except subprocess.TimeoutExpired:
        status = "benchmark_timeout"
        error_text = f"benchmark timed out after {cfg.benchmark_timeout_s}s"
    except Exception as exc:  # pragma: no cover - debugging path
        status = "benchmark_exception"
        error_text = repr(exc)

    finished_at = datetime.now(timezone.utc).isoformat()

    payload: Dict[str, object] = {
        "sweep_id": sweep_id,
        "scheduler": spec.scheduler,
        "rate": rate,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "launch_cmd": spec.command,
        "bench_cmd": bench_cmd,
        "launch_log_path": str(launch_log_path),
        "bench_log_path": str(bench_log),
        "benchmark_output_path": str(bench_jsonl),
        "wcp_total_limit": spec.wcp_total_limit,
        "wcp_chunk_size": spec.wcp_chunk_size,
        "error_text": error_text,
    }

    if summary is not None:
        server_info = summary.get("server_info", {})
        payload.update(
            {
                "completed": summary.get("completed"),
                "duration_s": summary.get("duration"),
                "request_throughput": summary.get("request_throughput"),
                "input_throughput": summary.get("input_throughput"),
                "output_throughput": summary.get("output_throughput"),
                "total_throughput": summary.get("total_throughput"),
                "mean_e2e_latency_ms": summary.get("mean_e2e_latency_ms"),
                "median_e2e_latency_ms": summary.get("median_e2e_latency_ms"),
                "p99_e2e_latency_ms": summary.get("p99_e2e_latency_ms"),
                "mean_ttft_ms": summary.get("mean_ttft_ms"),
                "p99_ttft_ms": summary.get("p99_ttft_ms"),
                "concurrency": summary.get("concurrency"),
                "max_concurrent_requests": summary.get("max_concurrent_requests"),
                "chunked_prefill_size": server_info.get("chunked_prefill_size"),
                "prefill_max_requests": server_info.get("prefill_max_requests"),
                "server_info_json": json.dumps(server_info, sort_keys=True),
                "summary_json": json.dumps(summary, sort_keys=True),
            }
        )

    run_id = insert_run_result(cfg.db_path, payload)
    print(
        f"[{spec.scheduler}] rate={rate:g} status={status} "
        f"mean_e2e={payload.get('mean_e2e_latency_ms')}"
    )
    return run_id


def is_stable(run_row: Dict[str, object], num_prompts: int) -> bool:
    return run_row["status"] == "ok" and int(run_row.get("completed") or 0) == num_prompts


def fetch_runs(db_path: Path, sweep_id: int) -> List[Dict[str, object]]:
    conn = _sqlite_connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM sglang_run_results
        WHERE sweep_id = ?
        ORDER BY scheduler, rate
        """,
        (sweep_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def build_comparisons(cfg: SweepConfig, sweep_id: int) -> List[Dict[str, object]]:
    if "baseline" not in cfg.schedulers or "wcp" not in cfg.schedulers:
        return []

    runs = fetch_runs(cfg.db_path, sweep_id)
    baseline_by_rate = {row["rate"]: row for row in runs if row["scheduler"] == "baseline"}
    wcp_by_rate = {row["rate"]: row for row in runs if row["scheduler"] == "wcp"}

    comparisons: List[Dict[str, object]] = []
    for rate in cfg.rates:
        baseline = baseline_by_rate.get(rate)
        wcp = wcp_by_rate.get(rate)
        baseline_stable = bool(baseline and is_stable(baseline, cfg.num_prompts))
        wcp_stable = bool(wcp and is_stable(wcp, cfg.num_prompts))
        both_stable = baseline_stable and wcp_stable

        improvement_pct = None
        wcp_won = False
        if both_stable:
            base_mean = float(baseline["mean_e2e_latency_ms"])
            wcp_mean = float(wcp["mean_e2e_latency_ms"])
            improvement_pct = ((base_mean - wcp_mean) / base_mean) * 100.0
            wcp_won = wcp_mean < base_mean

        payload = {
            "sweep_id": sweep_id,
            "rate": rate,
            "baseline_run_id": baseline["id"] if baseline else None,
            "wcp_run_id": wcp["id"] if wcp else None,
            "baseline_stable": int(baseline_stable),
            "wcp_stable": int(wcp_stable),
            "both_stable": int(both_stable),
            "wcp_won_mean_e2e": int(wcp_won),
            "baseline_mean_e2e_latency_ms": baseline.get("mean_e2e_latency_ms") if baseline else None,
            "wcp_mean_e2e_latency_ms": wcp.get("mean_e2e_latency_ms") if wcp else None,
            "improvement_pct_mean_e2e": improvement_pct,
            "baseline_request_throughput": baseline.get("request_throughput") if baseline else None,
            "wcp_request_throughput": wcp.get("request_throughput") if wcp else None,
        }
        insert_comparison(cfg.db_path, payload)
        comparisons.append(payload)

    return comparisons


def summarize_region(comparisons: Iterable[Dict[str, object]]) -> Dict[str, object]:
    stable_rates = []
    win_rates = []
    loss_rates = []
    unstable_rates = []

    for row in comparisons:
        rate = row["rate"]
        if row["both_stable"]:
            stable_rates.append(rate)
            if row["wcp_won_mean_e2e"]:
                win_rates.append(rate)
            else:
                loss_rates.append(rate)
        else:
            unstable_rates.append(rate)

    return {
        "stable_rates": stable_rates,
        "wcp_win_rates": win_rates,
        "wcp_loss_or_tie_rates": loss_rates,
        "unstable_rates": unstable_rates,
    }


def _launch_pair(
    cfg: SweepConfig,
    output_dir: Path,
) -> Tuple[Dict[str, LaunchSpec], Dict[str, Path], Dict[str, subprocess.Popen[bytes]]]:
    specs = {
        name: build_launch_spec(cfg, name)
        for name in cfg.schedulers
    }
    dirs = {
        name: output_dir / name
        for name in specs
    }
    logs = {
        name: dirs[name] / f"{name}_server.log"
        for name in specs
    }
    procs: Dict[str, subprocess.Popen[bytes]] = {}
    for name, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
    for name, spec in specs.items():
        procs[name] = launch_server(spec, logs[name])
    return specs, logs, procs


def _run_scheduler_benchmark_loop(
    cfg: SweepConfig,
    sweep_id: int,
    spec: LaunchSpec,
    output_dir: Path,
    launch_log_path: Path,
) -> None:
    for rate in cfg.rates:
        benchmark_one_rate(cfg, sweep_id, spec, output_dir, rate, launch_log_path)


def run_scheduler_pair_rates(
    cfg: SweepConfig,
    sweep_id: int,
    output_dir: Path,
) -> None:
    specs, launch_logs, procs = _launch_pair(cfg, output_dir)
    try:
        for name, spec in specs.items():
            if not wait_for_server(spec.host, spec.port, cfg.server_start_timeout_s):
                raise RuntimeError(
                    f"{name} server on gpu {spec.gpu_id} did not become ready within "
                    f"{cfg.server_start_timeout_s}s"
                )
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    _run_scheduler_benchmark_loop,
                    cfg,
                    sweep_id,
                    specs[name],
                    output_dir / name,
                    launch_logs[name],
                )
                for name in cfg.schedulers
            ]
            for future in futures:
                future.result()
    finally:
        for proc in procs.values():
            stop_process_tree(proc)


def parse_args(argv: Optional[Sequence[str]] = None) -> SweepConfig:
    parser = argparse.ArgumentParser(
        description="Sweep baseline and WCP SGLang over multiple request rates and record results in SQLite."
    )
    parser.add_argument("--exp-name", default=f"sglang_wcp_sweep_{_ts()}")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--sglang-root", default=DEFAULT_SGLANG_ROOT)
    parser.add_argument("--rates", type=float, nargs="+", default=[1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--baseline-port", type=int, default=30000)
    parser.add_argument("--wcp-port", type=int, default=30001)
    parser.add_argument("--baseline-gpu-id", type=int, default=0)
    parser.add_argument("--wcp-gpu-id", type=int, default=1)
    parser.add_argument("--baseline-chunked-prefill-size", type=int, default=512)
    parser.add_argument("--baseline-prefill-max-requests", type=int, default=32)
    parser.add_argument("--num-prompts", type=int, default=50)
    parser.add_argument("--random-input-len", type=int, default=512)
    parser.add_argument("--random-output-len", type=int, default=20)
    parser.add_argument("--mem-fraction-static", type=float, default=0.65)
    parser.add_argument("--attention-backend", default="torch_native")
    parser.add_argument("--sampling-backend", default="pytorch")
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--disable-cuda-graph", action="store_true", default=True)
    parser.add_argument("--disable-radix-cache", action="store_true", default=True)
    parser.add_argument("--warmup-requests", type=int, default=1)
    parser.add_argument("--server-start-timeout-s", type=int, default=180)
    parser.add_argument("--benchmark-timeout-s", type=int, default=1800)
    parser.add_argument("--request-timeout-s", type=int, default=60)
    parser.add_argument("--wcp-total-limit", type=int, default=21)
    parser.add_argument("--wcp-chunk-size", type=int, default=256)
    parser.add_argument("--wcp-prompt-type", default="p512d20:512:20:1.0")
    parser.add_argument("--disable-wcp-underload-bypass", action="store_true")
    parser.add_argument("--wcp-underload-threshold", type=int, default=None)
    parser.add_argument(
        "--schedulers",
        nargs="+",
        choices=["baseline", "wcp"],
        default=["baseline", "wcp"],
    )
    parser.add_argument("--notes")
    args = parser.parse_args(argv)

    return SweepConfig(
        exp_name=args.exp_name,
        db_path=Path(args.db_path),
        output_root=Path(args.output_root),
        model_path=args.model_path,
        sglang_root=args.sglang_root,
        rates=list(args.rates),
        host=args.host,
        baseline_port=args.baseline_port,
        wcp_port=args.wcp_port,
        baseline_gpu_id=args.baseline_gpu_id,
        wcp_gpu_id=args.wcp_gpu_id,
        baseline_chunked_prefill_size=args.baseline_chunked_prefill_size,
        baseline_prefill_max_requests=args.baseline_prefill_max_requests,
        num_prompts=args.num_prompts,
        random_input_len=args.random_input_len,
        random_output_len=args.random_output_len,
        mem_fraction_static=args.mem_fraction_static,
        attention_backend=args.attention_backend,
        sampling_backend=args.sampling_backend,
        disable_cuda_graph=args.disable_cuda_graph,
        disable_radix_cache=args.disable_radix_cache,
        tensor_parallel_size=args.tensor_parallel_size,
        warmup_requests=args.warmup_requests,
        request_timeout_s=args.request_timeout_s,
        server_start_timeout_s=args.server_start_timeout_s,
        benchmark_timeout_s=args.benchmark_timeout_s,
        wcp_total_limit=args.wcp_total_limit,
        wcp_chunk_size=args.wcp_chunk_size,
        wcp_prompt_type=args.wcp_prompt_type,
        wcp_enable_underload_bypass=not args.disable_wcp_underload_bypass,
        wcp_underload_threshold=args.wcp_underload_threshold,
        schedulers=list(args.schedulers),
        notes=args.notes,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    cfg = parse_args(argv)

    cfg.output_root.mkdir(parents=True, exist_ok=True)
    init_db(cfg.db_path)

    sweep_output_dir = cfg.output_root / f"{_ts()}_{cfg.exp_name}"
    sweep_output_dir.mkdir(parents=True, exist_ok=True)
    sweep_id = insert_sweep(cfg, sweep_output_dir)

    print(f"SQLite DB: {cfg.db_path}")
    print(f"Sweep output dir: {sweep_output_dir}")
    print(f"Sweep ID: {sweep_id}")
    print(f"Rates: {', '.join(f'{rate:g}' for rate in cfg.rates)}")
    print(
        f"GPU mapping: baseline->gpu{cfg.baseline_gpu_id}, "
        f"wcp->gpu{cfg.wcp_gpu_id}"
    )
    print(f"Schedulers: {', '.join(cfg.schedulers)}")

    print("\n=== Launching selected schedulers ===")
    run_scheduler_pair_rates(cfg, sweep_id, sweep_output_dir)

    comparisons = build_comparisons(cfg, sweep_id)
    if comparisons:
        region = summarize_region(comparisons)
        print("\n=== Stable Region Summary ===")
        print("Stable rates:", ", ".join(str(r) for r in region["stable_rates"]) or "<none>")
        print("WCP win rates:", ", ".join(str(r) for r in region["wcp_win_rates"]) or "<none>")
        print(
            "WCP loss/tie rates:",
            ", ".join(str(r) for r in region["wcp_loss_or_tie_rates"]) or "<none>",
        )
        print("Unstable rates:", ", ".join(str(r) for r in region["unstable_rates"]) or "<none>")
    else:
        print("\nNo baseline-vs-WCP comparison generated for this sweep.")
    print(f"Query DB: {cfg.db_path}")
    print(f"Sweep ID: {sweep_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
