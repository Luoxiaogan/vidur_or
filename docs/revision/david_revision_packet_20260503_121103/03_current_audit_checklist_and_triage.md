# Minimal Packet Audit Checklist

Source: user-provided external audit comment on the minimal packet containing only original paper, revised paper, response letter, review reports, AE report, and decision letter.

Date recorded: 2026-05-03.

Merged sources:
- Minimal packet audit pasted by user on 2026-05-03.
- Round5 audit report: `docs/research/round5/deep-research-report (2).md`.

## Overall Verdict

- The revision is substantially improved and not cosmetic.
- Remaining risk is concentrated in whether the negative queueing reviewer still sees the contribution as standard queueing/pipeline filling, and whether claims around open-system throughput, memory safety, validation, and tuning are over-scoped.
- Round5 audit agrees that the package is a substantive major revision and has crossed the seriousness threshold for re-review, but still treats it as high-risk unless local scope and exposition issues are closed.

## Current Triage After 2026-05-03 Patches

- No remaining checklist item currently requires a theorem rewrite or new experiment before the next advisor/GPT audit packet.
- Highest-signal resolved items:
  - Real-GPU validation scope is now separated: main comparisons are A100-configured Vidur simulations; appendix real-GPU runs provide direct timing measurements, support for simulator accuracy, and WAIT implementation evidence. The introduction does not name SGLang, while the response letter cites SGLang explicitly.
  - Unknown-output-length scope is now framed as no runtime use of a request's realized final output length, not distribution-free scheduling.
  - The contribution is now framed around endogenous KV-cache memory growth and dimensionality reduction to threshold/boundary queues, not as routine standard queueing.
  - Generic or unintroduced phrases flagged by the user (`resident population`, `decode-centered workloads`, `standard stochastic-process objects`, mechanical `summarize(s)` style) have been removed or locked against future use in paper-state docs.
- Remaining nonblocking watch items:
  - Proposition 2 keeps the \(C\ge M^*\) stabilizable-regime framing by author choice; current text explains that \(C<M^*\) is overloaded relative to the full offered-load benchmark.
  - The experiment-theory memory table remains deliberately omitted; adding it could overexpose fragile rate-by-rate provenance and is not necessary under the current conservative claims.
  - Real-data parameter selection remains described as a workload/rate-aware prespecified-grid calibration; avoid making stronger claims about a single untuned parameterization.
  - Overloaded-regime latency should continue to be described as completed-request latency paired with effective completion rate, not steady-state mean latency.

## Round6 Audit Triage

- Overall assessment:
  - Round6 is more conservative than prior GPT-Pro audits and repeats several already-addressed risks.
  - Treat it as a claim-scope and exposition stress test, not as an instruction to reopen the theory or add new experiments wholesale.
  - Do not adopt its strongest recommendations unless a local manuscript check confirms an actual mismatch.
- Items that are already covered or mostly false positives:
  - Nested WAIT fixed-memory/log-buffer issue: main text already states that the logarithmic term is a finite-horizon safety buffer and that, for fixed physical capacity, the theorem applies only to horizons and failure probabilities satisfying \(C\ge M_{\mathrm{req}}^{(\zeta,\pi)}\). Appendix E also separates no-overflow performance from high-probability physical feasibility.
  - WAIT proof collapsing stages: Appendix D already defines deterministic comparison slots, resident-stage memory invariant, full-threshold domination, one-slot delayed dominance, and terminal backlog-to-throughput/delay conversion. This appears to be a reviewer-style misread rather than a proof gap.
  - Stable operating range language: current Section 6 uses “observed transition from near-overloaded to overloaded” and avoids “steady-state mean latency.” Continue using “stable region” only for analytical \(M^*\le C\) statements.
- Items worth a low-cost local fix:
  - Real-data GPU appendix previously labeled the unknown-output real-data implementation as “WAIT” even though it uses segment partitions and continuation-based allocation. Rename locally to “Nested WAIT” to match the main unknown-output-length policy.
  - Front-facing comparison claims should continue to say “tested baselines” or “tested baseline configurations,” especially around Vidur/SGLang comparisons.
  - The response letter can keep saying real-GPU validations were added, but should preserve the division: main policy comparisons are Vidur simulations; physical A100/SGLang runs provide timing calibration, support for simulator accuracy, and implementation evidence.
