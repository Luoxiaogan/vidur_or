# Results Registry

## Main Text

- WAIT: asymptotic optimality result appears in the known-type section
  - Verified: ✅ 2026-04-29. `$verify-proof` checked Theorem `thm:wait_heavy_traffic`, the scaled-delay convention, the resident-stage memory invariant, the periodic full-slot comparison policy, and the one-slot delayed dominance transfer from the comparison policy to event-driven WAIT. The proof now avoids reusing `\lambda` for per-batch critical arrivals in the single-type warm-up.
- Nested WAIT: asymptotic optimality result appears in the unknown-type / extension development
  - Verified: ✅ 2026-04-29. `$verify-proof` checked Theorem `thm:nested_wait_heavy_traffic`, Algorithm `alg:nested_wait`, and Appendix proof `appendix::proof of nested_wait_heavy_traffic`; the tight downstream boundary buffer `n_k+\theta_k^{-1}\log(\cdot)` is supported by the carryover-residual queue convention and finite-horizon reflected-random-walk tail bound.
  - Extension correction: ✅ 2026-04-29. The segment-design extension now uses strict first-segment slack, consistent with its `O((\zeta T)^(-1))` throughput and `O(1)` service-normalized delay rates.
  - Second-round proof audit: ✅ 2026-04-29. Main WAIT and Nested WAIT theorem statements remain unchanged; Algorithm 1/2 conventions now match the proofs, and the time-varying extension uses scaled-window arrivals plus the integrated benchmark `\throughput_T^*`.
  - Follow-up `$verify-proof`: ✅ 2026-04-29. The time-varying theorem is now self-contained in its definitions of `p_k^*`, `\theta_k`, final-window truncation, and zero-downstream-input segments; no main-theorem rate or tight-buffer statement changed.
  - Latest GPT-Pro audit patch: ✅ 2026-04-30. Main WAIT and Nested WAIT theorem statements remain unchanged; Algorithms 1/2 now explicitly prevent overlapping server batches and use simultaneous stored-count completion updates. The time-varying extension now includes the no-long-lull condition required for its `O(1)` service-normalized delay guarantee.
  - Notation synchronization: ✅ 2026-05-01. The main WAIT and Nested WAIT theorem statements remain unchanged, but the surrounding prose now consistently distinguishes `M^*`, `M^\pi`, `M_{\mathrm{req}}^{(\zeta,\pi)}`, and `C`.
  - Proposition proof refinement: ✅ 2026-05-01. `$verify-proof` checked the service-capacity cut for Proposition `prop:large_rate` and the two-type indistinguishability construction for Proposition `prop:unknown_lower_bound`. Statements remain unchanged; proof prose now avoids template-style `Proof Outline` labels and uses flowing proof introductions.

## Experiments

- Section 6 should support the theory via:
  - empirical transition / stability-boundary comparisons on tested arrival-rate grids
  - effective-throughput comparisons
  - memory-safeguard / eviction evidence
  - conservative real-data claims: report plotted-rate latency and effective completion behavior, but do not claim a sharp lmsys stability boundary without the reruns listed in `real_data_remeasurement_checklist.md`
