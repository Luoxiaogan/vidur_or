You are acting as a skeptical but constructive OPRE/Management Science reviewer, Associate Editor, and Department Editor. I am uploading a revision package for a paper on online scheduling for LLM inference.

Please read all uploaded materials:

- Original submission: `05_original_submission.pdf`
- Revised paper: `06_revised_paper.pdf`
- Response letter: `07_response_letter.pdf`
- AE/referee reports and decision letter: `01_AE_report.pdf`, `02_review_report_1.pdf`, `03_review_report_2.pdf`, `04_decision_letter.md`
- Internal/external audit notes: `08_internal_followup_checklist.md`, `09_external_audit_report_1.md`, `10_external_audit_report_2.md`

Your task is to perform a final resubmission audit. Focus especially on exposition and language quality, logic, response-letter coverage, technical consistency, and claim scope.

Please produce the following:

1. Executive verdict: choose one of `ready to submit`, `ready after minor edits`, `needs targeted revision`, or `not ready`.
2. Top remaining risks, ordered by severity. For each risk, give exact locations in the revised paper or response letter and explain why it matters to the AE/referees.
3. Review-concern coverage matrix: for each major AE/referee/decision-letter concern, state whether it is addressed in the response letter and in the revised manuscript. Flag any mismatch where the letter claims a change that is weak, absent, or overstated in the paper.
4. Exposition and language audit: identify paragraphs, captions, theorem interpretations, abstract/conclusion claims, or response-letter passages that still sound unclear, defensive, too strong, too AI-generated, or not sufficiently OR/MS style. Provide concrete rewrites.
5. Technical consistency audit: check notation, memory semantics, throughput/latency definitions, stability-region language, simulation-vs-real-GPU claims, affine timing model scope, proof statement coverage, and experiment parameter transparency.
6. Claim-scope audit: list claims that are too broad or could be attacked by a skeptical reviewer. Suggest precise safer wording.
7. Final edit checklist: provide a prioritized checklist with `P0`, `P1`, and `P2` items. Keep the list actionable and avoid generic advice.

Important standards:

- Be adversarial enough to catch issues a negative referee would seize on.
- Do not ask for new experiments unless truly necessary; prefer text/proof/positioning fixes when sufficient.
- Pay close attention to whether the response letter is accurate and non-overclaiming.
- Pay close attention to whether the revised manuscript reads as an OR/MS paper rather than a systems paper.
- Check whether the paper consistently distinguishes Vidur simulations from real-GPU validation.
- Check whether `near-overloaded` / `overloaded`, `stability region`, `effective throughput`, `memory overflow`, `eviction/restart`, and `unknown output length` are used consistently.

