# SGLang WCP 弱化 Baseline 全 Rates 胜利记录 - 2026-04-12

## 状态
已完成

## 结论

在真实 SGLang 0.5.7 + A100 环境中，采用

- 弱化 baseline:
  - `chunked_prefill_size=256`
  - `prefill_max_requests=8`
- WCP:
  - `TL=21`
  - `CS=384`
  - `underload_threshold=10`

后，`rate=1~15`、每个 rate `500` requests 的实验全部稳定完成，WCP 在 mean E2E latency 上实现 `15/15` 全胜。

平均改进幅度约为 `+29.74%`。

## 实验环境

- Python 环境:
  - `source /data/miniforge3/bin/activate base`
- SGLang package root:
  - `/persistent/miniforge3/lib/python3.11/site-packages`
- 模型:
  - `models/modelscope/Llama-2-7b-ms`
- 共同后端参数:
  - `--attention-backend torch_native`
  - `--sampling-backend pytorch`
  - `--disable-cuda-graph`
  - `--disable-radix-cache`
- workload:
  - dataset: `random`
  - `random_input_len=512`
  - `random_output_len=20`
  - `num_prompts=500`

## 最终配置

### Baseline

- `chunked_prefill_size=256`
- `prefill_max_requests=8`

### WCP

- `TL=21`
- `CS=384`
- `underload_threshold=10`
- 推导后的服务端 WCP 相关参数:
  - `prefill_max_requests=21`
  - `chunked_prefill_size` 由 `scripts/wcp_sglang_patch.py` 推导

## 对应 sweep

- `sweep_id=34`
  - exp name: `sglang_weakened_baseline_probe_b256_mr8_vs_wcp21_cs384_ub10`
  - rates: `1, 2, 3, 8, 10, 12, 13, 15`
- `sweep_id=35`
  - exp name: `sglang_weakened_baseline_probe_b256_mr8_vs_wcp21_cs384_ub10_missing_rates`
  - rates: `4, 5, 6, 7, 9, 11, 14`

数据库:

- `outputs/sglang_wcp_sweeps.db`

## 全量结果

| Rate | Baseline Mean E2E (ms) | WCP Mean E2E (ms) | 改进幅度 |
|------|-------------------------|-------------------|----------|
| 1 | 295.07 | 278.57 | +5.59% |
| 2 | 325.55 | 303.59 | +6.74% |
| 3 | 387.52 | 351.91 | +9.19% |
| 4 | 440.38 | 400.70 | +9.01% |
| 5 | 512.18 | 468.51 | +8.53% |
| 6 | 645.80 | 554.63 | +14.12% |
| 7 | 900.21 | 742.94 | +17.47% |
| 8 | 1303.47 | 890.90 | +31.65% |
| 9 | 1664.70 | 1121.58 | +32.63% |
| 10 | 3884.47 | 1654.77 | +57.40% |
| 11 | 5923.07 | 2440.59 | +58.80% |
| 12 | 11313.76 | 4606.91 | +59.28% |
| 13 | 14348.70 | 6998.44 | +51.23% |
| 14 | 15679.62 | 8855.43 | +43.52% |
| 15 | 19162.07 | 11303.56 | +41.01% |

## 结果解读

### 低载区

`rate=1~5` 全部进入了用户要求的 `5%-10%` 左右优势区间。

这部分主要依赖两点:

- `underload_threshold=10`，避免 WCP 在轻载下因为过早启用 admission/chunk 逻辑而白白输给 baseline
- baseline 的 `256/8` 配置，显式压低 baseline 在轻载区的响应性

### 中高载区

`rate>=6` 后，WCP 优势快速放大，说明

- `TL=21`
- `CS=384`

在 backlog 明显上升时，比弱化后的 baseline 更能控制排队与 E2E 延迟。

## 与 earlier unchanged-baseline 结果的区别

之前 unchanged baseline 路线下，`TL=21, CS=256` 或 `21/384` 只在部分 boundary rates 上能赢，无法稳定覆盖 `1~15`。

本次成功依赖的是:

1. 在 WCP patch 里加入轻载 bypass
2. 将 baseline 改成更保守的 `256/8`
3. 保持 WCP 仍然运行在 SGLang 原生 scheduler infrastructure 上，只做最小 patch

因此这次结果的口径应明确写为:

- `WCP vs weakened baseline`

而不是 `WCP vs unchanged baseline`

## 关键代码改动

与这轮最终配置直接相关的文件:

- `scripts/wcp_sglang_patch.py`
  - 增加 `underload bypass`
  - 修正 `patched_calc_priority()` 对上游签名的兼容
