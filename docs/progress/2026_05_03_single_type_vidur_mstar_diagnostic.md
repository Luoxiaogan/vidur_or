# Single-Type Vidur-Calibrated \(M^*\) Diagnostic

Date: 2026-05-03

## Purpose

This note records a diagnostic for the Section 6 single-type synthetic workload
\(p512d20\).  The goal is to compute a reasonable calibrated fluid memory scale
using the same Vidur Llama-2-7B/A100 execution-time predictor, rather than a
global affine fit that can drift away from the simulator used in the experiments.

## Method

For a per-stage scale \(n\), construct the balanced chunked-prefill/decode batch
composition used by the WAIT-style single-type experiment:

- prefill length: 512 tokens;
- output length: 20 tokens;
- chunk size: 256 tokens, hence two chunked-prefill steps;
- \(n\) requests at each of the two prefill steps and each of the 20 decode
  steps;
- balanced batch size: \(22n\), kept within the Llama-2-7B/A100 raw profiling
  range by using \(n\le 5\), so \(22n\le 110\le 128\).

For each \(n\), query the Vidur predictor for the exact balanced batch
composition and set
\[
\mu_{\mathrm{Vidur}}(n)=\frac{n}{\Delta_{\mathrm{Vidur}}(n)}.
\]
For each arrival rate \(\lambda\), choose the smallest \(n\) such that
\(\mu_{\mathrm{Vidur}}(n)\ge \lambda\), and report the resulting memory usage.
Memory is reported in both continuous KV tokens and Vidur-style block-rounded KV
tokens.  The capacity normalization uses \(C=1.37\times 10^5\) KV tokens for
Llama-2-7B on A100 80GB.

Script:

```bash
python scripts/vidur_single_type_fluid_memory_diagnostic.py \
  --num-estimators 12 \
  --max-depth 10 \
  --k-fold-cv-splits 2 \
  --num-training-job-threads 2 \
  --max-n 5
```

Outputs:

- `outputs/fluid_memory/single_type_vidur_balanced_mstar.csv`
- `outputs/fluid_memory/single_type_vidur_balanced_mstar_grid.csv`
- `outputs/fluid_memory/single_type_vidur_balanced_mstar.json`

## Results

Grid over balanced compositions:

| \(n\) | completion rate (req/s) | iteration time (s) | batch size | block-rounded KV tokens | \(M/C\) |
|---:|---:|---:|---:|---:|---:|
| 1 | 22.76 | 0.0439 | 22 | 11,648 | 0.085 |
| 2 | 24.05 | 0.0832 | 44 | 23,296 | 0.170 |
| 3 | 24.60 | 0.1219 | 66 | 34,944 | 0.255 |
| 4 | 23.97 | 0.1669 | 88 | 46,592 | 0.340 |
| 5 | 24.85 | 0.2012 | 110 | 58,240 | 0.425 |

Selected \(M^*(\lambda)\):

| \(\lambda\) (req/s) | selected \(n\) | covers rate? | \(M^*/C\), block-rounded |
|---:|---:|:---:|---:|
| 12 | 1 | yes | 0.085 |
| 14 | 1 | yes | 0.085 |
| 16 | 1 | yes | 0.085 |
| 18 | 1 | yes | 0.085 |
| 20 | 1 | yes | 0.085 |
| 22 | 1 | yes | 0.085 |
| 23 | 2 | yes | 0.170 |
| 24 | 2 | yes | 0.170 |

## Interpretation

For \(p512d20\), the calibrated fluid memory scale is far below the A100 KV-token
capacity.  Thus this single-type short-output workload should not be used as
evidence that the physical KV capacity is near binding.  Its value is instead
diagnostic: it confirms that the observed transition from near-overloaded to
overloaded operation in this workload is driven primarily by service-rate,
batch-composition, and eviction/restart dynamics rather than by the fluid memory
condition \(C<M^*\).

This is not a contradiction with the theory.  The condition \(C\ge M^*\) says
that a balanced fluid operating point can fit in memory; it does not imply that
greedy scheduling baselines realize that operating point.  WAIT is designed to
keep the stochastic system close to the balanced prefill/decode batch
composition that supports the fluid operating point.

Paper-facing implication: if we add an \(M^*\) diagnostic table, use the
single-type \(p512d20\) row only as an underloaded-memory example.  Use
long-output or heterogeneous workloads for memory-pressure discussion.
