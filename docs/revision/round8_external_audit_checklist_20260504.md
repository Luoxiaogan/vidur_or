# Round8 External Audit Checklist - 2026-05-04

Sources:
- `docs/research/round8/deep-research-report (2).md`
- User-pasted round8 audit report beginning with verdict "Mostly improved, but I would not resubmit as-is."

## Overall Triage

Both reports agree that the revision is substantially stronger than the original submission. The core first-round concerns are mostly addressed: open-system throughput framing, GPU-resident KV-cache memory accounting, arrival-rate latency/completion-rate experiments, linear service-time-model scope, and broad exposition quality.

The remaining risk is concentrated in claim scope and proof readability, not in a need to redesign the whole paper. The highest-risk attack points are:
- Multi-type WAIT proof/coupling: a skeptical queueing reviewer may question whether event-driven partial batches pay extra fixed overhead relative to the auxiliary full-threshold process.
- Nested WAIT memory guarantee: the logarithmic safety buffer grows with horizon/failure-probability requirements, so front-facing language must not read like an unconditional fixed-memory asymptotic theorem.
- Real-data tuning: per-arrival-rate grid selection is transparent but can look rate-aware/oracle-like unless carefully labeled.
- Real-GPU validation: should remain supplemental validation and implementation evidence, not a claim that all Vidur comparisons are physically replicated.

## P0 - Must Resolve Before Resubmission

### P0.1 Multi-Type WAIT Coupling / Fixed-Overhead Objection

**Audit concern.** The auxiliary embedded full-threshold process pays the fixed overhead \(d_0\) once per reference batch, while event-driven WAIT could launch several smaller subset batches and pay \(d_0\) multiple times. A reviewer may argue that the coupling controls an embedded opportunity scale but not calendar-time service opportunities.

**Current manuscript status.**
- Current proof already uses an auxiliary embedded full-threshold process and sample path coupling.
- The paper should not describe this as a loose comparison or heuristic. It should frame the proof as a coupling between event-driven WAIT and a conservative embedded process, with explicit accounting for calendar-time duration.

**Recommended fix.**
- Add a local proof clarification in `pf_thm_wait.tex`:
  - State that the event-driven policy is single-server and non-overlapping.
  - The embedded process is used to create conservative review epochs in calendar time, not to replace actual batches one-for-one.
  - The one-slot lag bound is in physical time because any in-service WAIT batch has duration at most the full-threshold duration \(\Delta^\pi/\zeta\).
  - If a type is skipped due to the server being busy, its delay is charged to the same one full-threshold slot.
- Avoid weakening the theorem unless this clarification reveals a real gap.

**User preference.** Do not self-deprecate the proof. Present it as a coupling technique using queueing-theory language, not as a "comparison clock."

### P0.2 Nested WAIT Finite-Horizon Safety Buffer Scope

**Audit concern.** The safety buffer grows like \(\log(m(1+\zeta T/d_0)/\delta)\). For fixed physical memory \(C\), the high-probability physical feasibility guarantee applies only when the required buffer fits in memory.

**Current manuscript status.**
- Theorem 2 and proof already separate no-overflow dynamics from high-probability physical feasibility.
- Some abstract/contribution/response-letter phrasing may still be overread as unconditional memory safety.

**Recommended fix.**
- Search and tighten front-facing phrases around Nested WAIT:
  - Prefer: "finite-horizon safety buffer" / "additional safety buffer" / "under the stated memory condition."
  - Avoid: unconditional "prevents overflow" or broad "asymptotically optimal" without qualifiers.
- Keep language concise; do not overburden the abstract with long theorem caveats.

### P0.3 Real-Data Tuning Protocol Label

**Audit concern.** Section 6.2 reports the lowest-latency configuration from a prespecified grid for each offered arrival rate. This may look like hindsight tuning unless explicitly framed.

**Current manuscript status.**
- Current text already says the online scheduler does not use future arrivals or individual final output lengths.
- User prefers not to keep foregrounding this issue in future external-audit prompts.

**Recommended fix.**
- Add one natural sentence in Section 6.2 if not already present:
  - "The resulting curve should be read as a rate-aware calibrated implementation of Nested WAIT rather than a single fixed-parameter configuration."
- Do not add defensive or lengthy calibration prose unless advisor asks.

### P0.4 Real-GPU Validation Scope

