# Symbols

- `\lambda`: arrival rate / QPS in experiments
- `\lambda^*`: stability boundary
- `n_j`: per-type, per-stage WAIT threshold
- `n_j^*`: equilibrium per-stage inventory of type-`j` prompts in the fluid model
- `n_k`: per-segment Nested WAIT threshold
- `\mathrm{tl}`: system-wide batch-size cap used to determine the segment-level caps and per-stage thresholds
- `M^*`: memory requirement needed to support the fluid equilibrium; for fixed capacity `C`, `M^*(\lambda) \le C` defines the fluid stability region
- `M^\pi`: base threshold memory induced by a WAIT/Nested WAIT threshold vector
- `M_{\mathrm{req}}^{(\zeta,\pi)}`: physical memory required by the scaled policy; for WAIT this equals `M^\pi` and is independent of `\zeta`, while for Nested WAIT it equals `M^\pi` plus the finite-horizon downstream safety buffer
- `C`: physical memory capacity
- `tab:notation`: consolidated notation table, now located in Appendix `app:notation`
