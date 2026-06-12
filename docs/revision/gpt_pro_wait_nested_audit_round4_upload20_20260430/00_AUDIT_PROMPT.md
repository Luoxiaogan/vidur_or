# GPT Pro Follow-Up Proof Audit Prompt: WAIT and Nested WAIT

You are acting as a mathematically adversarial proof auditor for an Operations Research / Management Science paper on online scheduling for LLM inference. This is a follow-up audit after several GPT-Pro proof-audit passes and local `$verify-proof` patches. Your task is to determine whether the current WAIT and Nested WAIT theorem statements, algorithms, proofs, memory accounting, and scaling conventions are now mathematically correct and internally consistent.

Please read the uploaded files in this folder. The most important files are:

1. `01_LLM_or_revised.pdf`: rendered revised paper.
2. `05_known_type_WAIT.tex`: WAIT algorithm and Theorem `thm:wait_heavy_traffic`.
3. `06_unknown_type_NestedWAIT.tex`: Nested WAIT algorithm and Theorem `thm:nested_wait_heavy_traffic`.
4. `08_pf_thm_WAIT.tex`: proof of WAIT theorem.
5. `09_pf_thm_NestedWAIT.tex`: proof of Nested WAIT theorem.
6. `10_pf_thm_timevarying.tex`: time-varying proof.
7. `11_pf_lemmas.tex`: auxiliary lemmas.
8. `03_model.tex`: model primitives, stage notation, memory, latency, TTFT, preemption, and eviction definitions.
9. `04_fluid.tex`: fluid model, ideal-fluid equilibrium, and memory requirement \(M^*\).
10. `07_extension.tex`: time-varying and general-segment extensions.
11. `12_appendix_notation.tex`: notation table.
12. `14_state_symbols.md`--`18_state_dependencies.md`: internal symbol and verification state.

## Background

The paper studies online scheduling for LLM inference under growing KV-cache memory. Requests wait outside the GPU before prefill, then become GPU-resident after admission. Once resident, their KV caches remain on GPU while they wait between iterations or at Nested WAIT boundaries unless they complete or are evicted. The paper proposes:

- **WAIT** for known output lengths/types: type-specific per-stage thresholds \(n_j\).
- **Nested WAIT** for unknown output lengths/types: segment-level thresholds \(n_k\), nested prefix scheduling, and downstream boundary queues controlled by binomial thinning.

The intended proof contribution is a dimensionality reduction: threshold policies convert a high-dimensional memory-coupled scheduling process into lower-dimensional threshold queues while preserving memory feasibility.

## Current Patch State To Verify

Please specifically verify the following current conventions and patches:

