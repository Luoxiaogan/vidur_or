# Real-Data Remeasurement Checklist

## Status
- Current paper text and Figure D now reflect the **observed** real-data sweep that is already recorded.
- For now, we are **keeping those observed results as-is**.
- The items below are what should be rerun before making any stronger claim about the real-data stability boundary or about the exact strength of Nested WAIT on lmsys.

## 1. Source-of-Truth Reconstruction

These are the minimum items needed to make the current real-data section auditable.

- Re-export the full lmsys 50-bin QPS grid used for the paper:
  - `QPS = 10, 20, ..., 150`
  - policies: `vLLM`, `Sarathi(256)`, `Sarathi(512)` if still relevant, `Nested WAIT`
- For every QPS point, record the exact config that produced the plotted number:
  - chunk size
  - total limit / `tl`
  - segment count or segment size
  - any gate / wait-gate switches
  - number of requests and warmup/truncation rule
- Import the full grid into a durable local table (instead of keeping Figure D as a hand-transcribed artifact).
- Check that the current `experiments.db` matches the paper-facing sweep. Right now the local `real_data` table is incomplete relative to the figure.

## 2. Figure D Data Cleanup

These items are needed so the plotted figure is directly reproducible from stored data.

- Rebuild Figure D from the database or a committed CSV, not from hard-coded values in the script.
- Store the exact latency series used by Figure D in a committed artifact.
- Store the exact throughput series used by Figure D in a committed artifact.
- Verify that the plotted throughput panel is based on measured completions or a clearly documented stylized rule.
- Confirm that the paper caption, prose, and plotting script all refer to the same QPS grid.

## 3. Boundary Clarification Sweep

These runs are needed if we want to say more than “observed sweep outcomes.”

- Run a denser local sweep around the real-data crossover / transition region.
- Minimum recommended QPS set:
  - `35, 40, 45, 50, 55, 60, 65, 70`
- If compute budget allows, add:
  - `75`
- Goal:
  - pin down where vLLM first deteriorates
  - confirm where the Sarathi--Nested WAIT gap first becomes material
  - recover the exact `QPS=50` Nested WAIT configuration and latency used in the all-lower-latency Figure D series

## 4. Long-Horizon Validation on Real Data

These runs are needed before using “stability boundary” language for lmsys.

- Pick 2-3 QPS points near the suspected Sarathi / Nested WAIT transition.
- Recommended candidates:
  - `50`, `60`, `70`
  - or `55`, `60`, `65` if the denser sweep above is available
- For each chosen QPS, rerun with increasing horizons / request counts.
- Minimum progression:
  - current baseline horizon
  - `2x`
  - `4x`
  - `8x`
- Record whether mean latency plateaus or keeps drifting upward.

## 5. Repeatability / Variance Checks

These runs are needed if we want the real-data claim to sound statistically stable rather than anecdotal.

- Repeat the key real-data points with multiple seeds / repeated Poisson draws.
- Minimum points:
  - one low-load point where policies are close
  - the `QPS=50` near-tie point
  - one or two medium/high-load points where Nested WAIT is clearly better
- Recommended minimum set:
  - `40`, `50`, `60`, `100`
- Report:
  - mean
  - standard deviation / confidence interval
  - whether policy ordering changes across seeds

## 6. Hyperparameter Robustness for Nested WAIT

These runs are needed if we want to argue the gain is structural rather than a fragile per-point tuning accident.

- For each key QPS, rerun a narrow local search around the selected Nested WAIT config.
- Minimum metadata to preserve:
  - selected best config
  - top 3 nearby configs
  - performance gap among them
- Important checkpoints:
  - whether the best config is isolated or part of a stable basin
  - whether the all-lower-latency ordering remains stable around `QPS=50` after a careful local search

## 7. Segment-Count / Segment-Size Consistency

These runs are needed because the paper now reports a segment-count sensitivity analysis for the real-data setup.

- Reconfirm whether the main real-data figure should be tied to a single paper-facing choice of `m`, and if so whether `m=50` remains the right choice under the current real-data setup.
- Recheck comparison set:
  - `m=10`
  - `m=25`
  - `m=50`
  - `m=100`
  - `m=200`
- Ensure that the ablation table and the main real-data figure are based on the same underlying workload definition and compatible tuning rules.

## 8. Appendix / Configuration Audit

These items are needed so the appendix does not silently describe an obsolete experiment.

- Re-verify the real-data `tl` search grid actually used for the 50-bin results.
- Re-verify whether chunk-size search was part of the final selected pipeline.
- Re-verify whether the paper should mention:
  - only `tl`
  - `tl + chunk size`
  - `tl + chunk size + segment size`
- After that, update:
  - `papers/appendix_sim_fidelity.tex`
  - any configuration tables
  - any state/progress docs that still mix old and new real-data setups

## 9. Claims That Should Wait Until After Reruns

Do **not** strengthen the real-data wording beyond the current observed-sweep phrasing until the items above are done.

- Do not claim an exact real-data stability boundary.
- Do not claim `Nested WAIT` wins at every rate.
- Do not claim a precise boundary ordering like synthetic unless supported by a denser sweep plus horizon validation.
- Do not describe the throughput panel as a measured stability frontier unless it is backed by measured completion data.

## 10. Recommended Execution Order

If time is limited, do the reruns in this order.

1. Reconstruct and store the exact paper-facing 10--150 sweep data.
2. Dense local sweep around `40--70`.
3. Repeatability checks at `40`, `50`, `60`, `100`.
4. Long-horizon validation near the crossover.
5. Hyperparameter robustness around the selected Nested WAIT configs.
6. Appendix/configuration cleanup after the above is settled.
