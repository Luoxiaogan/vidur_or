# Response Letter Claim Audit Checklist

Date: 2026-04-28

Scope: Check each substantive claim in `papers/response_letter.tex` against the current active manuscript `.tex` files. This file tracks whether the response letter accurately describes changes that are visible in the manuscript source.

| ID | Response-letter claim | Manuscript evidence checked | Status | Action |
| --- | --- | --- | --- | --- |
| C1 | The revision reframes the open-system objective around stability, effective throughput net of evictions, and latency over arrival-rate sweeps. | `papers/model.tex` defines effective throughput, latency, and TTFT; `papers/fluid.tex` defines the fluid stability region through `M^* <= C`; `papers/numerical.tex` explains stable completion rates and latency sweeps. | Pass | Keep. |
| C2 | Section 2 now introduces prompts, prefill/decode, batching, KV-cache growth, memory, policy space, and notation narratively. | `papers/model.tex` contains subsections for prompts, batching/time, memory, and objective/policy; `papers/appendix_notation.tex` defines `app:notation` and `tab:notation`. | Pass | Keep. |
| C3 | The memory constraint counts all resident GPU KV caches, not only the current batch; eviction restarts work. | `papers/model.tex` defines `G^t`, includes `B^t subseteq G^t`, and states LIFO eviction/restart. `papers/known_type.tex` and `papers/unknown_type.tex` state unselected prompts retain KV caches. | Pass | Keep. |
| C4 | Equation (1) is presented as a decode-dominant affine iteration-time model with A100 validation and PD-disaggregated motivation. | `papers/model.tex` explains `d_0`, `d_1`, decode-dominant scope, piecewise-linear alternatives, and PD disaggregation; `papers/appendix_b_additional.tex` reports A100/SGLang calibration with `R^2=0.9943`, MAPE `1.93%`; `papers/appendix_b_additional.tex` reports PD experiment; `papers/numerical.tex` now uses the same SGLang/`1.93%` calibration wording. | Pass after manuscript sync | Updated `papers/numerical.tex` to replace stale vLLM/`1.5%` wording with SGLang/`1.93%`. |
| C5 | The theoretical framing no longer relies on classical heavy-traffic terminology; it is long-horizon/asymptotic under fixed load. | `papers/known_type.tex` and `papers/unknown_type.tex` state long-horizon scaling; response letter uses "long-horizon/asymptotic." Some theorem labels still contain legacy `heavy_traffic` identifiers, but the visible narrative has been changed. | Pass with implementation caveat | Do not mention internal label names. |
| C6 | WAIT/Nested WAIT are positioned as dimensionality reductions from memory-coupled state-action dynamics to threshold/boundary queues. | `papers/known_type.tex` theorem discussion explains threshold queues and deterministic feasibility; `papers/unknown_type.tex` theorem discussion explains binomial thinning and boundary queues. | Pass | Keep. |
| C7 | The paper adds examples and explanatory figures for WAIT and Nested WAIT. | `papers/known_type.tex` includes `ex:fcfs_cascade`, `fig:wait`, and `alg:wait`; `papers/unknown_type.tex` includes `ex:unknown_output`, `fig:nested_wait`, `fig:nested_wait_example`, and `alg:nested_wait`. | Pass | Kept, but changed fragile "Figure 1/Figure 2" wording to descriptive references. |
| C8 | The proof appendix is modularized into proposition proofs, WAIT proof, Nested WAIT proof, time-varying proof, and lemmas. | `papers/Appendix.tex` inputs `pf_thm_wait`, `pf_thm_nested`, `pf_thm_timevarying`, and `pf_lemmas`; those files define separate proof sections. | Pass | Replaced fragile "Appendix D.2" wording with "proof appendix for Theorem 1." |
| C9 | Section 6 states hardware, simulator, baseline configurations, WAIT/Nested WAIT settings, arrival-rate sweeps, and 10 replications. | `papers/numerical.tex` contains these setup paragraphs and states 10 independent simulation replications for main rate-sweep points. | Pass | Keep. |
| C10 | Real-data Nested WAIT thresholds are constructed from empirical continuation probabilities and a system-wide batch-size cap. | `papers/numerical.tex` real-data subsection defines `L`, `Delta l'_k`, `lambda'_k`, `p_k`, `q_k`, `n_k`, `tl`, and integerization. | Pass | Keep. |
| C11 | Long-decode evidence includes latency/completion-rate curves and near-capacity eviction-induced restart diagnostics. | `papers/numerical.tex` has `fig:long_decode` and `tab:eviction`; table uses latency `30.2s` vs `26.4s` and restart rate `2.88%` vs `0%`. | Pass | Replaced fragile "Figure 5 and Table 2" wording with descriptive references. |
| C12 | Additional experiments include threshold-without-waiting, simulator calibration, real-GPU SGLang single-type and real-data runs, repeated-run variability, and PD-disaggregated deployment. | `papers/appendix_b_additional.tex` contains subsections `app:no_wait`, `app:gpu_validation`, `app:multi_seed`, and `app:pd_disagg`; it contains `fig:wait_gate_ablation`, `fig:sim_fidelity`, `fig:sglang`, `tab:sglang_realtrace`, `fig:sglang_realtrace`, `tab:multi_seed`, and `fig:pd_disagg`. | Pass | Replaced "Appendix C" and "Figure C.2" wording with descriptive references. |
| C13 | Related work was expanded to cover system work, concurrent OR/LLM-inference theory, known/unknown output lengths, unit-time versus batch-dependent time, and PD systems. | `papers/introduction.tex` contains `Other Related Work`, with Splitwise/DistServe/Orca/Sarathi, Jaillet/Wang/Chen/Li, and the distinction from our memory-dependent iteration-time model. | Pass | Replaced inaccurate "Section 1.3" with "Other Related Work subsection." |
| C14 | Notation table was moved to the Notation Summary appendix. | `papers/appendix_notation.tex` defines `\section{Notation Summary}`, `app:notation`, and `tab:notation`; `papers/model.tex` references it. | Pass | Replaced "Appendix B notation table" with descriptive wording. |
| C15 | Real-GPU parameter reporting is reproducible. | `papers/appendix_b_additional.tex` gives single-type GPU parameters in prose and real-data GPU parameters in `tab:sglang_realtrace`. | Pass after wording fix | Replaced "parameter tables" plural with "parameter descriptions, including a parameter table." |