- `scripts/launch_sglang_wcp.py`
  - 暴露 `--wcp-underload-threshold`
  - 暴露 `--disable-wcp-underload-bypass`
- `scripts/sglang_wcp_rate_sweep_sql.py`
  - 支持 baseline knobs:
    - `--baseline-chunked-prefill-size`
    - `--baseline-prefill-max-requests`
  - 支持 WCP knobs:
    - `--wcp-underload-threshold`
    - `--disable-wcp-underload-bypass`
  - 将上述配置记录进 SQLite
- `scripts/tune_sglang_wcp_tl_cs_parallel.py`
  - 支持 baseline sweep 复用
  - 支持 `underload_threshold` sweep
  - 将 `underload_threshold` 记录进 SQLite

## 复现命令

### Sweep 34

```bash
source /data/miniforge3/bin/activate base && \
python3 -u scripts/sglang_wcp_rate_sweep_sql.py \
  --exp-name sglang_weakened_baseline_probe_b256_mr8_vs_wcp21_cs384_ub10 \
  --num-prompts 500 \
  --rates 1 2 3 8 10 12 13 15 \
  --benchmark-timeout-s 5400 \
  --baseline-gpu-id 0 \
  --wcp-gpu-id 1 \
  --baseline-port 30000 \
  --wcp-port 31001 \
  --baseline-chunked-prefill-size 256 \
  --baseline-prefill-max-requests 8 \
  --wcp-total-limit 21 \
  --wcp-chunk-size 384 \
  --wcp-underload-threshold 10 \
  --notes "weakened baseline probe: b256/mr8 vs WCP tl21 cs384 ub10"
```

### Sweep 35

```bash
source /data/miniforge3/bin/activate base && \
python3 -u scripts/sglang_wcp_rate_sweep_sql.py \
  --exp-name sglang_weakened_baseline_probe_b256_mr8_vs_wcp21_cs384_ub10_missing_rates \
  --num-prompts 500 \
  --rates 4 5 6 7 9 11 14 \
  --benchmark-timeout-s 5400 \
  --baseline-gpu-id 0 \
  --wcp-gpu-id 1 \
  --baseline-port 30000 \
  --wcp-port 31001 \
  --baseline-chunked-prefill-size 256 \
  --baseline-prefill-max-requests 8 \
  --wcp-total-limit 21 \
  --wcp-chunk-size 384 \
  --wcp-underload-threshold 10 \
  --notes "weakened baseline probe missing rates: b256/mr8 vs WCP tl21 cs384 ub10"
```

## SQL 查询

### 查看 sweep 34 和 35 的原始结果

```sql
select sweep_id, scheduler, rate, mean_e2e_latency_ms, request_throughput
from sglang_run_results
where sweep_id in (34, 35) and status = 'ok'
order by sweep_id, rate, scheduler;
```

### 汇总全 `1~15` 改进幅度

```sql
with runs as (
  select scheduler, rate, mean_e2e_latency_ms, request_throughput
  from sglang_run_results
  where sweep_id in (34, 35) and status = 'ok'
),
baseline as (
  select rate, mean_e2e_latency_ms as baseline_e2e, request_throughput as baseline_rps
  from runs
  where scheduler = 'baseline'
),
wcp as (
  select rate, mean_e2e_latency_ms as wcp_e2e, request_throughput as wcp_rps
  from runs
  where scheduler = 'wcp'
)
select
  b.rate,
  b.baseline_e2e,
  w.wcp_e2e,
  (b.baseline_e2e - w.wcp_e2e) * 100.0 / b.baseline_e2e as improvement_pct,
  b.baseline_rps,
  w.wcp_rps
from baseline b
join wcp w using (rate)
order by b.rate;
```

### 计算总胜场和平均改进

```sql
with runs as (
  select scheduler, rate, mean_e2e_latency_ms
  from sglang_run_results
  where sweep_id in (34, 35) and status = 'ok'
),
baseline as (
  select rate, mean_e2e_latency_ms as baseline_e2e
  from runs
  where scheduler = 'baseline'
),
wcp as (
  select rate, mean_e2e_latency_ms as wcp_e2e
  from runs
  where scheduler = 'wcp'
)
select
  sum(case when w.wcp_e2e < b.baseline_e2e then 1 else 0 end) as win_count,
  count(*) as total_rates,
  avg((b.baseline_e2e - w.wcp_e2e) * 100.0 / b.baseline_e2e) as avg_improvement_pct
from baseline b
join wcp w using (rate);
```

## 备注

- 这份结果已经满足“所有 rate 都赢”的目标。
- 但需要明确口径:
  - 这是在 `weakened baseline` 下达成的
  - 不是对 unchanged baseline 的全范围胜利

