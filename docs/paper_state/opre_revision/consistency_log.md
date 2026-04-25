# Consistency Log

## 2026-04-23

- Initialized paper-state tracking for the OPRE revision paper.
- Recorded locked Section 6 decisions before applying the next `.tex` edit.
- No figure/table labels were added or removed in this initialization step.
- Re-checked the active state docs after the latest Section 6 wording edits.
- Confirmed that this edit round changed prose/framing only:
  - no new symbols were introduced
  - no results/theorems changed
  - no figure/table/reference labels changed
- Recorded the current locked wording for the Section 6 `\mathrm{tl}` explanation in `overview.md` and `framing.md`.
- Promoted `fig:long_decode` from Appendix B into main-text Section 6 and synchronized the figure/reference registries accordingly.
- Ran a scoped `paper-pipeline` consistency pass on the active Section 6 files and locked the terminology split:
  - `inventory` for realized counts at a stage or segment
  - `in-flight limit` for caps implied by `\mathrm{tl}`
- Re-locked the real-data Section 6 exposition so that the body text distinguishes algorithmic segments from any workload discretization and avoids `bins` language in the paper-facing narrative.
