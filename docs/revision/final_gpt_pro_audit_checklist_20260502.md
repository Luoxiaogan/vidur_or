# Final GPT-Pro / Deep-Research Audit Checklist - 2026-05-02

This checklist consolidates the latest GPT-Pro audit feedback and the attached deep-research report. It is intended to guide the final targeted revision pass before resubmission. The core conclusion from both audits is that no new experiments are required; the remaining work is claim-scope control, proof-coverage verification, exposition polish, and response-letter alignment.

## Current Verdict

- Status: targeted revision checklist resolved as of the latest pass.
- Main reason: the previously localized risks around proof coverage, abstract/contribution scope, real-data tuning interpretation, and response-letter tone have been patched or scoped in the active manuscript/response-letter sources.
- Submission posture: ready for final PDF-level review and advisor-facing package review, subject to the user's final approval.

## P0 - Must Resolve Before Submission

### P0.1 Proposition 4 proof coverage

- Audit concern: the revised main text states Proposition 4, a matching lower bound for latency and TTFT for any non-predictive online policy when \(C=M^*\), but the appendix visibly lists proofs for Propositions 1, 2, 3, and 5 only.
- Risk: a formal proposition without proof is high risk because the reviewers explicitly asked for proof clarity.
- Required action:
  - Verify whether a proof exists under a different label or is embedded in another proof.
  - If yes, add an explicit appendix subsection and cross-reference.
  - If no, either add a proof or downgrade the proposition to a discussion/remark.
- Owner decision needed: keep as formal proposition with proof, or soften.
- Resolved in `papers/Appendix.tex`: added an explicit appendix proof subsection and kept the formal proposition. The response letter does not foreground this proposition because it was not a reviewer-specific request.

### P0.2 Abstract claim-scope control

- Audit concern: the abstract can be read as saying the full vLLM/Sarathi comparison was physically run on A100.
- Correct scope: main policy comparisons are Vidur simulations configured for A100; physical A100/SGLang experiments are supplemental validation.
- Required action:
  - Distinguish "Vidur simulations configured for A100" from "physical-A100/SGLang validation."
  - Avoid implying every main baseline comparison was fully reproduced on physical GPU.
- Resolved in `papers/abstract.tex`: final wording distinguishes Vidur simulations configured for A100 from experiments on a real A100 GPU.

### P0.3 Safety-buffer wording

- Audit concern: "logarithmic in the failure probability" is technically wrong or misleading.
- Correct wording: logarithmic in the horizon and inverse failure probability.
- Required action:
  - Patch abstract and any theorem/theorem-summary language if needed.
- Resolved in `papers/abstract.tex`: safety buffer is described as logarithmic in the horizon and inverse failure probability.

### P0.4 Response-letter overclaim / proof-organization claim

- Audit concern: response letter says the appendix is reorganized around theorem/proposition proof logic. This is unsafe if Proposition 4 remains unproved.
- Required action:
  - Resolve P0.1 first.
  - Then align response letter with actual proof coverage.
  - Replace broad "fully addressing" style language with more precise editorial language.
- Resolved in `papers/response_letter.tex`: broad `fully addressing` language was removed, proof-organization claims now match the modular appendix structure, and P0.1 proof coverage has been restored.

## P1 - Strongly Recommended Claim-Strength Edits

### P1.1 Contribution bullet: asymptotic optimality

- Audit concern: "Both algorithms are asymptotically optimal" is too broad.
- Correct scope:
  - Under the affine, decode-centered model;
  - under the stated long-horizon scaling;
  - relative to the fluid effective-throughput benchmark;
  - with the stated latency/TTFT guarantees.
- Required action:
  - Patch Introduction contribution bullet and any similar statements in abstract/conclusion.
- Resolved in `papers/introduction.tex` and `papers/conclusion.tex`: contribution and conclusion scope are tied to the affine decode-centered model, stated memory conditions, and the fluid effective-throughput benchmark.

### P1.2 Memory-overflow prevention wording

