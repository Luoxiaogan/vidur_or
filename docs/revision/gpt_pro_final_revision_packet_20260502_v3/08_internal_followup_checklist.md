# Final External GPT Audit Follow-Up Checklist - 2026-05-02

This checklist consolidates the two latest external GPT review reports:

1. `docs/research/deep-research-report (1) 2.md`
2. User-pasted GPT executive audit beginning with verdict `ready after minor edits`

The combined recommendation is: **ready after minor edits / needs targeted revision**. No new experiments are requested. The remaining work is local manuscript/response-letter scope control and proof packaging.

## P0 - Discuss / Resolve Before Submission

### P0.1 Theorem 4 proof packaging

- **Concern**: Appendix A.2 states Theorem 4 as a formal theorem but only says the proof follows Theorem 2. This is weaker than the proof organization expected after the AE proof-clarity criticism.
- **Risk**: A skeptical reviewer can call this another formal theorem without a verifiable proof.
- **Options**:
  - Add a short explicit proof sketch/subsection for Theorem 4.
  - Downgrade Theorem 4 to a corollary / extension result of Theorem 2.
- **Likely fix**: Add a short proof paragraph that defines aggregated segment arrival rates, continuation probabilities, boundary queues, and shows that the same binomial thinning / martingale buffer / drift argument applies with \(L\) segment boundaries.
- **Needs user discussion**: theorem vs corollary wording.

### P0.2 Abstract GPU-validation scope

- **Concern**: Current abstract says Vidur simulations are “validated by real-A100 experiments,” which can be read as full physical-GPU validation of all policy comparisons.
- **Correct scope**: Main policy comparisons are Vidur simulations configured for A100. Physical A100/SGLang runs validate the timing model and implementation behavior, and provide supplemental end-to-end comparisons.
- **Likely fix**:
  - Replace with wording like:
    `In Vidur simulations configured for Llama-2-7B on an A100 GPU, with supplemental real-A100/SGLang validation of the timing model and implementation behavior, ...`
- **Can edit directly** after user approves wording.

### P0.3 Abstract / conclusion safety-buffer scope

- **Concern**: “finite-horizon logarithmic safety buffer preventing memory overflow and evictions” is directionally correct but underspecified.
- **Correct scope**: logarithmic in horizon and inverse failure probability; high-probability finite-horizon no-overflow feasibility under theorem conditions.
- **Potential tension**: user prefers concise abstract language and has asked to avoid long conditional phrases.
- **Needs user discussion**: how much scope to put in abstract versus theorem text.

## P1 - Strongly Recommended Edits

### P1.1 Real-data tuning protocol label

- **Concern**: Section 6.2 says “select the lowest-latency configuration on this prespecified grid for each offered arrival rate,” which is transparent but can read as per-rate oracle tuning.
- **Current protection**: Text already states calibration uses workload distribution and offered rate, and online scheduler does not use future arrivals or individual output-length predictions.
- **Recommended addition**:
  - `The resulting curve should be read as a rate-aware calibrated implementation of Nested WAIT, not as a single fixed-parameter configuration.`
  - If true, add: `The plotted replications use fresh arrival draws and are not used to choose \(\mathrm{tl}\), \(L\), or thresholds.`
- **Needs user confirmation**: whether calibration/test separation with fresh draws is literally true.

### P1.2 Empirical stability terminology

- **Concern**: Captions / Section 6 opening use “stability boundary,” which can sound theorem-like in finite simulations.
- **Current protection**: Section 6 defines \(\lambda^*\) as empirical transition point on the arrival-rate grid.
- **Recommended fix**:
  - Replace some caption uses with `empirical transition point` or `observed stability transition`.
  - Keep “stability boundary” only where already qualified or theoretically defined.
- **Can edit directly**.

### P1.3 Proposition 3 proof tightening

- **Concern**: FCFS lower-bound proof jumps from constant overflow probability to queue growth / throughput gap.
- **Recommended fix**: Add a few lines formalizing disjoint two-iteration blocks or regenerative block argument.
- **Can edit directly**, but should be proof-checked after patch.

