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
  - `system-wide batch-size cap` for `\mathrm{tl}`, `segment-level cap` for `B_k=\Delta l'_k n_k`, and `per-stage threshold` for stage-level controls
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
  - `fluid model` for the average-flow approximation
  - `fluid equilibrium` for the balanced operating point and stage distribution
  - `M^*` for the memory requirement needed to support that equilibrium
  - `realized stability region` for policy-specific or experiment-facing stability comparisons
- Updated `symbols.md`, `framing.md`, `overview.md`, and `changelog.md` accordingly.
- Continued the Section 5 Nested WAIT polish pass.
- Confirmed this edit round changed prose and figure captions only:
  - no theorem/result statements were changed
  - no figure/table labels were added or removed
  - no new mathematical symbols were introduced
- Locked the Section 5 narrative direction: `Algorithm Overview` now starts from the unknown-output-length example, then abstracts to segment-boundary revelation, segment-level coupling, and a logarithmic safety buffer for boundary queues.

## 2026-04-29

- Ran `$verify-proof` on Theorem `thm:nested_wait_heavy_traffic` and its Appendix proof.
- Confirmed the theorem statement remains unchanged:
  - Algorithm `alg:nested_wait` still uses nested prefix waiting, not independent segment service.
  - The memory condition keeps the tighter downstream boundary buffer `n_k+\theta_k^{-1}\log(\cdot)`.
  - Delay metrics use the service-normalized convention recorded in the known-type section.
- Fixed one proof issue found during verification:
  - The high-probability memory step had used the shortcut `V^r <= n_k + max_i S_i`, which is not valid for a reflected random walk after a downward excursion.
  - The proof now uses a finite-horizon Lindley/reflected-random-walk excursion bound with the same `log(1+\zeta T/d_0)` factor.
- Confirmed the deterministic `n_k` boundary term is absorbed by the base memory scale because `n_k<n_{k-1}` and the corresponding boundary-stage memory is already represented in `M^\pi`.
- Ran `$verify-proof` on Theorem `thm:wait_heavy_traffic` and Appendix `appexidx::proof of wait_heavy_traffic`.
- Confirmed the WAIT theorem statement remains unchanged:
  - the nonpositive-drift rate is `O((\zeta T)^(-1/2))` for normalized throughput and `O((\zeta T)^(1/2))` for service-normalized delay;
  - the strict-slack rate is `O(1/(\zeta T))` for normalized throughput and `O(1)` for service-normalized delay.
- Fixed one notation issue:
  - the single-type warm-up no longer redefines `\lambda` as expected arrivals per batch;
  - it now uses `\tilde{\lambda}` for continuous arrival rate, `\mu=\tilde{\lambda}\Delta T` for expected arrivals per batch, and the critical condition `\mu=n`.
- Confirmed the multi-type proof uses the deterministic full-threshold comparison clock only as a conservative comparison process, not as the actual event-driven WAIT batch count.
- Applied the second GPT-Pro proof-audit corrections.
- Confirmed the main WAIT and Nested WAIT theorem statements remain unchanged.
- Locked the memory convention requested by reviewers:
  - prompts waiting before prefill are outside the GPU-resident KV-cache state;
  - prompts already admitted to the GPU but waiting between decode iterations or at Nested WAIT boundaries retain their KV caches and count against memory.
- Confirmed Nested WAIT remains a nested prefix policy in Algorithm `alg:nested_wait`.
- Confirmed the tight downstream memory buffer remains `n_k+\theta_k^{-1}\log(\cdot)` by using the post-review carryover-residual convention.
- Corrected the segment-design extension's first-segment condition to strict slack, matching its `O((\zeta T)^(-1))` throughput and `O(1)` service-normalized delay claims.
- Applied the remaining second-round proof-audit clarifications.
- Locked the algorithmic convention that WAIT batches all eligible types at a decision epoch and stores the selected counts until completion.
- Locked the Nested WAIT convention that a prefix batch includes each selected downstream segment's resident boundary stage and interior stages; completion advances the stored selected counts, not queue lengths observed later.
- Locked the time-varying extension convention:
  - time `t` is physical time;
  - a service-normalized batch length `h` corresponds to physical duration `h/\zeta`;
  - scaled-window expected arrivals are denoted `\mathcal A_j^{(\zeta)}(t,h)=\zeta\int_t^{t+h/\zeta}\lambda_j^u\,du`;
  - the time-varying benchmark is `\throughput_T^*=(1/T)\int_0^T\sum_j\lambda_j^t l'_j\,dt`.
