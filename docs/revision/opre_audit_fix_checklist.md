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
- [x] `Self` Added Additional Experiments GPU implementation scope: the SGLang WAIT patch is a conservative hybrid approximation that preserves threshold-style admission near capacity and delegates lightly loaded states to the native scheduler.
- [x] `Self` A100/L20 clarification is resolved in Section 2.2 and the response letter: the old L20 profiling plot has been replaced by an A100 Llama-2-7B validation figure, and the Additional Experiments appendix reports A100/SGLang simulator and end-to-end validation.
- [x] `Self` Softened response-letter stability-boundary language: replaced claims that the boundary is directly visible/identified with latency-growth and completion-rate-saturation diagnostic language.
- [x] `Self` Checked response-letter figure/table references for fragile hard-coded numbers; no direct Figure/Table number references remain.
- [x] `Self` Softened remaining overstrong empirical-boundary language in the Introduction and Section 6, replacing `latency diverges/remains bounded` phrasing with latency-growth and completion-rate-saturation diagnostics.
- [x] `Proof` Appendix D / Theorem 1 latency scaling: separated terminal backlog, normalized throughput loss, and time-averaged backlog in the proof. The appendix now gives \(O((\zeta T)^{-1/2})\) for normalized throughput loss and \(O((\zeta T)^{1/2})\) for latency/TTFT at zero drift, with \(O((\zeta T)^{-1})\) and \(O(1)\) under strict slack.
- [x] `Discuss` Long-decode Table 1: author decision is to keep the current framing without emphasizing mixed memory settings further.
- [x] `Discuss` Real-data main claim strength: keep the lmsys result as observed-grid evidence rather than a sharp real-workload stability-boundary claim.
- [x] `Discuss` Real-data parameter placement: use a short main-text description rather than a table. Section 6 now states that real-data Nested WAIT partitions decode stages 0--500 into \(L\) equal-width segments, chooses \(L\in\{1,2,3,4,5,10,20\}\), chooses `tl` from `40,60,...,300`, and uses `\eta=0.05`; the old segment-count ablation remains commented out.
- [x] `Discuss` Extension segment-design claims: removed/qualified stale concrete claims such as `fixed prefill length 62`, `L=10`, `m=500`, and matching the full `m`-type algorithm from the active OPRE manuscript. The extension now states the general coarse-segmentation logic.
- [x] `Discuss` Proposition lower-bound exposition: keep the standard worst-case construction framing, i.e., `there exists an instance such that ...`; no need to rewrite the appendix proof into the illustrative single-type example.

## 1. Can Fix Directly Next

- [x] `Self` Final response-letter reference hygiene: avoid fragile hard-coded figure/table numbers where descriptive references are enough; recheck exact numbers only after final compile.
- [x] `Self` Global wording audit: search and qualify overstrong `exactly`, `optimal`, `best`, `throughout`, and `stability boundary` claims where they exceed the evidence.

## 2. Needs Author Discussion Before Editing

- [x] `Discuss` Decision-letter significance framing: approved and implemented the positioning that the contribution is policy-induced dimensionality reduction for a memory-growth control problem with restart feedback, not just pipeline filling / positive recurrence. Covered in the Introduction, theorem-interpretation paragraphs, and response-letter D.3.

## 3. Needs Data / Provenance

- [x] `Data` Real-data dataset summary: reconciled Section 6 text statistics with the plotted distribution and source CSV. The active paper now states that the lmsys distribution figure and sampling population use requests with both prefill and decode lengths below 500 tokens, with prefill mean/median `58.6/21`, decode mean/median `147.3/116`, about `31%` decode length at most 50, and about `14%` exceeding 300. The figure is regenerated by `scripts/plot_lmsys_distribution.py` from the same filter.
- [ ] `Data` Real-data parameter provenance: reconstruct from SQL/progress/scripts the actual per-rate `tl`, segment endpoints, segment count, segment budgets, `seg_margin`, arrival grid, number of requests, and replications used for Figure D / lmsys. Current recovered tuning grids: `tl` candidates approximately `40,60,...,300`; segment-count candidates `L in {1,2,3,4,5,10,20}` with equal-width partitions over decode stages 0--500; `\eta=0.05`. Active text reports this finite-grid calibration and does not report the old segment-count ablation. Smaller arrival rates may use fewer segments because admission delay is more costly in underloaded regimes; verify per-rate selected configs before strengthening reproducibility claims. 2026-05-02 SQL audit: `real_data_provenance_runs` contains 28 valid metric rows and 3 malformed historical rows; valid coverage is only QPS \(10,20,50,60\), so SQL still does not reconstruct the full Figure D grid. Use `real_data_provenance_valid` for future summaries.
- [x] `Data` Real-data robustness: resolved for the current submission by keeping the real-data claims at observed-tested-grid strength. The manuscript and response letter do not claim a sharp real-workload stability boundary or a complete per-rate provenance table. If the lmsys discussion is strengthened later, this item must reopen together with the per-rate provenance item above.
- [x] `Data` Experimental parameter reporting: resolved through Section 6 prose plus the Additional Experiments appendix rather than a new main-text table. Section 6 now states the model/hardware/simulator, memory cap, baseline settings, replication count, synthetic arrival grids, real-data sampling size, real-data arrival grid, and WAIT/Nested WAIT tuning grids. Appendix B reports SGLang/GPU parameters and the real-data GPU parameter table. A separate main-text table would duplicate this material and cost space.
- [x] `Data` Capacity / memory numbers: verified current paper-facing consistency. Section 6 reports the A100/Llama-2-7B KV-cache cap scale (\(\approx 1.37\times 10^5\) tokens) with citations and states that memory overflow triggers eviction/restart. Paper-facing text uses `system-wide batch-size cap` for \(\mathrm{tl}\), not memory capacity, and the old `tl=400/1000` real-data tuning values appear only in historical progress/provenance notes. Theory notation is aligned: \(C\) is physical capacity, \(M^*\) is the fluid-equilibrium memory requirement, \(M^\pi\) is base threshold memory, and \(M_{\mathrm{req}}^{(\zeta,\pi)}\) is the scaled-policy required memory. Exact per-rate real-data threshold vectors are intentionally not tabulated under the current conservative reproducibility posture.