1. **WAIT batches all eligible types only when the server is idle.** Algorithm 1 defines \(J(t)=\{j:n_{j0}\ge n_j\}\), batches every \(j\in J(t)\) when no batch is in service, and stores selected counts \(a_{js}\) with the batch.
2. **WAIT comparison clock.** In the proof, \(B_\zeta(T)=\lfloor \zeta T/\Delta^\pi\rfloor\) is the number of deterministic full-threshold comparison slots, not the actual number of event-driven WAIT batches.
3. **WAIT resident memory.** Unselected resident decode prompts remain on GPU and count against memory. Prompts waiting outside GPU before prefill do not occupy KV-cache memory.
4. **Nested WAIT prefix structure.** Algorithm 2 forms a prefix batch \(1,\dots,k\) only when no batch is in service, stores selected counts, and completion advances exactly those selected prompts.
5. **Nested WAIT stage convention.** For \(k\ge2\), the resident boundary stage is \(s=l_{k-1}'\), and the threshold-controlled interior is \(s=l_{k-1}'+1,\dots,l_k'\). The prefix batch includes both the boundary stage and the interior stages for each selected segment.
6. **Nested WAIT resident memory.** Prompts paused at downstream boundaries or inside segments retain KV caches and count against GPU memory. Only the Segment-1 external prefill queue is nonresident.
7. **Nested WAIT post-review residual.** \(V^r_{(k)}\) is a post-review carryover residual, not a pre-review boundary queue. This convention is intended to support the tight downstream buffer \(n_k+\theta_k^{-1}\log(\cdot)\), rather than \(2n_k+\cdots\).
8. **Nested WAIT finite-horizon feasibility.** The physical no-overflow guarantee is finite-horizon and requires a logarithmic safety buffer depending on \(\zeta T\) and \(\delta\). It is not a fixed-buffer guarantee uniformly over arbitrarily growing horizons.
9. **Time-varying scaled windows.** The extension now defines
   \[
       \mathcal A_j^{(\zeta)}(t,h)
       =
       \zeta\int_t^{\min\{T,t+h/\zeta\}}\lambda_j^u\,du,
   \]
   where \(t\) is physical time and \(h\) is service-normalized length.
10. **Time-varying benchmark.** The theorem now defines
   \[
       \throughput_T^*=\frac{1}{T}\int_0^T\sum_j \lambda_j^t l_j'\,dt.
   \]
11. **Time-varying downstream probabilities.** The theorem now defines \(p_k^*\) as a supremum over scaled windows with positive denominator, sets \(p_k^*=0\) only for zero-downstream-input cases, and defines \(\theta_k\) directly from \(p_k^*\).
12. **Segment-design extension.** The first-segment condition is strict, and the theorem uses a finite-horizon logarithmic memory term with \(m(1+\zeta T/d_0)/\delta\).
13. **Time-varying no-long-lull condition.** The time-varying theorem now adds a no-long-lull condition for Segment 1: the service-normalized expected time to collect \(n_1\) external arrivals is uniformly bounded. This was added because scaled-window upper slack controls overload but does not by itself rule out long under-arrival lulls.

## Critical Conventions To Check

1. In the scaled system, arrival rates scale by \(\zeta\), processing times scale by \(1/\zeta\), and memory capacity is compared against the threshold memory requirement.
2. Throughput is normalized by \(\zeta T\).
3. The theorem-level latency and TTFT are service-normalized metrics:
   \[
       \Latency^{(\zeta,\pi)}=\zeta\Latency_{\rm cal}^{(\zeta,\pi)},\qquad
       \TTFT^{(\zeta,\pi)}=\zeta\TTFT_{\rm cal}^{(\zeta,\pi)}.
   \]
4. Stage \(s=0\) means prompts awaiting prefill. A prompt waiting outside the GPU before prefill has no resident KV cache. A prompt already admitted to the GPU but waiting between iterations or at a Nested WAIT boundary retains its KV cache and counts against memory.
5. Nested WAIT should remain a nested prefix policy, not a segment-independent policy.

## Task 1: WAIT Audit

Audit Theorem `thm:wait_heavy_traffic`, Algorithm 1, and `pf_thm_wait.tex`. Check:

1. Whether the theorem statement can remain unchanged.
2. Whether Algorithm 1 stores selected counts at batch formation and uses them consistently at completion.
3. Whether the resident-stage invariant \(N_{js}(t)\le n_j\) is valid and sufficient for memory feasibility.
4. Whether the periodic comparison policy is correctly constructed and used.
5. Whether the one-slot delayed dominance lemma is sufficient for entry starts, stage advancements, completions, throughput, latency, and TTFT.
6. Whether service-normalized delay conversion is consistent with the theorem rates.
7. Whether the server-idle guard and simultaneous stored-count completion update are sufficient to rule out overlapping batches and in-place double advancement.

## Task 2: Nested WAIT Audit

Audit Theorem `thm:nested_wait_heavy_traffic`, Algorithm 2, `pf_thm_nested.tex`, and `pf_lemmas.tex`. Focus especially on:

1. Whether Algorithm 2's prefix-batch completion logic is precise enough. In particular, does "advance by one service step" plus the surrounding boundary logic correctly handle selected boundary prompts at \(s=l_{k-1}'\)?
2. Whether the memory convention for nonresident Segment-1 queue versus resident downstream waiting prompts is clear and mathematically consistent.
3. Whether the segment-interior and boundary-stage conventions are consistent across algorithm, theorem, proof, and memory formula \(M^\pi\).
4. Whether the binomial thinning argument is valid under nonanticipativity and exchangeability of surviving prompts.
5. Whether the post-review carryover-residual convention rigorously supports the tight \(n_k+\theta_k^{-1}\log(\cdot)\) memory buffer.
6. Whether the high-probability memory bound correctly uses \(B_\zeta^{\max}\le 1+\zeta T/d_0\) and the reflected-random-walk excursion bound.
7. Whether the no-overflow expected performance guarantees are properly separated from the high-probability physical feasibility guarantee.

If you believe the tight buffer is valid, explain exactly why. If you believe a \(2n_k+\cdots\) buffer is still necessary, give a precise counterargument under the current post-review convention.

## Task 3: Extension Consistency

Audit `extension.tex` and `pf_thm_timevarying.tex`:

1. Does the segment-design extension now use strict first-segment slack where needed?
2. Does the theorem's rate match the stated drift conditions?
3. Does the time-varying theorem use a dimensionally correct scaled-window definition?
4. Does the time-varying proof use the same post-review residual convention as the main Nested WAIT proof?
5. Is the worst-case thinning domination valid for cohorts pooled across multiple time intervals?
6. Is the \(p_k^*\) definition self-contained and compatible with the \(\theta_k\) root and lower bound?
7. Is \(p_k^*\) being \(\zeta\)-dependent a problem for the theorem statement, or is it acceptable under the finite-horizon scaled system?
8. Is using \(m\) rather than \(L\) in the segment-design log term acceptable as a conservative union-bound factor?
9. Does the new no-long-lull condition correctly fix the time-varying delay claim, or does the theorem/proof still need a different delay qualification?

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
