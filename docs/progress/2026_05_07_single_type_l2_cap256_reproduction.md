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
- SQL helper: `docs/sql/single_type_boundary_winners.sql`.

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

## Follow-up Boundary Tuning

After checking the original Figure B provenance, the large `lambda=23` gap was traced to an older Llama-3 style configuration:

- Model: `meta-llama/Meta-Llama-3-8B`.
- Memory margin: `0.1`.
- Sarathi batch cap: `512`.
- WAIT: `tl=21`, `chunk_size=256`, scheduler `wait_gate=off`.
- Requests/metric: `10000` requests, seed `42`, middle-50% request window.
- Reproduced at `lambda=23`: Sarathi `8.787s`, WAIT `1.270s`, win `85.5%`.

Under the current Llama-2/Sarathi-cap-256 setting, `lambda=23` is not yet at the same overload boundary:

- Run tag: `section6_single_type_l2_cap256_n10000_seed42_20260507`.
- `lambda=23`: Sarathi `1.254s`, best WAIT `1.205s`, win `3.9%`.
- Changing Sarathi cap from `256` to `512`, changing memory margin from `0.01` to `0.1`, or switching scheduler `wait_gate` off did not materially change the Llama-2 `lambda=23` result.

The corresponding Llama-2 boundary appears about two arrival-rate units later. The tuned Llama-2/cap-256 boundary winners are stored under selection tag `section6_single_type_l2_cap256_boundary_winners_n10000_seed42_20260507`:

| rate | Sarathi512 cap256 mean | WAIT mean | win | WAIT config |
| ---: | ---: | ---: | ---: | --- |
| 24 | 4.228 | 1.846 | 56.3% | `WAIT_tl30_cs256_wgON` |
| 25 | 11.086 | 2.994 | 73.0% | `WAIT_tl240_cs512_wgON` |
| 26 | 18.634 | 4.688 | 74.8% | `WAIT_tl200_cs256_wgON` |

These rows show that the large-win mechanism is reproducible under Llama-2/cap-256 near its observed boundary, but not specifically at `lambda=23` with the current Llama-2 service curve.

## Reproduction Commands

Run the main Llama-2/cap-256 curve:

```bash
python scripts/section6_single_type_reproduction.py \
  --run-tag section6_single_type_l2_cap256_main_20260507 \
  --mode all \
  --rates 12,13,14,15,16,17,18,19,20,21,22,23,24 \
  --tl-values 20,25,30,35,40,45,50 \
  --wcp-chunk-sizes 256 \
  --nreq 5000 \
  --memory-margin-fraction 0.01 \
  --sarathi-batch-size-cap 256 \
  --trim-head-frac 0 \
  --trim-tail-frac 0
```

Run the Llama-2 boundary grid with middle-50% latency:

```bash
python scripts/section6_single_type_reproduction.py \
  --run-tag section6_single_type_l2_cap256_boundary_grid_n10000_seed42_20260507 \
  --mode all \
  --rates 24,25,26 \
  --tl-values 20,30,40,50,60,80,100,120,160,200 \
  --wcp-chunk-sizes 256 \
  --nreq 10000 \
  --seed 42 \
  --memory-margin-fraction 0.01 \
  --sarathi-batch-size-cap 256 \
  --trim-head-frac 0.25 \
  --trim-tail-frac 0.25
```

Run the rate-25 chunk-size refinement:

```bash
python scripts/section6_single_type_reproduction.py \
  --run-tag section6_single_type_l2_cap256_rate25_chunk_tune_n10000_seed42_20260507 \
  --mode all \
  --rates 25 \
  --tl-values 160,180,200,220,240 \
  --wcp-chunk-sizes 64,128,256,384,512 \
  --nreq 10000 \
  --seed 42 \
  --memory-margin-fraction 0.01 \
  --sarathi-batch-size-cap 256 \
  --trim-head-frac 0.25 \
  --trim-tail-frac 0.25
```

Reproduce the older Llama-3 large-win sanity check:

```bash
python scripts/section6_single_type_reproduction.py \
  --run-tag section6_single_type_l3_oldstyle_n10000_seed42_20260507 \
  --mode all \
  --rates 23 \
  --tl-values 21 \
  --wcp-chunk-sizes 256 \
  --nreq 10000 \
  --seed 42 \
  --model-name meta-llama/Meta-Llama-3-8B \
  --memory-margin-fraction 0.1 \
  --sarathi-batch-size-cap 512 \
  --no-wait-gate \
  --trim-head-frac 0.25 \
  --trim-tail-frac 0.25
```

Query the selected boundary winners:

```bash
sqlite3 -header -column outputs/databases/section6_single_type_reproduction.db \
  < docs/sql/single_type_boundary_winners.sql
```
