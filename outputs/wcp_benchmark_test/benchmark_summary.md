# WCP vs vLLM Benchmark Results

## Configuration
- Model: models/modelscope/Llama-2-7b-ms
- WCP Parameters: tl=21, cs=256
- Decode Length: 20
- Iterations: 3

## Overall Results
- **Mean Improvement**: 8.39%
- **WCP Wins**: 10/10 configurations
- **vLLM Wins**: 0/10 configurations

## Detailed Results

| Batch | Prefill | vLLM (ms) | WCP (ms) | Improvement |
|-------|---------|-----------|----------|-------------|
| 1 | 256 | 290.05 | 266.97 | +7.96% |
| 1 | 512 | 290.34 | 271.70 | +6.42% |
| 4 | 256 | 302.65 | 273.28 | +9.71% |
| 4 | 512 | 311.91 | 284.06 | +8.93% |
| 8 | 256 | 311.02 | 287.81 | +7.46% |
| 8 | 512 | 350.13 | 316.32 | +9.66% |
| 16 | 256 | 340.84 | 313.18 | +8.12% |
| 16 | 512 | 393.04 | 354.49 | +9.81% |
| 32 | 256 | 396.32 | 371.19 | +6.34% |
| 32 | 512 | 502.18 | 454.23 | +9.55% |

## Conclusion

WCP achieves an average improvement of **8.39%** over vLLM default scheduling.
WCP wins in all tested configurations, demonstrating the effectiveness of:
- Nested Booking Limit with segment-wise control
- Per-request chunked prefill
- Per-segment gate mechanism
