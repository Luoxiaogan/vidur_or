# Results Registry

## Main Text

- WAIT: asymptotic optimality result appears in the known-type section
  - Verified: ✅ 2026-04-29, updated 2026-05-04. `$verify-proof` checked Theorem `thm:wait_heavy_traffic`, the scaled-delay convention, the GPU-resident memory invariant, the auxiliary embedded full-threshold process, and the type-wise sample path coupling from the embedded process to event-driven WAIT. The proof avoids reusing `\lambda` for per-batch critical arrivals in the single-type warm-up and now describes the multi-type step through embedded review intervals and service-opportunity coupling. Follow-up proof refinement on 2026-05-04 rewrote the multi-type coupling through batch eligibility times `\tau_{jq}` and actual start times `\sigma_{jq}`, giving the calendar-time inequality `\sigma_{jq}\le \tau_{jq}+L_\zeta` that explicitly accounts for subset-batch fixed overhead.
- Nested WAIT: asymptotic optimality result appears in the unknown-type / extension development
  - Verified: ✅ 2026-04-29. `$verify-proof` checked Theorem `thm:nested_wait_heavy_traffic`, Algorithm `alg:nested_wait`, and Appendix proof `appendix::proof of nested_wait_heavy_traffic`; the tight downstream boundary buffer `n_k+\theta_k^{-1}\log(\cdot)` is supported by the carryover-residual queue convention and finite-horizon reflected-random-walk tail bound.
  - Extension correction: ✅ 2026-04-29. The segment-design extension now uses strict first-segment slack, consistent with its `O((\zeta T)^(-1))` throughput and `O(1)` service-normalized delay rates.
  - Second-round proof audit: ✅ 2026-04-29. Main WAIT and Nested WAIT theorem statements remain unchanged; Algorithm 1/2 conventions now match the proofs, and the time-varying extension uses scaled-window arrivals plus the integrated benchmark `\throughput_T^*`.
  - Follow-up `$verify-proof`: ✅ 2026-04-29. The time-varying theorem is now self-contained in its definitions of `p_k^*`, `\theta_k`, final-window truncation, and zero-downstream-input segments; no main-theorem rate or tight-buffer statement changed.
  - Latest GPT-Pro audit patch: ✅ 2026-04-30. Main WAIT and Nested WAIT theorem statements remain unchanged; Algorithms 1/2 now explicitly prevent overlapping server batches and use simultaneous stored-count completion updates. The time-varying extension now includes the no-long-lull condition required for its `O(1)` service-normalized delay guarantee.
  - Notation synchronization: ✅ 2026-05-01. The main WAIT and Nested WAIT theorem statements remain unchanged, but the surrounding prose now consistently distinguishes `M^*`, `M^\pi`, `M_{\mathrm{req}}^{(\zeta,\pi)}`, and `C`.
  - Proposition proof refinement: ✅ 2026-05-01, updated 2026-05-04. `$verify-proof` checked the service-capacity cut for Proposition `prop:large_rate` and the two-type indistinguishability construction for Proposition `prop:unknown_lower_bound`. Statements remain unchanged; proof prose now avoids template-style `Proof Outline` labels and uses flowing proof introductions. The FCFS and unknown-output lower-bound proofs now use explicit block / conditioning arguments to make the constant-deficit mechanism easier to verify. Follow-up wording on 2026-05-04 uses `unrevealed admission batch` and `boundary-survivor count`.

## Experiments

- Section 6 should support the theory via:
  - empirical transition / stability-boundary comparisons on tested arrival-rate grids
  - effective-throughput comparisons
  - memory-safeguard / eviction evidence
  - representative `M^*(\lambda)` versus `C` checks when using real-data arrival-rate curves, currently recorded by Table `tab:lmsys_mstar`
  - conservative real-data claims: report plotted-rate latency and effective completion behavior, but do not claim a sharp lmsys stability boundary without the reruns listed in `real_data_remeasurement_checklist.md`
