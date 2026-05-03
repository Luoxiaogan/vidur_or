# LMSYS Section 6 Reproduction Scaffold

## Source Text To Reproduce

Active manuscript source:

- `papers/numerical.tex`, Section 6:
  - Vidur discrete-event simulator.
  - Single NVIDIA A100 80GB.
  - Llama-2-7B.
  - Real workload from `lmsys-chat-1m`.
  - Filtered workload: prefill and decode lengths below 500 tokens.
  - 5,000 sampled requests per arrival rate.
  - Poisson arrivals.
  - Arrival-rate grid: `10,20,...,150` requests/s.
  - Baselines: vLLM and Sarathi.
  - Sarathi paper description: chunked prefill with chunk size 512; not a Nested WAIT-style global threshold.
  - Nested WAIT calibration: empirical continuation probabilities from the workload and offered arrival rate.
  - Request-generator bins: 50 decode-length bins.
  - Nested WAIT grid: `tl in {40,60,...,300}`, `L in {1,2,3,4,5,10,20}`, `eta=0.05`.
  - Latency metric: main figures average over independent simulation replications; current runner records one run per config and trims completed-request latency with head/tail fractions.

Response-letter and state-doc posture:

- `papers/response_letter.tex` and `docs/paper_state/opre_revision/response_letter_claim_audit.md` claim the revision reports the calibration rule and finite grids, not a complete per-arrival-rate provenance table.
- `docs/paper_state/opre_revision/real_data_remeasurement_checklist.md` states that current SQL provenance is incomplete and must be rebuilt before stronger claims about the full Figure D grid.

## Canonical Runner

Use the paper-facing scaffold:

```bash
python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_20260503 \
  --mode all
```

By default the scaffold only prints the generated plan. Add `--execute` to run it:

```bash
python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_20260503 \
  --mode all \
  --execute
```

For incremental work:

```bash
python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_20260503 \
  --mode baselines \
  --execute

python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_20260503 \
  --mode wcp \
  --execute
```

The scaffold delegates to `scripts/real_data_provenance_rerun.py`, which handles resumable SQLite logging and skips cached rows for the same run tag unless `--force` is supplied.

The code is intentionally split as follows:

- `src/vidur_or_experiments/lmsys/config.py`: paper-facing Section 6 defaults.
- `src/vidur_or_experiments/lmsys/runner_command.py`: command generation only.
- `src/vidur_or_experiments/lmsys/database.py`: reproduction DB registry and summary views.
- `src/vidur_or_experiments/lmsys/provenance_runner.py`: resumable Vidur execution, result parsing, and raw provenance logging.
- `scripts/lmsys_section6_reproduction.py`: thin CLI aggregation entrypoint.
- `scripts/lmsys_db.py`: thin CLI aggregation entrypoint for database setup and summary.
- `scripts/real_data_provenance_rerun.py`: compatibility CLI entrypoint for the provenance runner.
- `docs/sql/lmsys_reproduction_schema.sql`: SQL copy of the DB objects created by the Python database helper.

## Fixed Paper-Facing Defaults

- `model_name = meta-llama/Llama-2-7b-hf`
- `db_path = outputs/databases/lmsys_section6_reproduction.db`
- `device = a100`
- `memory_margin_fraction = 0.1`
- `prediction_max_prefill_chunk_size = 16384`
- `prediction_max_batch_size = 2048`
- `prediction_max_tokens_per_request = 65536`
- `qps = 10,20,...,150`
- `nreq = 5000`
- `nbins = 50`
- `Sarathi chunks = 512,256`
- `Sarathi batch_size_cap = 1000000`
- `WCP chunk_size = 128`
- `tl = 40,60,...,300`
- `L = 1,2,3,4,5,10,20`
- `seg_margin eta = 0.05`
- `WAIT_CP_GATE = on`
- `wait_gate = on`
- `segment_priority = head`
- `latency trim = middle 50%` via `trim_head_frac=0.25`, `trim_tail_frac=0.25`

## Important Reproduction Checks

- The manuscript says Sarathi's `512` is a prefill chunk size. The scaffold therefore treats Sarathi256 and Sarathi512 as chunk-size baselines and sets a very large Sarathi batch cap so the baseline is governed by memory reservation rather than a Nested WAIT-style total-limit cap.
- The manuscript describes Nested WAIT as a threshold-waiting policy. The scaffold therefore uses `wait_gate=on`. Historical strong Figure-D-like runs often used `wait_gate=off`; those are diagnostic runs, not the default paper-text reproduction target.
- The manuscript does not expose WCP chunk size as a tuning dimension in the real-data paragraph. The scaffold fixes WCP `chunk_size=128` as an implementation default. If this fails to reproduce the plotted curve, the next audit step is to decide whether chunk size must be disclosed as a searched implementation parameter.
- `experiments.db` currently has a merge conflict after pull. Do not resolve the binary database by choosing one side until both the remote DB and local tuning DB are backed up or intentionally merged.

## Diagnostic Commands

Print the full paper grid without executing:

```bash
python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_20260503 \
  --mode all
```

Run a small smoke test:

```bash
python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_smoke_20260503 \
  --mode all \
  --qps 10 \
  --limit 5 \
  --execute
```

Run only qps 50/60/70 WCP under the paper-text grid:

```bash
python scripts/lmsys_section6_reproduction.py \
  --run-tag section6_lmsys_reproduction_20260503 \
  --mode wcp \
  --qps 50,60,70 \
  --execute
```
