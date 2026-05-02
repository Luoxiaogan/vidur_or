# Revision Audit for OPRE-2025-04-1885

**Overall verdict:** **Risky**

**Main reason:** The revision is materially stronger than the original and fixes most of the issues that made the first round vulnerable—especially the open-system interpretation, the misuse of “heavy traffic,” the memory model, and the experimental framing around latency versus arrival rate. But it is **not yet bulletproof**. The biggest remaining exposure is **not the theory anymore**; it is the **credibility and auditability of the real-data numerical evidence**, plus a still-residual **Reviewer 3 significance risk** if the contribution is read as “pipeline filling + stability proof” rather than “policy-induced dimensionality reduction for a nonstandard memory-coupled control problem.”

**Top 5 must-fix issues before resubmission**

1. **Make the lmsys real-data figure fully auditable and reproducible** before you lean on it in the cover letter or response letter.
2. **Do not overstate the real-data result as a sharp stability-boundary finding** unless you complete the denser sweep, long-horizon validation, and repeatability checks flagged in your own internal checklist.
3. **Sharpen the manuscript’s significance story one more time for Reviewer 3**: make the “why this is not just positive recurrence / pipeline filling” argument impossible to miss.
4. **Add one explicit bridge sentence in the numerical section tying the experiments back to the decode-dominant scope of Equation (1)**, not only to the A100 fit.
5. **Do one last consistency pass on figure labels and small wording drifts**—especially the lingering `QPS` axis labels in the real-data figure and any low-load language that sounds stronger than the plots warrant.

## Review matrix

| Lens | Main criticism from round one | Audit judgment | Why |
|---|---|---|---|
| **AE** | Exposition far below journal standard; risky major revision; latency was underdeveloped | **Mostly addressed** | The revised manuscript is much clearer, slower, and more OR-facing. Section 2 now introduces memory, policy space, and effective throughput clearly; Section 6 now uses rate sweeps with latency and effective completion rate instead of unstable-horizon plots. But the real-data evidence still has auditability risk from your own internal notes. |
| **DE / General OR reader** | Is the narrative coherent and publication-ready? | **Partially addressed** | The conceptual story is now coherent. The remaining risk is less about logic and more about empirical provenance and whether the contribution still feels significant enough at the OR level. |
| **Reviewer 1** | Notation inconsistency, OOM/KV-cache capacity, Eq. (1) realism, policy-space clarity | **Addressed** | The revised paper explicitly counts all resident GPU KV caches, defines eviction/restart, separates stage notation, and adds a notation appendix. |
| **Reviewer 2** | Eq. (1) regime unclear, proof details unclear, need reproducible configs, no-wait alternative, real GPU validation, long outputs | **Mostly addressed** | The revised paper now states the decode-dominant scope of Eq. (1), adds A100/SGLang calibration, includes threshold-without-waiting, repeated-run checks, PD-disaggregation, and long-decode evidence. The remaining gap is not a missing response but that the real-data audit trail is still not fully durable. |
| **Reviewer 3** | Heavy-traffic misuse, open-system throughput confusion, unstable-regime latency evidence, contribution may be too simple, memory model ambiguity, poor writing | **Mostly addressed, but still the main risk** | The manuscript now reframes the problem around stability region, effective throughput, evictions, and latency-versus-arrival-rate. The memory model is corrected. Writing is far better. But Reviewer 3 could still say the significance case is borderline unless the nontriviality argument lands even more explicitly. |

## Response-letter factual consistency

**Bottom line:** the response letter is **substantially credible**. On the main conceptual points, it now describes changes that do appear in the revised manuscript. I did **not** find a major “paper says X / response letter says Y” contradiction on the flagship items. The biggest factual-risk area is instead **future drift**: if you change figures or rerun the lmsys section after this point, the response letter can easily become stale.

