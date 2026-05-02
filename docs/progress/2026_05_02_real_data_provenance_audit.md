# Real-data provenance audit - 2026-05-02

## Scope

This note records the current recoverability of the lmsys Figure D / real-data Vidur provenance from `experiments.db`, progress notes, and the rerun scripts.

## Current SQL state

`experiments.db` contains three relevant objects:

- `real_data`: early partial sweep, not the full Figure D grid.
- `real_data_provenance_runs`: durable rerun table created for the later provenance pipeline.
- `reproduction_configs`: durable configs for single-type and two-type repeated-run reproduction, not the full lmsys Figure D sweep.

I added two non-destructive views for safer future queries:

- `real_data_provenance_valid`: rows where both `mean_latency` and `p99_latency` are numeric.
- `real_data_provenance_malformed`: rows where historical insertion wrote nonnumeric JSON/path data into metric columns.

Current counts:

| Object | Rows |
| --- | ---: |
| `real_data_provenance_runs` | 31 |
| `real_data_provenance_valid` | 28 |
| `real_data_provenance_malformed` | 3 |

## Valid provenance coverage

Valid rows currently cover only QPS \(10,20,50,60\), not the full Figure D grid \(10,20,\ldots,150\).

Best valid rows by QPS/policy family:

| QPS | Policy family | Best valid config | Mean latency |
| ---: | --- | --- | ---: |
| 10 | Sarathi | `Sarathi256` | 1.696 |
| 10 | WCP / Nested WAIT | `auto50seg_tl80_cs32_wgON` | 3.301 |
| 20 | Sarathi | `Sarathi256` | 1.876 |
| 50 | Sarathi | `Sarathi256` | 3.939 |
| 50 | vLLM | `vLLM` | 29.823 |
| 50 | WCP / Nested WAIT | `auto50seg_tl400_cs32` | 4.421 |
| 60 | Sarathi | `Sarathi512` | 7.450 |
| 60 | vLLM | `vLLM` | 40.137 |
| 60 | WCP / Nested WAIT | `auto50seg_tl400_cs32` | 8.469 |

Thus the current SQL provenance does not recover a full per-arrival-rate winning configuration table for Figure D. In particular, the valid SQL rows still show raw WCP/Nested WAIT above the best Sarathi row at QPS \(50\) and \(60\). This matches the earlier audit finding that the paper-facing Figure D curve is an observed/presentation artifact rather than a fully reconstructed SQL-backed best-config table.

## Malformed rows

Three rows in `real_data_provenance_runs` have nonnumeric `mean_latency` / `p99_latency` values because older insertion logic wrote prompt-types and command JSON into metric columns. These rows are retained for forensics but must not be used for numerical summaries. Use `real_data_provenance_valid` for all future summaries.

## Rerun pipeline status

`scripts/real_data_provenance_rerun.py` is the correct durable rerun path. It logs:

- scheduler family and hyperparameters,
- baseline variant,
- `WAIT_CP_GATE` / `wait_gate`,
- `prompt_types_json`, `command_json`,
- metric CSV path and stdout/stderr paths,
- optional threshold/segment metadata.

The script's documented intended grid is much larger than the rows currently completed in SQL:

- QPS \(10,20,\ldots,150\),
- Sarathi-256 and Sarathi-512 baselines, optionally vLLM,
- auto-50-segment WCP and uniform-segment WCP,
- adaptive `tl` grid capped at 300,
- uniform segment counts \(m\in\{5,10,20,50\}\),
- \(n_{\mathrm{req}}=5000\).

## Paper implication

Do not strengthen the current real-data claim to a sharp lmsys stability boundary or a complete per-rate provenance claim. The current manuscript/response-letter posture remains submission-safe because it reports the calibration rule, finite search grids, and plotted-rate comparison without promising a full per-rate selected-configuration table for Figure D.

If stronger reproducibility is desired later, finish `scripts/real_data_provenance_rerun.py` for the full QPS grid and regenerate Figure D directly from `real_data_provenance_valid`.