### P1.4 Response-letter real-GPU scope

- **Concern**: Response letter can still be read as saying every main baseline comparison was physically replicated.
- **Recommended insertion**:
  - `The main policy comparisons remain Vidur simulations configured for A100 hardware; the physical-A100/SGLang experiments are supplemental validations of the iteration-time model and implementation behavior.`
- **Can edit directly**.

### P1.5 Response-letter real-data tuning label

- **Concern**: The response letter should explicitly label real-data Nested WAIT as rate-aware calibrated implementation.
- **Recommended insertion**:
  - `The real-data curve should be read as a rate-aware calibrated implementation selected from a prespecified grid, not as a single fixed-parameter Nested WAIT configuration.`
- **Can edit directly** after user confirms phrasing.

## P2 - Language / Exposition Cleanup

### P2.1 Remove or avoid empty Endnotes heading

- **Concern**: Empty `Endnotes` heading before references looks unfinished.
- **Status**: Need visual/source check. Current source defines `\notesname{Endnotes}` but this may be style metadata, not rendered empty heading.
- **Action**: inspect PDF around references before editing.

### P2.2 Introduction operational failure sentence

- **Concern**: “Users experience this as error messages (e.g., ‘Something went wrong’)” is system/blog-like.
- **Suggested replacement**:
  - `Operationally, this appears as failed or aborted generations under heavy load.`
- **Action**: locate current sentence and decide whether to patch.

### P2.3 Related work “frameworks remain scarce” / stability phrasing

- **Concern**: Since related work now cites several concurrent papers, phrases that sound dismissive should be softened.
- **Suggested replacement**:
  - `Analytical frameworks are emerging, but most focus on different timing or information models.`
  - For final sentence, use `helps explain why threshold-based admission can bring the empirically observed operating range closer to the fluid prediction in the tested settings.`
- **Action**: patch if the current wording still sounds too strong.

### P2.4 Conclusion scope and language

- **Concerns**:
  - “decouples interactions across prompt types” could be reframed as inducing lower-dimensional threshold/boundary queues.
  - “expand the empirically realized stable region” could become “stable operating range” for empirical claim scope.
  - The theorem scope sentence should keep model/memory/safety-buffer conditions clear.
- **Action**: patch after abstract/theory scope is settled.

### P2.5 Response-letter tone compaction

- **Concern**: Response letter remains professional but long/template-like in places.
- **Possible action**:
  - Compress opening bullets from six to four.
  - Reduce repeated “This suggestion led us...” / “This point is central...” phrasing.
- **Needs user decision**: response letter is already acceptable; compaction could consume time and risk new wording churn.

## P3 - Already Mostly Covered / Low Risk

### P3.1 Eq. (1) timing model scope

- **Status**: Covered in Section 2.2, Appendix H.2, and response letter.
- **Remaining only**: abstract GPU-validation scope.

### P3.2 Memory semantics

- **Status**: Covered in Section 2.3/2.4 and algorithms; GPU-resident waiting/preempted KV cache is explicit.

### P3.3 Open-system throughput objective

- **Status**: Covered in Section 2.4 and Section 6 diagnostics; response letter aligned.

### P3.4 Main proof coverage

- **Status**: Propositions 1--5, Theorems 1--3 covered.
- **Remaining only**: Appendix A.2 Theorem 4 proof packaging.

## Suggested Execution Order

1. Discuss P0.1: keep Theorem 4 as theorem with proof sketch vs downgrade to corollary.
2. Patch abstract GPU-validation and safety-buffer scope.
3. Patch real-data tuning label in Section 6.2 and response letter.
4. Patch Theorem 4 proof packaging and optionally Proposition 3 proof tightening.
5. Patch stability terminology / related-work / conclusion language.
6. Compile `LLM_or.pdf` and `response_letter.pdf`.
7. Update packet PDF and progress / paper-state docs.