Attack:  
**Severity:** Major  
**Reviewer Lens:** AE / DE  
**Location:** `response_letter.pdf`, pp. 12–15; `LLM_or.pdf`, Sections 2.3–2.4, 3, 4.3, 5.2, 6; `response_letter_claim_audit.md`, C1–C15  
**Issue:** The response letter’s headline claims mostly check out, but its credibility still depends on the numerical section staying frozen after this audit.  
**Evidence:** The revised manuscript does, in fact, redefine effective throughput as completed decode tokens net of eviction in Section 2.4; it reframes the fluid model as a stability benchmark in Section 3; it gives dimensionality-reduction explanations after Theorem 1 and Theorem 2; and it adds Appendix H experiments for threshold-without-waiting, GPU validation, repeated runs, and PD deployment. Your internal claim-audit file independently reaches the same conclusion and explicitly records that the earlier A100 calibration wording mismatch was fixed.  
**Why it matters:** This is good news—but it also means the response letter is now tightly coupled to the current PDF. If the manuscript changes again, especially in Section 6 or Appendix H, you can accidentally recreate a mismatch very late in the process.  
**Fix:** Treat the current response letter as **version-locked** to the current manuscript. If you rerun or regenerate any Section 6 / Appendix H figures, re-audit C9–C12 and then do one final pass on every response-letter sentence that references experiments, GPU validation, or figure content.

Attack:  
**Severity:** Major  
**Reviewer Lens:** AE / R3  
**Location:** `response_letter.pdf`, pp. 14–15; `LLM_or.pdf`, Section 6.1 and 6.2; `real_data_remeasurement_checklist.md`, sections “Boundary Clarification Sweep,” “Long-Horizon Validation on Real Data,” and “Claims That Should Wait Until After Reruns”  
**Issue:** The response letter’s tone on the real-data numerical evidence is slightly stronger than your own internal confidence level justifies.  
**Evidence:** The response letter says the revised numerical section now meaningfully addresses low-load, near-capacity, and overloaded regimes, and that Nested WAIT has lower latency throughout the sweep. But your internal checklist explicitly says the current lmsys figure should be treated as **observed sweep outcomes**, that denser sweeps are still needed around the crossover, that long-horizon validation on real data is still needed before stronger stability-boundary language, and that repeatability/hyperparameter robustness remain unfinished.  
**Why it matters:** Even if the manuscript itself is careful, a strong response-letter tone invites a skeptical reviewer to probe exactly the one place where your own internal notes say the evidence is least settled.  
**Fix:** In the response letter, soften the lmsys claim to something like: “On the observed sweep, Nested WAIT is lower-latency throughout the tested rate range; we do not interpret this figure as establishing an exact real-data stability boundary.” If you complete the reruns, then restore the stronger language.

Attack:  
**Severity:** Minor  
**Reviewer Lens:** AE / DE  
**Location:** `response_letter_claim_audit.md`, “Remaining synchronization risks”  
**Issue:** You already know the final response letter should avoid fragile figure/appendix numbering, but that risk still exists right before submission.  
**Evidence:** Your own audit checklist says not to hard-code appendix letters or figure/table numbers unless copied after final compile.  
**Why it matters:** This is exactly the sort of avoidable sloppiness that can make a strong revision look careless.  
**Fix:** Use descriptive references wherever possible in the letter, or reinsert exact figure/table numbers only after the final camera-ready manuscript is compiled.

## Remaining rejection risks

