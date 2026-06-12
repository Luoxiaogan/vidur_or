# PDF-Only Deep Research Upload Bundle

Purpose: external GPT deep-research audit of the OPRE major-revision package for `OPRE-2025-04-1885`.

This bundle intentionally excludes TeX source files. The goal is to make GPT compare the rendered original submission, reviewer comments, revised manuscript, and response letter as a reviewer/AE/DE would read them.

## Priority Reading Order

1. `original_submission.pdf` — first submitted version reviewed by AE/R1/R2/R3.
2. `review_materials/decision_letter.md` — decision letter and Reviewer 3 text.
3. `review_materials/AE_report.pdf` — AE report.
4. `review_materials/Review_OPRE-2025-04-1885.pdf` — Reviewer 1 report.
5. `review_materials/Review_for__Optimizing_LLM_Inference__Fluid_Guided_Online_Scheduling_with_Memory_Constraints_.pdf` — Reviewer 2 report.
6. `LLM_or.pdf` — revised manuscript.
7. `response_letter.pdf` — response letter.
8. `revision_state/REVISION_PLAN.md` — author-side revision strategy.
9. `revision_state/response_letter_claim_audit.md` — local checklist comparing response-letter claims against the revised manuscript.

## Audit Goal

Act as Reviewer 1, Reviewer 2, Reviewer 3, AE, and DE. Evaluate whether the revised paper and response letter adequately address all review concerns.

Compare:

- original submission vs reviewer comments;
- reviewer comments vs revised manuscript;
- response letter vs revised manuscript;
- response letter vs actual reviewer concerns.

Focus on:

- whether the response letter is credible and complete;
- whether the revised paper really fixes the main review concerns;
- whether the revision narrative is coherent from the perspective of OPRE reviewers;
- whether there are remaining rejection risks;
- whether language is professional, non-defensive, and OR/OM appropriate.

## Highest-Priority Checks

- Open-system throughput interpretation: effective throughput, completion rate, stability region, latency, TTFT.
- Correct framing of \(M^*\): memory requirement for the ideal-fluid equilibrium, not throughput-optimal memory.
- Removal of misleading heavy-traffic framing.
- Explanation of why WAIT/Nested WAIT are not trivial pipeline filling.
- Unknown output length and on-the-fly classification in Nested WAIT.
- Memory overflow, eviction-induced restarts, and why they make the control problem nonstandard.
- Numerical section consistency: latency, effective completion rate, simulator validation, long-decode eviction diagnostic, real-data workload.
- Whether the response letter overclaims or under-explains any revision.

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

- overall verdict: Strong revise / Mostly ready / Risky / High rejection risk;
- top 5 must-fix issues before resubmission;
- reviewer-specific remaining risks;
- response-letter edits that would most improve credibility;
- paper sections that are already strong and should not be over-edited.