- Audit concern: "prevent memory overflow" sounds unconditional.
- Correct scope:
  - WAIT: under the threshold memory condition.
  - Nested WAIT: under the finite-horizon safety-buffer condition, with high probability.
- Required action:
  - Replace unconditional language with condition-scoped language where needed.
- Resolved in `papers/abstract.tex`, `papers/introduction.tex`, `papers/known_type.tex`, and `papers/unknown_type.tex`: WAIT eviction-prevention claims are scoped to stated/corresponding memory conditions, and Nested WAIT memory-overflow claims are scoped to the finite-horizon high-probability safety buffer.

### P1.3 Empirical stability-region wording

- Audit concern: "enlarge the realized stability region" can sound like a theorem claim.
- Correct scope: empirically realized stable operating range in the tested simulation/GPU-validation settings.
- Required action:
  - Use empirical/simulated/tuned comparison language in abstract, introduction, numerical section, and response letter.
- Resolved in `papers/introduction.tex`, `papers/abstract.tex`, and `papers/conclusion.tex`: empirical claims now use stable-region language and distinguish simulation from real-GPU validation.

### P1.4 Real-data tuning interpretation

- Audit concern: Section 6.2 real-data results may read like per-arrival-rate oracle tuning.
- Correct scope:
  - Nested WAIT is distribution-aware;
  - parameters are selected from a prespecified grid using workload distribution and offered arrival rate;
  - the curve is a rate-aware calibrated implementation, not one fixed untuned parameterization.
- Required action:
  - Resolved in Section 6.2 and the response letter: real-data calibration is described as a prespecified grid using workload distribution and offered arrival rate, with no realized future arrivals or individual output-length predictions.

### P1.5 GPU validation scope

- Audit concern: main text and response letter should not imply full physical-GPU replication of every simulator baseline comparison.
- Correct scope:
  - A100/SGLang validation supports the iteration-time model and implementation behavior;
  - main policy league tables remain Vidur simulations configured for A100.
- Required action:
  - Resolved in Section 6, the appendix opener, abstract, conclusion, and response letter: main policy comparisons are Vidur simulations configured for A100; physical-GPU experiments are supplemental validation and implementation checks.

## P2 - Exposition / OR-MS Style Improvements

### P2.1 Response letter opening

- Audit concern: current opening is complete but somewhat template-like.
- Suggested direction:
  - Lead with three main review-team messages: open-system objective, resident-memory semantics, and theoretical difficulty beyond routine stability.
  - Then summarize how the revision addresses each.
- Required action:
  - Rewrite opening paragraph and possibly compress seven bullets into fewer higher-level points.
- Resolved conservatively in `papers/response_letter.tex`: kept the clear overview structure, but smoothed the theoretical-contribution bullet with the exogenous-service/endogenous-memory-growth contrast and replaced the awkward `Professionalized the exposition` label with `Improved exposition and organization`.

### P2.2 Section 2.4 objective paragraph

- Audit concern: still can be made more queueing-native and less implementation-heavy.
- Target message:
  - With exogenous arrivals, stable policies cannot complete more useful work than offered load.
  - Scheduling preserves useful service by avoiding restart waste and controlling delay.
  - Effective throughput is completed decode-token service net of evictions; latency and TTFT describe how service is delivered.
- Required action:
  - Optional polish only; current version is substantially improved.

### P2.3 Fluid model \(M^*\) exposition

- Audit concern: formulas are correct, but reader needs a clearer plain-English mapping.
- Target message:
  - \(M^*\) is the resident-memory requirement for the fluid equilibrium.
  - Long decode is costly because it increases both the number of occupied stages and average cache size.
  - This creates approximately quadratic dependence on decode length away from the critical denominator.
- Required action:
  - Add or refine one short explanatory paragraph.
- Resolved in `papers/fluid.tex`: the text now states that \(M^*\) is the resident-memory requirement for the fluid equilibrium, explains the approximately quadratic dependence on decode length away from the critical denominator, and connects long-decode pressure to threshold control.

### P2.4 Theorem 1/2 proof-roadmap wording