Attack:  
**Severity:** Critical  
**Reviewer Lens:** AE / DE  
**Location:** `overview.md` (“Current technical focus” and “Next pipeline step”); `real_data_remeasurement_checklist.md`, sections 1–10; `LLM_or.pdf`, Section 6.2  
**Issue:** The lmsys real-data section is still the least auditable part of the package.  
**Evidence:** Your internal overview says the “current technical focus” is still to preserve Section 6 consistency while **finalizing remaining data-provenance items for the lmsys real-data sweep and repeated-run diagnostics**. The checklist says the full lmsys sweep still needs source-of-truth reconstruction, figure data cleanup, denser crossover sweeps, long-horizon validation, repeatability checks, and hyperparameter robustness. It explicitly warns: **do not strengthen the real-data wording beyond the current observed-sweep phrasing until these are done**. Meanwhile, the paper’s Section 6.2 presents exact rate-by-rate performance statements and a polished figure as if the evidence layer is already stable.  
**Why it matters:** This is the single strongest “paper may still look vulnerable on second round” issue. Not because the result is necessarily wrong, but because an editor or skeptical reviewer can smell when a figure is not yet fully provenance-secure.  
**Fix:** Before resubmission, either:  
1. fully reconstruct the real-data figure from committed durable data, log the exact per-rate configs, and complete at least the recommended 40–70 local sweep plus repeatability checks; **or**  
2. materially soften the real-data claims in both manuscript and response letter and present them as illustrative rather than boundary-establishing.

Attack:  
**Severity:** Major  
**Reviewer Lens:** R3 / AE  
**Location:** `LLM_or.pdf`, Theorem 1 discussion on pp. 21–22, lines roughly 1002–1016; Theorem 2 discussion on pp. 27–28, lines roughly 1304–1323; `response_letter.pdf`, pp. 13–15; `REVISION_PLAN.md`, core points 2–3 and 8–10  
**Issue:** The manuscript is much better on nontriviality, but Reviewer 3 could still regard the significance argument as only partially won.  
**Evidence:** The revised paper now says the primitive state must track entry queues, resident prompts at each decode stage, accumulated KV cache, and eviction/restart feedback, and that WAIT / Nested WAIT reduce this to threshold queues and boundary queues. That is exactly the right answer. But your response letter states this point even more forcefully than the paper does. The internal revision plan also shows that you know this is the narrative backbone of the whole revision.  
**Why it matters:** Reviewer 3’s deepest objection was not just terminology; it was “why is this contribution significant enough for OR?” If that answer is merely present rather than dominant, the paper can still get a lukewarm or negative rereview.  
**Fix:** Add one more high-signal sentence in the Introduction and one in the theorem-intuition paragraphs that says, in plain OR language: *the main contribution is not a new stochastic limit theorem, but a policy structure that converts a memory-growth control problem with restart feedback into tractable lower-dimensional queues.* Make that impossible to miss.

Attack:  
**Severity:** Major  
**Reviewer Lens:** R2 / AE  
**Location:** `LLM_or.pdf`, Section 2.2, pp. 10–11; Section 6 opening, pp. 28–29; Appendix H.2, pp. 70–73  
**Issue:** Equation (1) is now much better defended, but the bridge from “decode-dominant scope” to “the workloads we actually test” is still one notch weaker than ideal.  
**Evidence:** Section 2.2 now does the right thing: it explicitly presents the affine iteration-time model as a decode-centered approximation, notes possible nonlinear alternatives, and points to PD-disaggregated serving as a natural fit. Appendix H.2 then gives strong A100/SGLang validation with MAPE 1.93% and \(R^2 = 0.9943\). But Section 6 itself moves quickly from that calibration to the experiments without one crisp reminder that the tested workloads fall in the intended regime or that the appendix validates the range actually used in the main figures.  
**Why it matters:** Reviewer 2’s concern was not only “does a line fit well?” but also “what regime is this model actually claiming to represent?”  
**Fix:** Add one sentence in the Section 6 opener, e.g.: “These synthetic and sampled workloads are decode-heavy enough that the decode-centered affine iteration-time approximation in Section 2.2 is the intended first-order model; Appendix H.2 validates it on the batch-size range used here.”

