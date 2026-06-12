# GPT Pro Proof Audit Prompt: WAIT and Nested WAIT

You are acting as a mathematically adversarial proof auditor for an Operations Research / Management Science paper on online scheduling for LLM inference. Your job is not to polish language first; your job is to verify whether the theorem statements, algorithms, proof reductions, stochastic bounds, memory accounting, and scaling conventions are mathematically correct and internally consistent.

Please read the uploaded files in this folder. The most important files are:

1. `papers/LLM_or.pdf`: full revised paper, for context and cross-checking theorem statements against the rendered version.
2. `papers/known_type.tex`: WAIT algorithm and Theorem `thm:wait_heavy_traffic`.
3. `papers/unknown_type.tex`: Nested WAIT algorithm and Theorem `thm:nested_wait_heavy_traffic`.
4. `papers/pf_thm_wait.tex`: proof of WAIT theorem.
5. `papers/pf_thm_nested.tex`: proof of Nested WAIT theorem.
6. `papers/pf_lemmas.tex`: auxiliary lemmas used by WAIT and Nested WAIT.
7. `papers/model.tex`: model primitives, stage notation, memory, latency, TTFT, and eviction definitions.
8. `papers/fluid.tex`: fluid model, ideal-fluid equilibrium, and memory requirement \(M^*\).
9. `papers/extension.tex` and `papers/pf_thm_timevarying.tex`: extensions that should remain consistent with the Nested WAIT proof.
10. `papers/appendix_notation.tex`: notation summary.
11. `docs/paper_state/opre_revision/symbols.md`: locked symbol definitions from the revision state.
12. `docs/paper_state/opre_revision/results.md` and `docs/paper_state/opre_revision/consistency_log.md`: current internal verification notes.

## Paper Context

The paper studies online scheduling for LLM inference under growing KV-cache memory. Requests arrive over time, enter prefill, and then advance one token per decode iteration. Resident KV caches count against GPU memory. If memory overflows, the serving system may evict and restart prompts, reducing useful completed service. The paper proposes:

- **WAIT** for known output lengths/types: type-specific per-stage thresholds \(n_j\).
- **Nested WAIT** for unknown output lengths/types: segment-level thresholds \(n_k\) and boundary queues controlled by binomial thinning.

The intended proof contribution is a dimensionality reduction: the threshold policy converts a high-dimensional memory-coupled scheduling process into lower-dimensional threshold queues while preserving memory feasibility.

## Critical Conventions To Check

Please explicitly check the following conventions against all relevant files:

1. In the scaled system, arrival rates scale by \(\zeta\), processing times scale by \(1/\zeta\), and memory capacity \(C\) is fixed.
2. Throughput is normalized by \(\zeta T\).
3. The theorem-level latency and TTFT are **service-normalized** metrics: \(\Latency^{(\zeta,\pi)}=\zeta\Latency_{\rm cal}^{(\zeta,\pi)}\) and \(\TTFT^{(\zeta,\pi)}=\zeta\TTFT_{\rm cal}^{(\zeta,\pi)}\). Therefore rates involving latency/TTFT should scale with \(\zeta T\), not \(T/\zeta\), in theorem statements.
4. Stage \(s=0\) means not-yet-prefilled prompts waiting outside the resident GPU KV-cache state. A prompt waiting for prefill should not consume GPU KV-cache memory.
5. Once a prompt is admitted and resident, its KV cache remains on GPU unless it completes or is evicted.

## Task 1: WAIT Proof Audit

Audit the proof of Theorem `thm:wait_heavy_traffic` in `known_type.tex` and `pf_thm_wait.tex`. Focus on:

1. The threshold condition \(\Delta T(n_{1:m}) \le n_j/\lambda_j\) and memory condition \(M^*\le M^\pi\le C\).
2. The definition of \(M^\pi\), including prefill allocation and all resident decode stages.
3. The resident-stage invariant \(N_{js}(t)\le n_j\).
4. The bound that any realized event-driven WAIT batch has processing time at most the full-threshold comparison slot length \(\Delta^\pi/\zeta\).
5. The periodic full-slot comparison policy \(\bar\pi\): verify that \(B_\zeta(T)=\lfloor \zeta T/\Delta^\pi\rfloor\) is clearly the number of deterministic comparison slots, not the actual number of event-driven WAIT batches.
6. The one-slot delayed comparison dominance lemma: check whether it is sufficient to transfer throughput, latency, and TTFT bounds from \(\bar\pi\) to actual event-driven WAIT, including resident stage advancements.
7. The throughput conversion from terminal backlog to normalized effective-throughput gap.
8. The latency/TTFT conversion from time-averaged backlog to service-normalized delay.
9. The single-type warm-up notation: verify that \(\lambda\) is not incorrectly reused as both an arrival rate and an expected per-batch arrival count. The current draft uses \(\tilde\lambda\) and \(\mu=\tilde\lambda\Delta T\) in the single-type warm-up.