- Audit concern: proof explanations are better but should emphasize policy-induced dimensionality reduction.
- Target message:
  - The nontrivial step is not proving recurrence after a stable queue is isolated.
  - WAIT/Nested WAIT first create threshold/boundary queues before memory overflow occurs.
  - This reduces a high-dimensional memory-coupled controlled process to tractable queues plus memory-feasibility checks.
- Required action:
  - Polish theorem interpretation paragraphs if time allows.
- Resolved in `papers/known_type.tex` and `papers/unknown_type.tex`: theorem interpretation paragraphs emphasize that WAIT/Nested WAIT create threshold or boundary queues before overflow, reducing the high-dimensional memory-coupled controlled process to tractable queues plus memory-feasibility conditions.

### P2.5 Notation mapping

- Audit concern: \(M^*\), \(M^\pi\), and \(M_{\mathrm{req}}^{(\zeta,\pi)}\) can still be hard to parse.
- Suggested mapping:
  - \(M^*\): fluid-equilibrium memory requirement.
  - \(M^\pi\): base threshold memory of a chosen policy.
  - \(M_{\mathrm{req}}^{(\zeta,\pi)}\): physical memory requirement after finite-horizon/high-probability safety buffers.
- Required action:
  - Add short mapping around Section 4.3 and Section 5.2 if current text is not enough.
- Resolved in `papers/known_type.tex` and `papers/unknown_type.tex`: current text maps \(M^*\) to the fluid-equilibrium memory requirement, \(M^\pi\) to base threshold memory, and \(M_{\mathrm{req}}^{(\zeta,\pi)}\) to the physical memory requirement including finite-horizon safety buffers when needed.

## P3 - Careless / Consistency Checks

### P3.1 Splitwise citation

- Audit concern: Splitwise should cite `patel2024splitwise`, not the cost blog `patel2023peeling`.
- Already patched preliminarily in `papers/introduction.tex`; final search needed.
- Resolved: active paper-facing sources cite Splitwise with `patel2024splitwise`; stale Patel 2023 wording appears only in bibliography/state context where appropriate.

### P3.2 Preemption semantics

- Audit concern: make clear that preemption means pausing while KV cache remains GPU-resident; it does not mean free CPU/SSD swapping.
- Already patched preliminarily in `papers/model.tex`; user should review.
- Resolved in `papers/model.tex` and `papers/unknown_type.tex`: preemption is described as scheduler-side pausing with GPU-resident KV cache retained, not CPU/SSD swap-out.

### P3.3 Known/unknown type wording

- Check for inconsistent use of "known arrival types" vs. "known output lengths at admission."
- Desired wording:
  - known output lengths / known prompt types when output length is known at admission;
  - unknown output lengths when type is revealed by decode progress.
- Resolved in `papers/known_type.tex`, `papers/unknown_type.tex`, `papers/introduction.tex`, and `papers/response_letter.tex`: paper-facing narrative now uses known/unknown output lengths or output-length classes; mathematical `type j` remains as the class index.

### P3.4 Effective throughput vs. effective completion rate

- Check captions and text:
  - effective throughput = token-level completed decode-token service net of eviction;
  - effective completion rate = request-level completions per unit time in experiments.
- Resolved: Section 2 defines token-level effective throughput, while Section 6 captions and prose use request-level effective completion rate for plotted completion-rate panels.

### P3.5 PD wording

- Audit concern: "closely matches the modeling assumptions" may be too strong.
- Suggested wording: "aligns more closely with the decode-centered timing model."
- Resolved in `papers/appendix_b_additional.tex`: PD wording now says the architecture aligns more closely with the decode-centered timing model.

### P3.6 Final stale-phrase search

- Search active sources and PDFs for:
  - `fully addressing`
  - `heavy traffic` outside bibliography/reviewer context
  - `in-flight limit`
  - `threshold collection`
  - `tl=400`, `tl=1000`
  - `direct vLLM measurements`
  - stale "Splitwise (Patel 2023)" phrasing
- Active-source search completed after the latest edits. Remaining hits are checklist/state/reviewer-context text, not paper-facing stale phrases.