**Audit concern.** A100/SGLang validation is helpful but narrower than the full Vidur experiment suite.

**Current manuscript status.**
- The introduction should not mention SGLang.
- Response letter can cite SGLang and should say real-GPU experiments provide validation and implementation evidence, not full replication of all simulator comparisons.

**Recommended fix.**
- Keep manuscript language as "supplemental real-GPU validation" or "Appendix validation."
- In response letter, use: "physical-A100/SGLang experiments provide supplemental timing validation, support for simulator accuracy, and implementation evidence."
- Avoid saying all main policy comparisons are validated on physical GPU.

## P1 - Strongly Recommended, But Not Full Rewrite

### P1.1 Lower-Bound Propositions 3/5

**Audit concern.** Proofs may read like illustrative block-event sketches rather than formal lower bounds.

**Current status.**
- The proofs were already revised toward sample-path/block language and policy-filtration language.

**Recommended fix.**
- Do one more language pass only:
  - Use "consider disjoint blocks" / "condition on the policy's filtration" / "conditional survivor count" language.
  - Avoid adding response-letter discussion unless reviewers explicitly asked.
- Do not demote to examples unless advisor wants a much more conservative theory package.

### P1.2 Experiment-Theory Memory Terms

**Audit concern.** Table 2 reports \(M^*(\lambda)\) versus \(C\), but not always \(M^\pi/C\), thresholds, or Nested WAIT buffer terms.

**Current status.**
- Real-data \(M^*(\lambda)\) table is a useful bridge.
- A full per-workload \(M^\pi\) table could overcomplicate the paper and expose fragile provenance.

**Recommended fix.**
- Add at most one local clarifying sentence:
  - The table is a fluid stable-region diagnostic, while the plotted simulations include near-overloaded and overloaded regimes and use finite-grid threshold choices.
- Do not add a large new table unless requested by advisor.

### P1.3 Linear Service-Time Model Scope

**Audit concern.** The model is validated on a limited A100/Vidur setting and may not cover prefill-heavy or nonlinear regimes.

**Current status.**
- Section 2.2 already discusses linear model scope and richer calibrated curves.
- User prefers "linear multi-stage model with endogenous memory growth," not "decode-centered."

**Recommended fix.**
- Check that abstract/conclusion say "linear multi-stage model" and "endogenous memory growth" where appropriate.
- Avoid introducing new broad caveats that weaken the paper unnecessarily.

### P1.4 Memory Realism / Swap-Out

**Audit concern.** The model does not include CPU/SSD swap-out and swap-in latency.

**Current status.**
- Section 2.4 already states that preemption is GPU-resident pause/resume and not CPU/SSD swap-out.

**Recommended fix.**
- If needed, add one sentence near the model scope:
  - "This is the resident-serving abstraction analyzed in the paper; modeling explicit swap-out/swap-in latency would require additional state and transfer-time terms."
- Do not make this a headline limitation unless advisor asks.

## P2 - Optional Polish / Scope Discipline

- Replace broad "optimality" language with "fluid-benchmark tracking" where possible.
- Keep empirical claims to "tested configurations" / "observed transition from near-overloaded to overloaded."
- Keep overloaded latency language paired with effective completion rate; do not use "steady-state mean latency."
- If adding any proof roadmap language, keep it short and technical. Avoid adding a new figure unless there is a clear page/space plan.
- Avoid mechanical or weak phrases in response letter: "review team," "summarizes," "objects," "standard queueing objects," "decode-centered workloads."

## Not Recommended Before Resubmission Unless Advisor Requests

- Rewriting the theorem to a synchronized full-threshold WAIT variant.
- Downgrading lower-bound propositions to examples.
- Adding a full tuned-baseline grid or holdout experiment.
- Adding a large \(M^\pi\)/threshold table for every experimental workload.
- Adding a new proof-roadmap figure late in the revision unless it replaces existing text and does not increase page pressure.

## Immediate Execution Order

1. Inspect and patch the WAIT proof clarification around calendar-time coupling and fixed overhead.
2. Search abstract/conclusion/response letter for Nested WAIT memory-safety and "optimality" overclaims.
3. Check Section 6.2 real-data tuning language; add one natural rate-aware calibrated sentence if needed.
4. Check real-GPU validation scope in abstract/conclusion/response letter.
5. Compile paper and response letter.
6. Update progress/paper-state docs and regenerate audit packet only after edits are finalized.
