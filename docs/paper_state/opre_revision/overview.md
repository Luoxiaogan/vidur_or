# OPRE Revision Overview

- Paper: `Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints`
- Venue: `Operations Research`
- Manuscript: `OPRE-2025-04-1885`
- Primary source: [papers/LLM_or.tex](/Users/ruicheng/Documents/GitHub/vidur_or/papers/LLM_or.tex:1)
- Main experiment section: [papers/numerical.tex](/Users/ruicheng/Documents/GitHub/vidur_or/papers/numerical.tex:1)

## Current Status

- Revision stage: major revision
- Current writing focus: final review-response consistency pass after the Section 2--6 and appendix proof/numerical revisions.
- Current technical focus: preserve claim strength while checking each reviewer point against the revised paper and response letter.

## Active Decisions

- Section 6 opening paragraph should contextualize vLLM and Sarathi as `two widely used open-source LLM inference servers`.
- Section 6 diagnostic paragraph should avoid the bare phrase `open system` at the opener.
- When describing eviction in experiments prose, state the mechanism concretely:
  - eviction is last-in-first-out
  - an evicted request restarts from the beginning if admitted again
- Vidur validation citations in Section 6 should retain quantitative evidence rather than vague phrases such as `prior work shows`.
- The Section 6 WAIT / Nested WAIT setup paragraph should describe `\mathrm{tl}` as a system-wide batch-size cap and then explain how it induces segment-level caps and per-stage thresholds.
- In the real-workload setup, write the Nested WAIT calibration grid as `\mathrm{tl}\in\{40,60,\ldots,300\}`, `L\in\{1,2,3,4,5,10,20\}`, and `\eta=0.05`.
- In Section 6, use `inventory` for realized counts, `system-wide batch-size cap` for `\mathrm{tl}`, `segment-level cap` for `B_k=\Delta l'_k n_k`, and `per-stage threshold` for the derived scheduling thresholds; avoid the phrases `in-flight limit` and `admission threshold` for `\mathrm{tl}`.
- Real-data Nested WAIT calibration should be described as a finite-grid tradeoff, not as monotone improvement in `\mathrm{tl}` or segment count `L`: overly small caps/segments underuse control resolution, while overly large caps/segments increase overflow pressure or make prompts wait at segment thresholds too often.
- In Section 6, use `arrival rate \lambda` consistently rather than alternating between `rate` and `QPS`; add `requests per second` only as a unit clarification.
- In Section 6, refer to the two-type synthetic workload by its explicit tuple rather than by the shorthand label `W3`.
- In Section 6, explain vLLM and Sarathi as FCFS-based baselines that share a local capacity-reservation rule before admission. Describe the rule by its OR role: it reserves a small KV-cache buffer before admitting a new request, but it is not a dynamic limit on the total number of jobs in service.
- When distinguishing Sarathi from vLLM, state that Sarathi's chunked-prefill rule interleaves partial prefill with decode work and reduces head-of-line blocking from long prefills. Do not imply that chunked prefill controls the cumulative decode-side population.
- For the prefill-decode-disaggregated appendix experiment, state that Vidur uses a decode-only request generator with post-prefill context length `630` and decode length `20` (`p630d20`). In that setting, Sarathi's chunked-prefill rule no longer changes the scheduling decision, so the baseline is reported as vLLM's PD scheduler.
- The repeated-run appendix table is aligned with the main figure-facing near-boundary latency ordering and its reproduction configurations are recorded in `experiments.db.reproduction_configs` under `run_tag='section6_reproduction_20260426'`.
- The extension material is appendix-only in the OPRE manuscript. Main-body pointers should cite `Appendix~\ref{sec:extension}` rather than `Section~\ref{sec:extension}`.
- The model section should introduce symbols narratively as they arise; the consolidated notation table is appendix-only and referenced as Table~`\ref{tab:notation}` in Appendix~`\ref{app:notation}`.
- The theory/framing terminology is now split as follows:
  - `fluid model` = the average-flow approximation
  - `fluid equilibrium` = the balanced operating point and its stage distribution
  - `M^*` = the memory requirement needed to support that equilibrium
  - `fluid stability region` = theoretical arrival-rate set defined by `M^*(\lambda)\le C`
  - `realized stability region` = policy-specific or experiment-facing stable arrival-rate range

## Next Pipeline Step

- Before finalizing camera-ready numerical claims, resolve the remaining lmsys real-data provenance items in [real_data_remeasurement_checklist.md](/Users/ruicheng/GitHub/vidur_or/docs/paper_state/opre_revision/real_data_remeasurement_checklist.md:1), especially exact per-arrival Nested WAIT configs and durable Figure D source data.
- Under the current manuscript wording, the unresolved lmsys provenance item is not blocking submission because the paper reports the calibration rule and finite grids rather than a full per-arrival configuration table or a sharp real-data stability-boundary estimate. It becomes blocking only if the paper later makes a stronger per-rate provenance or exact boundary claim.
- If exact repeated-run reproducibility is required, regenerate the repeated-run table from durable rows keyed to `section6_reproduction_20260426` rather than relying on mixed historical rows.
- After any `.tex` edit, update `changelog.md` and any affected state files.
