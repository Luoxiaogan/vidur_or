# Insights

- Section 6 should present the experiments as evidence about stability regions and wasted work from evictions, not just raw latency comparisons.
- When the text explains a baseline mechanism, prefer operational description over systems jargon.
- Endogenous memory growth is also the reason the analysis needs dimensionality reduction: without thresholds, the primitive state tracks resident prompts across output-length classes and prefill/decode stages, plus eviction/restart feedback. WAIT and Nested WAIT reduce this to threshold and boundary queues that capture the memory-coupled dynamics.