Please state whether the WAIT theorem statement can remain unchanged. If not, identify the minimal theorem or proof correction.

## Task 2: Nested WAIT Proof Audit

Audit Theorem `thm:nested_wait_heavy_traffic` in `unknown_type.tex` and its proof in `pf_thm_nested.tex`. This is the most important part of the audit. Focus on whether the current proof rigorously supports the **tight high-probability memory bound** with buffer
\[
    n_k+\theta_k^{-1}\log(\cdot)
\]
rather than a looser
\[
    2n_k+\theta_k^{-1}\log(\cdot).
\]

Please check:

1. Algorithm-policy alignment: Nested WAIT should be a nested prefix policy. If a later segment is eligible, earlier segments in the prefix are also processed as appropriate. It should not silently become independent per-segment service.
2. Segment boundary convention: identify exactly which stages are included in segment interiors and which boundary queues are tracked separately. Check consistency between `unknown_type.tex`, Algorithm 2, `pf_thm_nested.tex`, and the memory formula \(M^\pi+\sum_{k\ge2}(l+l'_{k-1})c_k\).
3. Segment-1 entry queue: prompts waiting for segment 1 are not yet resident, so they do not occupy GPU KV-cache memory. Check the renewal/idle-time treatment.
4. Boundary thinning: when prompts cross from segment \(k-1\) to segment \(k\), verify that the binomial thinning with \(p_k=\Lambda_k/\Lambda_{k-1}\) is valid under the paper's type/revelation assumptions.
5. Boundary queue recursion: verify the current "carryover residual" convention. A newly surviving cohort from upstream may be charged to the upstream threshold cohort/base memory during the current opportunity, while only residual carryover across opportunities requires the extra \(c_k\) buffer. Is this convention rigorous enough to avoid the extra \(n_k\) in the high-probability memory buffer?
6. High-probability memory bound: verify the finite-horizon reflected-random-walk/excursion argument, Doob or martingale step, union bound over segment boundaries and opportunities, and the use of \(B_\zeta^{\max}\le 1+\zeta T/d_0\).
7. Performance guarantees: distinguish no-overflow process guarantees from physical-policy guarantees under a failure event. Check whether the theorem and proof properly separate expectation bounds from the \(1-\delta\) feasibility guarantee.
8. Service-normalized latency and TTFT: check that bounded expected queue lengths imply calendar-time delay \(O(1/\zeta)\) and service-normalized delay \(O(1)\).

If the tight memory bound is valid, explain why clearly. If it is not valid, give the smallest mathematically correct change, and first try to preserve the tight form before recommending the looser \(2n_k+\cdots\) buffer.

## Task 3: Extension Consistency

Check whether `extension.tex` and `pf_thm_timevarying.tex` remain consistent with the current Nested WAIT theorem and proof:

1. Do they use the same segment-boundary convention?
2. Do they use the same logarithmic memory buffer form and horizon term \(1+\zeta T/d_0\)?
3. Do their stated threshold conditions imply the same negative-drift or strict-slack requirements?
4. Are any stale formulas or older proof conventions still present?

## Output Format

Return a structured audit with the following sections:

1. **Overall Verdict**: one of `Pass`, `Pass with minor edits`, `Requires proof clarification`, or `Requires theorem/proof correction`.
2. **WAIT Findings**: each finding should include `Location`, `Severity` (`critical`, `warning`, `minor`), `Issue`, `Why it matters`, and `Suggested fix`.
3. **Nested WAIT Findings**: same format.
4. **Extension Consistency Findings**: same format.
5. **Tight Memory Bound Verdict**: explicitly answer whether the current Nested WAIT proof supports the tighter \(n_k+\theta_k^{-1}\log(\cdot)\) buffer. Give the exact reasoning or counterexample.
6. **Minimal Patch Plan**: list the smallest changes needed to make the paper proof-correct.

Please be adversarial. Do not assume the proof is correct just because the theorem statement is plausible. At the same time, do not recommend loosening the theorem unless a real mathematical gap requires it.
