# Deep Research Upload Bundle

Purpose: external GPT deep-research audit of the OPRE major-revision package for `OPRE-2025-04-1885`.

## Priority Reading Order

1. `LLM_or.pdf` — revised manuscript, rendered.
2. `response_letter.pdf` — response letter, rendered.
3. `review_materials/decision_letter.md` — decision letter and Reviewer 3 text.
4. `review_materials/AE_report.pdf` — AE report.
5. `review_materials/Review_OPRE-2025-04-1885.pdf` — Reviewer 1 report.
6. `review_materials/Review_for__Optimizing_LLM_Inference__Fluid_Guided_Online_Scheduling_with_Memory_Constraints_.pdf` — Reviewer 2 report.
7. `revision_state/REVISION_PLAN.md` — author-side revision strategy and framing.
8. `revision_state/response_letter_claim_audit.md` — local checklist comparing response-letter claims against the revised paper.
9. `source_tex/` — exact source files for line-level wording and consistency checks.

## Audit Goal

Act as Reviewer 1, Reviewer 2, Reviewer 3, AE, and DE. Evaluate whether the revised paper and response letter adequately address all review concerns.

Focus on:

- response-letter completeness and credibility;
- paper/letter consistency;
- open-system throughput and stability-region framing;
- `M^*`, ideal-fluid equilibrium, and effective throughput terminology;
- WAIT/Nested WAIT algorithm and proof interpretation;
- experiment reproducibility and figure/table consistency;
- OR/OM writing style, reviewer-facing tone, and rejection risks.

## Expected Output

For each finding, use:

```text
Attack:
Severity: Critical / Major / Minor / Suggestion
Reviewer Lens: AE / DE / R1 / R2 / R3 / General OR reader
Location:
Issue:
Evidence:
Why it matters:
Fix:
```

End with:

- top 5 must-fix issues before resubmission;
- reviewer-specific remaining risks;
- response-letter edits that would most improve credibility;
- paper sections that are already strong and should not be over-edited.
