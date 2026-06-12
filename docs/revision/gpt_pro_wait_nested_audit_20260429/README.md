# WAIT / Nested WAIT Proof Audit Upload Package

This folder is prepared for a GPT Pro web audit of the WAIT and Nested WAIT proofs.

## Suggested Upload

Upload the full folder or the files inside it to GPT Pro, then paste the contents of `AUDIT_PROMPT.md`.

## Contents

- `papers/LLM_or.pdf`: rendered revised paper.
- `papers/known_type.tex`: WAIT algorithm and theorem.
- `papers/unknown_type.tex`: Nested WAIT algorithm and theorem.
- `papers/pf_thm_wait.tex`: WAIT proof.
- `papers/pf_thm_nested.tex`: Nested WAIT proof.
- `papers/pf_lemmas.tex`: auxiliary lemmas.
- `papers/model.tex`: model primitives.
- `papers/fluid.tex`: fluid model and \(M^*\).
- `papers/extension.tex`: time-varying/general-segment extensions.
- `papers/pf_thm_timevarying.tex`: time-varying proof.
- `papers/appendix_notation.tex`: notation table.
- `papers/LLM_or.tex` and `papers/command.tex`: main wrapper and macros.
- `docs/paper_state/opre_revision/*.md`: current internal symbol and verification state.

## Main Audit Questions

1. Does the WAIT proof correctly transfer bounds from the periodic comparison process to actual event-driven WAIT?
2. Does the Nested WAIT proof rigorously support the tight downstream memory buffer \(n_k+\theta_k^{-1}\log(\cdot)\), without needing \(2n_k+\cdots\)?
3. Are throughput, service-normalized latency, TTFT, and high-probability memory guarantees stated and proved under consistent scaling?
