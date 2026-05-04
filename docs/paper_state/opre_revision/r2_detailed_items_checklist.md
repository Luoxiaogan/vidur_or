# Reviewer 2 Detailed-Item Checklist

This checklist tracks the detailed notation, proof, and experiment items in Reviewer 2's report. It is for internal submission QA and response-letter alignment.

## Modeling and Section 2

- [x] Clarify the operating regime of Equation (1): decode-dominant KV-cache loading, with nonlinear or piecewise-linear service curves possible outside this regime.
- [x] Clarify the inference-time validation figure/setup from the original Figure 3 comment: the current main-text figure now uses A100 Llama-2-7B validation results and states the batch composition explicitly, with input length \(256\), output length \(20\), batch states that may contain requests at different decode stages, x-axis equal to batch KV-cache size, and y-axis measured batch inference time. The paper-facing text now distinguishes the Llama-2-7B profiling-supported range \(B\le128\) from the additional \(B=256\) extrapolation check, whose recorded A100 error is \(4.93\%\).
- [x] Separate prompt type, decode stage, prefill length, and decode length notation: \(j(i)\), \(s_i^t\), \(l_j\), and \(l_j'\).
- [x] Clarify \(s_i^t=0\) as the prefill stage.
- [x] Clarify that the performance metric counts completed decode-token service and not prefill throughput.
- [x] Clarify the policy class and preemption convention: preemption keeps KV cache resident on GPU; eviction discards KV cache and restarts from prefill.

## Fluid Model and Theoretical Statements

- [x] Correct \(d\), \(d_0\), and \(d_1\) inconsistencies in the fluid calculations.
- [x] Clarify that \(M^*\) is the memory requirement needed to support the fluid equilibrium, not a throughput-optimal memory level.
- [x] Explain why \(C\ge M^*\) is a theoretical capacity condition and not a guarantee that an arbitrary online policy remains balanced.
- [x] Add the quadratic decode-length dependence of \(M^*\), clarifying why long responses make memory control important.
- [x] Clarify Proposition 2 / fluid upper-bound interpretation under exogenous arrivals: stable completed service cannot exceed the offered decode-token load.
- [x] Replace heavy-traffic wording with long-horizon/asymptotic-regime wording under fixed load.

## Proof Appendix

- [x] Add decode-stage advancement logic in Theorem 1's proof: completion requires staged advancement, not immediate departure after one queue service.
- [x] Define \(\Delta T(\cdot)\), \(M^\pi\), and \(M^*\) before they are used in theorem/proof statements.
- [x] Distinguish deterministic comparison slots from actual event-driven WAIT batches.
- [x] Add GPU-resident memory accounting: unselected decode prompts remain GPU-resident and count against memory.
- [x] Add one-slot delayed dominance for transferring the periodic comparison process back to actual WAIT.
- [x] Add Nested WAIT post-review boundary-residual convention supporting the tight \(n_k+\theta_k^{-1}\log(\cdot)\) safety buffer.
- [x] Cite standard reflected-random-walk, Cramer-Lundberg, Doob maximal-inequality, and Kingman-type tools where appropriate.
- [x] Remove or correct stale undefined/ambiguous appendix symbols, including the old booking-limit wording and old \(S^k\)-style notation.

## Experiments

- [x] State Section 6 hardware, simulator, baseline configurations, arrival-rate grids, and replication count.
- [x] Reconcile the lmsys dataset summary with the plotted distribution: the paper now states the filtered workload population, mean/median prefill and decode lengths, and short/long response shares consistently with Figure~`\ref{fig:lmsys_distribution}`.
- [x] State Sarathi's chunked-prefill configuration role and the baseline memory-reservation rule.
- [x] State WAIT / Nested WAIT threshold-construction rules and the main real-data tuning grids: \(\mathrm{tl}\in\{20,40,\ldots,200\}\), \(L\in\{1,2,3,4,5,10,20\}\), and \(\eta=0.05\).
- [x] Add a quantitative real-data \(M^*(\lambda)\) versus \(C\) check: Table~`\ref{tab:lmsys_mstar}` reports representative fluid-memory values for the real dataset and places the fluid stable-region crossing near \(74.1\) requests/s under memory capacity \(C\).
- [x] Add simulator-to-GPU validation on A100 and end-to-end real-GPU checks.
- [x] Add long-decode workload \(\texttt{p512d1000}\) and near-capacity eviction-induced restart diagnostic.
- [x] Add threshold-without-waiting diagnostic on the single-type workload.
- [ ] Reconstruct durable per-arrival-rate source data and selected Nested WAIT configurations for the full lmsys Figure D comparison before making any stronger real-data stability-boundary claim. Current main text intentionally reports the calibration rule and finite grids, not a full per-point provenance table. Current submission status: safe under the present claim strength; do not upgrade the real-data discussion to a sharp stability-boundary or exact per-rate configuration claim until this is resolved. 2026-05-02 SQL audit: `real_data_provenance_valid` covers only QPS \(10,20,50,60\), with 28 valid metric rows; three malformed historical rows were isolated in `real_data_provenance_malformed`.

## Related Work and Positioning

- [x] Add objective related-work coverage for concurrent LLM-inference scheduling theory, including online/regret/robust-prediction models and stochastic batch-processing models.
- [x] State the distinction from these papers positively: existing works establish guarantees under their timing and information models, while this paper links a memory-dependent iteration-time model to the fluid stability region and eviction-control mechanism.
- [x] Align the response letter with the related-work paragraph: acknowledge the reviewers' request, describe the added references, and avoid claiming priority over concurrent work.

## Current One-By-One Review Pass

- Last checked point: related-work / concurrent-paper positioning. Status: covered in both manuscript and response letter.
- Last checked point: real-data Figure D provenance. Status: still open for exact rerun reproducibility, but safe under the current manuscript/response-letter claim strength because the text reports the calibration rule and finite grids without claiming a sharp real-data stability boundary or a per-rate provenance table.
- Last checked point: compact experimental-parameter reporting. Status: covered through Section 6 prose plus Appendix B GPU/replication/parameter details; no new main-text table is needed unless the response letter starts promising a table.
- Last checked point: capacity and memory-number consistency. Status: covered. Paper-facing text consistently separates physical capacity \(C\), fluid memory requirement \(M^*\), base threshold memory \(M^\pi\), scaled-policy required memory \(M_{\mathrm{req}}^{(\zeta,\pi)}\), and experimental \(\mathrm{tl}\) as a system-wide batch-size cap rather than a resident-memory guarantee. The real-data subsection now also includes Table~`\ref{tab:lmsys_mstar}` to compare \(M^*(\lambda)\) with memory capacity \(C\) at representative arrival rates.
- Last checked point: Proposition 1 capacity-cut framing. Status: patched without weakening the statement. The proof now uses a service-capacity cut rather than a balanced-batch argument, and the original `>=1` condition is supported by using \(d_0>0\) and finite memory capacity at equality.
- Last checked point: Proposition 5 / unknown-output lower bound formal status. Status: kept as a proposition and refined the appendix proof around an indistinguishable two-type construction with binomial survivor fluctuations at the first boundary; no weakening of the statement.
- Last checked point: Theorem 2 memory notation and threshold integerization convention. Status: patched. \(C\), \(M^\pi\), and \(M_{\mathrm{req}}^{(\zeta,\pi)}\) are separated, and WAIT/Nested WAIT/segment-design theorem text now states the integer-threshold rounding convention with \(O(1)\) changes absorbed.
- Last checked point: final QA compile and negative searches. Status: main paper compiles to 83 pages, response letter is up to date, and stale-phrase searches are clean on current paper-facing sources.
- Last checked point: post-caption-restore consistency pass. Status: response letter remains aligned with the current manuscript posture; Figure D PDF axis labels use `Arrival rate \(\lambda\)` and `Effective completion rate`; related-work/concurrent-paper positioning is covered without priority claims; time-varying extension separates throughput/memory guarantees from the additional first-segment waiting condition needed for service-normalized delay.
- Last checked point: response-letter sentences tied to Section 6 / Additional Experiments after the lmsys distribution-figure regeneration. Status: aligned with the conservative manuscript posture. Response letter reports setup details, finite real-data grids, A100 memory-cap calculation, simulator-to-GPU validation, and GPU-run parameter reporting without claiming a sharp lmsys stability boundary or full per-rate provenance table.
- Last checked point: generated figure captions versus PDFs, especially real-data, long-decode, simulator-validation, and GPU panels. Status: active captions match the generated figure files. Patched the response-letter description of the old L20 profiling replacement to say the revised A100 profiling figure uses the same GPU model as the main Vidur configuration.
- Last checked point: appendix references and labels after moving Extension and Notation appendices. Status: current logs show no undefined references/citations; Extensions, Notation Summary, Additional Experiments, GPU validation, PD disaggregation, and proof appendix labels resolve in the active source.
- Last checked point: PDF-level proofread for visible placeholders, unresolved markers, and stale terminology after final compile. Status: compiled main paper and response letter text contain no unresolved `??`, placeholder text, stale `tl=400/1000`, or old parameter phrasing; remaining LaTeX messages are nonfatal underfull/float-placement warnings.
- Next point to check: none on the current R2 detailed-item checklist except the deliberately open real-data per-arrival-rate provenance item. The 2026-05-02 SQL audit confirms this item remains open, but it is submission-safe only under the current conservative claim strength.