Remaining synchronization risks:

- If the manuscript later changes the real-data tuning parameters or regenerated figures, C9--C12 must be rechecked.
- Final response letter should not hard-code appendix letters or figure/table numbers unless they are copied after final manuscript compilation.
- Internal theorem labels still contain legacy `heavy_traffic` strings; this is harmless for the response letter as long as the visible paper text does not use that framing.

Second-pass review:

- Rechecked C1--C15 sequentially against the active manuscript source on 2026-04-28.
- No remaining response-letter overclaim was found after replacing fragile appendix/figure/table numbering with descriptive references.
- One manuscript-level inconsistency was found during C4 and fixed: Section 6 now matches the Additional Experiments appendix on the A100/SGLang calibration metric.

## 2026-04-30 Consistency Recheck

- Rechecked the response-letter claims most affected by recent proof, experiment, and advisor-packet edits: C1, C3, C4, C9--C12, and C15.
- Patched the response-letter statement about Section 3 so it now says the fluid model identifies the memory requirement and decode-stage allocation required for stability, rather than a generic memory level.
- Patched the \(M^*\) response so \(M^*\) is described as the memory requirement needed to sustain the fluid equilibrium, consistent with `framing.md` and `symbols.md`.
- Patched manuscript front matter so `effective throughput` is consistently token-level completed decode service net of eviction; Section 6 continues to use `effective completion rate` for request-level completion curves.
- Patched the organized review-comment digest so the active advisor packet refers to the review team without committing to a referee-count convention.
- Current status: response-letter claims remain aligned with the revised manuscript after the April 30 consistency pass.

## 2026-05-01 Review-Point Pass

- Rechecked the \(M^*\), \(C\), fluid-equilibrium, and fluid-stability-region language across the abstract, introduction, fluid section, known/unknown-type theory sections, conclusion, and response letter.
- Patched the manuscript and response letter so \(M^*\) is consistently the memory requirement needed to sustain the fluid equilibrium for a given arrival vector, and \(M^*\le C\) is consistently the condition that the load lies in the fluid stability region.
- Rechecked the related-work / concurrent-paper response. The manuscript now cites and distinguishes system-level works, concurrent online/regret/robust-prediction models, and stochastic batch-processing models. The response letter describes these additions without making a priority claim.
- Rechecked the real-data reproducibility response. The response letter claims only that the paper reports the calibration rule, finite grids, and GPU-run parameters; it does not claim a full per-arrival-rate provenance table for the lmsys rate sweep. This remains aligned with the current manuscript.
- Rechecked the real-data dataset summary against `lmsys_chat_1m_dataset/output_trace/lmsys_chat_1m_dataset.csv` and the plotted distribution. The manuscript now reports statistics for the same filtered workload population used in Figure~`\ref{fig:lmsys_distribution}`. The distribution figure is regenerated by `scripts/plot_lmsys_distribution.py`, so the plotted means and text now share the same filter.
- Rechecked lmsys Figure D provenance against the current response-letter wording. Exact per-arrival-rate winning configurations remain an open rerun/provenance item, but the response letter is aligned with the current conservative claim strength because it describes reported calibration rules and finite grids rather than a full per-rate configuration table.

## 2026-05-01 Section 6 / Additional Experiments Recheck

- Re-audited the response-letter claims tied to Section 6 and the Additional Experiments appendix after the lmsys distribution figure and real-data calibration paragraph were regenerated.
- The response letter remains aligned with the manuscript on the A100/Llama-2-7B memory-cap calculation: both state the approximate \(1.37\times 10^5\)-token KV-cache cap, cite the GPU/model/KV-cache sources, and explain that exceeding the cap leads to eviction and restart.
- The response letter remains aligned with the real-data Nested WAIT setup: both describe distribution-aware calibration using the workload distribution and offered arrival rate, with \(\mathrm{tl}\in\{40,60,\ldots,300\}\), \(L\in\{1,2,3,4,5,10,20\}\), and \(\eta=0.05\). Neither source claims that \(\mathrm{tl}\) is a resident-memory guarantee or that larger \(\mathrm{tl}\)/larger \(L\) is monotone better.
- The response letter remains conservative on real-data provenance: it says the manuscript reports the calibration rule and finite grids, and that the GPU appendix reports rate-specific GPU-run parameters. It does not claim a complete per-arrival-rate provenance table for the main lmsys Vidur sweep.
- Patched the internal audit checklist to remove stale wording that said the main text fixed \(L=10\) for all real-data runs.
- Rechecked the R2.1 figure-validation response against the current Section 2 figure and Appendix validation figure. Patched one phrase so the response now says the old L20 profiling plot was replaced by an A100 profiling figure using the same GPU model as the main Vidur configuration.
- Rechecked `experiments.db.real_data_provenance_runs` on 2026-05-02. SQL provenance remains incomplete for the main lmsys Vidur Figure D sweep: valid rows cover only QPS \(10,20,50,60\). The response letter remains aligned because it does not claim a complete per-arrival-rate provenance table for that sweep.
