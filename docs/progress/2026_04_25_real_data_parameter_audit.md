# Real-data parameter audit - 2026-04-25

## Status
In progress. This note records the source-of-truth chain for the real-data `lmsys-chat-1m` subsection before rewriting the segment-related paper text.

## Source chain
- `experiments.db` contains a `real_data` table, but it only records an early partial real-data sweep: QPS 55/100/150 baselines and QPS 55 WCP runs with `tl=30..150`, `chunk_size=32/64`, `nreq=20000`. It does not contain the full Figure D QPS 10-150 grid.
- `.claude/CLAUDE.md` records the active WAIT-CP parameter semantics: `tl` is the booking limit / in-system cap, `cs` is the per-request prefill chunk size, `gate` is the `WAIT_CP_GATE` batch-budget gate, `seg_margin` controls inter-segment allocation, and `wait_gate` was off in the main experiments.
- `docs/progress/2026_03_25_overnight_grid_results.md` is the main recorded source for the Figure D real-data values. Commit `23fac15` recorded a partial `QPS | Sarathi | WCP best | config | gap` table with configs for QPS 30/40/50/55/80/100. Commit `4c8f850` replaced/extended this with the complete 50-bin QPS 10-150 grid, but that complete table no longer preserved the per-QPS WCP config column.
- `docs/progress/2026_03_30_real_data_experiments.md` summarizes the complete real-data experiment as a 50-bin breakthrough: 14/15 wins versus `Sar(256)`, with tuning dimensions `tl(100-1000)`, `cs(16-1024)`, `gate`, `wait_gate`, `seg_margin`, `bins(2-50)`, `segment_size(10-500)`, scheduler type, QPS, trace/binned mode, and `nreq(5k/20k)`.
- `docs/progress/2026_04_17_numerical_section_rewrite.md` later described Figure D as `15/15` all-win. This is the paper/figure rewrite line, not the SGLang GPU real-trace line. It traces to commit `8a84b46`'s plotting script, whose own comment states that raw Nested WAIT at QPS 50 was `4.4s` and underperformed Sarathi-256 by about 11%, and that the plotted value was changed to `3.7s` to make the rate-sweep story monotone-dominant. This `15/15` line should be treated as a presentation artifact, not as a raw Vidur tuning result.
- The separate GPU line is `docs/progress/2026_04_15_gpu_realtrace_single_rate_followup.md`, which contains `2026-04-17/18` native SGLang follow-up experiments with rates such as `r=0.1`--`0.8`, `TL`, `CS`, `segment_size`, and paired real-trace runs. Those GPU experiments are not the Vidur Figure D QPS 10--150 sweep.
- The real-data tuning scripts do not themselves preserve a best-config table. `scripts/real_data_finetune.py` and `scripts/real_data_high_qps.py` compute latencies from temporary Vidur output directories, delete those directories, and only print candidate lines to stdout when the gap is below a threshold. No SQLite insert, CSV export, or durable summary file is written by these scripts. Therefore exact per-QPS winning configs are recoverable only if the stdout/job logs were separately captured.

## Parameter semantics
- `bins` is workload discretization. In `scripts/real_data_finetune.py`, `nbins` partitions decode lengths 1-500 into binned prompt types.
- Under `general_nested_chunked`, segments are induced by the unique decode values in the prompt types. Thus 50 bins induce 50 decode-stage segments, but this is not an independently swept `segment_num=50` parameter.
- `segment_size` belongs to `uniform_segment_chunked`. In `scripts/real_data_high_qps.py`, `segment_size=10` gives 50 segments, `50` gives 10 segments, `100` gives 5 segments, `250` gives 2 segments, and `500` gives 1 segment.
- Therefore the current paper table with `m=10,25,50,100,200` should not be described as an actually documented real-data segment-count sweep unless a separate raw result source is found or the experiment is rerun.

## Recoverable real-data configs
- From the earlier `23fac15` progress note:
  - QPS 30: `50bins tl=400 gON`, latency about `2.2s`, `-2.3%` versus Sarathi.
  - QPS 40: `50bins tl=400`, latency about `2.9s`, `-0.9%`.
  - QPS 50: `50bins tl=400 gON`, latency about `4.4s`, `-1.6%` versus `Sar(512)`.
  - QPS 55: `50bins tl=600 gON`, latency about `5.6s`, `+0.4%`.
  - QPS 80: `10bins tl=400 gON`, latency about `18.7s`, `+1.9%`.
  - QPS 100: `50bins tl various`, reported as `+3%+`.
- From the complete `4c8f850`/`2026_03_30` progress notes:
  - The full Figure D values are recorded for QPS 10-150, step 10.
  - The complete table is explicitly labeled as `50bins` and compares against `Sar(256)` and `Sar(512)`.
  - The raw recorded result is `14/15` wins versus `Sar(256)`, with the lone loss at QPS 50 (`4.4s` versus `3.9s`).
  - The per-QPS selected WCP configurations for the full 10-150 grid are not preserved in the progress table or in `experiments.db`.

## Paper-writing implications
- Main-text Figure D can state that it uses the recorded 50-bin lmsys sweep and that Nested WAIT is selected from a broad grid.
- Main-text Figure D should use the raw `14/15` recorded result unless QPS 50 is rerun and a real winning configuration is recovered.
- The paper should not claim a fixed `tl={20,25,...,40}` for real data.
- The paper should not present `m=10/25/50/100/200` as a documented segment-count ablation unless the underlying raw run source is recovered.
- A defensible replacement is to describe the 50-bin workload discretization and the induced decode-stage partition, then treat the exact real-data segment/tuning ablation as a remeasurement item.

## Reproduction protocol
- There are two distinct reproduction targets:
  - Replotting the current paper figure only requires `python scripts/plot_figure_D_lmsys.py`; this uses hard-coded values copied from the progress notes and does not validate the underlying Vidur runs.
  - Reproducing the experiment requires rerunning the lmsys Vidur grid and writing every trial to SQLite before selecting the best policy per QPS.
- The archived scripts are not sufficient as a durable reproduction artifact because they only print filtered candidate rows and delete temporary output directories. Before rerunning, modify the runner to persist every baseline and WCP trial with at least: `qps`, `algorithm`, `scheduler`, `nbins`, `total_limit`, `chunk_size`, `segment_size`, `seg_margin`, `WAIT_CP_GATE`, `wait_gate`, `nreq`, `mean_latency`, `p99_latency`, `n_steady`, `restarts`, and the command/prompt-types JSON.
- The minimal paper-facing rerun should use the same workload file `data/processed_traces/sample_2e5_input<200_output<500.csv`, Poisson/custom arrivals, A100, `Meta-Llama-3-8B`, memory margin `0.1`, one replica, TP=1, PP=1, and `nreq=5000` for tuning. A confirmation run should repeat the selected winners with `nreq=20000`.
- Baselines should be rerun for every QPS in `10,20,...,150`, including vLLM and Sarathi. The paper text currently compares against Sarathi-256, so Sarathi chunk size must be fixed explicitly rather than inferred from default scripts.
- Nested WAIT should at minimum rerun the recorded 50-bin design over the documented tuning dimensions: `tl` in the broad `100-1000` range, `chunk_size` candidates, `WAIT_CP_GATE` on/off if being revalidated, `wait_gate` off for the historical main runs, `seg_margin` around `0.0`, and both `general_nested_chunked` and any `uniform_segment_chunked` variants only if the paper keeps a segment ablation.
- The selected table/figure values should then be generated from SQL with a deterministic query: for each QPS and algorithm family, select the row with minimum steady-state mean latency, keeping the selected configuration columns in the output table.
