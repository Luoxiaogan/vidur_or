# OPRE-2025-04-1885 Revision Audit

I found all listed files accessible and audited the bundle against the uploaded brief. fileciteturn0file0

```text
Overall verdict: Risky

Main reason:
The revised package is substantially stronger than the original and the response letter is mostly serious, especially on Reviewer 3’s open-system throughput and latency objections. However, several remaining problems are not cosmetic: there are actual manuscript/appendix contradictions, proof-scaling inconsistencies, experiment-description mismatches, and response-letter overclaims that give a skeptical AE/R3 an easy path to say the revision is still not clean enough for OPRE.

Top 5 fixes before resubmission:
1. Fix mathematical/proof inconsistencies: Proposition 3 main-text example vs appendix proof, Appendix D latency scaling, and handwavy “any policy” arguments.
2. Fix real-data experiment inconsistencies and reproducibility: Figure 11 statistics, fixed-prefill vs sampled-prefill language, segment count/endpoints, η, tl values, and tuning rules.
3. Fix response-letter overclaims and fragile language: remove “revision plan” language, qualify A100/SGLang validation scope, and add concrete capacity/threshold details.
4. Fix figure/table/caption ambiguities: especially Table 1 memory setting, Appendix A.2’s unsupported “L=10 matches full m-type” claim, and Figure 12 completion-rate interpretation.
5. Fix professional polish issues that DE/AE will notice immediately: manuscript title mismatch, Algorithm 2 initialization typo, reference placeholder “[Insert Date Here],” and overstrong “linear model holds exactly” language.
```

## Review matrix

| Role | What they asked for | Where revised paper addresses it | Where response letter addresses it | Assessment |
|---|---|---|---|---|
| **DE** | Major revision, especially exposition quality; warned that another version with poor writing would likely be rejected. | Revised abstract/introduction, Section 2 model, Sections 4–6, expanded appendices. | Response letter pp. 1–2 gives a broad revision summary. | **Partial.** The narrative is much improved, but visible internal inconsistencies and reference/algorithm errors still make the package look unfinished. |
| **AE** | Full exposition overhaul; clearer model assumptions; use standard stochastic-process tools; clarify theory novelty. | Section 2 pp. 9–14; Sections 3–5 pp. 14–28; appendices C–G pp. 49–69; related work pp. 7–8. | Response letter pp. 2–4. | **Partial to convincing.** Main text is stronger, but proof appendices still contain handwavy and inconsistent claims. |
| **R1** | Clarify OOM/KV-cache safeguards, Eq. (1), notation, policy space, batching, examples, algorithm intuition, typos. | Section 2 pp. 9–14; Eq. (1) p. 11; memory constraint p. 12; policy class pp. 13–14; WAIT pp. 18–22; notation table p. 48. | Response letter pp. 4–7. | **Mostly convincing.** R1’s concerns are largely addressed, except for validation-scope overclaim and algorithm/proof sloppiness. |
| **R2** | Clarify Eq. (1) scope, prefill/decode model, \(C\ge M^*\), theorem proof details, no-wait ablation, heavy-traffic wording, exact experimental parameters, A100 validation, long-output tests. | Eq. (1) p. 11; Sections 3–5; Section 6 pp. 28–36; Appendix H pp. 70–75. | Response letter pp. 7–12. | **Partial.** The revision adds the right material, but exact numerical settings and proof details remain too loose. |
| **R3** | Correct open-system throughput framing, remove heavy-traffic claims, explain why theory is nontrivial, add latency-vs-arrival-rate evidence, clarify memory/preemption, improve writing. | Objective pp. 13–14; fluid benchmark pp. 14–17; WAIT/Nested WAIT pp. 18–28; experiments pp. 28–36. | Response letter pp. 12–16. | **Improved but still risky.** The framing is much better, but R3 can still attack proof rigor, tuning transparency, and overloaded-regime interpretations. |

---

# 1. Response Letter Risks

## Finding 1

Attack: Title drift between response letter and revised manuscript  
Severity: Major  
Reviewer Lens: AE / DE  
Location: `response_letter.pdf`, p. 1; `LLM_or.pdf`, title page p. 1  
Issue: The response letter uses the original title “Fluid-Guided Online Scheduling,” while the revised manuscript title is “Fluid-Based Online Scheduling.”  
Evidence: Response letter header: “Fluid-Guided Online Scheduling with Memory Constraints.” Revised manuscript title page: “Fluid-Based Online Scheduling with Memory Constraints.”  
Why it matters: This is a visible resubmission-package inconsistency. It suggests insufficient final checking and may irritate the DE before they even reach the technical content.  
Fix: Either revert the manuscript title to “Fluid-Guided” or update the response letter and submission metadata to “Fluid-Based.” Do not leave mixed titles.

## Finding 2

Attack: Response-letter overclaim on A100/SGLang validation scope  
Severity: Major  
Reviewer Lens: R2 / AE  
Location: `response_letter.pdf`, pp. 3, 7, 11; `LLM_or.pdf`, Appendix H.2 pp. 70–73  
Issue: The response letter implies that direct A100/SGLang validation covers the “batch-size range used in experiments,” but Appendix H.2 validates a narrower setting: prefill length 256, decode length 20, batch sizes 1–256.  
Evidence: Appendix H.2 reports “prefill length 256 and decode length 20” and a MAPE of 1.93%. The main numerical section includes p512d20, p512d1000, two-type workloads, and real-data workloads.  
Why it matters: Reviewer 2 specifically asked about simulator fidelity. If the response letter sounds broader than the evidence, it invites a credibility objection.  
Fix: Replace the broad claim with: “We added direct A100/SGLang validation for the single-type p256d20 calibration grid over batch sizes 1–256, obtaining MAPE 1.93%. The long-decode and real-data studies remain primarily simulator-based, with smaller-scale end-to-end GPU checks reported separately in Appendix H.2.”

