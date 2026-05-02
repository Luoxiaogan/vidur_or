# Response Letter Style Bank

Purpose: keep the revision letter appreciative, concrete, and non-mechanical. The goal is not to repeat "we are grateful" in every response, but to show that the editor/referee comments were taken seriously and led to visible manuscript changes.

## References Consulted

- Local reference letter: `papers/docs/response_letter.pdf`.
  - Strong pattern: opens with broad gratitude to the editor and review team, then immediately summarizes the most significant changes.
  - Strong pattern: for major comments, starts with agreement or direct acknowledgment, then explains what was added or revised.
  - Strong pattern: when a comment identifies related literature or positioning gaps, the response says what conceptual overlap exists before drawing distinctions.
- Noble (2017), "Ten simple rules for writing a response to reviewers," PLOS Computational Biology.
  - Key advice: begin with an overview; be polite and respectful; accept that unclear reader understanding may indicate unclear writing; begin responses with a direct answer when possible; make changes explicit.
- ThinkSCIENCE, "Writing effective response letters to reviewers: Tips and a template."
  - Key advice: keep the tone collegial and balanced; do not start every response with "We are grateful for this valuable comment"; avoid overstating that the reviewers "greatly improved" the manuscript in every line.
- Additional public examples from journal response letters.
  - Common pattern: "We thank the reviewers for their constructive comments" in the opening, followed by point-by-point responses that emphasize concrete manuscript changes.

## Style Principle

The right "appreciative" tone has three levels:

- Opening: explicit and warm gratitude to the editor, associate editor, and reviewers.
- Section introductions: acknowledge the reviewer's broad contribution to the revision.
- Individual responses: usually start with agreement or direct acknowledgment of the substance, not another generic thanks.

Bad repetitive pattern:

```tex
We are grateful for this helpful comment, which helped us improve the manuscript.
```

Better pattern:

```tex
We agree that accurate positioning is essential, and we appreciate the reviewer for drawing our attention to this literature. In the revised manuscript, we have added...
```

Why better: it thanks the reviewer once, but the main content is agreement plus action.

## Useful Openings

Use these for the opening paragraph or section-level introductions.

```tex
We want to start by thanking you and the review team for the incredibly helpful and technically detailed feedback. We have been highly receptive to the comments and worked carefully to ensure that the revised manuscript addresses the points raised by the review team.
```

```tex
We thank Reviewer 1 for the careful reading and for emphasizing the importance of modeling clarity, notation consistency, and OOM safeguards. These comments shaped the rewrite of Section 2 and the memory discussion throughout the paper.
```

```tex
We sincerely thank Reviewer 2 for the detailed and constructive technical report. The comments on the time model, the role of the memory assumption, the proof structure, and experimental reproducibility led to several substantive improvements in both the main text and the appendix.
```

## Direct Agreement Patterns

Use these when the reviewer is right and we made the requested change.

```tex
We agree that [issue] is essential. In the revised manuscript, we have...
```

```tex
The reviewer is right that [issue] created avoidable ambiguity in the original manuscript. The revised manuscript now...
```

```tex
This comment correctly identifies [specific gap]. We now...
```

```tex
This is an important practical question. In the revised manuscript, we...
```

```tex
This diagnostic suggestion substantially improved the numerical section. The main figures now...
```

## Respectful Qualification Patterns

Use these when we partly agree but need to define scope.

```tex
We agree with the concern and have clarified the scope of the model. Rather than claiming universality, the revised manuscript now positions [model] as...
```

```tex
This is a useful distinction. The revised paper separates the clean theorem statement from the implementable design...
```

```tex
We agree that this condition is substantive. The revised paper treats [quantity] as..., not as...
```

## Positioning / Novelty Patterns

Use these for comments about contribution, related work, or whether the theory is nontrivial.

```tex
We agree that the contribution needed to be stated more precisely. The paper no longer presents the contribution as [old framing]. Instead, we emphasize...
```

```tex
This comment gets to the core of the theoretical positioning. The difficult step is not [standard implication]; it is [specific difficulty].
```

```tex
The revised manuscript now makes this source of difficulty explicit: [technical mechanism]. This observation motivates...
```

```tex
The key distinction is [distinction]. This leads to a different modeling problem and a different policy structure.
```

## Experimental Transparency Patterns

Use these for numerical reproducibility and evidence comments.

```tex
We agree that the experimental settings needed to be more transparent. We substantially rewrote Section 6 and the Additional Experiments appendix to make the settings reproducible.
```

```tex
The revised numerical section now reports [metric] together with [metric], so the reader can see [mechanism] across [regimes].
```

```tex
This is a natural stress test for the proposed memory-control mechanism, and we added...
```

## Phrases To Avoid Or Use Sparingly

- Avoid repeating "We are grateful for this comment" at the start of many individual responses.
- Avoid "This comment was very helpful" as a standalone sentence.
- Avoid "helped us improve the manuscript" without saying what changed.
- Avoid claiming "the manuscript is greatly improved" too often; let concrete changes show it.
- Avoid defensive phrases such as "we believe the reviewer misunderstood"; write "the original manuscript did not make this sufficiently clear."

## Applied Rule For This Paper

For this OPRE revision letter:

- Use warm gratitude in the opening and reviewer-section introductions.
- For each point, start with the scientific content:
  - "We agree that..."
  - "The reviewer is right that..."
  - "This comment correctly identifies..."
  - "This is an important practical question..."
- Then immediately say what changed:
  - "The revised manuscript now..."
  - "We added..."
  - "We rewrote..."
  - "The appendix now..."
- End with mechanism-level content, not generic praise.
