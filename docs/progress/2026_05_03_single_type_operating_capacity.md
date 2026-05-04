# Single-Type \(C_{\mathrm{op}}\) Versus \(M^*\) Diagnostic

Date: 2026-05-03

## Question

For the Section 6 single-type workload \(p512d20\), the physical A100 KV-token
capacity is much larger than the balanced fluid memory scale.  The question is
whether we can still give a capacity/memory diagnostic that is consistent with
the observed latency transition without weakening the theory.

## Resolution

Use the configured operating envelope induced by the experiment, not the raw
physical GPU capacity, when interpreting the single-type figure.  In this
experiment, WAIT uses a system-wide cap \(\mathrm{tl}=21\), chunk size \(256\),
and output length \(20\).  The prefill has two chunks, so the single-type
pipeline has
\[
K+l'=2+20=22
\]
prefill/decode stages.  The cap therefore corresponds to a fractional balanced
fluid composition with
\[
P=\frac{21}{22}=0.9545
\]
requests per stage.

The theorem remains stated in terms of a memory budget \(C\).  For the
configured experiment, the relevant budget for the WAIT operating point is
the operating capacity \(C_{\mathrm{op}}\) induced by \(\mathrm{tl}=21\), while
the physical capacity \(C_{\mathrm{phys}}\) is a larger hardware upper bound.
Thus the consistent relationship is
\[
M^*(\lambda)\approx M^\pi \le C_{\mathrm{op}}\le C_{\mathrm{phys}}.
\]

## Computation

Script:

```bash
python scripts/vidur_single_type_operating_envelope.py
```

Output:

- `outputs/fluid_memory/single_type_tl21_operating_envelope.csv`
- `outputs/fluid_memory/single_type_tl21_operating_envelope.json`

The script uses the Vidur Llama-2-7B/A100 predictor and enumerates the 22
representative 21-request batch compositions obtained by omitting one
prefill/decode stage from the full balanced 22-stage composition.  Rotating
over these omitted-stage compositions gives the fractional balanced
\(\mathrm{tl}=21\) operating point.

## Results

| quantity | value |
|---|---:|
| pipeline depth \(K+l'\) | 22 |
| system-wide cap \(\mathrm{tl}\) | 21 |
| fractional per-stage level \(P=21/22\) | 0.9545 |
| operating capacity \(C_{\mathrm{op}}\), worst-case block-rounded tokens | 11,424 |
| fluid memory \(M^\pi\), block-rounded fractional composition | 11,119 |
| \(M^\pi/C_{\mathrm{op}}\) | 0.973 |
| \(C_{\mathrm{op}}/C_{\mathrm{phys}}\), using \(C_{\mathrm{phys}}=1.37\times10^5\) | 0.083 |
| Vidur cycle service boundary | 22.59 req/s |

Additional sweep over \(\mathrm{tl}\le 100\):

| \(\mathrm{tl}\) | \(M^\pi\) block tokens | \(C_{\mathrm{op}}\) block tokens | \(C_{\mathrm{op}}/C_{\mathrm{phys}}\) | Vidur boundary (req/s) |
|---:|---:|---:|---:|---:|
| 21 | 11,119 | 11,424 | 0.083 | 22.59 |
| 30 | 15,884 | 16,320 | 0.119 | 23.40 |
| 40 | 21,178 | 21,760 | 0.159 | 23.82 |
| 50 | 26,473 | 27,200 | 0.199 | 24.32 |
| 75 | 39,709 | 40,800 | 0.298 | 24.31 |
| 100 | 52,945 | 54,400 | 0.397 | 24.58 |

Minimal caps in the \(\mathrm{tl}\le100\) sweep:

| target \(\lambda\) | smallest supporting \(\mathrm{tl}\) | \(M^\pi\) block tokens | \(C_{\mathrm{op}}\) block tokens |
|---:|---:|---:|---:|
| 22 | 20 | 10,589 | 10,880 |
| 23 | 26 | 13,766 | 14,144 |
| 24 | 44 | 23,296 | 23,936 |
| 24.5 | 57 | 30,179 | 31,008 |

Full-capacity extrapolation:

Using the paper's \(C_{\mathrm{phys}}=1.37\times 10^5\) KV-token capacity,
the conservative block-rounded condition
\[
\mathrm{tl}\cdot \lceil(512+20)/16\rceil 16 \le C_{\mathrm{phys}}
\]
gives \(\mathrm{tl}=251\).  With Vidur's Llama-2-7B/A100 predictor evaluated
with prediction batch-size support up to 256, this operating point has
\[
M^\pi=132{,}893,\qquad C_{\mathrm{op}}=136{,}544,\qquad
\mu_{\mathrm{op}}\approx 37.67\text{ req/s}.
\]
This is a capacity-scale extrapolation rather than the configuration used in
Figure B.

The Vidur cycle boundary is computed as follows.  One rotation over the 22
representative 21-request compositions completes 21 requests and takes
approximately 0.929 seconds, so
\[
\mu_{\mathrm{op}}=\frac{21}{0.929}\approx 22.6\text{ req/s}.
\]

## Interpretation

This diagnostic is consistent with Figure B:

- WAIT remains low-latency through roughly \(\lambda=22\)--\(23\) req/s.
- The configured operating envelope has \(M^\pi/C_{\mathrm{op}}\approx0.97\),
  so the cap-induced memory envelope is nearly filled by the balanced fluid
  composition.
- The service boundary of this configured envelope is approximately
  \(22.6\) req/s, matching the observed transition.
- The physical GPU capacity is much larger; it is not the binding quantity in
  this particular short-output synthetic workload.

This does not weaken the theory.  The theory says that if the balanced fluid
memory requirement fits within the policy's memory budget, then WAIT can keep
the stochastic system close to that fluid operating point.  In the single-type
experiment, the policy deliberately operates inside a smaller cap-induced
budget \(C_{\mathrm{op}}\), even though the raw GPU has additional unused KV
capacity.  The observed transition is therefore a transition of the configured
operating envelope, not evidence that the full physical A100 capacity is
exhausted.

Paper-facing sentence if needed:

> For the single-type workload, the physical A100 memory is not the binding
> constraint.  The relevant capacity in Figure~B is the operating envelope
> induced by the configured system-wide cap \(\mathrm{tl}=21\): its
> block-rounded fluid memory is \(0.97\) of that envelope, and the corresponding
> Vidur-calibrated service boundary is about \(22.6\) requests/s, matching the
> observed transition from near-overloaded to overloaded operation.