## Finding 3

Attack: “Revision plan” language leaks internal author process  
Severity: Major  
Reviewer Lens: R3 / AE  
Location: `response_letter.pdf`, R3 response, p. 14  
Issue: The response letter says the revision follows “the main point in our revision plan.” That sounds like internal workflow language rather than a polished response to reviewers.  
Evidence: The phrase explicitly refers to “our revision plan.”  
Why it matters: It can sound AI-generated or hastily assembled. It also reminds the panel that the paper may be patched together from an internal checklist.  
Fix: Replace with: “This point guided the revision: WAIT is not merely a work-conserving batching rule, but a dimensionality-reduction device that converts a high-dimensional memory-coupled scheduling problem into threshold queues with analyzable boundary behavior.”

## Finding 4

Attack: Capacity response lacks the concrete numbers R2 asked for  
Severity: Major  
Reviewer Lens: R2  
Location: `response_letter.pdf`, R2.3 response pp. 8–9; `LLM_or.pdf`, Section 6 pp. 29–34  
Issue: Reviewer 2 asked for clarity on \(C\), \(M^*\), memory feasibility, and exact experimental settings. The response says this was clarified, but the paper still does not give a compact table of \(C\), \(M^*\), batch budgets, \(t_l\), segment counts, and thresholds for the key figures.  
Evidence: Section 6 describes tuning rules and examples, but not a complete reproducibility table for Figures 7–12.  
Why it matters: This is exactly the kind of omission R2 can point to as “addressed verbally, not operationally.”  
Fix: Add one table in Section 6 or an appendix: figure/workload, \(C\), \(M^*\), \(B\), chunk size, \(t_l\), segment endpoints, \(\eta\), threshold vector, arrival-rate grid, number of replications.

## Finding 5

Attack: Response letter undersells the strongest R3 fix  
Severity: Minor  
Reviewer Lens: R3 / AE  
Location: `response_letter.pdf`, R3 responses pp. 12–16  
Issue: The response letter correctly discusses open-system throughput, but it does not highlight strongly enough that the manuscript now distinguishes token-level theoretical throughput from request-level experimental completion rate.  
Evidence: The paper makes this distinction in Section 2.5 and Section 6, but the response letter repeatedly uses “effective throughput” in a broad way.  
Why it matters: R3’s core criticism was conceptual. The response should make the corrected conceptual taxonomy unmistakable.  
Fix: Add a short clarifying sentence: “In the theory, effective throughput is decode-token throughput from completed requests; in the experiments, we report request-level effective completion rate separately from latency and TTFT.”

## Finding 6

Attack: “Finite-horizon validation” wording is imprecise  
Severity: Minor  
Reviewer Lens: R3  
Location: `response_letter.pdf`, R3 response, p. 14; `LLM_or.pdf`, Section 6.1.3 p. 33  
Issue: The response refers to “finite-horizon validation near the two-type stability boundary,” but the paper frames Figure 10 as a long-horizon validation.  
Evidence: Section 6.1.3 title: “Long-Horizon Validation.”  
Why it matters: Minor, but it creates avoidable mismatch around the very asymptotic/stability topic Reviewer 3 cared about.  
Fix: Replace “finite-horizon validation” with “long-horizon simulation validation near the empirical two-type stability boundary.”

---

# 2. Revised Paper Logic/Content Risks

## Finding 7

