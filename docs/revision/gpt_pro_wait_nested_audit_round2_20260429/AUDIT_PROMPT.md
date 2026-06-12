# GPT Pro Second-Round Proof Audit Prompt: WAIT and Nested WAIT

You are acting as a mathematically adversarial proof auditor for an Operations Research / Management Science paper on online scheduling for LLM inference. This is a second-round audit after a prior GPT-Pro proof audit and subsequent patches. Your job is to verify whether the revised WAIT and Nested WAIT theorem statements, algorithms, proofs, memory accounting, and scaling conventions are now mathematically correct and internally consistent.

Please read the uploaded files in this folder. The most important files are:

1. `papers/LLM_or.pdf`: rendered revised paper.
2. `papers/known_type.tex`: WAIT algorithm and Theorem `thm:wait_heavy_traffic`.
3. `papers/unknown_type.tex`: Nested WAIT algorithm and Theorem `thm:nested_wait_heavy_traffic`.
4. `papers/pf_thm_wait.tex`: proof of WAIT theorem.
5. `papers/pf_thm_nested.tex`: proof of Nested WAIT theorem.
6. `papers/pf_lemmas.tex`: auxiliary lemmas.
7. `papers/model.tex`: model primitives, stage notation, memory, latency, TTFT, and eviction definitions.
8. `papers/fluid.tex`: fluid model, ideal-fluid equilibrium, and memory requirement \(M^*\).
9. `papers/extension.tex`: time-varying and general-segment extensions.
10. `papers/pf_thm_timevarying.tex`: time-varying proof.
11. `papers/appendix_notation.tex`: notation table.
12. `docs/paper_state/opre_revision/*.md`: internal symbol and verification state.

## Background

The paper studies online scheduling for LLM inference under growing KV-cache memory. Requests wait outside the GPU before prefill, then become GPU-resident after admission. Once resident, their KV caches remain on GPU while they wait between iterations unless they complete or are evicted. The paper proposes:

- **WAIT** for known output lengths/types: type-specific per-stage thresholds \(n_j\).
- **Nested WAIT** for unknown output lengths/types: segment-level thresholds \(n_k\), nested prefix scheduling, and downstream boundary queues controlled by binomial thinning.

The intended proof contribution is a dimensionality reduction: threshold policies convert a high-dimensional memory-coupled scheduling process into lower-dimensional threshold queues while preserving memory feasibility.

## Prior Audit Findings That Were Patched

Please specifically verify that the following prior issues are now resolved and that the patches did not introduce new problems:

1. **WAIT comparison clock**: \(B_\zeta(T)=\lfloor \zeta T/\Delta^\pi\rfloor\) must be the number of deterministic comparison slots, not actual event-driven WAIT batches.
2. **WAIT resident-stage memory**: unselected resident decode prompts remain on GPU and must be counted in memory; prompts waiting outside GPU before prefill do not occupy KV-cache memory.
3. **WAIT one-slot dominance**: the proof must transfer comparison-policy throughput/delay bounds back to actual event-driven WAIT, including resident-stage advancements and completions.
4. **Nested WAIT prefix structure**: Algorithm 2 should describe completion of a prefix batch \(1,\dots,k\), not independent service of a single segment.
5. **Nested WAIT resident memory convention**: prompts paused at downstream boundaries or inside segments retain KV caches and count against GPU memory; only Segment-1 external prefill queue is nonresident.
6. **Nested WAIT boundary residual**: \(V^r_{(k)}\) should be a post-review carryover residual. This convention is what supports the tight downstream buffer \(n_k+\theta_k^{-1}\log(\cdot)\) instead of \(2n_k+\cdots\).
7. **Nested WAIT finite-horizon feasibility**: the physical no-overflow guarantee is finite-horizon and requires a logarithmic safety buffer depending on \(\zeta T\) and \(\delta\). It is not a fixed-buffer guarantee uniformly over arbitrarily growing horizons.
8. **Segment-design extension**: the first-segment condition in `eq:nested_wait_thresholds_L` should be strict, not non-strict, because the claimed \(O((\zeta T)^{-1})\) throughput gap and \(O(1)\) service-normalized delay require negative drift.
9. **Time-varying extension**: the proof should inherit the post-review residual convention and should justify stochastic domination when a boundary cohort contains prompts accumulated over several intervals.

