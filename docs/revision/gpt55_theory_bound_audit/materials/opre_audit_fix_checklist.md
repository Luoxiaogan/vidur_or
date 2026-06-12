# OPRE Revision Audit Fix Checklist

Date: 2026-04-28

Sources:
- `docs/revision/opre_revision_audit.md`
- `docs/revision/deep-research-report (1).md`

Purpose: merged action checklist for the revised manuscript and response letter. Tags:
- `Self`: safe for Codex to edit directly.
- `Discuss`: author decision needed before editing.
- `Data`: requires SQL/progress/experiment provenance.
- `Proof`: requires mathematical/proof-level verification.
- `Final QA`: should be checked after all figures/text freeze.

## 0. Completed Fixes

- [x] `Self` Title consistency: manuscript title, running title, and response-letter title use `Fluid-Guided Online Scheduling with Memory Constraints`.
- [x] `Self` Removed response-letter internal process language (`revision plan`) and replaced it with reviewer-facing dimensionality-reduction language.
- [x] `Self` Narrowed response-letter A100/SGLang validation scope from broad experiment-range wording to a single-type calibration grid plus separate end-to-end SGLang checks.
- [x] `Self` Softened PD-disaggregated wording from `holds exactly` to calibrated close approximation / especially appropriate decode-side model.
- [x] `Self` Replaced bibliography placeholder `Accessed: [Insert Date Here]` with `Accessed: 2026-04-28`.
- [x] `Self` Replaced Nested WAIT proof wording that suggested CPU storage with the correct statement: not-yet-prefilled prompts have no resident GPU KV cache.
- [x] `Self` Rewrote Algorithm 2 initialization range in explicit set notation.
- [x] `Self` Replaced response-letter `finite-horizon validation` wording with `long-horizon simulation validation`.
- [x] `Self` Clarified Proposition 3 as a worst-case lower bound; the following single-type example is now described as an illustration of the eviction-cascade mechanism.
- [x] `Self` Narrowed the Section 6 simulator-validation sentence to the specific single-type A100/SGLang calibration grid.
- [x] `Self` Added a Section 6 bridge sentence tying the numerical workloads to decode-side KV-cache growth and the affine iteration-time model's intended regime.
- [x] `Self` Updated the real-data figure axis labels from `Arrival rate QPS` to arrival-rate notation consistent with the text.
- [x] `Self` Softened the real-data result sentence from an unconditional `throughout the sweep` claim to `on the observed sweep`.
- [x] `Self` Response letter real-data tone now mirrors the manuscript's observed-sweep language and avoids claiming an exact real-data stability boundary.
- [x] `Self` Added a top-level response-letter model-scope sentence: single-GPU, decode-centered, recomputation-based eviction model.
- [x] `Self` Added/verified objective terminology distinguishing token-level effective throughput in theory from request-level effective completion rate in experiments.
- [x] `Self` Softened low-load wording in the introduction and numerical discussion; strong comparative language is reserved for near-capacity and overloaded regimes.
- [x] `Self` Added a Section 6 overload caveat: overloaded-regime latency is a finite-horizon diagnostic and completion-rate saturation shows failure to track offered load.
- [x] `Self` Added Appendix H GPU implementation scope: the SGLang WAIT patch is a conservative hybrid approximation that preserves threshold-style admission near capacity and delegates lightly loaded states to the native scheduler.
- [x] `Self` A100/L20 clarification already appears in Section 2.2: Figure 3 illustrates the L20 affine fit, while Appendix H reports A100/SGLang validation for the main simulations.
- [x] `Self` Softened response-letter stability-boundary language: replaced claims that the boundary is directly visible/identified with latency-growth and completion-rate-saturation diagnostic language.
- [x] `Self` Checked response-letter figure/table references for fragile hard-coded numbers; no direct Figure/Table number references remain.
- [x] `Self` Softened remaining overstrong empirical-boundary language in the Introduction and Section 6, replacing `latency diverges/remains bounded` phrasing with latency-growth and completion-rate-saturation diagnostics.
- [x] `Proof` Appendix D / Theorem 1 latency scaling: separated terminal backlog, normalized throughput loss, and time-averaged backlog in the proof. The appendix now gives \(O((\zeta T)^{-1/2})\) for normalized throughput loss and \(O((\zeta T)^{1/2})\) for latency/TTFT at zero drift, with \(O((\zeta T)^{-1})\) and \(O(1)\) under strict slack.
- [x] `Discuss` Long-decode Table 1: author decision is to keep the current framing without emphasizing mixed memory settings further.
- [x] `Discuss` Real-data main claim strength: keep the lmsys result as observed-grid evidence rather than a sharp real-workload stability-boundary claim.
- [x] `Discuss` Real-data parameter placement: use a short main-text description rather than a table. Section 6 now states that real-data Nested WAIT splits decode stages 0--500 into 10 equal-width segments and selects `tl` from `40,60,...,300`; the old segment-count ablation remains commented out.
- [x] `Discuss` Extension segment-design claims: removed/qualified stale concrete claims such as `fixed prefill length 62`, `L=10`, `m=500`, and matching the full `m`-type algorithm from the active OPRE manuscript. The extension now states the general coarse-segmentation logic.
- [x] `Discuss` Proposition lower-bound exposition: keep the standard worst-case construction framing, i.e., `there exists an instance such that ...`; no need to rewrite the appendix proof into the illustrative single-type example.

