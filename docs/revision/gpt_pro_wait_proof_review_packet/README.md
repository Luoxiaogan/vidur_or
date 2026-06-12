# GPT-Pro WAIT Proof Review Packet

Purpose: ask GPT-Pro to audit the revised known-type WAIT proof, especially the multi-type comparison-slot argument and the \(\zeta T\) scaling for service-normalized latency and TTFT.

## Files

- `revised_paper.pdf`: compiled revised paper for global context.
- `framing.md`: locked terminology and paper-state constraints.
- `source/known_type.tex`: main-text theorem statement and scaling definitions.
- `source/pf_thm_wait.tex`: Appendix D proof of Theorem 1.
- `source/pf_lemmas.tex`: corresponding lemma proof, including the multi-type comparison queue bound.
- `source/unknown_type.tex`: included only to check consistency of the scaled-delay convention in the Nested WAIT section.
- `web_prompt.md`: prompt to paste into GPT-Pro after uploading this folder.

## Recommended Upload

Upload the entire folder. If the web interface limits file count, upload `revised_paper.pdf`, `source/known_type.tex`, `source/pf_thm_wait.tex`, and `source/pf_lemmas.tex` first.
