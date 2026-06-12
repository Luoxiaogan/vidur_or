# Consistency Log

## 2026-04-23

- Initialized paper-state tracking for the OPRE revision paper.
- Recorded locked Section 6 decisions before applying the next `.tex` edit.
- No figure/table labels were added or removed in this initialization step.
- Re-checked the active state docs after the latest Section 6 wording edits.
- Confirmed that this edit round changed prose/framing only:
  - no new symbols were introduced
  - no results/theorems changed
  - no figure/table/reference labels changed
- Recorded the current locked wording for the Section 6 `\mathrm{tl}` explanation in `overview.md` and `framing.md`.
- Promoted `fig:long_decode` from Appendix B into main-text Section 6 and synchronized the figure/reference registries accordingly.
- Ran a scoped `paper-pipeline` consistency pass on the active Section 6 files and locked the terminology split:
  - `inventory` for realized counts at a stage or segment
  - `in-flight limit` for caps implied by `\mathrm{tl}`
- Re-locked the real-data Section 6 exposition so that the body text distinguishes algorithmic segments from any workload discretization and avoids `bins` language in the paper-facing narrative.

## 2026-04-26

- Ran the `update-paper-state` synchronization after the latest Section 6 / Appendix B numerical edits.
- Confirmed this edit round changed prose, captions, appendix tables, and SQL provenance only:
  - no theorem/result statements were added or removed
  - no new math symbols were introduced
  - no figure or table labels were added or removed
- Locked the OR-facing baseline description:
  - vLLM and Sarathi are FCFS-based baselines in these Vidur experiments
  - both use a local capacity-reservation rule before admitting new requests
  - Sarathi's chunked-prefill rule reduces prefill blocking but does not impose a total in-service population cap
- Locked the Appendix B PD-disaggregation description:
  - the experiment uses Vidur's decode-only request generator
  - the workload is `p630d20` with post-prefill context length `630` and decode length `20`
  - Sarathi is not separately reported because chunked prefill does not change decisions in a decode-only setting
- Recorded that repeated-run reproduction configurations are stored in `experiments.db.reproduction_configs` under `run_tag='section6_reproduction_20260426'`.
- Moved `sec:extension` from the main-text sequence to the appendices in the OPRE manuscript.
- Confirmed the structural edit preserves the existing extension labels and updates main-body prose references from `Section~\ref{sec:extension}` to `Appendix~\ref{sec:extension}`.
- Added appendix-specific hyperref anchor names in `LLM_or.tex`; the post-edit compile has no duplicate destination warnings and no undefined references.
- Moved the notation table from Section 2 to Appendix `app:notation` while preserving the table label `tab:notation`.
- Confirmed the model section now references the notation table narratively and introduces the key symbols in the surrounding prose instead of opening with a standalone notation subsection.

## 2026-04-27

- Ran `update-paper-state` after the Section 2--5 terminology synchronization pass.
- Confirmed this edit round changed terminology/framing prose only:
  - no theorem/result statements were added or removed
  - no figure/table labels were added or removed
  - no new mathematical symbols were introduced
- Locked the four-way distinction now used across the paper:
  - `ideal fluid model` for the average-flow approximation
  - `ideal-fluid equilibrium` for the balanced operating point and stage distribution
  - `M^*` for the memory requirement needed to support that equilibrium
  - `realized stability region` for policy-specific or experiment-facing stability comparisons
- Updated `symbols.md`, `framing.md`, `overview.md`, and `changelog.md` accordingly.
- Continued the Section 5 Nested WAIT polish pass.
- Confirmed this edit round changed prose and figure captions only:
  - no theorem/result statements were changed
  - no figure/table labels were added or removed
  - no new mathematical symbols were introduced
- Locked the Section 5 narrative direction: `Algorithm Overview` now starts from the unknown-output-length example, then abstracts to segment-boundary revelation, segment-level coupling, and a logarithmic safety buffer for boundary queues.
