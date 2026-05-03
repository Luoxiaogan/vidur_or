# experiments.db Merge Record

## Context

After pulling `origin/revision` on 2026-05-03, `experiments.db` had a binary
merge conflict:

- Stage 1: pre-pull base.
- Stage 2: remote `origin/revision`.
- Stage 3: local stashed experiment database.

The merge was handled non-destructively by exporting all three stages before
choosing a final database.

## Backups

All intermediate databases are stored in:

`outputs/database_merges/20260503_experiments_db/`

Files:

- `base_experiments.db`: Git merge base.
- `remote_experiments.db`: remote version from `origin/revision`.
- `local_experiments.db`: local stashed version.
- `conflicted_worktree_experiments.db`: worktree conflict artifact before replacement.
- `merged_experiments.db`: final merged database copied to `experiments.db`.

## Merge Rule

The final DB uses `local_experiments.db` as the base because it contains the
larger local tuning provenance:

- `real_data_provenance_runs`: 8294 local rows.
- `real_data_selected_configs`: 36 local rows.
- `real_data_sarathi_baselines`: 8 local rows.

Then remote-only content was imported:

- Copied the remote `reproduction_configs` table with 6 rows.
- Inserted remote `real_data_provenance_runs` rows into the local-shaped table
  using `INSERT OR IGNORE` on the existing unique key:
  `(run_tag, qps, algorithm, config_name, scheduler_type, baseline_variant,
  nbins, total_limit, chunk_size, segment_size, seg_margin, wait_cp_gate,
  wait_gate, nreq)`.
- Remote rows do not have the local `model_name` column, so imported remote rows
  set `model_name = NULL`.

## Result

Final `experiments.db`:

- `PRAGMA integrity_check`: `ok`.
- `real_data_provenance_runs`: 9933 rows.
- `reproduction_configs`: 6 rows.
- `real_data_selected_configs`: 36 rows.
- `real_data_sarathi_baselines`: 8 rows.

The conflict was marked resolved with `git add experiments.db`.