Attack:  
**Severity:** Major  
**Reviewer Lens:** AE / R3  
**Location:** `LLM_or.pdf`, Section 6.2, especially the “Results” paragraph on pp. 35–36; `real_data_remeasurement_checklist.md`, sections 3–5 and 9  
**Issue:** The real-data claims are currently stronger than the robustness evidence that your internal process says is settled.  
**Evidence:** The manuscript says Nested WAIT has lower latency throughout the lmsys sweep and reports point estimates at \(\lambda = 60\) and \(\lambda = 100\). Your internal checklist, however, says that near-crossover denser sweeps, long-horizon validation, seed-repeatability checks, and hyperparameter robustness are still needed before saying more than “observed sweep outcomes.”  
**Why it matters:** This is not a contradiction inside the PDF package, but it is a **submission-risk asymmetry**: the figures look publication-ready, while the underlying confidence level is still draft-like.  
**Fix:** Either finish the robustness program or dial the prose back to: “On the observed 10–150 sweep, Nested WAIT is lower-latency than Sarathi throughout; we regard the figure as evidence of robustness under a heterogeneous real distribution, not as a precise estimate of the real-data stability boundary.”

Attack:  
**Severity:** Minor  
**Reviewer Lens:** General OR reader  
**Location:** `LLM_or.pdf`, real-data figure axis text around p. 36  
**Issue:** The real-data figure still appears to use `QPS` on the axis label even though the main text has been cleaned to use arrival rate \(\lambda\) consistently.  
**Evidence:** The extracted figure text shows `Arrival rate QPS (queries/s)` on the real-data panels, while the surrounding manuscript prose uses \(\lambda\). Your own internal style notes explicitly tried to eliminate this drift.  
**Why it matters:** Tiny issue, but exactly the kind of consistency miss that weakens the impression of a painstakingly revised major revision.  
**Fix:** Change the figure axis text to “Arrival rate \(\lambda\) (queries/s)” or “Arrival rate (queries/s)” and keep the notation synchronized with the main text.

Attack:  
**Severity:** Minor  
**Reviewer Lens:** R3 / General OR reader  
**Location:** `response_letter.pdf`, pp. 14–15; `LLM_or.pdf`, pp. 30–33 and 35–36  
**Issue:** Some of the “three-regime latency advantage” rhetoric is a little stronger than the plots themselves.  
**Evidence:** The paper is careful in several places: for the single-type workload, it says policies are close at low load and diverge near the boundary; for the long-decode workload, it says the three policies are nearly indistinguishable at low rates and separate mainly near the boundary. That is good. But response-letter language can still be read as implying a meaningful advantage throughout underloaded, near-capacity, and overloaded regimes.  
**Why it matters:** Reviewer 3 will punish any hint of rhetorical oversell.  
**Fix:** Phrase low-load behavior as “comparable,” not “better”; reserve the strong comparative language for near-capacity and overloaded regimes where the figures actually show meaningful separation.

## What to soften, move to appendix, or back with replication evidence

Attack:  
**Severity:** Major  
**Reviewer Lens:** AE / DE  
**Location:** `LLM_or.pdf`, Section 6.2; `response_letter.pdf`, pp. 14–15  
**Issue:** The real-data section is the part most worth **backing with replication evidence**, not the part to rhetorically upgrade.  
**Evidence:** Your own checklist asks for denser sweeps, seed repeats, long-horizon validation, and durable source-of-truth reconstruction before stronger claims are made.  
**Why it matters:** This is the one place where added evidence buys a lot more credibility than added prose.  
**Fix:** If time is limited, prioritize in this order:  
- exact per-rate config reconstruction for the current figure;  
- dense local sweep around the crossover;  
- repeated seeds at \(40, 50, 60, 100\);  
- horizon doubling near the crossover.  
If you cannot do this, soften rather than decorate.

Attack:  
**Severity:** Suggestion  
**Reviewer Lens:** General OR reader  
**Location:** `LLM_or.pdf`, Section 6.2 threshold-allocation paragraph  
**Issue:** The real-data threshold-allocation paragraph is defensible, but it is also one of the densest implementation-heavy passages in the main text.  
**Evidence:** It currently explains \(L\), \(\Delta l'_k\), \(\lambda'_k\), \(p_k\), \(q_k\), \(n_k\), integerization, and the role of `tl` in one stretch.  
**Why it matters:** It solves a reproducibility problem, but it also slightly interrupts the narrative flow.  
**Fix:** Keep the conceptual part in the main text and consider moving the last integerization sentence or the exact stage-budget apportionment detail to an appendix or short online supplement—**but only if** reproducibility remains intact.

