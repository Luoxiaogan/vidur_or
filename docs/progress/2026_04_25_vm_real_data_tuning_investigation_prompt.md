# VM investigation prompt: real-data tuning provenance

Use this prompt on the VM where the original Vidur real-data tuning runs were executed.

## Goal

Recover the exact provenance of the paper-facing real-data lmsys Nested WAIT results:

- Which model was used in the Vidur tuning runs: `meta-llama/Meta-Llama-3-8B` or Llama-2-7B?
- For each QPS in the paper grid (`10,20,...,150`), what was the selected Nested WAIT configuration?
- Which baseline was used for the reported comparison: Sarathi-256, Sarathi-512, or both?
- Were the plotted Figure D values produced from raw Vidur runs, progress-note summaries, or manually edited arrays?
- Is there any stdout/job log that records the missing per-QPS winning configs?

Do not rewrite paper text. Only inspect files, logs, SQL, shell history, and run lightweight queries. If reruns are necessary, produce a rerun plan first rather than running the full grid.

## Repository and branch

Start from the VM repository, likely:

```bash
cd /persistent/vidur_or
git status --short
git branch --show-current
git log --oneline --decorate -n 20
```

Record the branch and commit hash before inspecting results.

## First-pass source audit

Inspect the exact scripts and historical commits:

```bash
rg -n "replica_config_model_name|Meta-Llama-3|Llama-2|Llama-3|Sarathi256|Sarathi512|chunk_size|50bins|bins|segment_size|QPS" \
  scripts/real_data_finetune.py \
  scripts/real_data_high_qps.py \
  scripts/plot_figure_D_lmsys.py \
  docs/progress/2026_03_25_overnight_grid_results.md \
  docs/progress/2026_03_30_real_data_experiments.md \
  docs/progress/2026_04_17_numerical_section_rewrite.md

git log --oneline -- scripts/real_data_finetune.py scripts/real_data_high_qps.py scripts/plot_figure_D_lmsys.py docs/progress/2026_03_25_overnight_grid_results.md docs/progress/2026_03_30_real_data_experiments.md

git grep -n "replica_config_model_name" \
  $(git rev-list --all -- scripts/real_data_finetune.py scripts/real_data_high_qps.py) -- \
  scripts/real_data_finetune.py scripts/real_data_high_qps.py
```

Answer explicitly whether the tuning scripts ever used Llama-2-7B, or whether they always used `meta-llama/Meta-Llama-3-8B`.

## SQLite audit

Find all local SQLite databases and inspect real-data tables:

```bash
find . -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print

for db in $(find . -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \)); do
  echo "==== $db"
  sqlite3 "$db" ".tables"
  sqlite3 "$db" "SELECT name, sql FROM sqlite_master WHERE type='table' AND (name LIKE '%real%' OR name LIKE '%lmsys%' OR name LIKE '%tuning%' OR name LIKE '%sweep%') ORDER BY name;"
done
```

For any promising table, print schema, row counts, distinct QPS/rates, algorithms, and best rows:

```bash
sqlite3 -header -column experiments.db "PRAGMA table_info(real_data);"
sqlite3 -header -column experiments.db "SELECT qps, algorithm, COUNT(*) rows, MIN(mean_latency) best_lat, MAX(mean_latency) worst_lat FROM real_data GROUP BY qps, algorithm ORDER BY qps, algorithm;"
sqlite3 -header -column experiments.db "SELECT * FROM real_data ORDER BY qps, algorithm, mean_latency LIMIT 200;"
```

If another DB has fuller real-data tuning results, extract a best-per-QPS table with all config columns.

## Log and artifact recovery

Search for captured stdout/job logs from the original tuning scripts:

```bash
find . /persistent /tmp -type f 2>/dev/null | rg -i "real_data|lmsys|finetune|high_qps|qps|50bins|vidur_rdf|vidur_hq2|slurm|nohup|stdout|stderr|screen|tmux|log|out$|err$"

rg -n "QPS=|bins tl=|auto50seg|seg tl=|WIN|Sar=|Sarathi|50 bins|50bins|tl=400|tl=600|tl various" \
  . /persistent 2>/dev/null
```

Also inspect shell history if available:

```bash
history | rg -i "real_data|finetune|high_qps|plot_figure_D|lmsys|nohup|tmux|screen|python"
rg -n "real_data_finetune|real_data_high_qps|plot_figure_D" ~/.bash_history ~/.zsh_history 2>/dev/null
```

If logs are found, recover the exact lines for each QPS, especially:

- QPS 10, 20, 30, 40, 50, 55, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150
- `nbins`
- `tl`
- `chunk_size`
- `WAIT_CP_GATE`
- `wait_gate`
- `seg_margin`
- scheduler type: `general_nested_chunked` or `uniform_segment_chunked`
- `segment_size` if applicable
- latency and gap

## Artifact directories

Check whether any temporary Vidur result directories survived:

```bash
find /tmp /persistent . -maxdepth 5 -type d 2>/dev/null | rg "vidur_rdf_|vidur_hq2_|real_data|lmsys|request_metrics"
find /tmp /persistent . -type f -name "request_metrics_*.csv" 2>/dev/null | rg "real|lmsys|rdf|hq2|vidur"
```

For surviving CSVs, compute mean latency over the last 75% of requests and total restarts:

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd

for p in Path(".").rglob("request_metrics_*.csv"):
    try:
        df = pd.read_csv(p)
    except Exception:
        continue
    if "request_e2e_time" not in df:
        continue
    s = df.iloc[len(df)//4:]
    restarts = int(s["num_restarts"].sum()) if "num_restarts" in s else None
    print(p, "n=", len(df), "steady=", len(s), "mean=", s["request_e2e_time"].mean(), "p99=", s["request_e2e_time"].quantile(0.99), "restarts=", restarts)
PY
```

## Required final output

Return a concise provenance report with these sections:

1. `Model`: exact model used by the paper-facing Vidur tuning scripts and evidence lines.
2. `Baselines`: Sarathi chunk size(s), vLLM settings, and whether Figure D compares to Sarathi-256 or Sarathi-512.
3. `Recovered per-QPS winners`: table with QPS, WCP latency, baseline latency, gap, `nbins`, scheduler, `tl`, `chunk_size`, `segment_size`, `WAIT_CP_GATE`, `wait_gate`, `seg_margin`, source file/log/SQL.
4. `Missing entries`: QPS values whose exact config cannot be recovered.
5. `Figure D provenance`: whether current plotted values are raw, copied from progress docs, or manually adjusted.
6. `Rerun plan`: smallest grid needed to fill missing configs, with SQL schema for durable logging.

Be explicit when something is not recoverable. Do not infer a winning config from the plotted latency unless a script/log/SQL row confirms it.