- Ran `$verify-proof` after the second-round proof patches.
- Confirmed the main WAIT theorem remains consistent with Algorithm `alg:wait` and Appendix D:
  - Algorithm `alg:wait` batches all eligible types and stores selected counts;
  - the proof's comparison index is deterministic comparison slots, not realized WAIT batches;
  - resident decode-stage prompts waiting on GPU remain included in the memory invariant.
- Confirmed the main Nested WAIT theorem keeps the tight downstream boundary buffer `n_k+\theta_k^{-1}\log(\cdot)`:
  - `V^r_{(k)}` is post-review carryover residual;
  - selected boundary cohorts are charged to `M^\pi`;
  - fresh survivors are treated as next-review input rather than requiring a `2n_k` buffer.
- Refined the time-varying extension convention:
  - `\mathcal A_j^{(\zeta)}(t,h)` now truncates the final partial window at `T`;
  - `p_k^*` and its root `\theta_k` are defined in the theorem text;
  - segments with `p_k^*=0` have no stochastic downstream input and can be omitted or merged.

## 2026-04-30

- Applied the latest GPT-Pro proof-audit clarifications.
- Locked the single-GPU event-loop convention:
  - Algorithms `alg:wait` and `alg:nested_wait` only launch a new batch when the server is idle;
  - arrivals during an active batch update queues but do not create overlapping batches;
  - completion updates use the selected counts stored at batch formation and are simultaneous.
- Locked the Nested WAIT completion convention:
  - selected downstream entry-boundary prompts move to the first interior stage;
  - selected interior prompts advance one stage;
  - selected terminal-boundary prompts either complete or move to the next resident boundary after output-length revelation.
- Corrected the time-varying extension's delay assumptions:
  - the scaled-window upper-slack condition controls overload;
  - the additional no-long-lull condition controls under-arrival waiting at Segment 1;
  - without this condition, an `O(1)` physical lull would become `O(\zeta)` in service-normalized delay.
- Ran a response-letter and paper consistency check:
  - patched residual `effective throughput` wording so the main text uses token-level completed decode service net of eviction, while Section 6 uses request-level effective completion rate for figures;
  - patched response-letter wording so `M^*` is a memory requirement, not an equilibrium memory level;
  - patched the segment-design appendix so `M^\pi` is described as base threshold-batch memory, not the fluid memory requirement;
  - patched the advisor review-comment digest so it refers to the review team without committing to a referee-count convention.
- Corrected the real-data Nested WAIT calibration narrative: `\mathrm{tl}` and segment count `L` are now described as finite-grid tradeoffs rather than monotone improvements, with too-large caps risking overflow pressure and too-large segment counts fragmenting caps and increasing threshold waiting.
- Ran a `paper-pipeline quick/status` maintenance pass:
  - LaTeX logs for the main paper, response letter, and organized advisor comments contain no undefined references/citations and no overfull hbox warnings;
  - synchronized `figures_tables.md` and `cross_references.md` with the current figure/table labels, including Appendix B additions and the commented-out real-data segment-ablation table;
  - updated framing and review-response state docs to remove stale third-referee and old effective-throughput wording;
  - updated the real-data remeasurement checklist to use the current `L \in \{1,2,3,4,5,10,20\}`, `\mathrm{tl}\in\{40,60,\ldots,300\}`, `\eta=0.05` paper-facing grid and to note that no segment-count ablation is active.
