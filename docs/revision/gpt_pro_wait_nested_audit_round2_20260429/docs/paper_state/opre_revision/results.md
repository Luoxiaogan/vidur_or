# Results Registry

## Main Text

- WAIT: asymptotic optimality result appears in the known-type section
  - Verified: ✅ 2026-04-29. `$verify-proof` checked Theorem `thm:wait_heavy_traffic`, the scaled-delay convention, the resident-stage memory invariant, the periodic full-slot comparison policy, and the one-slot delayed dominance transfer from the comparison policy to event-driven WAIT. The proof now avoids reusing `\lambda` for per-batch critical arrivals in the single-type warm-up.
- Nested WAIT: asymptotic optimality result appears in the unknown-type / extension development
  - Verified: ✅ 2026-04-29. `$verify-proof` checked Theorem `thm:nested_wait_heavy_traffic`, Algorithm `alg:nested_wait`, and Appendix proof `appendix::proof of nested_wait_heavy_traffic`; the tight downstream boundary buffer `n_k+\theta_k^{-1}\log(\cdot)` is supported by the carryover-residual queue convention and finite-horizon reflected-random-walk tail bound.
  - Extension correction: ✅ 2026-04-29. The segment-design extension now uses strict first-segment slack, consistent with its `O((\zeta T)^(-1))` throughput and `O(1)` service-normalized delay rates.

## Experiments

- Section 6 should support the theory via:
  - stability-boundary comparisons
  - effective-throughput comparisons
  - memory-safeguard / eviction evidence
