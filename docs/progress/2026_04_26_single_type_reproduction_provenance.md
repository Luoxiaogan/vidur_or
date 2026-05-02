# Single-type reproduction provenance - 2026-04-26

## Status
In progress. This note records the source-of-truth configuration chain for the Section 6 single-type and near-boundary repeated-run results before further paper edits.

## Main figure data
- The paper-facing single-type figure uses the \texttt{p512d20} workload: prefill length \(512\), decode length \(20\), Poisson arrivals, and Vidur on a single A100 with `meta-llama/Meta-Llama-3-8B`.
- The canonical SQL rows are in `experiments.db`, table `experiments`, with `timestamp LIKE '%_full'`, `l0=512`, `l1=20`, `nreq=5000`.
- The canonical WAIT configuration is `general_nested_chunked`, `total_limit=21`, `chunk_size=256`, `WAIT_CP_GATE=on`, `wait_gate=false`, `seg_margin=0.0`, and `force_clear=true`.
- The canonical Sarathi baseline is `scheduler=sarathi`, `chunk_size=512`, `batch_size_cap=512`; the canonical vLLM baseline is `scheduler=vllm`.
- At \(\lambda=22\), the figure-level single-type rows are Sarathi \(1.853\) s, vLLM \(18.227\) s, WAIT \(1.025\) s. At \(\lambda=23\), they are Sarathi \(5.076\) s, vLLM \(26.783\) s, WAIT \(1.292\) s.

## Multi-type W3 figure data
- The W3 workload is \(0.7\,\texttt{p512d20}+0.3\,\texttt{p512d50}\).
- Figure C reads `experiments.db`, table `rate_sweep_perseg`, `workload='W3'`, and uses the minimum latency per algorithm and rate.
- At \(\lambda=22\), the figure-level rows are Sarathi \(4.059\) s, vLLM \(56.701\) s, Nested WAIT \(2.359\) s with config `cs128_tl30`.
- At \(\lambda=23\), the figure-level rows are Sarathi \(8.408\) s, vLLM \(80.251\) s, Nested WAIT \(5.664\) s with config `cs128_tl30`.

## Repeated-run table provenance
- `papers/appendix_b_additional.tex` reports a repeated-run robustness table for the near-boundary single-type and W3 configurations at \(\lambda\in\{22,23\}\).
- The diagnostic is intended to summarize sampling variability for the same policy configurations used in the main figures.
- The reproduction configurations are now recorded in `experiments.db.reproduction_configs` under `run_tag='section6_reproduction_20260426'`, with one row for each Figure B/C policy configuration.
- Any final camera-ready table should be regenerated from durable repeated-run rows keyed to the same `run_tag` if exact repeated-run provenance is required.

## Reproduction caveat
- Local reruns with the same scheduler parameters reproduced the relative WCP/Sarathi ordering but produced larger absolute latencies under a reduced prediction grid. For example, at \(\lambda=22\), fast local reruns gave Sarathi \(2.325\) s and WAIT \(1.317\) s, preserving a similar relative improvement but not the exact SQL seconds.
- The likely cause is execution-time predictor provenance: `RandomForestRegressor()` is not seeded, and the historical predictor cache is not recorded in SQL. Exact second-level reproduction therefore requires preserving or regenerating the original predictor cache/environment, while parameter-level reproduction is determined by the configs above.

## Follow-up
- If final exact reproducibility is required, add a durable rerun table with `run_tag`, command JSON, predictor config, random seed, sklearn version, and the generated predictor cache hash.
- Figure scripts should avoid unconstrained aggregation over all historical rows. Prefer explicit source rows such as `_full` for Figure B and the intended `rate_sweep_perseg` rows for Figure C.

---
**Author**: Codex + user collaboration
**Date**: 2026-04-26
