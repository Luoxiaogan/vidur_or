#!/usr/bin/env python3
"""
Durable rerun pipeline for real-data lmsys tuning provenance.

This script reruns the paper-facing real-data grid with resumable SQLite
logging so every candidate can be traced back to:
  - exact scheduler family and hyperparameters
  - baseline variant
  - WAIT_CP_GATE / wait_gate settings
  - preserved stdout/stderr and request_metrics CSV artifacts

Default candidate profile mirrors the historical paper-facing search space
visible in the repository notes and scripts:
  - Baselines: vLLM, Sarathi-256, Sarathi-512
  - WCP candidates on the 50-bin workload:
      * general_nested_chunked ("auto50seg")
      * uniform_segment_chunked with segment_size sweep
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Iterable

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "experiments.db"
DEFAULT_TRACE = REPO_ROOT / "data" / "processed_traces" / "sample_2e5_input<200_output<500.csv"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "real_data_provenance"
DEFAULT_TABLE = "real_data_provenance_runs"
DEFAULT_TIMEOUT = 1800

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
    "--no-metrics_config_store_plots",
    "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size",
    "16384",
    "--random_forrest_execution_time_predictor_config_prediction_max_batch_size",
    "2048",
    "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request",
    "65536",
]


@dataclass(frozen=True)
class RunSpec:
    qps: int
    algorithm: str
    config_name: str
    scheduler_type: str
    baseline_variant: str | None
    nbins: int | None
    total_limit: int | None
    chunk_size: int | None
    segment_size: int | None
    seg_margin: float | None
    wait_cp_gate: str | None
    wait_gate: str | None
    m: int | None
    n_k_json: str | None
    segments_json: str | None
    nreq: int
    max_tokens: int
    prompt_types_json: str
    command_json: str
    source_note: str


@dataclass(frozen=True)
class SearchStrategy:
    include_vllm: bool
    include_sarathi512: bool
    wait_gate_values: list[str]
    default_tl_values: list[int]
    low_qps_values: set[int]
    extra_low_qps_tl_values: list[int]
    adaptive_tl_grid: bool
    adaptive_tl_step: int
    adaptive_tl_half_width: int
    adaptive_tl_slope: float
    adaptive_tl_min: int
    adaptive_tl_max: int
    segment_counts: list[int]


def parse_qps_list(raw: str) -> list[int]:
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return [int(x) for x in items]


def parse_int_list(raw: str) -> list[int]:
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return [int(x) for x in items]


def segment_size_for_count(segment_count: int, max_decode: int = 500) -> int:
    if segment_count <= 0:
        raise ValueError("segment_count must be positive")
    return max(1, max_decode // segment_count)


def make_range_list(start: int, end: int, step: int) -> list[int]:
    if step <= 0:
        raise ValueError("step must be positive")
    if end < start:
        return []
    values = list(range(start, end + 1, step))
    if values[-1] != end:
        values.append(end)
    return sorted(set(values))


def ensure_schema(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            timestamp TEXT,
            run_tag TEXT,
            qps INT,
            algorithm TEXT,
            config_name TEXT,
            scheduler_type TEXT,
            baseline_variant TEXT,
            nbins INT,
            total_limit INT,
            chunk_size INT,
            segment_size INT,
            seg_margin REAL,
            wait_cp_gate TEXT,
            wait_gate TEXT,
            m INT,
            n_k_json TEXT,
            segments_json TEXT,
            nreq INT,
            max_tokens INT,
            trace_file TEXT,
            prompt_types_json TEXT,
            command_json TEXT,
            return_code INT,
            mean_latency REAL,
            p99_latency REAL,
            n_steady INT,
            restarts INT,
            output_dir TEXT,
            csv_path TEXT,
            stdout_path TEXT,
            stderr_path TEXT,
            source_note TEXT,
            UNIQUE (
                run_tag, qps, algorithm, config_name, scheduler_type, baseline_variant,
                nbins, total_limit, chunk_size, segment_size, seg_margin,
                wait_cp_gate, wait_gate, nreq
            )
        )
        """
    )
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if "m" not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN m INT")
    if "n_k_json" not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN n_k_json TEXT")
    if "segments_json" not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN segments_json TEXT")
    conn.commit()