## 4. Needs Proof / Theory Verification

- [x] `Proof` Appendix D / Theorem 1 latency scaling: verify normalized versus unnormalized queue/latency quantities. The audit flags a possible contradiction where a queue-normalized \(O(B^{-1/2})\) statement may have been written as latency scaling.
- [x] `Proof` Proposition 1 capacity cut: recast the proof as a service-capacity cut in `papers/Appendix.tex` and updated the main-text explanation in `papers/fluid.tex`. The proposition keeps the original boundary condition (`>=1`): strict overload follows from memory-dependent service alone, while equality is handled by the positive per-iteration overhead \(d_0\) and the finite-memory upper bound on batch size.
- [x] `Proof` Proposition 5 / unknown-output lower bound: kept the proposition-level statement and refined the appendix proof rather than downgrading the result. The proof now uses a two-type indistinguishability construction: prompts are identical until the first decode boundary, survivor counts have binomial fluctuations, and at \(C=M^*\) a non-predictive policy must either admit at the fluid scale and face constant overflow probability or reserve capacity and incur a constant throughput gap.
- [x] `Proof` Theorem 2 notation: verified current paper-facing notation. \(C\) is physical memory capacity, \(M^\pi\) is base threshold memory, and \(M_{\mathrm{req}}^{(\zeta,\pi)}\) is the scaled-policy required memory including the finite-horizon downstream safety buffer for Nested WAIT.
- [x] `Proof` Threshold integerization convention: added explicit integer-threshold conventions in the WAIT theorem discussion, Nested WAIT theorem discussion, and segment-design extension. Real-valued fluid or segment designs are rounded to feasible integer thresholds, with \(O(1)\) changes absorbed in the asymptotic constants.
- [x] `Proof` Nested WAIT memory accounting: rechecked after the no-prefill-resident clarification. The main theorem/proof distinguish Segment-1 external prefill queue, resident downstream boundary queues, threshold-sized segment interiors charged to \(M^\pi\), and logarithmic safety buffers charged to \(M_{\mathrm{req}}^{(\zeta,\pi)}\).

## 5. Final QA After Text/Figures Freeze

- [x] `Final QA` Recompile `papers/LLM_or.tex` and `papers/response_letter.tex`. Main paper compiles to 83 pages; response letter is up to date. Remaining messages are nonfatal locale/underfull/float/font warnings.
- [x] `Final QA` Re-run negative searches for stale phrases in current paper-facing source: `revision plan`, `holds exactly`, `stored in CPU`, `finite-horizon validation`, `Arrival rate QPS`, `Insert Date Here`, broad `batch-size range used in our experiments`, `threshold collection`, `in-flight limit`, `tl=400`, `tl=1000`, and `fluid stability benchmark`. No hits in active manuscript/response-letter sources.
- [x] `Final QA` Re-audit every response-letter sentence tied to Section 6 / Additional Experiments after the lmsys distribution and real-data calibration text changes. Current response letter matches the conservative manuscript posture: it reports Section 6 setup details, finite real-data tuning grids, A100 memory-cap calculation, simulator-to-GPU validation, and GPU-run parameter reporting without claiming a sharp lmsys stability boundary or a complete per-rate provenance table.
- [x] `Final QA` Verify all figure captions match the generated PDFs, especially real-data and long-decode panels. Checked the active figure files referenced by `model.tex`, `numerical.tex`, and `appendix_b_additional.tex`, including the A100 validation figure, single/two-type/long-decode/lmsys panels, lmsys length distribution, simulator calibration, SGLang GPU panels, wait-versus-threshold-only figure, repeated-run table, and PD-disaggregated figure. Patched response-letter wording so the old L20 profiling plot is described as replaced by an A100 figure using the same GPU model as the main Vidur configuration.
- [x] `Final QA` Verify all appendix references and labels after moving Extension and Notation appendices. Checked the current LaTeX logs for undefined references/citations and rechecked labels for Extensions, Notation Summary, Additional Experiments, GPU validation, PD disaggregation, and proof appendix inputs; no unresolved appendix-reference issue was found.
- [x] `Final QA` Do one PDF proofread for appendix prose, line breaks, undefined labels, and table alignment. Extracted text from the compiled main paper and response letter and searched for unresolved markers, placeholders, stale experimental terms, old parameter values, and old appendix-number phrasing. No unresolved `??`, undefined-reference output, stale `tl=400/1000`, or old placeholder text was found in the compiled PDFs. LaTeX logs contain only nonfatal underfull/float-placement warnings.