## P4 - Response Letter Specific Edits

### P4.1 Rename queueing/latency response section

- Current concern: "Response to Queueing-Theory and Latency Concerns in the Decision Letter" may obscure that this addresses the negative referee.
- Suggested title: "Response to Referee 3 and Decision-Letter Queueing/Latency Concerns."
- Resolved conservatively in `papers/response_letter.tex`: the section title now avoids referee-count assumptions while explicitly foregrounding queueing, stability, and latency concerns.

### P4.2 Reduce repetitive gratitude phrases

- Current concern: repeated "This point is well taken" and similar language can sound formulaic.
- Desired style:
  - keep gratitude;
  - state the concrete change directly;
  - vary sentence openings.
- Resolved in `papers/response_letter.tex`: active-source checks no longer find repeated `well taken` / `We agree` openings, and the response now varies between gratitude, direct revision descriptions, and mechanism-focused explanations.

### P4.3 Scope limitations in closing/opening

- Add a concise limitation acknowledgment:
  - formal guarantees are for the affine decode-centered model and stated long-horizon scaling;
  - real-data parameters are selected from a prespecified rate-aware grid.
- Resolved in `papers/response_letter.tex`: the opening scopes the formal guarantees to the affine decode-centered model and asymptotic setting, while the numerical response states the prespecified workload/rate-aware real-data calibration grid.

### P4.4 Related-work response

- Add a clearer contrast axis:
  - information structure;
  - memory-dependent service-time model;
  - eviction/restart accounting.
- Resolved in `papers/response_letter.tex`: the related-work response contrasts classical exogenous-service formulations with endogenous KV-cache memory growth, output-length revelation, and eviction-induced restarts.

## Preliminary Patches Already Made Before This Checklist

These changes were made before pausing for checklist organization and should be reviewed before continuing:

- `papers/abstract.tex`
  - clarified Vidur A100-configured simulation versus physical A100/SGLang validation;
  - scoped asymptotic benchmark to the affine decode-centered model;
  - corrected safety-buffer wording to horizon and inverse failure probability.
- `papers/introduction.tex`
  - scoped contribution bullet around stated memory conditions and affine decode-centered model;
  - changed empirical stability-region wording to "empirically realized stable operating range";
  - corrected Splitwise citation to `patel2024splitwise`.
- `papers/model.tex`
  - clarified preemption as GPU-resident pausing and not CPU/SSD swap-out.

## Suggested Execution Order

1. Review the preliminary patches above with the user.
2. Resolve P0.1 Proposition 4 proof/remark decision.
3. Patch response letter opening and queueing/latency section title.
4. Patch Section 6.2 real-data tuning scope.
5. Patch any remaining theorem/abstract/conclusion claim-scope issues.
6. Compile paper and response letter.
7. Run final stale-phrase and consistency searches.
8. Update paper-state/progress docs after final approval.


## 2026-05-02 status update

- Added an explicit proof for the boundary-delay lower bound proposition in `papers/Appendix.tex`, while keeping the response letter focused on reviewer-raised proof-organization concerns rather than foregrounding this proposition.
- Refined abstract, introduction, conclusion, Section 6 real-data calibration, Additional Experiments GPU-validation scope, and response-letter wording to address P0/P1 claim-scope risks.
- Current compiled `LLM_or.pdf` and `response_letter.pdf` pass after the latest edits; P0--P4 checklist items have been closed in the active sources, leaving only final PDF-level review and advisor-facing package review.
- Completed an active-source stale-phrase pass for `fully addressing`, `in-flight limit`, `threshold collection`, stale `tl` values, direct-vLLM phrasing, and related claim-scope terms; remaining hits are reviewer-context wording or non-paper archival files.
- Smoothed several response-letter openings to reduce repetitive `well taken` / `we agree` phrasing while preserving a respectful response tone.
- Updated response-letter section title to avoid reviewer-number assumptions and sharpened the related-work response around information structure, memory-dependent batch timing, and eviction/restart accounting.