- Items not recommended before resubmission unless the advisor asks:
  - Adding a full \(M^*,M^\pi,C\) table for every experiment. This would consume space and may overexpose rate-by-rate construction details without directly addressing a theorem error.
  - Adding tuned-baseline grids or new TTFT figures. These are potentially useful but would expand the revision late and invite new methodological questions.
  - Downgrading Propositions 3/5. Current proofs were already refined; weakening them now may undercut the paper’s mechanism story.

## P0 Items From Audit

1. Proposition 2 open-system throughput framing.
   - Audit concern: Proposition 2 states an arrival-count upper bound under \(C\ge M^*\), but the bound itself does not require \(C\ge M^*\).
   - Suggested fix from audit: state the offered-load upper bound for any capacity and any nonanticipative policy; then state separately that \(M^*\le C\) is the fluid attainability/stabilizability condition.
   - Status: Partially addressed in discussion. Current direction: keep \(C\ge M^*\) in Proposition 2 because the theorem-facing benchmark is the stabilizable fluid regime, but explicitly explain after the proposition that the offered-load cap is an exogenous-arrival accounting bound and that \(C<M^*\) corresponds to overload relative to the full offered-load benchmark.

2. Experiment-theory memory table.
   - Audit concern: experiments disclose A100 KV-cache cap and parameter grids, but do not quantitatively link \(M^*\), chosen threshold memory \(M^\pi\) or \(\mathrm{tl}\), and capacity \(C\).
   - Suggested fix from audit: add a table for representative workloads/rates: workload, arrival rate, \(M^*\), chosen \(M^\pi\) or induced memory, physical cap \(C\), inside/outside fluid region.
   - Status: To discuss; may be costly and may risk overexposing weak points.

3. Real-data tuning protocol.
   - Audit concern: choosing lowest-latency configuration for each offered arrival rate can look oracle-like unless a calibration/holdout protocol is stated.
   - Suggested fix from audit: state calibration/holdout if true, otherwise describe as a best-on-grid frontier or soften comparisons.
   - Round5 emphasis: this is still one of the highest-risk experiment concerns because WAIT/Nested WAIT receive rate-aware grid calibration while baselines are closer to default configurations.
   - Status: To discuss carefully; user previously asked not to keep emphasizing this in GPT prompts. If addressed, prefer a natural local wording in Section 6 rather than a defensive caveat.

4. Memory-safety language.
   - Audit concern: unqualified “prevent overflow/eviction” should be scoped to stated memory conditions or high-probability finite-horizon guarantee.
   - Suggested fix from audit: use “under the stated memory condition” or “with probability at least \(1-\delta\).”
   - Status: Partially addressed; current abstract says “prevent memory overflow that would otherwise force evictions.”

5. Eviction/restart metrics.
   - Audit concern: clarify whether latency after eviction is measured from original user arrival or restart; clarify how restarted prompts count in simulations.
   - Suggested fix from audit: explicitly state metric convention.
   - Status: To check current Section 2/Section 6 wording.

6. Unknown-output-length scope.
   - Round5 concern: “unknown output lengths” can overclaim if it sounds distribution-free. The correct scope is that individual final output length is unknown at admission, while thresholds/segments use workload distribution and offered-rate information or estimates.
   - Suggested fix: keep this scope consistent in abstract, Section 5 opening, Section 6.2, and response letter.
   - Status: Partially addressed. The phrase “This section removes that information assumption” has been removed from `unknown_type.tex`; still need one pass for abstract/conclusion/response-letter consistency.

7. Overload latency and TTFT evidence.
   - Round5 concern: overload-region latency is computed over completed requests, so it is conditional-on-completion and not a steady-state mean latency. TTFT is a core theoretical metric but has limited numerical reporting.
   - Suggested fix: make conditional latency language clearer in Section 6/captions; either add TTFT evidence or reduce empirical TTFT language.
   - Status: To discuss. Effective completion-rate panels partially address incomplete requests.

