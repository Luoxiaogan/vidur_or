# WAIT / Nested WAIT Proof Audit Round 2

This folder is prepared for a second GPT Pro web audit of the WAIT and Nested WAIT proofs after incorporating the first proof-audit feedback.

## Suggested Upload

Upload this folder or `gpt_pro_wait_nested_audit_round2_20260429.zip` to GPT Pro, then paste the contents of `AUDIT_PROMPT.md`.

## Contents

- `papers/LLM_or.pdf`: rendered revised paper after the latest proof patches.
- `papers/known_type.tex`: WAIT algorithm and theorem.
- `papers/unknown_type.tex`: Nested WAIT algorithm and theorem.
- `papers/pf_thm_wait.tex`: WAIT proof.
- `papers/pf_thm_nested.tex`: Nested WAIT proof.
- `papers/pf_lemmas.tex`: auxiliary lemmas.
- `papers/model.tex`: model primitives and memory definitions.
- `papers/fluid.tex`: fluid model and \(M^*\).
- `papers/extension.tex`: time-varying and general-segment extensions.
- `papers/pf_thm_timevarying.tex`: time-varying proof.
- `papers/appendix_notation.tex`: notation table.
- `docs/paper_state/opre_revision/*.md`: current internal symbol and verification state.

## Main Round-2 Questions

1. Do the latest patches fully resolve the prior proof-audit findings?
2. Does the tight Nested WAIT memory buffer \(n_k+\theta_k^{-1}\log(\cdot)\) remain rigorous under the post-review residual convention?
3. Are resident GPU memory, scheduling preemption, prefix batching, and finite-horizon feasibility described consistently across theorem, algorithm, and proof?
