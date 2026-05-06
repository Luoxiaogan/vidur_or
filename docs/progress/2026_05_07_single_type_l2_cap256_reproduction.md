# Single-Type Llama-2 Cap-256 Reproduction - 2026-05-07

This note records the paper-facing single-type WAIT reproduction rerun after aligning the Vidur configuration with the Section 6 manuscript settings.

## Scope

- Workload: single-type synthetic `p512d20`.
- Arrival rates: `12,13,...,24`.
- Requests per run: `5000`.
- Model/device: `meta-llama/Llama-2-7b-hf` on simulated A100.
- Baseline: Sarathi with prefill `chunk_size=512` and scheduled-request `batch_size_cap=256`.
- WAIT/WCP: `general_nested_chunked`, `WAIT_CP_GATE=on`, scheduler `wait_gate=on`, memory cleanup enabled.
- WAIT grid: `tl in {20,25,30,35,40,45,50}`, `chunk_size=256`.
- Memory margin: `0.01`.
- Predictor limits: max prefill chunk `16384`, max batch size `2048`, max tokens per request `65536`.
- Paper-facing latency metric: untrimmed mean request E2E latency from `request_metrics_*.csv`.

## Database Records

- Database: `outputs/databases/section6_single_type_reproduction.db`.
- Full run tag: `section6_single_type_l2_cap256_main_20260507`.
- Winner selection tag: `section6_single_type_l2_cap256_wgON_rawmean_winners_20260507`.
- Run-level rows: `single_type_runs`, including full `command_json`, output paths, metric trim fractions, and return codes.
- Selected rows: `single_type_selected_winners`, filtered to WAIT rows with `wait_gate='on'`.

## Selected Winners

| rate | Sarathi512 cap256 mean | WAIT mean | win | WAIT config |
| ---: | ---: | ---: | ---: | --- |
| 12 | 0.4087 | 0.3944 | 3.50% | `WAIT_tl20_cs256_wgON` |
| 13 | 0.4373 | 0.4215 | 3.61% | `WAIT_tl20_cs256_wgON` |
| 14 | 0.4690 | 0.4511 | 3.81% | `WAIT_tl20_cs256_wgON` |
| 15 | 0.5047 | 0.4841 | 4.07% | `WAIT_tl20_cs256_wgON` |
| 16 | 0.5451 | 0.5229 | 4.07% | `WAIT_tl20_cs256_wgON` |
| 17 | 0.5926 | 0.5678 | 4.18% | `WAIT_tl20_cs256_wgON` |
| 18 | 0.6455 | 0.6190 | 4.12% | `WAIT_tl20_cs256_wgON` |
| 19 | 0.7047 | 0.6756 | 4.13% | `WAIT_tl20_cs256_wgON` |
| 20 | 0.7730 | 0.7436 | 3.80% | `WAIT_tl20_cs256_wgON` |
| 21 | 0.8617 | 0.8300 | 3.67% | `WAIT_tl20_cs256_wgON` |
| 22 | 0.9847 | 0.9505 | 3.47% | `WAIT_tl20_cs256_wgON` |
| 23 | 1.2548 | 1.2062 | 3.87% | `WAIT_tl20_cs256_wgON` |
| 24 | 2.6675 | 1.7354 | 34.94% | `WAIT_tl30_cs256_wgON` |

## Interpretation

The paper-facing rerun reproduces the qualitative Section 6 claim that WAIT is lower latency than Sarathi at every tested rate in `12..24` under the Llama-2/A100/Sarathi-cap-256 setting. The selected parameters are simple: `tl=20` for rates `12..23`, and `tl=30` at rate `24`.

The earlier manuscript sentence claiming an over-70% gap at `lambda=23` is not supported by this rerun. Under both untrimmed mean and middle-50% mean, the `lambda=23` improvement is about 3.9%. The large boundary separation appears at `lambda=24`, where WAIT improves over Sarathi by about 35%.