Attack: Proposition 3 example and appendix proof do not match  
Severity: Critical  
Reviewer Lens: AE / R3 / R2  
Location: `LLM_or.pdf`, Proposition 3 and Example 2 pp. 18–19; Appendix C.3 p. 50  
Issue: The main text presents a single-type FCFS cascade example with \(l=1\), \(l'=1\), \(C=12\), and \(\lambda=4\). The appendix proof of Proposition 3 instead constructs a two-type example with different lengths, arrival rates, and memory requirement.  
Evidence: Main text: “Consider a single type with \(l=1\), \(l'=1\), \(C=M^*=12\), and \(\lambda=4\).” Appendix C.3: “Consider a system with two types… type 1 has \(l_1=1,l_1'=1,\lambda_1=1\); type 2 has \(l_2=1,l_2'=2,\lambda_2=1\), so \(M^*=9\).”  
Why it matters: This is an actual inconsistency in a theorem-supporting example. A skeptical R3 or AE can use it to argue the revised theory is still not clean.  
Fix: Make the appendix proof prove the exact single-type example, or replace the main-text example with the two-type construction used in the proof. Also specify \(d_0,d_1\) normalization so that “about four arrivals during the previous iteration” is dimensionally meaningful.

## Finding 8

Attack: Algorithm 2 initialization typo undermines Nested WAIT clarity  
Severity: Major  
Reviewer Lens: R2 / R3  
Location: `LLM_or.pdf`, Algorithm 2 p. 26  
Issue: Algorithm 2 initializes segment queues over a degenerate range: \(s\in[l'_{k-1},l'_{k-1}]\).  
Evidence: Algorithm 2 line 1 appears to initialize only the boundary stage rather than all stages in the segment.  
Why it matters: Reviewer 2 asked for proof and algorithm clarity. This typo makes the central unknown-output-length algorithm look unreviewed.  
Fix: Replace with: “Initialize \(Q_{k,s}\leftarrow0\) for all segments \(k\in[L]\) and all decode stages \(s\in\{l'_{k-1}+1,\ldots,l'_k\}\), with the appropriate convention for the first segment.”

## Finding 9

Attack: PD-disaggregation claim is too strong  
Severity: Major  
Reviewer Lens: AE / General OR reader  
Location: `LLM_or.pdf`, Introduction p. 7; Appendix H.4 pp. 74–75  
Issue: The introduction says that in prefill/decode disaggregated deployment, “the linear iteration-time model in Section 2 then holds exactly, the same thresholds apply.”  
Evidence: The phrase “holds exactly” appears in the introduction. Appendix H.4 more carefully says the affine decode-only model is “especially appropriate.”  
Why it matters: “Exactly” is not defensible. Even decode-only service can show kernel, bandwidth, batching, and implementation nonlinearities.  
Fix: Replace with: “In decode-only deployment, the affine KV-cache model is a closer first-order approximation because prefill attention effects are separated; after calibrating \(d_0,d_1\), the same threshold construction applies.”

## Finding 10

Attack: Fluid scaling explanation may still look like disguised heavy traffic  
Severity: Major  
Reviewer Lens: R3  
Location: `LLM_or.pdf`, Section 4.2 pp. 20–22; Theorem 1 p. 21  
Issue: The paper says it removed heavy-traffic framing, but the asymptotic regime scales arrivals by \(\zeta\) and service times by \(1/\zeta\) while keeping load fixed. That is a fluid-scale/many-event limit, but the response letter sometimes describes it as merely a long-horizon argument.  
Evidence: Section 4.2 defines \(\lambda_j^\zeta=\zeta\lambda_j\), \(d_0^\zeta=d_0/\zeta\), \(d_1^\zeta=d_1/\zeta\).  
Why it matters: Reviewer 3 objected strongly to “heavy traffic” misuse. If the scaling is not explained carefully, they may say the revision renamed rather than fixed the issue.  
Fix: Add one paragraph immediately before Theorem 1: “This is a fluid-scale, fixed-load limit: the utilization parameters are unchanged, but the number of arrival and service opportunities over a fixed macroscopic horizon grows. It is not a heavy-traffic limit because the system is not taken to critical load.”

## Finding 11

Attack: Experimental tuning by arrival rate is not sufficiently defended  
Severity: Major  
Reviewer Lens: R2 / R3  
Location: `LLM_or.pdf`, Section 6, especially pp. 29–30 and pp. 34–36  
Issue: WAIT/Nested WAIT thresholds are selected using \(t_l\) grids and arrival-rate-dependent computations, but the paper does not explain whether baselines receive comparable tuning or whether the policy requires knowing arrival rates.  
Evidence: Section 6 states that \(t_l\) is selected from a grid at each arrival rate and then thresholds are derived.  
Why it matters: R3 may interpret the latency gains as tuned operating-point advantages rather than robust online scheduling gains.  
Fix: Add: “WAIT/Nested WAIT use arrival-rate estimates only to set thresholds; they do not use future arrivals or output-length predictions. Baseline chunk sizes and memory-reservation parameters are fixed to their recommended or best feasible settings across the sweep. Appendix Table X reports all tuned values.”

## Finding 12

Attack: Objective taxonomy is improved but still needs one sharper sentence  
Severity: Minor  
Reviewer Lens: R3  
Location: `LLM_or.pdf`, Section 2.5 pp. 13–14; Section 6 p. 28  
Issue: The paper now correctly says throughput is capped by offered load in a stable open system, but “throughput,” “effective throughput,” and “effective completion rate” are still close enough that a reader can lose the distinction.  
Evidence: The theory defines effective throughput as completed decode tokens; Section 6 reports request-level effective completion rate.  
Why it matters: This was central to Reviewer 3’s rejection risk.  
Fix: Add a boxed or italicized sentence in Section 2.5: “Throughout, ‘effective throughput’ in the theory is token throughput from requests that eventually complete; in experiments, ‘effective completion rate’ is request completions per second net of eviction-induced restarts.”

---

# 3. Theory/Proof Risks

## Finding 13

Attack: Appendix D latency scaling contradicts Theorem 1  
Severity: Critical  
Reviewer Lens: AE / R3  
Location: `LLM_or.pdf`, Theorem 1 p. 21; Appendix D p. 55  
Issue: Theorem 1 states latency/TTFT scale as \(O((\zeta T)^{1/2})\) at the boundary and \(O(1)\) under slack, but Appendix D says expected end-to-end latency scales as \(O(B^{-1/2})\).  
Evidence: Appendix D’s proof narrative states that “expected end-to-end latency scales as \(O(B^{-1/2})\),” which has the wrong direction for a waiting-time quantity.  
Why it matters: This is exactly the kind of proof inconsistency the AE warned about. It also directly touches R3’s latency concern.  
Fix: Correct the statement. If the normalized queue length is \(O(B^{-1/2})\), the unnormalized queue length is \(O(B^{1/2})\), and latency should be derived via Little’s law accordingly. State the boundary and slack cases separately, matching Theorem 1.

## Finding 14

Attack: Proposition 1 “under any scheduling policy” proof is too thin  
Severity: Major  
Reviewer Lens: AE / R2  
Location: `LLM_or.pdf`, Proposition 1 p. 15; Appendix C.1 p. 49  
Issue: Proposition 1 claims instability under any scheduling policy when load exceeds capacity, but the proof sketch appears to reason through balanced-stage service rather than an arbitrary admissible policy.  
Evidence: The proof discusses type-\(j\) prompt evolution and the required per-iteration service rate, but does not formalize why every possible scheduling policy is bounded by the same service-capacity inequality.  
Why it matters: AE asked for standard stochastic-process rigor, not intuitive derivations.  
Fix: Recast the proof as a capacity cut: define total required work per completed request, bound maximum possible processed token-work per unit time under Eq. (1), then show offered token-work exceeds service capacity. This avoids arguing through a balanced policy.

## Finding 15

Attack: Proposition 5 remains more assertion than proof  
Severity: Major  
Reviewer Lens: AE / R3  
Location: `LLM_or.pdf`, Proposition 5 p. 24; Appendix C.5 p. 51  
Issue: Proposition 5 says a policy must condition on continuation to avoid either late-stage over-admission or under-utilization, but the proof is a short impossibility argument without a formal policy class or minimax statement.  
Evidence: Appendix C.5 says, in effect, that for each batch configuration there is either underutilization or overflow risk.  
Why it matters: This proposition is intended to justify Nested WAIT as nontrivial. If it reads informal, R3 can say the theory still does not demonstrate more than intuitive pipeline filling.  
Fix: Either downgrade Proposition 5 to an “Observation” with a carefully stated example, or provide a formal two-instance indistinguishability proof: two output-length distributions sharing the same early history but requiring different downstream memory allocations.

## Finding 16

Attack: Appendix E revives the CPU-swapping concern  
Severity: Major  
Reviewer Lens: R3 / R1  
Location: `LLM_or.pdf`, Appendix E p. 57  
Issue: Appendix E says prompts waiting in the first segment are “stored in CPU and do not consume GPU memory.”  
Evidence: The phrase “stored in CPU” appears in the Nested WAIT proof appendix.  
Why it matters: R3 explicitly asked whether preempted or waiting jobs incur memory movement costs. The main paper tries to avoid reliance on CPU/SSD swapping, but this wording reopens the issue.  
Fix: Replace with: “Prompts not yet admitted to prefill have no resident KV cache and therefore do not consume GPU KV-cache memory. This statement does not rely on swapping an already-prefilled cache out of GPU memory.”

## Finding 17

Attack: Threshold integerization is not cleanly handled  
Severity: Minor  
Reviewer Lens: R2  
Location: `LLM_or.pdf`, Section 4.1 pp. 19–20; Appendix D pp. 52–55  
Issue: Thresholds such as \(n_j^*\), \(n_j\), and arrival means are treated as exact integers in algorithms and proofs, while the fluid solutions need not be integer.  
Evidence: Algorithm 1 uses integer queue thresholds; Lemma 1 uses Poisson arrivals and thresholds without a clear floor/ceiling convention.  
Why it matters: This is not fatal asymptotically, but R2 already flagged notation and proof precision.  
Fix: Add a convention: “All thresholds used by the algorithm are rounded to integers; this changes memory and throughput bounds by \(O(1)\), which is absorbed in the asymptotic constants.”

## Finding 18

Attack: Theorem 2 uses \(M\) while the model uses \(C\)  
Severity: Minor  
Reviewer Lens: General OR reader  
Location: `LLM_or.pdf`, Theorem 2 p. 27; Section 2.4 p. 12  
Issue: The model uses \(C\) as GPU memory capacity, but Theorem 2 states “if memory \(M\) satisfies…”  
Evidence: Theorem 2 switches from capacity \(C\) to “memory \(M\).”  
Why it matters: Minor notation drift, but reviewers already complained about notation.  
Fix: Use \(C\) consistently: “If the capacity \(C\) satisfies \(C\ge M^\pi+\cdots\).”

---

# 4. Experiment/Figure/Table Risks

## Finding 19

Attack: Real-data statistics conflict across text, figure, and appendix  
Severity: Critical  
Reviewer Lens: R2 / R3 / AE  
Location: `LLM_or.pdf`, Section 6.2 p. 34; Figure 11 p. 34; Appendix A.2 p. 46  
Issue: The real-data workload description gives different statistics in different places.  
Evidence: Section 6.2 says prefill is concentrated near 35 with median 30 and decode median 95. Figure 11 reports mean prefill 59.24, median prefill 21.00, mean decode 147.32, median decode 116.00. Appendix A.2 says fixed prefill length 62 and mean decode about 147.33, median 117.  
Why it matters: This is a concrete factual inconsistency in the experiment section. It undermines the credibility of the real-data results.  
Fix: Recompute and state one consistent dataset summary. If Section 6.2 uses sampled heterogeneous prefill lengths, remove “fixed prefill length 62” from Appendix A.2 or explain that Appendix A.2 is a separate design calculation using the sample mean.

## Finding 20

Attack: Real-data Nested WAIT parameters are not reproducible  
Severity: Major  
Reviewer Lens: R2 / AE  
Location: `LLM_or.pdf`, Section 6.2 pp. 34–36; Appendix A.2 pp. 44–47  
Issue: The paper gives formulas for segment construction but not the actual segment count, segment endpoints, continuation probabilities, \(\eta\), \(t_l\), or threshold values used in Figure 12.  
Evidence: Section 6.2 defines \(L\), \(\Delta l'_k\), \(\lambda'_k\), \(p_k\), \(q_k\), \(\eta\), and \(t_l\), but does not report the numerical values.  
Why it matters: R2 explicitly requested exact experimental parameters. This is still too hard to reproduce.  
Fix: Add a table: “Figure 12 parameters: \(L=\cdots\), segment endpoints \(=\cdots\), \(\eta=\cdots\), \(t_l\) by arrival-rate band \(=\cdots\), continuation probabilities \(=\cdots\), memory capacity \(C=\cdots\).”

## Finding 21

Attack: Table 1 memory setting is ambiguous  
Severity: Major  
Reviewer Lens: R2 / R3  
Location: `LLM_or.pdf`, Section 6.1.1 pp. 31–32; Table 1 p. 32  
Issue: The text first mentions a “baseline-memory sweep” at \(\lambda=4.0\), then Table 1 reports a “tightened-memory run” at the same arrival rate. The caption says the same comparison shows lower latency under WAIT, making it unclear whether the latency numbers are from the tightened-memory run or baseline-memory run.  
Evidence: Text: “the baseline-memory sweep gives 26.4s for WAIT and 30.2s for Sarathi. Table 1 reports the accompanying near-capacity eviction diagnostic… in the tightened-memory run.” Caption: “Under tightened memory… the same comparison also shows lower latency under WAIT.”  
Why it matters: Long-decode eviction diagnostics are one of the most important added experiments. Ambiguity here weakens the response to R2 and R3.  
Fix: Split the two claims: “The latency numbers in Table 1 are from the tightened-memory run” or “The latency numbers are from the baseline-memory sweep; the restart rates are from a separate tightened-memory run.” Do not mix them in one table unless all entries come from the same run.

## Finding 22

Attack: Appendix A.2 overclaims full \(m\)-type comparison  
Severity: Major  
Reviewer Lens: AE / R2  
Location: `LLM_or.pdf`, Appendix A.2 p. 47; Section 6.2 pp. 34–36  
Issue: Appendix A.2 says Section 6 validates that Nested WAIT with \(L=10\) segments matches the full \(m\)-type algorithm, but Section 6 does not show a full \(m\)-type comparison.  
Evidence: Appendix A.2: “Section 6 validates… Nested WAIT with \(L=10\) segments matches the performance of the full \(m\)-type algorithm…” Section 6 compares Nested WAIT to vLLM and Sarathi, not to a full \(m\)-type Nested WAIT benchmark.  
Why it matters: This is an unsupported claim. It is especially risky because it concerns dimensionality reduction, a central theoretical contribution.  
Fix: Either add the full \(m\)-type comparison, or replace with: “Section 6 evaluates the segmented policy on a real-data workload; Appendix A.2 explains why segmentation controls the memory buffer.”

## Finding 23

Attack: Figure 12 completion-rate saturation is under-explained  
Severity: Minor  
Reviewer Lens: R3  
Location: `LLM_or.pdf`, Figure 12 p. 36 and surrounding text  
Issue: The right panel shows effective completion rates saturating as arrival rate increases, but the text emphasizes latency benefits without explicitly interpreting the saturation/stability boundary.  
Evidence: Figure 12 right panel plots effective completion rate vs arrival rate; the curves flatten while arrival rate continues increasing.  
Why it matters: R3 specifically wanted correct open-system interpretation. This figure is an opportunity to show it.  
Fix: Add: “For arrival rates above the empirical stability region, completion rate saturates below offered load; latency in these overloaded regimes is reported only as a finite-horizon diagnostic.”

## Finding 24

Attack: Hybrid GPU implementation of WAIT is not clearly separated from Algorithm 1  
Severity: Major  
Reviewer Lens: R2 / General OR reader  
Location: `LLM_or.pdf`, Appendix H.2 pp. 71–73  
Issue: Appendix H.2 describes a real-GPU WAIT implementation with a transition block that switches to native scheduling in lightly loaded states. That is not exactly Algorithm 1.  
Evidence: Appendix H.2 says the implementation uses “a transition block” and native SGLang behavior in lightly loaded states.  
Why it matters: If GPU evidence is used to validate WAIT, the reader needs to know whether it validates the theoretical policy or a practical hybrid.  
Fix: Add a sentence: “The GPU implementation is a conservative hybrid approximation of Algorithm 1; it preserves WAIT’s threshold admission behavior near capacity but delegates lightly loaded states to the native scheduler.”

## Finding 25

Attack: Repeated-run table uses undefined “Multi-type W3” label  
Severity: Minor  
Reviewer Lens: R2  
Location: `LLM_or.pdf`, Appendix H.3 p. 74  
Issue: The repeated-run variability table labels a setting “Multi-type W3,” but W3 is not defined in the main text.  
Evidence: Appendix H.3 table row uses “Multi-type W3.”  
Why it matters: Minor, but it adds to the impression of leftover internal labels.  
Fix: Rename to the workload name used in Section 6, e.g., “Two-type p512d20/p512d60” or define W3 in the caption.

---

# 5. Consistency Risks

## Finding 26

Attack: Effective throughput vs effective completion rate still needs a glossary-level fix  
Severity: Major  
Reviewer Lens: R3 / AE  
Location: `LLM_or.pdf`, Abstract p. 2; Section 2.5 pp. 13–14; Section 6 p. 28; response letter pp. 1–2  
Issue: The paper mostly distinguishes token-level theoretical throughput from request-level experimental completion rate, but the abstract and response letter still compress them into “effective throughput” too freely.  
Evidence: The abstract says the policies improve “effective throughput” and “completion rate net of eviction,” while Section 6 reports “effective completion rate.”  
Why it matters: Reviewer 3’s main conceptual criticism was that throughput in a stable open system is capped by offered load. Any lingering ambiguity is dangerous.  
Fix: Define both terms once in the abstract or model section and use them consistently: “token-level effective throughput” for theory; “request-level effective completion rate” for experiments.

## Finding 27

Attack: No stale 1.5% MAPE found — this is resolved  
Severity: Suggestion  
Reviewer Lens: R2  
Location: `LLM_or.pdf`, Section 6 p. 28; Appendix H.2 p. 71  
Issue: The MAPE value appears consistently as 1.93%.  
Evidence: Section 6 and Appendix H.2 both report 1.93%.  
Why it matters: This is a positive consistency point.  
Fix: No change needed.

## Finding 28

Attack: No visible Llama-3/Llama-2 inconsistency found — mostly resolved  
Severity: Suggestion  
Reviewer Lens: R2 / AE  
Location: `LLM_or.pdf`, Section 2.2 p. 11; Section 6 p. 28; Appendix H.2 pp. 70–73  
Issue: The revised manuscript consistently uses Llama-2-7B/13B in the main validation and experiments.  
Evidence: Figure 3 caption and Section 6 refer to Llama-2; Appendix H.2 refers to Llama-2-7B.  
Why it matters: This was a likely stale-text risk; it appears fixed.  
Fix: No substantive change. Optionally make Figure 3 axis labels say “Llama-2-7B” and “Llama-2-13B” rather than “Llama 7B/13B.”

## Finding 29

Attack: A100 vs L20 wording is mostly consistent but needs one clarifying sentence  
Severity: Minor  
Reviewer Lens: R2  
Location: `LLM_or.pdf`, Figure 3 p. 11; Section 6 p. 28; Appendix H.2 pp. 70–73  
Issue: Figure 3 validates Eq. (1) on L20 GPUs, while Section 6 uses A100/Vidur and Appendix H.2 validates A100/SGLang. This is not contradictory, but the paper should explicitly say these are separate validation steps.  
Evidence: Figure 3 caption says L20; Section 6 says Vidur configured for A100; Appendix H.2 says A100/SGLang.  
Why it matters: R2 asked about A100 validation. The reader should not have to infer the hardware split.  
Fix: Add: “Figure 3 illustrates the affine model on L20 hardware; Appendix H.2 separately validates the A100/SGLang configuration used for the main simulations.”

## Finding 30

Attack: Reference placeholder remains in bibliography  
Severity: Major  
Reviewer Lens: DE / AE  
Location: `LLM_or.pdf`, References p. 40  
Issue: A reference contains a placeholder access date: “[Insert Date Here].”  
Evidence: Patel (2023) entry includes “Accessed: [Insert Date Here].”  
Why it matters: This is an obvious production-quality defect. Given the DE’s warning about writing quality, it is disproportionately damaging.  
Fix: Replace with an actual access date or remove the access-date field consistently.

## Finding 31

Attack: Appendix fixed-prefill description conflicts with real-data workload  
Severity: Major  
Reviewer Lens: R2 / AE  
Location: `LLM_or.pdf`, Appendix A.2 p. 46; Section 6.2 p. 34  
Issue: Appendix A.2 says the LMSYS validation uses “fixed prefill length 62,” while Section 6.2 describes sampled prefill lengths from real data.  
Evidence: Appendix A.2: “fixed prefill length 62.” Section 6.2: sample of 5,000 requests with distributional prefill lengths.  
Why it matters: It is unclear whether Appendix A.2 and Figure 12 use the same workload.  
Fix: State explicitly whether Appendix A.2 is a separate analytical design exercise using the sample mean, or revise it to match the actual Section 6.2 workload.

---

# 6. Language/OR-Style Risks

## Finding 32

Attack: Overstrong causal claim in introduction  
Severity: Minor  
Reviewer Lens: R3 / General OR reader  
Location: `LLM_or.pdf`, Introduction p. 5  
Issue: The introduction says WAIT lowers latency in underloaded regimes and near boundaries, but some experiments show low-load policies are nearly indistinguishable.  
Evidence: Section 6.1.3 says at low arrival rates all methods show similar mean latency.  
Why it matters: Overstating latency improvement risks triggering R3’s concern that latency is not properly interpreted.  
Fix: Replace with: “In underloaded regimes, thresholding can reduce latency when it prevents avoidable batching imbalance; near empirical stability boundaries, the larger effect is avoiding restart-driven congestion.”

## Finding 33

Attack: “Capacity theoretically sufficient” needs precise qualifier  
Severity: Minor  
Reviewer Lens: R3  
Location: `LLM_or.pdf`, Abstract p. 2; Introduction p. 5  
Issue: The phrase “capacity is theoretically sufficient for stability” is good rhetorically but should consistently mean “sufficient for the ideal-fluid equilibrium,” not all policies.  
Evidence: The fluid section defines \(M^*\) as the ideal-fluid memory requirement, not a universal policy guarantee.  
Why it matters: R3 may object that \(C\ge M^*\) is not sufficient for arbitrary scheduling stability.  
Fix: Use: “capacity is sufficient for the ideal-fluid equilibrium” or “capacity meets the ideal-fluid memory requirement \(M^*\).”

## Finding 34

Attack: Response-letter opening is slightly generic  
Severity: Suggestion  
Reviewer Lens: AE / DE  
Location: `response_letter.pdf`, p. 1  
Issue: The opening says the authors “took this concern seriously” and “substantially rewrote,” which is acceptable but generic.  
Evidence: Response letter first page.  
Why it matters: A stronger opening would foreground the conceptual correction rather than effort.  
Fix: Replace with: “The revision changes the paper’s organizing question from unconstrained throughput maximization to stability-region, effective-completion, latency, and TTFT control in an open stochastic serving system.”

## Finding 35

Attack: “Exactly” and “optimal” words should be audited globally  
Severity: Major  
Reviewer Lens: R3 / AE  
Location: `LLM_or.pdf`, Introduction p. 7; Sections 3–5  
Issue: A few words still sound stronger than the evidence: “holds exactly,” “asymptotically optimal,” and “throughput-optimal” can be misread without qualifiers.  
Evidence: “holds exactly” appears in the PD discussion; theorems are asymptotic under specific scaling and memory-buffer assumptions.  
Why it matters: The reviewers are already sensitive to overclaiming.  
Fix: Use qualified language: “asymptotically matches the ideal-fluid effective-throughput benchmark under the stated scaling and memory-buffer assumptions.”

## Finding 36

Attack: Some appendix prose still looks unpolished  
Severity: Minor  
Reviewer Lens: AE / DE  
Location: `LLM_or.pdf`, Appendix C pp. 49–51  
Issue: The appendix contains odd spacing and word breaks such as “C onsider” and “I n.”  
Evidence: Appendix C proof text.  
Why it matters: The DE explicitly warned about writing quality. These are small but visible.  
Fix: Run a final PDF proofread, not only LaTeX source review.

---

# 7. Reviewer-Specific Remaining Risks

## Finding 37

Attack: Likely R1 follow-up objections  
Severity: Major  
Reviewer Lens: R1  
Location: `LLM_or.pdf`, Section 2 pp. 9–14; Algorithm 1 p. 21; Algorithm 2 p. 26; Appendix H.2 pp. 70–73  
Issue: R1 may still ask the following:  
1. Where exactly is the OOM safeguard enforced inside WAIT/Nested WAIT, not only in the model?  
2. Are evicted prompts restarted from scratch in all simulations, or only in selected diagnostics?  
3. Does LIFO eviction match vLLM/Sarathi behavior or is it an assumed stress model?  
4. Does Eq. (1) remain valid for long-decode p512d1000 workloads?  
5. Why does the GPU validation use a hybrid WAIT implementation rather than Algorithm 1 exactly?  
Current manuscript answer: Mostly answered for memory accounting and restart semantics; partially answered for validation scope and hybrid GPU implementation.  
Why it matters: R1 was concerned with modeling realism. Remaining ambiguities are easy to fix.  
Fix: Add one implementation paragraph in Section 6: “All simulations use the same eviction/restart semantics stated in Section 2.4. Unless otherwise stated, WAIT/Nested WAIT thresholds are chosen so these policies do not evict; eviction rates are reported for baselines and tightened-memory diagnostics.”

## Finding 38

Attack: Likely R2 follow-up objections  
Severity: Major  
Reviewer Lens: R2  
Location: `LLM_or.pdf`, Sections 3–6; Appendix H  
Issue: R2 may still ask:  
1. What are the exact \(C\), \(M^*\), \(B\), \(t_l\), and threshold values for every main figure?  
2. Is the A100/SGLang MAPE validation representative of long-decode and real-data memory states?  
3. Why is Proposition 3’s proof not the same as the main example?  
4. Where is the full proof that decoding-stage dynamics are handled after prefill?  
5. What exactly is the no-wait threshold policy’s threshold and how is it tuned?  
6. Is the real-data segment construction reproducible from the paper alone?  
Current manuscript answer: Partially. The right pieces exist, but not in a sufficiently explicit table/proof chain.  
Why it matters: R2 was broadly positive, but R2’s revision requests were technical and parameter-specific.  
Fix: Add a compact “Experimental parameter table” and clean the proof/example mismatch.

## Finding 39

Attack: Likely R3 follow-up objections  
Severity: Critical  
Reviewer Lens: R3  
Location: `LLM_or.pdf`, Sections 2.5, 3, 4, 6; Appendices C–E  
Issue: R3 may still ask:  
1. Are you still calling an offered-load cap “throughput optimality”?  
2. Is WAIT more than pipeline filling with a threshold?  
3. Why are latency bounds nontrivial if stability already implies finite mean latency?  
4. Are overloaded-regime latency plots being interpreted correctly?  
5. Does \(C\ge M^*\) actually guarantee stability for the implemented policy or only for the ideal-fluid benchmark?  
6. Are thresholds tuned with arrival-rate knowledge, and is that operationally realistic?  
7. Why do proof appendices contain inconsistent scaling and example mismatches?  
Current manuscript answer: Conceptually much improved; technically still vulnerable.  
Why it matters: R3 was the most dangerous reviewer. They can accept the reframing but still reject on rigor/clarity.  
Fix: Add a short “What the theorems do and do not claim” paragraph after Theorem 1 and Theorem 2. Explicitly say \(M^*\) is an ideal-fluid benchmark, not a universal sufficient condition for every policy.

## Finding 40

Attack: Likely AE follow-up objections  
Severity: Major  
Reviewer Lens: AE  
Location: `LLM_or.pdf`, Appendices C–G; response letter pp. 2–4  
Issue: The AE may still ask:  
1. Are the appendices now proofs or still proof sketches?  
2. Why are there unsupported claims like the full \(m\)-type comparison?  
3. Are standard queueing results actually invoked, or only cited?  
4. Why do theorem statements and proof scalings disagree?  
5. Does the paper clearly separate modeling contribution from theorem contribution?  
Current manuscript answer: Main text is improved; appendices remain the weak point.  
Why it matters: AE already flagged the appendix/proof style as below standard.  
Fix: Tighten appendices by converting informal impossibility claims into observations, correcting scaling, and removing unsupported validation statements.

## Finding 41

Attack: Likely DE follow-up objections  
Severity: Major  
Reviewer Lens: DE  
Location: Entire package  
Issue: The DE may still ask:  
1. Why does the package still have a title mismatch?  
2. Why is there a bibliography placeholder?  
3. Why does Algorithm 2 contain a basic indexing typo?  
4. Why do experiment statistics conflict?  
5. Why should OPRE accept a revision whose response letter is stronger than parts of the manuscript?  
Current manuscript answer: Not adequately answered; these are final-quality issues.  
Why it matters: The DE’s threshold is not just “has the authors tried?” but “is this now journal quality?”  
Fix: Treat this as a final resubmission QA problem: title, references, algorithms, figures, table captions, and appendix claims must be checked line-by-line.

---

# 8. DE/AE Meta-Level Risks

## Finding 42

Attack: The response letter is more coherent than the paper in places  
Severity: Major  
Reviewer Lens: AE / DE  
Location: `response_letter.pdf`, pp. 1–16; `LLM_or.pdf`, Sections 6 and appendices  
Issue: The response letter tells a clean story: open-system stability, memory-coupled scheduling, WAIT as dimensionality reduction, Nested WAIT for unknown lengths. The manuscript mostly supports this, but inconsistencies in examples, appendices, and experiments make the final package look less coherent than the letter.  
Evidence: The letter’s claims about validation, real-data construction, and theory clarity are stronger than what the manuscript cleanly documents.  
Why it matters: Reviewers judge the manuscript, not the letter. If the letter seems to explain things that the paper itself does not, the revision looks patched.  
Fix: Move the response-letter clarity into the manuscript: one objective taxonomy paragraph, one parameter table, one “scope of validation” paragraph, and one theorem-scope paragraph.

## Finding 43

Attack: The revision may be perceived as appendicized rather than integrated  
Severity: Major  
Reviewer Lens: AE  
Location: `LLM_or.pdf`, main Sections 4–6; Appendices A–H  
Issue: Several important clarifications are pushed into appendices: GPU validation, repeated-run variability, no-wait ablation, PD disaggregation, segmentation design.  
Evidence: Section 6 mentions some of these briefly, but key limits and settings live in Appendix H or Appendix A.  
Why it matters: AE complained that appendices were “deposit boxes.” The revision improves this but does not fully eliminate the risk.  
Fix: Add a concise “Additional validation and robustness” paragraph in Section 6 summarizing Appendix H with exact limitations, not just positive results.

---

# Must-fix before resubmission

1. **Correct actual contradictions:** title mismatch; Proposition 3 example/proof mismatch; Appendix D latency-scaling contradiction; Algorithm 2 initialization typo; real-data statistics conflict.
2. **Add an experimental-parameter table:** \(C\), \(M^*\), \(B\), chunk size, \(t_l\), threshold values, segment endpoints, \(\eta\), continuation probabilities, arrival grids, replications.
3. **Revise response-letter overclaims:** especially A100/SGLang validation scope, “revision plan” language, and claims that all parameter concerns are fully resolved.
4. **Clarify real-data workload:** sampled prefill/decode distributions vs fixed prefill 62; Figure 11 statistics; Section 6.2 vs Appendix A.2.
5. **Remove unsupported Appendix A.2 claim:** do not say \(L=10\) matches the full \(m\)-type algorithm unless that comparison is shown.
6. **Fix professional polish:** reference placeholder, odd appendix word breaks, undefined “W3,” and overstrong “holds exactly.”

# Should-fix if time

1. Add a short theorem-scope paragraph explaining that the scaling is fluid-scale/fixed-load, not heavy traffic.
2. Add a glossary sentence distinguishing token-level effective throughput from request-level effective completion rate.
3. Clarify Table 1’s memory setting and whether latency/restart values come from the same run.
4. Qualify overloaded-regime latency plots as finite-horizon diagnostics.
5. In Appendix H.2, explicitly say the real-GPU WAIT implementation is a practical hybrid approximation of Algorithm 1.

# Do-not-change / already strong

1. The open-system reframing is much better: \(M^*\) is now mostly treated as an ideal-fluid memory requirement rather than “throughput-optimal memory.”
2. The response to Reviewer 3 is serious and mostly non-defensive.
3. The paper now clearly explains KV-cache growth, eviction-induced restarts, and why memory coupling matters.
4. The Nested WAIT narrative is much stronger: it now emphasizes on-the-fly classification at segment boundaries rather than output-length prediction.
5. The stale MAPE issue appears fixed: I found 1.93% consistently, not 1.5%.
6. The Llama-2/A100/L20 distinctions are mostly defensible once the hardware-validation roles are clarified.