## 1. Can Fix Directly Next

- [x] `Self` Final response-letter reference hygiene: avoid fragile hard-coded figure/table numbers where descriptive references are enough; recheck exact numbers only after final compile.
- [x] `Self` Global wording audit: search and qualify overstrong `exactly`, `optimal`, `best`, `throughout`, and `stability boundary` claims where they exceed the evidence.

## 2. Needs Author Discussion Before Editing

- [ ] `Discuss` Reviewer 3 significance framing: approve one or two high-signal statements positioning the contribution as policy-induced dimensionality reduction for a memory-growth control problem with restart feedback, not just pipeline filling / positive recurrence.

## 3. Needs Data / Provenance

- [ ] `Data` Real-data dataset summary: reconcile Section 6 text statistics, plotted distribution statistics, and Appendix A.2 language. Produce one source-of-truth summary for sampled prefill/decode lengths.
- [ ] `Data` Real-data parameter provenance: reconstruct from SQL/progress/scripts the actual per-rate `tl`, segment endpoints, segment count, segment budgets, `seg_margin`, arrival grid, number of requests, and replications used for Figure D / lmsys. Current recovered tuning grids: `tl` candidates approximately `40,60,...,300`; segment-count candidates `m in {1,2,3,4,5,10,20}`. Active text uses 10 equal-width segments over decode stages 0--500 and does not report the old segment-count ablation. Smaller arrival rates may use fewer segments because admission delay is more costly in underloaded regimes; verify per-rate selected configs before strengthening reproducibility claims.
- [ ] `Data` Real-data robustness: either finish durable per-rate config reconstruction plus denser crossover, long-horizon, and seed-repeatability checks, or keep all claims explicitly as observed-sweep evidence.
- [ ] `Data` Experimental parameter table: build a compact reproducibility table for key figures/workloads, including workload, model, hardware/simulator, arrival grid, requests/replications, baseline settings, WAIT/Nested WAIT tuning parameters, and eviction semantics.
- [ ] `Data` Capacity / memory numbers: verify whether \(C\), \(M^*\), chunk size, total in-flight limit, and threshold vectors can be reported cleanly for each key experiment without overclaiming precision.

## 4. Needs Proof / Theory Verification

- [x] `Proof` Appendix D / Theorem 1 latency scaling: verify normalized versus unnormalized queue/latency quantities. The audit flags a possible contradiction where a queue-normalized \(O(B^{-1/2})\) statement may have been written as latency scaling.
- [ ] `Proof` Proposition 1 capacity cut: check whether the proof of the `under any scheduling policy` condition should be recast as a service-capacity cut rather than a balanced-policy argument.
- [ ] `Proof` Proposition 5 / unknown-output lower bound: decide whether to keep it as a proposition with a formal indistinguishability construction, or downgrade/phrase it as an observation if the proof remains informal.
- [ ] `Proof` Theorem 2 notation: replace memory \(M\) with capacity \(C\) where appropriate, while preserving the role of \(M^\pi\) as the threshold-induced memory requirement.
- [ ] `Proof` Threshold integerization convention: add a convention that algorithmic thresholds/budgets are rounded to integers and that the resulting \(O(1)\) change is absorbed in the asymptotic constants.
- [ ] `Proof` Nested WAIT memory accounting: recheck \(M^\pi\), prefill treatment, boundary queues, and safety-buffer terms after the recent clarification that prompts not yet admitted to prefill do not consume GPU KV-cache memory.

## 5. Final QA After Text/Figures Freeze

- [ ] `Final QA` Recompile `papers/LLM_or.tex` and `papers/response_letter.tex`.
- [ ] `Final QA` Re-run negative searches for stale phrases: `revision plan`, `holds exactly`, `stored in CPU`, `finite-horizon validation`, `Arrival rate QPS`, `Insert Date Here`, and broad `batch-size range used in our experiments`.
- [ ] `Final QA` Re-audit every response-letter sentence tied to Section 6 / Appendix H after any figure or numerical text change.
- [ ] `Final QA` Verify all figure captions match the generated PDFs, especially real-data and long-decode panels.
- [ ] `Final QA` Verify all appendix references and labels after moving Extension and Notation appendices.
- [ ] `Final QA` Do one PDF proofread for appendix prose, line breaks, undefined labels, and table alignment.
