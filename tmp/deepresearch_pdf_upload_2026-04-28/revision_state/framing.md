# Framing

## Locked Terms

- Use `effective throughput` for completion rate net of evictions in narrative prose.
- Use `asymptotic regime` or `long-horizon regime`, not `heavy traffic`, in body text.
- Use `memory consumption` for dynamic usage and `memory requirement` for the capacity required by a target operating point.
- Use `ideal fluid model` for the average-flow approximation itself.
- Use `ideal-fluid equilibrium` for the balanced operating point of the fluid model, including the per-stage populations `n_j^*`, iteration time `\Delta T^*`, throughput benchmark `\throughput^*`, and memory requirement `M^*`.
- Describe `M^*` as the memory requirement needed to support the ideal-fluid equilibrium, not as the equilibrium itself.
- Use `ideal-fluid stability benchmark` or `ideal-fluid stability region` for the theoretical arrival-rate set defined by `M^*(\lambda)\le C` at fixed capacity `C`.
- Use `realized stability region` when comparing concrete policies or experiments; WAIT/Nested WAIT enlarge the realized stability region by preventing eviction cascades and moving performance closer to the ideal-fluid benchmark.
- Use `KV cache` consistently, without a hyphen, throughout the active paper.
- Use `inventory` for the observed number of requests currently present at a stage or segment.
- Use `in-flight limit` for a cap induced by `\mathrm{tl}` at the global or segment level; do not alternate with `budget` for the same object.
- In experiments prose, use `arrival rate $\lambda$` consistently across synthetic and real workloads; if units matter, introduce them once as `requests per second`.
- In Section 6, refer to the two-type synthetic workload directly by its tuple `$(0.7\,\texttt{p512d20},\,0.3\,\texttt{p512d50})$` rather than by an ad hoc label such as `W3`.

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
- In the same setup paragraph, state explicitly which workloads use WAIT versus Nested WAIT, and define `m` as the number of decode-stage segments.
- In the same setup paragraph, keep count-versus-cap terminology separate:
  - `inventory` for the realized count
  - `in-flight limit` for the cap implied by `\mathrm{tl}`
- In the real-workload subsection, do not use `bins` language in the main-text exposition.
- Distinguish workload discretization from the algorithmic segment count $m$; if the implementation detail is not paper-facing, describe Nested WAIT only at the decode-stage-segment level.
- Avoid implementation-heavy phrases such as `entry stage is released`.
- For the real-workload search grid, write `\{20,25,\ldots,40\}`.
