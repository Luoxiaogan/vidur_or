# 2026-05-07 LMSYS Cap-256 Winner Selection

## Paper-facing benchmark口径

- Model: `meta-llama/Llama-2-7b-hf`.
- Device: `a100`, tensor parallel size 1, pipeline stages 1.
- Workload: LMSYS-derived 50-bin decode distribution, `nreq=5000`.
- Metric: middle 50% request e2e latency, `trim_head_frac=0.25`, `trim_tail_frac=0.25`.
- Baseline: Sarathi with prefill `chunk_size=512` and scheduled-request `batch_size_cap=256`.
- WCP selection requires `wait_gate=on`.
- WCP memory cleanup is enabled in the generated Vidur command.

## Durable records

- Baseline run tag: `section6_lmsys_cap256_baselines_10_150_20260507`.
- qps70 confirmation tags:
  - `qps70_sarathi512_batchcap256_pred2048_20260506`.
  - `qps70_paper_batchcap256_wcp_confirm_20260506`.
- High-qps confirmation tag: `section6_lmsys_cap256_highqps_confirm_20260507`.
- Database table: `section6_lmsys_selected_winners`.
- Selection tag: `section6_cap256_waiton_winners_20260507`.
- Run-level configs are stored in `reproduction_configs` for the baseline run, high-qps WCP confirmation run, tail-priority probe, and final winner selection. Per-run rows retain full `command_json`, `prompt_types_json`, `n_k_json`, and `segments_json` provenance.

## Selected winners

| qps | Sarathi512 cap256 mean | WCP mean | win | WCP config |
|---:|---:|---:|---:|---|
| 10 | 1.688170 | 1.687841 | 0.02% | `auto4seg_tl70_cs256_sm0p05_wgON` |
| 20 | 2.081040 | 2.080306 | 0.04% | `auto3seg_tl160_cs128_sm0p05_wgON` |
| 30 | 3.140654 | 3.010185 | 4.15% | `auto1seg_tl100_cs128_sm0p05_wgON` |
| 40 | 4.129904 | 4.097272 | 0.79% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 50 | 4.747597 | 4.706791 | 0.86% | `auto2seg_tl280_cs128_sm0p05_wgON` |
| 60 | 9.485880 | 5.522961 | 41.78% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 70 | 14.789535 | 10.065044 | 31.94% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 80 | 18.968755 | 14.128483 | 25.52% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 90 | 22.153214 | 17.423513 | 21.35% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 100 | 24.669906 | 20.084488 | 18.59% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 110 | 26.852464 | 22.240951 | 17.17% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 120 | 28.590675 | 24.064557 | 15.83% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 130 | 30.099663 | 25.620069 | 14.88% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 140 | 31.504775 | 26.973871 | 14.38% | `auto1seg_tl300_cs128_sm0p05_wgON` |
| 150 | 32.528842 | 28.161907 | 13.42% | `auto1seg_tl300_cs128_sm0p05_wgON` |

## Interpretation

The cap-256 Sarathi baseline is the key paper-facing denominator. Under this denominator, WCP wins at every qps from 10 to 150. The low-qps wins are intentionally tiny and should be described as essentially matching Sarathi, while qps 30 and the higher-qps regime show material gains.

For the paper text, avoid overclaiming at qps 10 and 20: those wins are only 0.02% and 0.04%. The robust story is that WCP matches Sarathi at low load and wins increasingly once the system is congested.