- Rechecked coverage against Reviewer 2's detailed items:
  - added `r2_detailed_items_checklist.md` for point-by-point internal QA;
  - replaced the old L20 inference-time validation with an A100 Llama-2-7B validation figure whose batch composition is explicit: \(28\) measured batch-size settings with \(B\) ranging from \(1\) to \(256\), input length \(256\), output length \(20\), and x-axis equal to batch KV-cache size;
  - confirmed the OOM/eviction distinction is explicit in the model: GPU-resident preempted prompts retain KV cache, while eviction discards KV cache and restarts from prefill;
  - kept the \(C\ge M^*\) response conservative by treating experiments as empirical underloaded / near-overloaded / overloaded diagnostics rather than direct proof of the theory condition;
  - kept the explicit batch-composition notation for Figure~`\ref{fig:batching_example}` as a Section 2 readability improvement, not as the original Figure 3 response;
  - added the missing `bari2025optimal` related-work citation.

## 2026-05-01

- Ran `$update-progress` and `$update-paper-state` after the latest theory/response consistency pass.
- Locked the memory notation used in the theory and response letter:
  - `C` denotes physical memory capacity;
  - `M^*` denotes the memory requirement for the fluid equilibrium;
  - `M^\pi` denotes the base threshold memory induced by a policy;
  - `M_{\mathrm{req}}^{(\zeta,\pi)}` denotes the physical memory required by the scaled policy, including any finite-horizon safety buffer.
- Confirmed the known-type WAIT section now states `M_{\mathrm{req}}^{(\zeta,\pi)}=M^\pi`, independent of `\zeta`.
- Confirmed the unknown-type Nested WAIT section now separates base threshold memory from the logarithmic downstream boundary safety buffer.
- Locked the response-letter interpretation of the `C\ge M^*` condition:
  - it is a fluid-model stabilizability condition;
  - the experiments test whether threshold-based online scheduling keeps the stochastic system in a stable operating regime under underloaded, near-overloaded, and overloaded regimes.
- Locked the real-data Nested WAIT calibration narrative:
  - `\mathrm{tl}` and segment count `L` are selected from finite grids;
  - the tradeoff is nonmonotone, because overly large caps can increase overflow pressure and overly fine segmentations can fragment caps and increase segment-threshold waiting.
- Confirmed the phrase `threshold collection` was removed from paper-facing source files and replaced with the more context-specific first-segment waiting language.
- Updated the real-data Nested WAIT grid to `\mathrm{tl}\in\{40,60,\ldots,300\}` and added a Section 6 memory-scale calculation: Llama-2-7B on A100~80\,GB leaves room for approximately `1.37e5` FP16 KV-cache tokens after model weights and the baseline `1%` memory margin.
- Continued the reviewer-point checklist pass:
  - synchronized state docs so `fluid stability region` is the locked phrase for the arrival-rate set defined by `M^*(\lambda)\le C`;
  - removed stale state-doc references to the old real-data grid `\{20,25,\ldots,40\}` and replaced them with the active `\mathrm{tl}\in\{40,60,\ldots,300\}`, `L\in\{1,2,3,4,5,10,20\}`, `\eta=0.05` calibration grid;
  - confirmed related-work / concurrent-paper positioning is covered in both the manuscript and response letter;
  - kept the lmsys real-data provenance item open but submission-safe under the current conservative claim strength.
- Reconciled the real-data dataset summary with the plotted lmsys distribution:
  - Figure~`\ref{fig:lmsys_distribution}` is based on requests with both prefill and decode lengths below `500` tokens;
  - the manuscript now reports prefill mean/median `58.6/21`, decode mean/median `147.3/116`, about `31%` decode length at most `50`, and about `14%` exceeding `300`;
  - the distribution figure is regenerated by `scripts/plot_lmsys_distribution.py` from `lmsys_chat_1m_dataset/output_trace/lmsys_chat_1m_dataset.csv` using the same `prefill<500, decode<500` filter as the text;
  - this closes the audit item about inconsistent Section 6 text versus distribution-figure statistics.