def slugify(raw: str) -> str:
    return (
        raw.replace("/", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace(",", "_")
        .replace("(", "")
        .replace(")", "")
    )


def build_bins(df: pd.DataFrame, qps: int, nbins: int) -> list[dict]:
    seg_size = max(1, 500 // nbins)
    prompt_types = []
    for idx in range(nbins):
        lo = idx * seg_size + 1
        hi = 500 if idx == nbins - 1 else min(500, (idx + 1) * seg_size)
        mask = (df.num_decode_tokens >= lo) & (df.num_decode_tokens <= hi)
        sub = df[mask]
        if len(sub) == 0:
            continue
        prompt_types.append(
            {
                "type": f"d{hi}",
                "prefill": max(1, int(sub.num_prefill_tokens.mean())),
                "decode": int(hi),
                "arrival_rate": round(qps * len(sub) / len(df), 4),
            }
        )
    return prompt_types


def compute_general_nested_segments(
    prompt_types: list[dict], total_limit: int, seg_margin: float
) -> list[dict]:
    unique_decodes = sorted({int(pt["decode"]) for pt in prompt_types})
    if not unique_decodes:
        return []

    raw_segments = []
    raw_segments.append(
        {
            "count": unique_decodes[0] if unique_decodes else 1,
            "arrival_sum": sum(float(pt["arrival_rate"]) for pt in prompt_types),
        }
    )
    for idx in range(1, len(unique_decodes)):
        prev_decode = unique_decodes[idx - 1]
        raw_segments.append(
            {
                "count": unique_decodes[idx] - prev_decode,
                "arrival_sum": sum(
                    float(pt["arrival_rate"])
                    for pt in prompt_types
                    if int(pt["decode"]) > prev_decode
                ),
            }
        )

    ratios = []
    for idx in range(len(raw_segments) - 1):
        cur = raw_segments[idx]["arrival_sum"]
        nxt = raw_segments[idx + 1]["arrival_sum"]
        p_k = nxt / cur if cur > 0 else 0.0
        ratios.append(min(p_k + seg_margin, 0.99))

    cumulative_ratio = [1.0]
    for ratio in ratios:
        cumulative_ratio.append(cumulative_ratio[-1] * ratio)

    denominator = sum(
        raw_segments[idx]["count"] * cumulative_ratio[idx]
        for idx in range(len(raw_segments))
    )
    n_1 = total_limit / denominator if denominator > 0 else 0.0
    n_per_seg = [n_1 * cumulative_ratio[idx] for idx in range(len(raw_segments))]

    segments_info = []
    global_stage = 0
    for idx, raw_seg in enumerate(raw_segments):
        seg_total_limit = int(round(n_per_seg[idx] * raw_seg["count"]))
        base = seg_total_limit // raw_seg["count"] if raw_seg["count"] > 0 else 0
        remainder = seg_total_limit % raw_seg["count"] if raw_seg["count"] > 0 else 0
        seg_start = global_stage
        global_stage += raw_seg["count"]
        seg_end = global_stage - 1
        p_k = None
        q_k = None
        if idx < len(raw_segments) - 1:
            cur = raw_seg["arrival_sum"]
            nxt = raw_segments[idx + 1]["arrival_sum"]
            p_k = nxt / cur if cur > 0 else 0.0
            q_k = ratios[idx]
        segments_info.append(
            {
                "segment_index": idx,
                "start": seg_start,
                "end": seg_end,
                "count": raw_seg["count"],
                "arrival_sum": raw_seg["arrival_sum"],
                "p_k": p_k,
                "q_k": q_k,
                "n_k": n_per_seg[idx],
                "n_k_floor": max(1, int(n_per_seg[idx])),
                "n_k_ceil": int(ceil(n_per_seg[idx])),
                "seg_total_limit": seg_total_limit,
                "per_stage_limit_min": base,
                "per_stage_limit_max": base + 1 if remainder > 0 else base,
            }
        )
    return segments_info


def compute_uniform_segments(
    prompt_types: list[dict], total_limit: int, segment_size: int
) -> list[dict]:
    if not prompt_types:
        return []
    max_decode = max(int(pt["decode"]) for pt in prompt_types)
    if max_decode <= 0:
        return []
    num_segments = max(1, ceil(max_decode / segment_size))
    n_k = total_limit / max_decode
    segments_info = []
    for idx in range(num_segments):
        seg_start = idx * segment_size
        seg_end = min((idx + 1) * segment_size, max_decode) - 1
        seg_count = seg_end - seg_start + 1
        seg_total_limit = int(round(n_k * seg_count))
        base = seg_total_limit // seg_count if seg_count > 0 else 0
        remainder = seg_total_limit % seg_count if seg_count > 0 else 0
        segments_info.append(
            {
                "segment_index": idx,
                "start": seg_start,
                "end": seg_end,
                "count": seg_count,
                "arrival_sum": None,
                "p_k": None,
                "q_k": None,
                "n_k": n_k,
                "n_k_floor": max(1, int(n_k)),
                "n_k_ceil": int(ceil(n_k)),
                "seg_total_limit": seg_total_limit,
                "per_stage_limit_min": base,
                "per_stage_limit_max": base + 1 if remainder > 0 else base,
            }
        )
    return segments_info


def build_baseline_specs(
    qps: int,
    prompt_types_json: str,
    nreq: int,
    max_tokens: int,
    include_vllm: bool,
    include_sarathi512: bool,
) -> list[RunSpec]:
    specs: list[RunSpec] = []
    baseline_defs = [
        (
            "sarathi",
            "Sarathi256",
            [
                "--replica_scheduler_config_type",
                "sarathi",
                "--sarathi_scheduler_config_chunk_size",
                "256",
                "--sarathi_scheduler_config_batch_size_cap",
                "256",
            ],
        )
    ]
    if include_sarathi512:
        baseline_defs.append(
            (
                "sarathi",
                "Sarathi512",
                [
                    "--replica_scheduler_config_type",
                    "sarathi",
                    "--sarathi_scheduler_config_chunk_size",
                    "512",
                    "--sarathi_scheduler_config_batch_size_cap",
                    "512",
                ],
            )
        )
    if include_vllm:
        baseline_defs.insert(0, ("vllm", "vLLM", ["--replica_scheduler_config_type", "vllm"]))

    for algo, variant, extra_args in baseline_defs:
        cmd = COMMON + [
            "--custom_request_generator_config_prompt_types",
            prompt_types_json,
            "--custom_request_generator_config_max_tokens",
            str(max_tokens),
            "--custom_request_generator_config_num_requests",
            str(nreq),
        ] + extra_args
        specs.append(
            RunSpec(
                qps=qps,
                algorithm=algo,
                config_name=variant,
                scheduler_type=extra_args[1],
                baseline_variant=variant,
                nbins=50,
                total_limit=None,
                chunk_size=None if algo == "vllm" else int(extra_args[3]),
                segment_size=None,
                seg_margin=0.0,
                wait_cp_gate="off",
                wait_gate="off",
                m=None,
                n_k_json=None,
                segments_json=None,
                nreq=nreq,
                max_tokens=max_tokens,
                prompt_types_json=prompt_types_json,
                command_json=json.dumps(cmd),
                source_note="paper_grid_baseline",
            )
        )
    return specs


def build_wcp_specs(
    qps: int,
    prompt_types_json: str,
    nreq: int,
    max_tokens: int,
    wait_gate_values: list[str],
    tl_values: list[int],
    segment_counts: list[int],
) -> list[RunSpec]:
    specs: list[RunSpec] = []
    prompt_types = json.loads(prompt_types_json)
    seg_margin = 0.0
    chunk_size = 32
    wait_cp_gate = "on"

    for wait_gate in wait_gate_values:
        wait_gate_flag = "ON" if wait_gate == "on" else "OFF"
        for tl in tl_values:
            segments_info = compute_general_nested_segments(prompt_types, tl, seg_margin)
            if tl < len(segments_info):
                continue
            cmd = COMMON + [
                "--custom_request_generator_config_prompt_types",
                prompt_types_json,
                "--custom_request_generator_config_max_tokens",
                str(max_tokens),
                "--custom_request_generator_config_num_requests",
                str(nreq),
                "--replica_scheduler_config_type",
                "general_nested_chunked",
                "--general_nested_chunked_scheduler_config_prompt_types",
                prompt_types_json,
                "--general_nested_chunked_scheduler_config_total_limit",
                str(tl),
                "--general_nested_chunked_scheduler_config_total_num_requests",
                str(nreq),
                "--general_nested_chunked_scheduler_config_chunk_size",
                str(chunk_size),
                "--general_nested_chunked_scheduler_config_seg_margin",
                str(seg_margin),
                "--general_nested_chunked_scheduler_config_force_clear",
            ]
            if wait_gate != "on":
                cmd.append("--no-general_nested_chunked_scheduler_config_wait_gate")

            specs.append(
                RunSpec(
                    qps=qps,
                    algorithm="wcp_real",
                    config_name=f"auto50seg_tl{tl}_cs{chunk_size}_wg{wait_gate_flag}",
                    scheduler_type="general_nested_chunked",
                    baseline_variant=None,
                    nbins=50,
                    total_limit=tl,
                    chunk_size=chunk_size,
                    segment_size=None,
                    seg_margin=seg_margin,
                    wait_cp_gate=wait_cp_gate,
                    wait_gate=wait_gate,
                    m=len(segments_info),
                    n_k_json=json.dumps([seg["n_k"] for seg in segments_info]),
                    segments_json=json.dumps(segments_info),
                    nreq=nreq,
                    max_tokens=max_tokens,
                    prompt_types_json=prompt_types_json,
                    command_json=json.dumps(cmd),
                    source_note="paper_grid_wcp_auto50",
                )
            )

        for segment_count in segment_counts:
            seg_size = segment_size_for_count(segment_count)
            for tl in tl_values:
                segments_info = compute_uniform_segments(prompt_types, tl, seg_size)
                if tl < len(segments_info):
                    continue
                cmd = COMMON + [
                    "--custom_request_generator_config_prompt_types",
                    prompt_types_json,
                    "--custom_request_generator_config_max_tokens",
                    str(max_tokens),
                    "--custom_request_generator_config_num_requests",
                    str(nreq),
                    "--replica_scheduler_config_type",
                    "uniform_segment_chunked",
                    "--uniform_segment_chunked_scheduler_config_prompt_types",
                    prompt_types_json,
                    "--uniform_segment_chunked_scheduler_config_total_limit",
                    str(tl),
                    "--uniform_segment_chunked_scheduler_config_total_num_requests",
                    str(nreq),
                    "--uniform_segment_chunked_scheduler_config_chunk_size",
                    str(chunk_size),
                    "--uniform_segment_chunked_scheduler_config_segment_size",
                    str(seg_size),
                    "--uniform_segment_chunked_scheduler_config_seg_margin",
                    str(seg_margin),
                    "--uniform_segment_chunked_scheduler_config_force_clear",
                ]
                if wait_gate != "on":
                    cmd.append("--no-uniform_segment_chunked_scheduler_config_wait_gate")

                specs.append(
                    RunSpec(
                        qps=qps,
                        algorithm="wcp_real",
                        config_name=f"uniform_m{segment_count}_tl{tl}_cs{chunk_size}_wg{wait_gate_flag}",
                        scheduler_type="uniform_segment_chunked",
                        baseline_variant=None,
                        nbins=50,
                        total_limit=tl,
                        chunk_size=chunk_size,
                        segment_size=seg_size,
                        seg_margin=seg_margin,
                        wait_cp_gate=wait_cp_gate,
                        wait_gate=wait_gate,
                        m=len(segments_info),
                        n_k_json=json.dumps([seg["n_k"] for seg in segments_info]),
                        segments_json=json.dumps(segments_info),
                        nreq=nreq,
                        max_tokens=max_tokens,
                        prompt_types_json=prompt_types_json,
                        command_json=json.dumps(cmd),
                        source_note="paper_grid_wcp_uniform50",
                    )
                )

    return specs


def build_run_specs(
    df: pd.DataFrame,
    qps_list: Iterable[int],
    nreq: int,
    mode: str,
    strategy: SearchStrategy,
) -> list[RunSpec]:
    specs: list[RunSpec] = []
    max_tokens = 539
    for qps in qps_list:
        tl_values = resolve_tl_values_for_qps(qps, strategy)
        prompt_types_json = json.dumps(build_bins(df, qps, 50))
        if mode in {"all", "baselines"}:
            specs.extend(
                build_baseline_specs(
                    qps,
                    prompt_types_json,
                    nreq,
                    max_tokens,
                    strategy.include_vllm,
                    strategy.include_sarathi512,
                )
            )
        if mode in {"all", "wcp"}:
            specs.extend(
                build_wcp_specs(
                    qps,
                    prompt_types_json,
                    nreq,
                    max_tokens,
                    strategy.wait_gate_values,
                    tl_values,
                    strategy.segment_counts,
                )
            )
    return specs


def adaptive_tl_values_for_qps(
    qps: int,
    step: int,
    half_width: int,
    slope: float,
    min_tl: int,
    max_tl: int,
) -> list[int]:
    center = int(round(qps * slope / step) * step)
    start = max(min_tl, center - half_width)
    end = min(max_tl, center + half_width)
    if start > end:
        start = end = max(min_tl, min(max_tl, center))
    return make_range_list(start, end, step)


def three_point_tl_values_for_qps(
    qps: int,
    step: int,
    slope: float,
    min_tl: int,
    max_tl: int,
) -> list[int]:
    center = int(round(qps * slope / step) * step)
    center = min(max_tl, max(min_tl, center))

    values = {center}
    offset = step
    while len(values) < 3 and (center - offset >= min_tl or center + offset <= max_tl):
        if center - offset >= min_tl:
            values.add(center - offset)
        if len(values) >= 3:
            break
        if center + offset <= max_tl:
            values.add(center + offset)
        offset += step
    return sorted(values)


def resolve_tl_values_for_qps(qps: int, strategy: SearchStrategy) -> list[int]:
    use_adaptive = strategy.adaptive_tl_grid and (
        not strategy.low_qps_values or qps in strategy.low_qps_values
    )
    if use_adaptive:
        if strategy.adaptive_tl_half_width <= strategy.adaptive_tl_step:
            return three_point_tl_values_for_qps(
                qps=qps,
                step=strategy.adaptive_tl_step,
                slope=strategy.adaptive_tl_slope,
                min_tl=strategy.adaptive_tl_min,
                max_tl=strategy.adaptive_tl_max,
            )
        return adaptive_tl_values_for_qps(
            qps=qps,
            step=strategy.adaptive_tl_step,
            half_width=strategy.adaptive_tl_half_width,
            slope=strategy.adaptive_tl_slope,
            min_tl=strategy.adaptive_tl_min,
            max_tl=strategy.adaptive_tl_max,
        )

    tl_values = list(strategy.default_tl_values)
    if qps in strategy.low_qps_values:
        tl_values = sorted(set(tl_values + strategy.extra_low_qps_tl_values))
    return tl_values


def build_search_strategy(args: argparse.Namespace) -> SearchStrategy:
    wait_gate_values = [item.strip() for item in args.wait_gate_values.split(",") if item.strip()]
    default_tl_values = parse_int_list(args.tl_values)
    low_qps_values = set(parse_qps_list(args.low_qps)) if args.low_qps else set()
    extra_low_qps_tl_values = (
        parse_int_list(args.extra_low_qps_tl_values)
        if args.extra_low_qps_tl_values
        else []
    )
    return SearchStrategy(
        include_vllm=args.include_vllm,
        include_sarathi512=args.include_sarathi512,
        wait_gate_values=wait_gate_values,
        default_tl_values=default_tl_values,
        low_qps_values=low_qps_values,
        extra_low_qps_tl_values=extra_low_qps_tl_values,
        adaptive_tl_grid=args.adaptive_tl_grid,
        adaptive_tl_step=args.adaptive_tl_step,
        adaptive_tl_half_width=args.adaptive_tl_half_width,
        adaptive_tl_slope=args.adaptive_tl_slope,
        adaptive_tl_min=args.adaptive_tl_min,
        adaptive_tl_max=args.adaptive_tl_max,
        segment_counts=parse_int_list(args.segment_counts),
    )


def already_logged(conn: sqlite3.Connection, table: str, run_tag: str, spec: RunSpec) -> bool:
    row = conn.execute(
        f"""
        SELECT 1 FROM {table}
        WHERE run_tag IS ?
          AND qps IS ?
          AND algorithm IS ?
          AND config_name IS ?
          AND scheduler_type IS ?
          AND baseline_variant IS ?
          AND nbins IS ?
          AND total_limit IS ?
          AND chunk_size IS ?
          AND segment_size IS ?
          AND seg_margin IS ?
          AND wait_cp_gate IS ?
          AND wait_gate IS ?
          AND nreq IS ?
        LIMIT 1
        """,
        (
            run_tag,
            spec.qps,
            spec.algorithm,
            spec.config_name,
            spec.scheduler_type,
            spec.baseline_variant,
            spec.nbins,
            spec.total_limit,
            spec.chunk_size,
            spec.segment_size,
            spec.seg_margin,
            spec.wait_cp_gate,
            spec.wait_gate,
            spec.nreq,
        ),
    ).fetchone()
    return row is not None


def prune_stale_wcp_rows(
    conn: sqlite3.Connection,
    table: str,
    run_tag: str,
    specs: list[RunSpec],
) -> int:
    keep_keys = {
        (
            spec.qps,
            spec.algorithm,
            spec.config_name,
            spec.scheduler_type,
            spec.baseline_variant,
            spec.nbins,
            spec.total_limit,
            spec.chunk_size,
            spec.segment_size,
            spec.seg_margin,
            spec.wait_cp_gate,
            spec.wait_gate,
            spec.nreq,
        )
        for spec in specs
        if spec.algorithm == "wcp_real"
    }
    if not keep_keys:
        return 0

    stale_rowids = []
    for row in conn.execute(
        f"""
        SELECT rowid, qps, algorithm, config_name, scheduler_type, baseline_variant,
               nbins, total_limit, chunk_size, segment_size, seg_margin,
               wait_cp_gate, wait_gate, nreq
        FROM {table}
        WHERE run_tag=? AND algorithm='wcp_real'
        """,
        (run_tag,),
    ):
        rowid = row[0]
        key = tuple(row[1:])
        if key not in keep_keys:
            stale_rowids.append(rowid)

    if not stale_rowids:
        return 0

    conn.executemany(
        f"DELETE FROM {table} WHERE rowid=?",
        [(rowid,) for rowid in stale_rowids],
    )
    conn.commit()
    return len(stale_rowids)


def persist_metrics(
    conn: sqlite3.Connection,
    table: str,
    run_tag: str,
    trace_file: Path,
    spec: RunSpec,
    result: subprocess.CompletedProcess[str],
    mean_latency: float | None,
    p99_latency: float | None,
    n_steady: int | None,
    restarts: int | None,
    output_dir: Path,
    csv_path: Path | None,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    conn.execute(
        f"""
        INSERT OR REPLACE INTO {table} (
            timestamp,
            run_tag,
            qps,
            algorithm,
            config_name,
            scheduler_type,
            baseline_variant,
            nbins,
            total_limit,
            chunk_size,
            segment_size,
            seg_margin,
            wait_cp_gate,
            wait_gate,
            nreq,
            max_tokens,
            trace_file,
            prompt_types_json,
            command_json,
            return_code,
            mean_latency,
            p99_latency,
            n_steady,
            restarts,
            output_dir,
            csv_path,
            stdout_path,
            stderr_path,
            source_note,
            m,
            n_k_json,
            segments_json
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            datetime.now().isoformat(),
            run_tag,
            spec.qps,
            spec.algorithm,
            spec.config_name,
            spec.scheduler_type,
            spec.baseline_variant,
            spec.nbins,
            spec.total_limit,
            spec.chunk_size,
            spec.segment_size,
            spec.seg_margin,
            spec.wait_cp_gate,
            spec.wait_gate,
            spec.nreq,
            spec.max_tokens,
            str(trace_file),
            spec.prompt_types_json,
            spec.command_json,
            result.returncode,
            mean_latency,
            p99_latency,
            n_steady,
            restarts,
            str(output_dir),
            str(csv_path) if csv_path else None,
            str(stdout_path),
            str(stderr_path),
            spec.source_note,
            spec.m,
            spec.n_k_json,
            spec.segments_json,
        ),
    )
    conn.commit()


def collect_metrics(output_dir: Path) -> tuple[float | None, float | None, int | None, int | None, Path | None]:
    csvs = sorted(glob.glob(str(output_dir / "**" / "request_metrics_*.csv"), recursive=True))
    if not csvs:
        return None, None, None, None, None
    csv_path = Path(csvs[0])
    df = pd.read_csv(csv_path)
    if "request_e2e_time" not in df:
        return None, None, None, None, csv_path
    completed = df[df["request_e2e_time"].notna()]
    if completed.empty:
        return None, None, None, None, csv_path
    start = len(completed) // 4
    steady = completed.iloc[start:]
    restarts = None
    if "num_restarts" in steady:
        restarts = int(steady["num_restarts"].fillna(0).sum())
    return (
        float(steady["request_e2e_time"].mean()),
        float(steady["request_e2e_time"].quantile(0.99)),
        int(len(steady)),
        restarts,
        csv_path,
    )


def run_one(
    conn: sqlite3.Connection,
    table: str,
    run_tag: str,
    trace_file: Path,
    output_root: Path,
    spec: RunSpec,
    timeout: int,
    force: bool,
) -> tuple[bool, str]:
    if not force and already_logged(conn, table, run_tag, spec):
        return False, f"skip cached qps={spec.qps} {spec.config_name}"

    run_dir = output_root / run_tag / f"qps_{spec.qps}" / slugify(spec.config_name)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    cmd = json.loads(spec.command_json) + ["--metrics_config_output_dir", str(run_dir)]

    env = os.environ.copy()
    env["WAIT_CP_GATE"] = spec.wait_cp_gate or "off"

    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(result.stderr, encoding="utf-8", errors="replace")

    mean_latency, p99_latency, n_steady, restarts, csv_path = collect_metrics(run_dir)
    persist_metrics(
        conn=conn,
        table=table,
        run_tag=run_tag,
        trace_file=trace_file,
        spec=spec,
        result=result,
        mean_latency=mean_latency,
        p99_latency=p99_latency,
        n_steady=n_steady,
        restarts=restarts,
        output_dir=run_dir,
        csv_path=csv_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    if result.returncode != 0:
        return True, f"FAIL qps={spec.qps} {spec.config_name} rc={result.returncode}"
    if mean_latency is None:
        return True, f"MISS qps={spec.qps} {spec.config_name} no_csv_or_metric"
    return True, f"OK qps={spec.qps} {spec.config_name} mean={mean_latency:.3f}s p99={p99_latency:.3f}s"


def print_summary(conn: sqlite3.Connection, table: str, run_tag: str) -> None:
    print("\n=== coverage ===")
    for row in conn.execute(
        f"""
        SELECT qps, algorithm, COUNT(*) AS rows, MIN(mean_latency) AS best
        FROM {table}
        WHERE run_tag=?
        GROUP BY qps, algorithm
        ORDER BY qps, algorithm
        """,
        (run_tag,),
    ):
        print(row)

    print("\n=== best WCP vs Sarathi256 / Sarathi512 ===")
    query = f"""
    WITH wcp AS (
        SELECT qps, config_name, scheduler_type, nbins, total_limit, chunk_size, segment_size,
               wait_cp_gate, wait_gate, seg_margin, m, n_k_json, mean_latency,
               ROW_NUMBER() OVER (PARTITION BY qps ORDER BY mean_latency) AS rn
        FROM {table}
        WHERE run_tag=? AND algorithm='wcp_real' AND mean_latency IS NOT NULL
    ),
    sar256 AS (
        SELECT qps, mean_latency AS sar256_latency
        FROM {table}
        WHERE run_tag=? AND algorithm='sarathi' AND baseline_variant='Sarathi256'
    ),
    sar512 AS (
        SELECT qps, mean_latency AS sar512_latency
        FROM {table}
        WHERE run_tag=? AND algorithm='sarathi' AND baseline_variant='Sarathi512'
    )
    SELECT
        wcp.qps,
        ROUND(wcp.mean_latency, 4) AS wcp_latency,
        ROUND(sar256.sar256_latency, 4) AS sar256_latency,
        ROUND(sar512.sar512_latency, 4) AS sar512_latency,
        ROUND((wcp.mean_latency - sar256.sar256_latency) / sar256.sar256_latency * 100.0, 2) AS gap_vs_sar256_pct,
        ROUND((wcp.mean_latency - sar512.sar512_latency) / sar512.sar512_latency * 100.0, 2) AS gap_vs_sar512_pct,
        wcp.config_name,
        wcp.scheduler_type,
        wcp.nbins,
        wcp.m,
        wcp.n_k_json,
        wcp.total_limit,
        wcp.chunk_size,
        wcp.segment_size,
        wcp.wait_cp_gate,
        wcp.wait_gate,
        wcp.seg_margin
    FROM wcp
    LEFT JOIN sar256 USING (qps)
    LEFT JOIN sar512 USING (qps)
    WHERE wcp.rn=1
    ORDER BY wcp.qps
    """
    for row in conn.execute(query, (run_tag, run_tag, run_tag)):
        print(row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rerun real-data lmsys experiments with durable provenance logging.")
    parser.add_argument("--run-tag", default=f"real_data_provenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--db-path", default=str(DEFAULT_DB))
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--trace-file", default=str(DEFAULT_TRACE))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--qps", default="10,20,30,40,50,60,70,80,90,100,110,120,130,140,150")
    parser.add_argument("--nreq", type=int, default=5000)
    parser.add_argument("--mode", choices=["all", "baselines", "wcp"], default="all")
    parser.add_argument("--include-vllm", action="store_true", help="Also run vLLM as a secondary baseline.")
    parser.add_argument("--include-sarathi512", action="store_true", help="Also run Sarathi512 as a secondary baseline.")
    parser.add_argument("--wait-gate-values", default="on", help="Comma-separated wait_gate values to sweep, e.g. on or on,off.")
    parser.add_argument("--tl-values", default="300", help="Fallback tl grid used when adaptive tl is disabled.")
    parser.add_argument("--low-qps", default="", help="Comma-separated low-QPS values that should receive an expanded tl grid.")
    parser.add_argument("--extra-low-qps-tl-values", default="", help="Additional tl values to merge into the grid for the specified low-QPS set.")
    parser.add_argument(
        "--adaptive-tl-grid",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use a shifted fixed-step tl grid that moves upward with QPS.",
    )
    parser.add_argument("--adaptive-tl-step", type=int, default=20, help="Step size for the adaptive tl grid.")
    parser.add_argument(
        "--adaptive-tl-half-width",
        type=int,
        default=20,
        help="Half-width around the adaptive tl center; defaults to one step for three tl values.",
    )
    parser.add_argument("--adaptive-tl-slope", type=float, default=6.0, help="Center tl ~= slope * qps for the adaptive grid.")
    parser.add_argument("--adaptive-tl-min", type=int, default=40, help="Minimum tl in the adaptive grid.")
    parser.add_argument("--adaptive-tl-max", type=int, default=300, help="Maximum tl in the adaptive grid.")
    parser.add_argument("--segment-counts", default="5,10,20,50", help="Comma-separated segment-count choices m for uniform_segment_chunked.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N generated specs.")
    parser.add_argument("--force", action="store_true", help="Ignore cached rows for the same run-tag and rerun.")
    parser.add_argument("--prune-stale", action="store_true", help="Delete cached WCP rows for this run-tag that are outside the generated grid.")
    parser.add_argument("--print-plan", action="store_true", help="Print generated specs without executing.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    trace_file = Path(args.trace_file)
    output_root = Path(args.output_root)
    qps_list = parse_qps_list(args.qps)
    strategy = build_search_strategy(args)
    df = pd.read_csv(trace_file)

    specs = build_run_specs(
        df=df,
        qps_list=qps_list,
        nreq=args.nreq,
        mode=args.mode,
        strategy=strategy,
    )
    if args.limit is not None:
        specs = specs[: args.limit]

    print(f"run_tag={args.run_tag}")
    print(f"table={args.table}")
    print(f"mode={args.mode}")
    print(f"qps={qps_list}")
    print(f"wait_gate_values={strategy.wait_gate_values}")
    print(f"default_tl_values={strategy.default_tl_values}")
    print(f"low_qps_values={sorted(strategy.low_qps_values)}")
    print(f"extra_low_qps_tl_values={strategy.extra_low_qps_tl_values}")
    print(f"segment_counts={strategy.segment_counts}")
    print(f"adaptive_tl_grid={strategy.adaptive_tl_grid}")
    if strategy.adaptive_tl_grid:
        print(
            f"adaptive_tl_params=step{strategy.adaptive_tl_step},"
            f"half_width{strategy.adaptive_tl_half_width},"
            f"slope{strategy.adaptive_tl_slope},"
            f"min{strategy.adaptive_tl_min},max{strategy.adaptive_tl_max}"
        )
    print(f"spec_count={len(specs)}")

    if args.print_plan:
        for spec in specs:
            print(
                f"{spec.qps:3d} | {spec.algorithm:8s} | {spec.config_name:26s} | "
                f"{spec.scheduler_type:24s} | tl={spec.total_limit} cs={spec.chunk_size} "
                f"seg={spec.segment_size} nbins={spec.nbins} m={spec.m} "
                f"wait_cp={spec.wait_cp_gate} wait={spec.wait_gate}"
            )
        return 0

    conn = sqlite3.connect(args.db_path)
    ensure_schema(conn, args.table)
    if args.prune_stale:
        pruned = prune_stale_wcp_rows(conn, args.table, args.run_tag, specs)
        print(f"pruned_stale_wcp_rows={pruned}", flush=True)

    try:
        for idx, spec in enumerate(specs, start=1):
            changed, message = run_one(
                conn=conn,
                table=args.table,
                run_tag=args.run_tag,
                trace_file=trace_file,
                output_root=output_root,
                spec=spec,
                timeout=args.timeout,
                force=args.force,
            )
            prefix = f"[{idx:03d}/{len(specs):03d}]"
            print(prefix, message, flush=True)
        print_summary(conn, args.table, args.run_tag)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
