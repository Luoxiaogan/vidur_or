You are a mathematical proof reviewer for an Operations Research / queueing theory paper. I uploaded the revised paper PDF and the relevant LaTeX source files.

Please adversarially proofread the revised Nested WAIT proof, focusing on proof correctness rather than style. The theorem statement should remain as follows unless there is a genuine mathematical inconsistency:

- Nested WAIT handles unknown output lengths by using decode-stage segments. Segment 1 receives external arrivals; segment \(k\ge2\) receives prompts that survive boundary \(l_{k-1}'\).
- The threshold assumptions are
  \[
  \Delta T_{[1,\dots,m]}(n_1,\dots,n_m)<\frac{n_1}{\sum_{j=1}^m\lambda_j},
  \qquad
  p_k<\frac{n_k}{n_{k-1}}<1,\quad k=2,\dots,m,
  \]
  where \(p_k=(\sum_{j=k}^m\lambda_j)/(\sum_{j=k-1}^m\lambda_j)\).
- The theorem reports normalized throughput and service-normalized delay. In the paper, \(\Latency^{(\zeta,\pi)}=\zeta\Latency_{\rm cal}^{(\zeta,\pi)}\) and \(\TTFT^{(\zeta,\pi)}=\zeta\TTFT_{\rm cal}^{(\zeta,\pi)}\).
- The stated Nested WAIT guarantee is
  \[
  \throughput^*-\mathbb E[\throughput^{(\zeta,\pi)}]=O((\zeta T)^{-1}),
  \qquad
  \mathbb E[\Latency^{(\zeta,\pi)}],\mathbb E[\TTFT^{(\zeta,\pi)}]=O(1),
  \]
  with memory not exceeded with probability at least \(1-\delta\).
- The revised proof uses an actual realized-opportunity upper bound \(B_\zeta^{\max}\le 1+\zeta T/d_0\) for the high-probability memory union bound, rather than treating \(\lfloor \zeta T/(d_0+d_1M^\pi)\rfloor\) as an actual batch count.

Files to inspect:

- `source/model.tex`: metric definitions.
- `source/known_type.tex`: scaling and service-normalized delay convention.
- `source/unknown_type.tex`: Nested WAIT algorithm, assumptions, theorem statement, and memory condition.
- `source/pf_thm_nested.tex`: Appendix proof of the Nested WAIT theorem.
- `source/pf_lemmas.tex`: supporting coupling and martingale-root arguments.
- `source/extension.tex` and `source/pf_thm_timevarying.tex`: check only for consistency with the main Nested WAIT proof.
- `framing.md`: paper terminology constraints.

Please check the proof for:

1. Whether the entry-queue argument for segment 1 is correct, including the claim that not-yet-prefilled prompts do not occupy GPU KV-cache memory.
2. Whether the downstream boundary queue construction is rigorous: in each opportunity, at most \(n_{k-1}\) prompts cross from segment \(k-1\), and the number continuing to segment \(k\) is dominated by \(\mathrm{Binomial}(n_{k-1},p_k)\).
3. Whether the assumption \(p_k<n_k/n_{k-1}<1\) is sufficient and correctly aligned with the martingale-root existence proof. If the proof could handle \(n_k\ge n_{k-1}\) as a degenerate case, explain whether excluding it is acceptable or overly restrictive.
4. Whether the Lindley domination for downstream queues is stated with the correct indexing. Check that the opportunity index for segment \(k\) need not equal the global actual batch index.
5. Whether the throughput argument is rigorous enough: bounded expected entry and boundary queues imply \(O(1)\) terminal unfinished decode work, hence normalized throughput gap \(O((\zeta T)^{-1})\).
6. Whether the service-normalized latency and TTFT argument is correct: bounded time-average queue length in prompt count, physical rates scaled by \(\zeta\), physical delay \(O(1/\zeta)\), service-normalized delay \(O(1)\).
7. Whether the memory accounting is correct:
   \[
   M^\pi=\sum_{k=1}^m n_k(l+\bar s_k)\delta_k,
   \qquad
   M^\pi+\sum_{k=2}^m(l+l_{k-1}')c_k.
   \]
   In particular, check for off-by-one stage errors in \(\delta_1,\delta_k,\bar s_k\), and check whether resident boundary queues are double-counted or under-counted.
8. Whether the high-probability bound is correct: Doob's inequality, union bound over \(k=2,\dots,m\) and \(r\le B_\zeta^{\max}\), and the resulting log term \(\ln(m(1+\zeta T/d_0)/\delta)\).
9. Whether the time-varying and general-segment extension statements remain consistent after changing the threshold condition and memory log term.
10. Whether any proof step should be promoted to a named lemma for rigor, especially the binomial-thinning boundary-queue construction or the memory-accounting bound.

For each issue, use this format:

```
LOCATION:
SEVERITY: CRITICAL / WARNING / MINOR
ISSUE:
SUGGESTED FIX:
```

If a proof step requires a new lemma, state the lemma precisely. If the proof is acceptable modulo minor wording, say that explicitly. Do not spend time on generic language polishing unless it affects mathematical correctness.
