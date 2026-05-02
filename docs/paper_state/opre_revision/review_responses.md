# Review Responses

## Reviewer 2 / AE-Relevant Experimental Points

- Simulator fidelity must be stated quantitatively, with direct citation to the Vidur paper and local appendix validation.
- Section 6 should explain why throughput differences reflect stability-region differences under the serving model used here.
- The response to the `C\ge M^*` concern now treats `M^*` as the memory requirement for the fluid equilibrium. The paper explains that `M^*\le C` is a fluid-model stabilizability condition, while the experiments evaluate whether WAIT/Nested WAIT realize the corresponding stable operating regime under stochastic memory growth and eviction risk.
- Real-data Nested WAIT parameter reporting is now conservative: it states the finite grids for the system-wide batch cap and segment count, explains that these policy parameters are distribution-aware and arrival-rate dependent, and avoids claiming that larger caps or finer segmentation are monotone improvements.
- Section 6 now also reports the A100~80\,GB / Llama-2-7B KV-cache token scale, so the real-data `\mathrm{tl}` grid is interpreted alongside the physical memory capacity rather than as an abstract request-count knob.

## Decision-Letter / Referee-Relevant Framing Points

- Use `effective throughput`, not bare `throughput`, in narrative prose when evictions matter.
- Keep the experiments tied to the paper's main mechanism: eviction prevention and stability-region expansion.
- For response-letter language, keep the experimental claims tied to observed latency, effective completion, and eviction patterns across underloaded, near-overloaded, and overloaded regimes; do not present those runs as direct proof of the theorem condition.
