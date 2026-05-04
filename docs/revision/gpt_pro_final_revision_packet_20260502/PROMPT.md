# Prompt for GPT-Pro Final Revision Audit

You are serving as a senior OPRE/Management Science reviewer and an AE/DE-style editorial auditor. Please audit this revision package thoroughly.

Uploaded materials:

- `01_AE_report.pdf`: AE report.
- `02_review_report_1.pdf`: referee report 1.
- `03_review_report_2.pdf`: referee report 2.
- `04_decision_letter.md`: editor decision letter.
- `05_original_submission.pdf`: original submitted paper.
- `06_revised_paper.pdf`: revised paper.
- `07_response_letter.pdf`: response letter.

Please perform the following audit:

1. Build a complete checklist of the editor, AE, and referee concerns from the review materials.
2. For each concern, verify whether the response letter addresses it clearly and whether the revised manuscript actually contains the corresponding change.
3. Identify any mismatch between the response letter and revised paper, including overclaims, missing citations, unclear experimental descriptions, notation inconsistencies, or proof statements that are not supported by the text.
4. Compare the original and revised paper at a high level. Assess whether the revision materially improves the paper in the ways requested by the reviewers.
5. Pay especially close attention to exposition, language, and presentation quality. Please read as an OPRE/Management Science audience would read it, not as an implementation engineer. Flag places where the writing is:
   - too mechanical, defensive, vague, or "AI-like";
   - too computer-systems oriented for an OR/MS audience;
   - missing the economic/queueing intuition behind the model or policy;
   - using terminology inconsistently across theory, experiments, and the response letter;
   - overexplaining implementation detail while underexplaining the decision logic;
   - making transitions that are abrupt, repetitive, or hard for a first-time reader to follow;
   - using captions, theorem interpretations, or response-letter paragraphs that do not clearly explain why the result matters.
6. For language and exposition, provide concrete sentence-level or paragraph-level rewrite suggestions where possible. Prioritize high-impact edits rather than copyediting every minor phrase.
7. Pay special attention to:
   - objective/stability/throughput framing;
   - memory overflow, eviction, restart, and GPU-resident cache semantics;
   - fluid model and memory requirement notation;
   - WAIT and Nested WAIT theorem/proof clarity;
   - real-data experiment claims and parameter transparency;
   - simulator-to-GPU validation and baseline descriptions;
   - related-work positioning and concurrent-paper discussion;
   - response-letter tone, completeness, and professionalism.
8. Flag any sentence or paragraph that could be read as too strong, unsupported, defensive, vague, awkward, or inconsistent with the paper.
9. Give a final editorial risk assessment: `ready`, `ready after minor edits`, `needs targeted revision`, or `not ready`.

For the output, please use this structure:

1. Executive verdict.
2. Major remaining risks, ordered by severity.
3. Checklist table mapping each review concern to response-letter coverage and manuscript coverage.
4. Specific edits recommended for the response letter.
5. Specific edits recommended for the revised paper.
6. Exposition and language audit: the most important paragraphs/sentences to polish, with suggested rewrites.
7. Any claims that should be softened or backed by additional evidence.
8. Final submission-readiness recommendation.

Be rigorous and adversarial, but do not ask for new experiments unless the current text makes a claim that cannot be supported without them. If a current weakness is already handled by conservative wording, state that explicitly.
