# Paper Polish and Overleaf Merge Checkpoint - 2026-04-28

## Status
🚧 In progress

## Summary
This checkpoint records the current OPRE revision polish state and the safe Overleaf merge preview. The paper compiles locally, but the Overleaf copy has not yet been overwritten in this checkpoint because the merge scope was being narrowed when progress was requested.

## Completed

### Paper polish
- Section 2 objective and notation presentation were polished for OR-style narrative: notation table moved to the appendix, and the main text introduces key terms narratively.
- Sections 3--5 were polished around fluid-model terminology, WAIT/Nested WAIT threshold explanations, memory requirements, and theorem interpretation paragraphs.
- The Nested WAIT theorem discussion now connects directly to the theorem's memory/no-overflow guarantee, explains unknown output lengths through boundary completion/survival events, and refers to general segment design in the appendix.
- The numerical section opener was revised to avoid meta-evaluative phrasing. It now starts from the open-system queueing identity that stable completed requests match the offered rate.

### Writing-advisor updates
- Captured advisor feedback on mechanism-first theorem interpretation and metric exposition.
- Added an experiments advisor rule: `Use Mechanism-First Metric Exposition`.
- Refined sentence patterns to avoid AI-like openings such as `X alone is not informative` and labels such as `primary diagnostic`.

### Local validation
- `latexmk -pdf -interaction=nonstopmode LLM_or.tex` passes locally.
- Current compiled output: `papers/LLM_or.pdf`, 75 pages.

## Overleaf Merge Preview

### Target
- Overleaf directory: `/Users/ruicheng/Library/CloudStorage/Dropbox-MIT/Ao Ruicheng/应用/Overleaf/OR for LLM inference revision`
- Git source: `papers/`

### Classification from safe preview
- `CONFLICT`: 0 files
- `GIT_NEWER`: 15 root manuscript files
- `GIT_ONLY`: new files and figures, including the `Experiments_pdf/` directory and new appendix files
- `OVERLEAF_ONLY`: 0 files within the narrowed root-manuscript scope

### Root files detected as newer locally
- `Appendix.tex`
- `LLM_or.tex`
- `abstract.tex`
- `conclusion.tex`
- `extension.tex`
- `fluid.tex`
- `introduction.tex`
- `known_type.tex`
- `main.bib`
- `model.tex`
- `numerical.tex`
- `pf_thm_nested.tex`
- `pf_thm_timevarying.tex`
- `pf_thm_wait.tex`
- `unknown_type.tex`

### Merge-scope decision
- Sync only the active OPRE root manuscript dependencies for `LLM_or.tex`.
- Include `Experiments_pdf/` figures used by the active manuscript.
- Include new active appendix/support files such as `appendix_notation.tex`, `appendix_b_additional.tex`, `appendix_sim_fidelity.tex`, `command.tex`, class/style files, bibliography files, and logo assets required for compilation.
- Do not copy non-active variants or legacy subtrees such as `msom/`, `competitions/`, `arxiv/`, `sig/`, `ssrn/`, `LLM_arxiv.tex`, `LLM_ssrn.tex`, root compiled PDFs, logs, aux files, or conflicted-copy artifacts.

## Open Items
- Execute the narrowed Overleaf merge with backups for the 15 overwritten root files.
- After Dropbox sync completes, verify that the Overleaf project compiles with the copied `Experiments_pdf/` directory.
- Continue paper polishing from the next requested subsection after the Overleaf sync is completed.

## Changed Files

| Type | Count | Notes |
|------|-------|-------|
| Modified paper files | 15+ | Main manuscript sections, proofs, appendix files, and figures |
| New support files | Several | `appendix_notation.tex`, additional appendix/figure assets |
| Advisor-library updates | Several | Feedback and reusable writing patterns |
| Overleaf files changed | 0 so far | Merge preview completed; copy not executed in this checkpoint |

## Related Files
- `papers/numerical.tex`
- `papers/unknown_type.tex`
- `papers/LLM_or.pdf`
- `.claude/CLAUDE.md`

