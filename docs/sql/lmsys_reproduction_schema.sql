-- Canonical SQLite objects for Section 6 LMSYS reproduction databases.
--
-- The raw run table is also created by scripts/real_data_provenance_rerun.py.
-- It is repeated here so a reproduction database can be initialized before the
-- first run and inspected without implicit schema creation.

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