Attack:  
**Severity:** Suggestion  
**Reviewer Lens:** AE  
**Location:** `response_letter.pdf` overall tone  
**Issue:** The response letter is now professional and non-defensive, but it would gain credibility from one more explicit statement of what remains simplified.  
**Evidence:** The paper clearly states the decode-dominant scope and single-GPU setting; the letter mostly emphasizes what was repaired.  
**Why it matters:** Editors often trust revisions more when authors explicitly distinguish “fixed” from “out of scope.”  
**Fix:** Add one sentence near the top-level revision summary: “We retained a simplified single-GPU, recomputation-based serving model and now state its intended decode-centered scope explicitly rather than presenting it as universal.”

## What not to over-edit

These parts are now genuinely strong and should **not** be destabilized by another large rewrite:

- **The open-system reframing in Section 2.4 and Section 3.** This is the single most important conceptual repair. The revised manuscript now clearly defines effective throughput as completed work net of eviction, states that stable open systems match offered load, and reframes the fluid model as a stability benchmark. That directly answers Reviewer 3’s biggest queueing-theory objection.

- **The memory model in Section 2.3.** Counting **all resident GPU KV caches**, making eviction explicit, and modeling restart under LIFO is a major improvement over the original “current batch” ambiguity. This is one of the most effective parts of the revision.

- **The FCFS cascade example and WAIT motivation in Section 4.** The example is concrete, intuitive, and does real argumentative work. Keep it.

- **The unknown-output-length explanation in Section 5.** Example 3 plus the segment-boundary explanation is one of the clearest pieces of the revised paper. It makes Nested WAIT look principled rather than ad hoc.

- **Appendix H.2 and H.4.** The A100/SGLang validation and PD-disaggregation material are exactly the kind of appendix evidence that makes the revision feel serious. Do not prune them unless space absolutely forces it.

- **The new latency-versus-arrival-rate experimental framing.** This is the right answer to the “unstable-regime latency is not meaningful” criticism. Keep that framing intact.

## Reviewer-specific bottom line

- **AE:** Much improved. Likely no longer a “writing-is-fatal” paper. Remaining concern is whether the numerical package, especially lmsys, feels fully trustworthy and stable enough for acceptance.
- **Reviewer 1:** Probably satisfied.
- **Reviewer 2:** Probably satisfied if you keep the A100/SGLang evidence, parameter descriptions, and no-wait comparison intact. A small extra sentence linking experiments back to the decode-dominant modeling regime would help.
- **Reviewer 3:** Still the swing reviewer. The paper is far stronger than before, but this reviewer could still resist on **significance** or on any impression that the lmsys evidence is polished faster than it is audited.
- **DE / final decision risk:** The package now looks like a serious major revision, not a cosmetic rewrite. The main thing that can still hurt you is **claim strength outrunning provenance strength** in the real-data section.

## Response-letter edits that would most improve credibility

- Soften real-data language from “systematically better across regimes” to “lower latency on the observed sweep; exact real-data boundary characterization is beyond the present figure.”
- Add one sentence explicitly acknowledging the retained model scope: single GPU, decode-centered time model, recomputation-based eviction.
- If any numerical figure changes after reruns, re-audit every response-letter sentence tied to Section 6 or Appendix H before submission.

## Open questions and limitations of this audit

This is a **document-level revision audit** of the uploaded package: original submission, review materials, revised manuscript, response letter, and internal revision-state documents. I did **not** rerun experiments or independently verify the underlying database/provenance beyond what your own internal notes disclose. On that basis, the paper is **substantially improved but still risky**, with the remaining risk concentrated in **real-data evidentiary auditability** and **Reviewer 3 significance framing**.