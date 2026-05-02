# Framing

## Locked Terms

- Use `effective throughput` for completed decode-token service net of eviction in global paper claims; in Section 6 figure prose, define the plotted request-level metric explicitly as effective completion rate.
- Use `asymptotic regime` or `long-horizon regime`, not `heavy traffic`, in body text.
- Use `memory consumption` for dynamic usage and `memory requirement` for the capacity required by a target operating point.
- Use `C` only for physical memory capacity. Use `M^*` for the fluid-equilibrium memory requirement, `M^\pi` for base threshold memory, and `M_{\mathrm{req}}^{(\zeta,\pi)}` for scaled-policy required memory. For WAIT, `M_{\mathrm{req}}^{(\zeta,\pi)}=M^\pi`; for Nested WAIT, it adds the finite-horizon downstream safety buffer.
- Use `fluid model` for the average-flow approximation itself.
- Use `fluid equilibrium` for the balanced operating point of the fluid model, including the per-stage populations `n_j^*`, iteration time `\Delta T^*`, throughput benchmark `\throughput^*`, and memory requirement `M^*`.
- Describe `M^*` as the memory requirement needed to support the fluid equilibrium, not as the equilibrium itself.
- Use `fluid stability region` for the theoretical arrival-rate set defined by `M^*(\lambda)\le C` at fixed capacity `C`. Do not use `fluid stability benchmark` in paper-facing prose.
- Use `realized stability region` when comparing concrete policies or experiments; WAIT/Nested WAIT enlarge the realized stability region by preventing eviction cascades and moving performance closer to the fluid benchmark.
- Use `KV cache` consistently, without a hyphen, throughout the active paper.
- Use `inventory` for the observed number of requests currently present at a stage or segment.
- Use `system-wide batch-size cap` for `\mathrm{tl}`, `segment-level cap` for `B_k=\Delta l'_k n_k`, and `per-stage threshold` for the stage-level controls induced from those caps; avoid the phrases `in-flight limit` and `admission threshold` for `\mathrm{tl}`.
- In experiments prose, use `arrival rate $\lambda$` consistently across synthetic and real workloads; if units matter, introduce them once as `requests per second`.
- In Section 6, refer to the two-type synthetic workload directly by its tuple `$(0.7\,\texttt{p512d20},\,0.3\,\texttt{p512d50})$` rather than by an ad hoc label such as `W3`.
- In real-data Nested WAIT calibration, do not describe `\mathrm{tl}` or segment count `L` as monotone improvements. The correct tradeoff is U-shaped/interior: too-small `\mathrm{tl}` underuses batching/control, too-large `\mathrm{tl}` can create overflow pressure; too-small `L` blurs decode-stage differences, too-large `L` fragments segment-level caps and makes prompts wait at segment thresholds too often.

## Section 6 Framing

- Do not open the diagnostic paragraph with the bare queueing label `the system is open`.
- Prefer concrete mechanism language:
  - `requests arrive exogenously and depart after completion`
  - `throughput equals the arrival rate under stability`
- When explaining eviction in experiments prose, say:
  - the server evicts the most recently admitted request under a last-in-first-out rule
  - an evicted request restarts from the beginning if admitted again
- Cite the Vidur paper directly as the source of simulator-validation evidence, and keep quantitative fidelity statements in the prose.
- In the Section 6 setup paragraph, foreground how thresholds are computed for the experiments, rather than emphasizing implementation details of `\mathrm{tl}`.
- In the same setup paragraph, state explicitly which workloads use WAIT versus Nested WAIT, and use `L` for the number of decode-stage segments in the real-data calibration.
- In the same setup paragraph, keep count-versus-cap-versus-threshold terminology separate:
  - `inventory` for the realized count
  - `system-wide batch-size cap` for `\mathrm{tl}`
  - `segment-level cap` for `B_k=\Delta l'_k n_k`
  - `per-stage threshold` for the derived scheduling thresholds
- In the real-workload subsection, do not use `bins` language in the main-text exposition.
- Distinguish workload discretization from the algorithmic segment count $m$; if the implementation detail is not paper-facing, describe Nested WAIT only at the decode-stage-segment level.
- Avoid implementation-heavy phrases such as `entry stage is released`.
- For the real-workload search grid, write `\mathrm{tl}\in\{40,60,\ldots,300\}`, `L\in\{1,2,3,4,5,10,20\}`, and `\eta=0.05`.
