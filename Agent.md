# Agent Progress Notes

## 2026-04-16: Wait vs No-Wait Revision Progress

### Goal
- Address reviewer request on `wait vs no-wait` / "threshold without waiting".
- Compare WCP with `wait_gate=on` and `wait_gate=off`.
- Store representative scenarios and results into SQLite for reproducibility.

### What Was Added
- New script: `scripts/wait_vs_nowait_scenarios.py`
- New SQLite tables in `experiments.db`:
  - `wait_vs_nowait_scenarios`
  - `wait_vs_nowait_runs`
  - `wait_vs_nowait_summary`

### Scenario Coverage
- `single_shortdecode_r18`
- `single_longdecode_r4`
- `memory_limited_r3`
- `balanced_multitype_r20`
- `hetero_multitype_r20`
- `same_prefill_diff_decode_r20`

### Current Interpretation
- `wait_on` looks stronger in more regular scenarios:
  - single-type short decode
  - balanced multi-type
  - same-prefill mixed decode
- `wait_off` remains useful in more extreme scenarios:
  - very long decode
  - memory-limited workloads
  - highly heterogeneous multi-type workloads
- Working takeaway for response letter:
  - neither variant uniformly dominates;
  - `wait_on` helps batch formation in regular settings;
  - `wait_off` helps avoid blocking in long-tail / heterogeneous settings.

### Reproduction
```bash
python scripts/wait_vs_nowait_scenarios.py
```

### Useful SQL
```sql
SELECT scenario_name, ROUND(mean_off,3), ROUND(mean_on,3), ROUND(delta_pct,2), preferred_variant
FROM wait_vs_nowait_summary
ORDER BY scenario_name;
```

```sql
SELECT scenario_name, wait_gate, mean_latency, p99_latency, short_mean, long_mean
FROM wait_vs_nowait_runs
ORDER BY scenario_name, wait_gate;
```

### Next Steps
- Add 2-4 more scenarios if stronger "each has advantages" evidence is needed.
- Convert summary into response-letter text.
- Optionally add one paper-facing table or appendix note keyed to `wait_vs_nowait_summary`.