8. Theory-to-experiment bridge.
   - Round5 concern: main theorems cover cleaner regimes, while real-data experiments use heterogeneous prefill lengths, coarse segmentation, and rate-aware calibration. Readers need a clear distinction between theorem-covered guarantees and theorem-guided implementation.
   - Suggested fix: add a short assumption/implementation bridge paragraph or table.
   - Status: To discuss; avoid overburdening main text unless needed.

## P1 Items From Audit

1. Add backlog or incomplete-request fraction for overloaded latency figures.
   - Rationale: latency is conditional on completed requests in overload.
   - Status: To discuss; effective completion rate already partially addresses this.

2. Add one concise “why this is not just positive recurrence” paragraph.
   - Rationale: emphasize state-space reduction from endogenous memory growth to threshold/boundary queues.
   - Round5 emphasis: this remains the main risk with the negative queueing referee. The strongest framing is endogenous memory growth plus eviction/restart, which expands the state/action space; WAIT/Nested WAIT reduce it to threshold and boundary queues.
   - Status: Mostly addressed in introduction/conclusion; check if further sharpening needed.

3. Explicitly label response-letter section as response to negative referee / decision-letter referee.
   - Status: To discuss; current title is “Response to Queueing, Stability, and Latency Concerns.”

4. Caveat unknown output lengths.
   - Rationale: unknown per request at admission, but distributional information is used for threshold calibration.
   - Status: To check current abstract/contributions/theorem wording.

5. Tighten real-GPU validation language.
   - Rationale: validation supports timing and limited implementation evidence, not full physical replication of all main comparisons.
   - Status: Mostly addressed.

6. Add simulation horizon/request-count/randomization details for Figures 7--9.
   - Status: To check current Section 6.

7. Real-GPU validation scope.
   - Round5 concern: Appendix H validates the timing model and limited implementation behavior, but does not fully reproduce every Vidur baseline comparison on physical GPUs.
   - Status: Mostly addressed in abstract/conclusion/response letter; one final search for overbroad “real-GPU validation” phrasing is recommended.

8. Eviction policy / swap semantics robustness.
   - Round5 concern: model now clearly uses resident KV caches and eviction/restart, but readers may ask whether results depend on LIFO or no-swap assumptions.
   - Suggested fix: add a small scope sentence if space permits.
   - Status: Optional unless a local sentence is easy.

## P2 Items From Audit

1. Shorten repetitive gratitude phrases in response letter.
2. Replace vague words such as “moderate,” “controlled,” “especially,” and “close approximation” where possible.
3. Consider a short main-text proof-sketch box for Theorem 1 or 2.
4. Add notation note distinguishing token-level effective throughput from request-level effective completion rate near Section 6.
5. Standardize capitalization for terms such as Key-Value cache, time-to-first-token, decode-centered, and prefill-decode disaggregated.

6. Language items flagged by Round5.
   - Avoid or refine: “memory is a resource to exploit rather than merely a constraint,” “This pattern matches the paper’s mechanism,” “best tradeoff on this grid,” “supports the use of Vidur,” “continues to improve decode-side delay.”
   - Preferred direction: replace abstract mechanism claims with concrete, testable descriptions of resident KV-cache control, threshold-balanced composition, and tested-setting evidence.

## Immediate Discussion Queue

1. Check current Proposition 2 and decide whether to split offered-load upper bound from \(M^*\le C\) attainability.
2. Check current metric convention for eviction/restart latency.
3. Decide whether to add any minimal \(M^*\) vs \(C\) table or avoid opening that front.
4. Decide whether the real-data grid should remain as currently worded or be reframed as a best-on-grid frontier.
5. Check if response letter should name the decision-letter/negative-referee critique more explicitly.
6. Do a consistency pass for “unknown output lengths”: unknown individual final length at admission, not distribution-free scheduling.
7. Do a consistency pass for overload latency: completed-request conditional latency plus effective completion rate.
8. Decide whether TTFT needs a small numerical supplement or only a tighter empirical-claim scope.
9. Check high-risk phrases from Round5 language audit and replace only those that sound overbroad.
