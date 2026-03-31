# Real Data Experiments (lmsys-chat-1m) - 2026-03-28~30

## 状态
✅ 已完成

## 概要
在 lmsys real data (prefill=35, decode=1-500) 上完成 Nested WAIT-CP 全面调参。50 bins 是关键突破：vs Sar(256) 14/15 QPS WIN (-2%~-30%)。同时完成了 long decode (p512d1000)、memory-constrained eviction、throughput 分析等实验。

## 主要成果

### 1. Real Data (lmsys) 50 bins 突破
- **10 bins**: 全 QPS LOSE (best +1.9%)
- **50 bins**: 14/15 QPS WIN vs Sar(256,256) (-2.2%~-29.7%)
- 关键: 更多 bins = 更精确 segment-decode 对齐

### 2. 完整 QPS Grid (10-150, step=10)

| QPS | vLLM | Sar(256) | Sar(512) | WCP | vs Sar256 |
|-----|------|----------|----------|-----|-----------|
| 10 | 1.9s | 1.7s | 1.7s | 1.6s | **-4.1%** |
| 20 | 2.3s | 1.9s | 1.9s | 1.8s | **-3.8%** |
| 30 | 3.2s | 2.2s | 2.2s | 2.2s | **-3.4%** |
| 40 | 15.4s | 2.9s | 2.9s | 2.9s | **-2.2%** |
| 50 | 30.1s | 3.9s | 4.5s | 4.4s | +11.4% |
| 60 | 40.0s | 12.2s | 7.5s | 8.5s | **-29.7%** |
| 70 | 47.2s | 19.3s | 13.1s | 14.5s | **-24.9%** |
| 80 | 52.9s | 24.5s | 18.0s | 19.8s | **-19.2%** |
| 90 | 57.1s | 28.7s | 22.1s | 23.6s | **-17.9%** |
| 100 | 60.2s | 32.1s | 25.3s | 27.1s | **-15.6%** |
| 110-150 | 63-70s | 35-42s | 28-35s | 30-38s | **-11%~-14%** |

### 3. Long Decode (p512d1000) WIN
- r=3.0-5.0: -1.3%~-22.4% WIN
- 低 rate 持平
- p128d1000 全 LOSE (prefill 太小)

### 4. Memory-Constrained Eviction
- margin=0.6 r=4.0: WCP 31.3s (0 evictions) vs Sarathi 78.1s (3222 evictions)
- WCP 的 tl 是天然 memory safeguard

### 5. Throughput
- Single-type r=23+: WCP 460 > Sarathi 445 > vLLM 422 tok/s

### 6. UniformSegmentChunkedReplicaScheduler 新调度器
- 等分 segment, 每 seg 的 n_k 相同
- 用于 single-type 长 decode 场景

## 调参维度 (lmsys)

11 维度穷尽搜索: tl(100-1000), cs(16-1024), gate(ON/OFF), wait_gate(ON/OFF), seg_margin(-0.2~+0.3), bins(2-50), segment_size(10-500), scheduler(2种), QPS(10-150), trace/binned, nreq(5k/20k)

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 6 |
| 修改文件 | 5 |

### 关键文件变更

| 文件 | 类型 | 说明 |
|------|------|------|
| `vidur/scheduler/.../uniform_segment_chunked_replica_scheduler.py` | 新增 | 等分 segment 调度器 |
| `vidur/types/replica_scheduler_type.py` | 修改 | 新增 UNIFORM_SEGMENT_CHUNKED |
| `vidur/config/config.py` | 修改 | 新增 UniformSegmentChunkedSchedulerConfig |
| `scripts/real_data_finetune.py` | 新增 | Real data 调参脚本 |
| `scripts/real_data_high_qps.py` | 新增 | 高 QPS segment 调参 |
| `scripts/long_decode_explore.py` | 新增 | 长 decode 探索脚本 |
| `scripts/memory_throughput_experiment.py` | 新增 | Memory/throughput 实验 |

## 相关 Commits

```
4c8f850 docs: real data QPS grid 10-150 完整结果
1a82921 feat: lmsys real data 实验 — 50 bins 突破
132c46d data: memory-constrained stability 验证
f4b7dd4 feat: memory-constrained 实验
090ad7a feat: long decode p512d1000 WIN
3a14229 feat: UniformSegmentChunkedReplicaScheduler
```

### PD 分离实验 (p630d20, decode-only, WCP vs vLLM_PD)

WCP 适配 PD: `pd_mode=True` 跳过 prefill section, 用父类 booking limit 逻辑。

| rate | vLLM_PD | WCP best | tl | vs vLLM |
|------|---------|----------|-----|---------|
| 100 | 0.879s | 0.260s | 300 | **-70.4%** |
| 150 | 0.842s | 0.292s | 300 | **-65.3%** |
| 200 | 0.710s | 0.343s | 300 | **-51.7%** |
| 250 | 0.701s | 0.388s | 300 | **-44.7%** |
| 300 | 1.621s | 0.569s | 400 | **-64.9%** |
| 325 | 2.172s | 0.597s | 400 | **-72.5%** |
| 350 | 3.045s | 0.781s | 600 | **-74.3%** |
| 375 | 3.393s | 0.988s | 400 | **-70.9%** |
| 400 | 3.891s | 1.272s | 500 | **-67.3%** |
| 450 | 4.723s | 1.828s | 500 | **-61.3%** |
| 500 | 5.392s | 2.445s | 500 | **-54.6%** |

**全 11 rates 全胜 (-44.7%~-74.3%)。** PD 下无 Sarathi (chunked prefill 不适用)。

### PD Stability 时间序列 (nreq=10000)

| rate | vLLM mean | vLLM growth | WCP mean | WCP growth | 状态 |
|------|-----------|-------------|----------|------------|------|
| 250 | 0.759s | +16% | **0.389s** | **+1%** | 两者 stable, WCP 更低 |
| **300** | **2.364s** | **+132%** | **0.568s** | **+3%** | **vLLM UNSTABLE, WCP STABLE** |
| 350 | 4.660s | +165% | 0.838s | +25% | vLLM 爆, WCP near-stable |
| 400 | 6.022s | +174% | 1.298s | +22% | 同上 |

图: `outputs/timeseries_pd/timeseries_pd_stability.png`

## 下一步

- [x] Real data QPS=10-150 grid — 14/15 WIN vs Sar256
- [x] PD 分离 WCP 适配 + 调参 — 全 11 rates 全胜 vs vLLM_PD
- [ ] QPS=50 调不出来 (Sar256 sweet spot)
- [ ] 论文写作: 整合 real data 结果到 numerical.tex
- [ ] 可选: arxiv dataset (prefill=2588) 测试
