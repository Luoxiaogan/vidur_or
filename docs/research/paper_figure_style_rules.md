# Paper Figure Style Rules

## Purpose
This note records reusable figure-refinement rules that emerged while polishing the long-decode main-text figure in the OR revision. The goal is not to make figures merely "nicer," but to make them easier to read without compromising quantitative honesty.

## Core Rules

### 1. Judge figures at page scale, not only as standalone images
- Always inspect the compiled paper PDF after replacing a figure.
- A standalone PNG/PDF can look fine while still failing after page-width shrinkage.
- In practice, legend collisions, annotation overlap, and marker crowding often appear only in the compiled manuscript.

### 2. Never improve readability by changing the result
- Do not tweak data values just to create cleaner visual separation.
- Prefer honest visual devices:
  - axis redesign
  - layout changes
  - annotation relocation
  - small marker dodges
  - better whitespace use

### 3. Prefer redesigning the main axis over adding a zoom inset
- A zoom inset often adds complexity without fixing the real readability problem.
- If both low-load and near-boundary behavior matter, redesign the primary axis so both regions are readable in one view.
- Use insets only when the main axis cannot be made legible without breaking the main story.

### 4. Transition points should be explicit, but the annotation system must respect whitespace
- If transition points matter to the argument, mark them directly in the figure.
- Do not let callout boxes, arrows, or rings compete with legends or sit on top of the most important curve segments.
- Prefer anchoring callouts in natural whitespace and letting arrows point outward toward the data.

### 5. When several policies are close, separate markers slightly without changing semantics
- If multiple policies share the same x-values and nearly identical y-values, complete overlap makes the figure unreadable.
- A small horizontal dodge is acceptable when it is purely a display choice and does not alter the underlying values.
- This is especially useful in low-load regions where the correct message is "nearly tied, but visible," not "indistinguishable because hidden."

### 6. Secondary panels must agree visually with the primary panel
- A stylized throughput or stability panel is acceptable only if its knee/plateau locations match the primary latency panel's takeoff points.
- If the right panel implies a different boundary than the left panel, readers will distrust the figure before reading the caption.

### 7. Captions should summarize the readout, not rescue the graphic
- If the caption must explain where the important separation is because the figure does not show it clearly, the figure still needs work.
- The figure should already reveal the main comparison.
- The caption should compress the message, not compensate for visual failure.

## Practical Checklist
- Replace the figure in the paper and compile before judging the layout.
- Check whether the main conclusion is visible without reading the caption first.
- Check legend, callout, and transition-marker overlap at page scale.
- Check whether a secondary panel implies the same stability ordering as the primary panel.
- Check whether close policies need marker separation.
- Check whether the figure is honest to the underlying data.

## Figure G Example
- The long-decode figure improved once the latency panel used a stretched nonlinear main axis instead of a zoom inset.
- The transition-point callout worked only after moving it into upper-center whitespace rather than letting it compete with the legend.
- The throughput panel became credible only after its stylized boundaries were aligned with the visible latency takeoff.
- The two baseline transition markers at `\lambda=4.0` required additional horizontal separation to remain legible at manuscript scale.
