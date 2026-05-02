# Organized Review Comments

OPRE Revision: "Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints"

## Decision Editor / Area Editor

**Overall decision.** The decision was major revision, although the Associate Editor recommended reject-and-resubmit. The Area Editor described the revision as risky and warned that if the exposition problems persisted, the paper would likely be rejected in the next round.

**Core concerns.**

- The exposition was significantly below the journal's expectations and required serious, conscientious revision.
- The original paper did not address latency adequately, even though latency is a central trade-off in modern AI inference.
- Throughput should not be treated as the only objective. The revision needed to explain the throughput-latency trade-off and the stability implications more carefully.
- The response should be specific about how each reviewer concern was addressed.

## Associate Editor

**Overall assessment.** The AE viewed the problem as timely and potentially important, but found that the original exposition obscured the technical content. The AE emphasized that a clearer revision could still reveal technical or modeling issues that were hidden by the original presentation.

**Strengths identified.**

- The problem of optimizing LLM inference is high-impact and relevant to both Operations Research and Computer Science.
- The stochastic model and theoretical development are interesting and ambitious.
- At least one reviewer viewed the theoretical development as solid and well grounded.

**Core concerns.**

- The writing, notation, lack of intuition, and errors made the paper difficult to digest.
- The model assumptions required clearer justification, especially the affine iteration-time model in Equation (1).
- The treatment of memory, OOM risk, preemption, and waiting jobs needed to be clarified.
- The theoretical contribution needed clearer positioning. If the novelty is in modeling and problem structuring rather than new stochastic-process tools, the paper should say so directly.
- The proof exposition was too high-level in the main text and too hard to verify in the appendix.
- The appendix should rely more on standard stochastic-process results where appropriate rather than proving standard facts from first principles.
- The paper should explain the zero-drift and negative-drift cases more efficiently, since these random-walk behaviors are standard in stochastic models.

## Reviewer 1

**Overall assessment.** Reviewer 1 viewed the topic as important and potentially impactful, but recommended major revision because modeling clarity and notation problems prevented a full assessment of the contribution.

**Positive comments.**

- The topic is important and well motivated.
- The paper takes an ambitious step toward connecting operational modeling with AI-system design.
- The framework could have practical impact if the assumptions and mechanisms are more clearly articulated and validated.

**Core concerns.**

- It was unclear how the proposed algorithms ensure that KV-cache usage never exceeds capacity, especially under heavy workloads and uncertain output lengths.
- The paper needed a more explicit discussion of OOM safeguards.
- The affine iteration-time assumption in Equation (1) may not hold across GPU architectures or workload regimes, and the paper needed to discuss possible nonlinear timing behavior.
- Section 2 had notation conflicts: similar notation was used for prompt length, output length, decode stage, and current processing stage.
- The policy space \(\Pi\) and the batching operations implied by a policy were not defined clearly enough before the algorithms.
- The paper needed more intuition after key definitions and after Algorithm 1.
- Several typos and notation errors needed correction, including \(d\) versus \(d_1\) and "Throughput" spelling.

## Reviewer 2

**Overall assessment.** Reviewer 2 was generally positive. The reviewer described the paper as timely, technically rigorous, and of broad interest, but asked for clearer modeling scope, proof details, and experimental reproducibility.

**Positive comments.**

- The paper addresses an important operational challenge in LLM inference under GPU memory limits.
- The fluid-guided approach provides theoretical insight and practical scheduling principles.
- The theoretical development was viewed as solid and well grounded.
- The treatment of unknown output lengths through Nested WAIT was viewed as insightful.
- Figures 1--2 and Section 2 were viewed as educational for OR readers.

**Core concerns.**

- Equation (1) needed a clearer statement of which LLM-inference timing regime it represents.
- The paper should explain how the affine time model relates to existing LLM-inference timing studies and to different prefill/decode regimes.
- The original Figure 3 needed clearer inference-time validation details, including the model family, hardware, and tokens-per-batch experimental setup.
- The assumption \(C \ge M^*\) may be strong in practice, especially given GPU KV-cache limits, and should be acknowledged.
- The proof of Theorem 1 needed clearer decode-stage analysis and more explicit coupling details.
- The paper needed to clarify whether Proposition 2 is simply an upper bound from arrived decode tokens.
- Section 3 and Sections 4--5 had several formula and notation issues that required correction.
- Section 6 needed more experimental detail: batch size, memory bound, capacity, Sarathi configuration, vLLM configuration, and Nested WAIT parameters.
- The paper should clarify what "Prompt Number" means in the original Figure 7.
- The real-data experiment needed specific threshold and capacity values to improve reproducibility.

## Decision-Letter Queueing and Positioning Concerns

**Overall assessment.** The decision materials raised the strongest concerns about whether the original paper reached the level of Operations Research. The concerns centered on queueing interpretation, theoretical positioning, latency evidence, and writing quality.

**Queueing-theory concerns.**

- The original "heavy traffic" analysis was not a conventional heavy-traffic limit. It was closer to an infinite-horizon or long-horizon limit under fixed load.
- Some latency results seemed to follow from standard positive-recurrence arguments, so the paper needed to explain what was technically nontrivial.
- With exogenous arrivals, any stable policy completes work at the offered arrival rate. The paper should not frame the objective as unconstrained throughput maximization at a fixed arrival rate.
- The more appropriate interpretation is the range of arrival rates a policy can stabilize, i.e., the stability region.
- The original simulations appeared to be in unstable regimes, which made latency comparisons hard to interpret.
- The decision letter recommended plotting mean latency as a function of arrival rate, which would also reveal stability boundaries.

**Contribution concerns.**

- WAIT appeared to be a pipeline-filling idea: keep a roughly constant number of jobs at each progress stage and advance a type when enough jobs have accumulated.
- The paper needed to explain why this idea is more than a straightforward pipeline-filling rule.
- The concern was whether the fluid analysis was mainly an exercise in Little's law and related formulas.
- The paper needed a stronger explanation of latency effects and algorithmic contribution.

**Modeling concerns.**

- The memory constraint seemed to apply only to jobs in the current batch.
- If preempted jobs preserve KV caches, the paper needed to explain where those caches reside and whether moving memory between GPU and other storage is realistic.
- A more realistic model might need the memory constraint to apply to all active jobs, not just the current batch.

**Writing concerns.**

- The fluid models were not fully defined.
- The paper provided too little interpretation for formulas derived from the fluid model.
- Typos and notation inconsistencies made the paper harder to read.

## Summary of Main Revision Targets

| Theme | Review team concern |
|---|---|
| Exposition | Rewrite the paper for clarity, notation consistency, intuition, and proof readability. |
| Memory model | Clarify KV-cache accounting, OOM prevention, preemption, eviction, and restart behavior. |
| Time model | Justify the affine iteration-time model and state its decode-dominant scope. |
| Queueing objective | Reframe throughput around stability region, useful completed service, and latency. |
| Theory | Explain what is nontrivial beyond standard positive recurrence and pipeline filling. |
| Experiments | Add arrival-rate latency curves, stability-region evidence, repeated runs, GPU validation, and reproducible parameters. |
