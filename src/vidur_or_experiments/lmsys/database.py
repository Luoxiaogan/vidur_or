"""SQLite helpers for LMSYS reproduction databases."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import DEFAULT_DB_PATH, Section6LmsysConfig
from .runner_command import build_runner_command


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS real_data_provenance_runs (
  timestamp TEXT,
  run_tag TEXT,
  model_name TEXT,
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
  m INT,
  n_k_json TEXT,
  segments_json TEXT,
  n_completed INT,
  metric_trim_head_frac REAL,
  metric_trim_tail_frac REAL
);

CREATE TABLE IF NOT EXISTS reproduction_configs (
  run_tag TEXT PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  profile TEXT NOT NULL,
  config_json TEXT NOT NULL,
  command_json TEXT NOT NULL,
  notes TEXT
);

CREATE VIEW IF NOT EXISTS lmsys_best_baseline AS
SELECT
  qps,
  MIN(mean_latency) AS best_baseline_latency
FROM real_data_provenance_runs
WHERE algorithm IN ('vllm', 'sarathi')
  AND return_code = 0
  AND mean_latency IS NOT NULL
GROUP BY qps;

CREATE VIEW IF NOT EXISTS lmsys_best_wcp AS
SELECT *
FROM (
  SELECT
    r.*,
    ROW_NUMBER() OVER (
      PARTITION BY r.qps
      ORDER BY r.mean_latency, r.total_limit, r.m, r.chunk_size, r.config_name
    ) AS rn
  FROM real_data_provenance_runs r
  WHERE r.algorithm = 'wcp_real'
    AND r.return_code = 0
    AND r.mean_latency IS NOT NULL
)
WHERE rn = 1;

CREATE VIEW IF NOT EXISTS lmsys_best_wcp_vs_baseline AS
SELECT
  w.qps,
  w.config_name,
  w.mean_latency AS wcp_latency,
  b.best_baseline_latency,
  (b.best_baseline_latency - w.mean_latency) / b.best_baseline_latency * 100.0 AS win_pct,
  w.total_limit,
  w.chunk_size,
  w.m,
  w.seg_margin,
  w.wait_cp_gate,
  w.wait_gate,
  w.n_k_json,
  w.segments_json,
  w.run_tag
FROM lmsys_best_wcp w
JOIN lmsys_best_baseline b USING (qps);
"""


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def record_reproduction_config(
    config: Section6LmsysConfig,
    profile: str = "section6_lmsys",
    notes: str = "",
) -> None:
    initialize_database(config.db_path)
    payload = {
        "run_tag": config.resolved_run_tag(),
        "db_path": str(config.db_path),
        "mode": config.mode,
        "qps": config.qps,
        "nreq": config.nreq,
        "nbins": config.nbins,
        "model_name": config.model_name,
        "device": config.device,
        "sarathi_baseline_chunk_sizes": config.sarathi_baseline_chunk_sizes,
        "sarathi_baseline_batch_size_cap": config.sarathi_baseline_batch_size_cap,
        "wcp_chunk_sizes": config.wcp_chunk_sizes,
        "tl_values": config.tl_values,
        "nested_segment_counts": config.nested_segment_counts,
        "seg_margins": config.seg_margins,
        "wait_cp_gate_values": config.wait_cp_gate_values,
        "wait_gate_values": config.wait_gate_values,
        "segment_priority_orders": config.segment_priority_orders,
        "trim_head_frac": config.trim_head_frac,
        "trim_tail_frac": config.trim_tail_frac,
        "extra_runner_args": list(config.extra_runner_args),
    }
    command = build_runner_command(config)
    with sqlite3.connect(config.db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO reproduction_configs
              (run_tag, profile, config_json, command_json, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                config.resolved_run_tag(),
                profile,
                json.dumps(payload, sort_keys=True),
                json.dumps(command),
                notes,
            ),
        )
        conn.commit()
