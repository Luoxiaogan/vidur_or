# GPT-Pro Nested WAIT Proof Review Packet

Purpose: ask GPT-Pro to audit the revised Nested WAIT proof, especially the unknown-output-length boundary-queue construction, memory safety buffer, and \(\zeta T\) scaling.

## Files

- `revised_paper.pdf`: compiled revised paper for global context.
- `framing.md`: locked terminology and paper-state constraints.
- `source/model.tex`: metric definitions, including effective throughput, latency, and TTFT.
- `source/known_type.tex`: Section 4 scaling definitions, especially service-normalized delay.
- `source/unknown_type.tex`: Nested WAIT algorithm, assumptions, theorem statement, and theorem interpretation.
- `source/pf_thm_nested.tex`: Appendix proof of the Nested WAIT theorem.
- `source/pf_lemmas.tex`: supporting coupling and martingale-root arguments.
- `source/extension.tex`: time-varying and general segment-design theorem statements.
- `source/pf_thm_timevarying.tex`: appendix proof text for the time-varying extension.
- `web_prompt.md`: prompt to paste into GPT-Pro after uploading this folder.

## Recommended Upload

Upload the entire folder. If the web interface limits file count, upload `revised_paper.pdf`, `source/unknown_type.tex`, `source/pf_thm_nested.tex`, `source/pf_lemmas.tex`, and `source/known_type.tex` first.