## Critical Conventions To Check

1. In the scaled system, arrival rates scale by \(\zeta\), processing times scale by \(1/\zeta\), and memory capacity is compared against the appropriate threshold memory requirement.
2. Throughput is normalized by \(\zeta T\).
3. The theorem-level latency and TTFT are service-normalized metrics: \(\Latency^{(\zeta,\pi)}=\zeta\Latency_{\rm cal}^{(\zeta,\pi)}\) and \(\TTFT^{(\zeta,\pi)}=\zeta\TTFT_{\rm cal}^{(\zeta,\pi)}\).
4. Stage \(s=0\) means prompts awaiting prefill. A prompt waiting outside the GPU before prefill has no resident KV cache. A prompt already admitted to the GPU but waiting between iterations or at a Nested WAIT boundary retains its KV cache and counts against memory.
5. Nested WAIT should remain a nested prefix policy, not a segment-independent policy.

## Task 1: WAIT Audit

Audit Theorem `thm:wait_heavy_traffic` and its proof. Check:

1. Whether the theorem statement can remain unchanged.
2. Whether Algorithm 1 stores selected counts at batch formation and uses them consistently at completion.
3. Whether the resident-stage invariant \(N_{js}(t)\le n_j\) is valid and sufficient for memory feasibility.
4. Whether the periodic comparison policy is correctly constructed and used.
5. Whether the one-slot delayed dominance lemma is sufficient for entry starts, stage advancements, completions, throughput, latency, and TTFT.
6. Whether service-normalized delay conversion is consistent with the theorem rates.

## Task 2: Nested WAIT Audit

Audit Theorem `thm:nested_wait_heavy_traffic`, Algorithm 2, and the proof. Focus especially on:

1. Whether Algorithm 2's prefix-batch completion logic matches the proof.
2. Whether the memory convention for nonresident Segment-1 queue versus resident downstream waiting prompts is clear and mathematically consistent.
3. Whether the segment-interior and boundary-stage conventions are consistent across algorithm, theorem, and proof.
4. Whether the binomial thinning argument is valid under nonanticipativity and exchangeability of surviving prompts.
5. Whether the post-review carryover-residual convention rigorously supports the tight \(n_k+\theta_k^{-1}\log(\cdot)\) memory buffer.
6. Whether the high-probability memory bound correctly uses \(B_\zeta^{\max}\le 1+\zeta T/d_0\) and the reflected-random-walk excursion bound.
7. Whether the no-overflow expected performance guarantees are properly separated from the high-probability physical feasibility guarantee.

If you believe the tight buffer is valid, explain exactly why. If you believe a \(2n_k+\cdots\) buffer is still necessary, give a precise counterargument under the current post-review convention.

## Task 3: Extension Consistency

Audit `extension.tex` and `pf_thm_timevarying.tex`:

1. Does the segment-design extension now use strict first-segment slack where needed?
2. Does the theorem's rate match the stated drift conditions?
3. Does the time-varying proof use the same post-review residual convention?
4. Is the worst-case thinning domination valid for cohorts pooled across multiple time intervals?
5. Is using \(m\) rather than \(L\) in the segment-design log term acceptable as a conservative union-bound factor?

## Output Format

Return a structured audit with:

1. **Overall Verdict**: `Pass`, `Pass with minor edits`, `Requires proof clarification`, or `Requires theorem/proof correction`.
2. **Resolved Prior Findings**: list which prior findings are now fixed and why.
3. **Remaining WAIT Findings**: each with `Location`, `Severity`, `Issue`, `Why it matters`, and `Suggested fix`.
4. **Remaining Nested WAIT Findings**: same format.
5. **Extension Consistency Findings**: same format.
6. **Tight Memory Bound Verdict**: explicitly answer whether the current proof supports \(n_k+\theta_k^{-1}\log(\cdot)\).
7. **Minimal Patch Plan**: only if any correction remains.

Be adversarial. Do not assume the proof is correct. Also do not recommend weakening theorem statements unless there is a concrete mathematical gap under the current definitions.
