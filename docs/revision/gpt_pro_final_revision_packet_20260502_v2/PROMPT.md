# Prompt For GPT-Pro Final Revision Audit

You are acting as a demanding OPRE / Management Science / Operations Research reviewer and associate-editor advisor. Please audit this revision package before resubmission.

Please read all uploaded files:

1. `01_AE_report.pdf`
2. `02_review_report_1.pdf`
3. `03_review_report_2.pdf`
4. `04_decision_letter.md`
5. `05_original_submission.pdf`
6. `06_revised_paper.pdf`
7. `07_response_letter.pdf`
8. `08_internal_audit_checklist.md`

Your task is to evaluate the revised manuscript and response letter against the original review concerns. Be strict and concrete.

## Main Questions

1. Does the revised paper directly address the AE, referee, and decision-letter concerns?
2. Does the response letter accurately describe what changed in the revised paper, without overclaiming?
3. Are there any remaining gaps between the response letter and the revised manuscript?
4. Are any claims in the abstract, introduction, theory sections, numerical section, conclusion, or response letter too strong relative to the evidence or proofs?
5. Are the theoretical statements and appendix proof coverage aligned with the main-text propositions and theorems?
6. Are the numerical experiments described transparently enough, including simulator-versus-real-GPU scope, workload settings, parameter tuning, memory cap, replications, and stability/latency interpretation?
7. Does the paper now read like an OR/MS paper rather than a systems-only paper?
8. Are there remaining exposition or language problems that could irritate a skeptical reviewer?

## Specific Items To Check

- Whether the paper properly handles the open-system throughput issue: stable systems cannot complete more useful work than offered load, and instability should show up through latency growth, completion-rate saturation, eviction, or restart waste.
- Whether the memory model is clear: GPU-resident KV cache includes admitted prompts that are paused/preempted, and exceeding memory causes eviction/restart.
- Whether WAIT and Nested WAIT are positioned as nontrivial threshold policies for controlling endogenous memory growth, not as routine batching or ordinary queueing.
- Whether the affine decode-centered timing model is scoped appropriately and supported by the A100 validation.
- Whether Vidur simulation comparisons are clearly distinguished from supplemental real-GPU validation.
- Whether real-data Nested WAIT tuning is transparent: parameters are selected from a prespecified grid using the workload distribution and offered arrival rate, not future realized arrivals or individual output-length predictions.
- Whether the proof appendix contains proof coverage for every formal proposition/theorem in the revised paper, especially lower-bound propositions.
- Whether the finite-horizon Nested WAIT safety buffer is described correctly as logarithmic in the horizon and inverse failure probability.
- Whether related work and response-letter language fairly position concurrent LLM-inference scheduling papers.
- Whether the response letter tone is professional, appropriately appreciative, and not formulaic or defensive.

## Output Format

Please return:

1. Executive verdict: `ready`, `ready after minor edits`, `needs targeted revision`, or `not ready`.
2. Top remaining risks, ordered by severity.
3. A table mapping each AE/referee/decision-letter concern to response-letter coverage and manuscript coverage.
4. Specific edits needed in the response letter, with suggested replacement language where useful.
5. Specific edits needed in the revised paper, with section/page references where possible.
6. Exposition and language audit: identify awkward, AI-like, defensive, vague, or non-OR/MS phrasing.
7. Claim-scope audit: identify any claims that should be softened, sharpened, or backed by evidence.
8. Final resubmission recommendation.

For every finding, include severity, location, why it matters, and a concrete suggested fix.
