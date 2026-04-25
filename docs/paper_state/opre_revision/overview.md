# OPRE Revision Overview

- Paper: `Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints`
- Venue: `Operations Research`
- Manuscript: `OPRE-2025-04-1885`
- Primary source: [papers/LLM_or.tex](/Users/ruicheng/Documents/GitHub/vidur_or/papers/LLM_or.tex:1)
- Main experiment section: [papers/numerical.tex](/Users/ruicheng/Documents/GitHub/vidur_or/papers/numerical.tex:1)

## Current Status

- Revision stage: major revision
- Current writing focus: Section 6 narrative flow and OR exposition
- Current technical focus: clarify the Section 6 setup prose, especially the `tl` admission rule, baseline descriptions, and OR-facing exposition

## Active Decisions

- Section 6 opening paragraph should contextualize vLLM and Sarathi as `two widely used open-source LLM inference servers`.
- Section 6 diagnostic paragraph should avoid the bare phrase `open system` at the opener.
- When describing eviction in experiments prose, state the mechanism concretely:
  - eviction is last-in-first-out
  - an evicted request restarts from the beginning if admitted again
- Vidur validation citations in Section 6 should retain quantitative evidence rather than vague phrases such as `prior work shows`.
- The Section 6 WAIT / Nested WAIT setup paragraph should describe `\mathrm{tl}` as a global in-system cap and explain admission using the threshold-or-fill-to-`\mathrm{tl}` rule.
- In the real-workload setup, write the search grid as `\{20,25,\ldots,40\}` rather than enumerating mixed increments.
- In Section 6, use `inventory` for realized counts and `in-flight limit` for caps implied by `\mathrm{tl}`; do not switch to `budget` for the same cap.
- In Section 6, use `arrival rate \lambda` consistently rather than alternating between `rate` and `QPS`; add `requests per second` only as a unit clarification.
- In Section 6, refer to the two-type synthetic workload by its explicit tuple rather than by the shorthand label `W3`.

## Next Pipeline Step

- Continue the paragraph-by-paragraph polish of [papers/numerical.tex](/Users/ruicheng/Documents/GitHub/vidur_or/papers/numerical.tex:1), with the Section 6 setup paragraph now serving as the locked reference for `\mathrm{tl}` wording.
- After any `.tex` edit, update `changelog.md` and any affected state files.
