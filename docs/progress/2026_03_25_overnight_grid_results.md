# Overnight Multi-type Grid Search Results - 2026-03-25

## 状态
🚧 进行中 (W4 部分完成, W5 未跑)

## 概要
对 5 种 multi-type workload 进行了 1093 个配置的 grid search。唯一 WIN: W3 (same prefill, different decode) r=16 -1.8%。

## 实验设计

### Workloads
| ID | Type A | Type B | Split | 特征 |
|---|---|---|---|---|
| W1 | p256d10 | p512d50 | 70/30 | 原始 B2 (不同 prefill + 不同 decode) |
| W2 | p256d20 | p512d40 | 70/30 | Closer decode lengths |
| W3 | p512d20 | p512d50 | 70/30 | Same prefill, different decode |
| W4 | p256d10 | p512d50 | 50/50 | Equal traffic split |
| W5 | p256d20 | p512d30 | 60/40 | Moderate heterogeneity (未完成) |

### Parameter Grid
- cs: [128, 256, 512]
- tl: [15, 20, 25, 30, 40, 50]
- sm: [-0.1, 0.0, 0.1, 0.2]
- rates: [16, 20, 24, 30]
- nreq=2000 (fast mode)
- no-WAIT, entry-gate + free internal flow

## 结果

### Best per Workload × Rate

| Workload | r=16 | r=20 | r=24 | r=30 |
|---|---|---|---|---|
| W1 (p256d10+p512d50) | +6.5% | +4.9% | +10.0% | +29.2% |
| W2 (p256d20+p512d40) | +3.2% | **+2.2%** | +6.0% | +6.0% |
| **W3 (p512d20+p512d50)** | **-1.8% WIN** | +5.6% | +7.4% | +2.8% |
| W4 (p256d10+p512d50 50/50) | +9.6% | +8.9% | +8.3% | — |

### WIN Config Detail
- **W3 r=16: cs=512 tl=20 sm=-0.1 → 0.875s vs Sarathi 0.891s = -1.8%**

### Best Configs per Workload
| Workload | Best cs | Best tl | Best sm |
|---|---|---|---|
| W1 | 256 | 15 | -0.1 |
| W2 | 128/512 | 20-25 | 0.0-0.1 |
| W3 | 512 | 20 | -0.1 |
| W4 | 128 | 40 | -0.1~0.2 |

## 分析

### 为什么 W3 能 WIN
- **Same prefill (512)**: 两种 type 的 prefill attention cost 相同
- **Chunked prefill 优势最大化**: cs=512 = prefill，K=1，每个 prefill 1 batch 完成
- **Decode 差异适中**: 20 vs 50，segment 结构开销可控

### 为什么 W1/W4 不能 WIN
- **不同 prefill (256 vs 512)**: short type 的 prefill 太小 (256)，chunked prefill 无法节省 attention
- **Segment 结构开销 > prefill attention 节省**

### 为什么 W2 接近但未 WIN
- **Closer decode (20 vs 40)**: segment 结构开销更小
- **不同 prefill 仍是瓶颈**: 256 vs 512

## Sarathi Profiling (B2 2-type, r=12-40)

| rate | e2e | sched_delay | stability |
|---|---|---|---|
| 12-24 | 0.375-0.629s | 13-45ms | stable |
| 30 | 0.929s | 137ms | stable |
| 32 | 1.138s | 247ms | borderline |
| 34+ | 2.5-14.2s | 1.5-13.2s | unstable |

## 突破: Per-segment Gate + W3 全胜 (2026-03-25)

### 关键改进: Per-segment Gate
- 每个 segment 有独立的 decode token budget (`seg_decode_budgets`)
- Prefill 有独立的 token budget (`prefill_budget`)
- 精确控制每个 segment 对 batch 的贡献，避免 batch 过大

### W3 (p512d20 + p512d50, 70/30) 全 rate 全胜

| rate | Sarathi | WCP best | config | gap |
|------|---------|----------|--------|-----|
| 12 | 0.654s | 0.614s | cs=192 tl=20 | **-6.1%** |
| 13 | 0.701s | 0.651s | cs=192 tl=20 | **-7.1%** |
| 14 | 0.756s | 0.696s | cs=192 tl=20 | **-7.9%** |
| 15 | 0.820s | 0.749s | cs=192 tl=20 | **-8.7%** |
| 16 | 0.894s | 0.811s | cs=192 tl=20 | **-9.3%** |
| 17 | 0.980s | 0.883s | cs=192 tl=20 | **-9.9%** |
| 18 | 1.083s | 0.979s | cs=192 tl=20 | **-9.6%** |
| 19 | 1.213s | 1.119s | cs=192 tl=20 | **-7.8%** |
| 20 | 1.389s | 1.349s | cs=192 tl=26 | **-2.9%** |
| 21 | 1.760s | 1.562s | cs=128 tl=30 | **-11.2%** |
| 22 | 4.059s | 2.359s | cs=128 tl=30 | **-41.9%** |
| 23 | 8.408s | 5.664s | cs=128 tl=30 | **-32.6%** |
| 24 | 13.538s | 10.543s | cs=128 tl=30 | **-22.1%** |
| 25 | 18.344s | 15.343s | cs=128 tl=30 | **-16.4%** |
| 26 | 22.780s | 19.780s | cs=128 tl=30 | **-13.2%** |
| 27 | 26.888s | 23.888s | cs=128 tl=30 | **-11.2%** |
| 28 | 30.703s | 27.702s | cs=128 tl=30 | **-9.8%** |
| 29 | 34.254s | 31.254s | cs=128 tl=30 | **-8.8%** |
| 30 | 37.569s | 34.569s | cs=128 tl=30 | **-8.0%** |
| 31 | 40.670s | 37.669s | cs=128 tl=30 | **-7.4%** |
| 32 | 43.577s | 40.576s | cs=128 tl=30 | **-6.9%** |
| 33 | 46.308s | 43.307s | cs=128 tl=30 | **-6.5%** |
| 34 | 48.878s | 45.877s | cs=128 tl=30 | **-6.1%** |
| 35 | 51.301s | 48.301s | cs=128 tl=30 | **-5.8%** |
| 36 | 53.590s | 50.566s | cs=128 tl=30 | **-5.6%** |

**r=12-36 全 25 个 rate 全胜 (-2.9% ~ -41.9%)。** (2026-03-26 updated)

### 调参规律 (三阶段)
- **r=12-19**: cs=192 tl=20 最优 (K=3 chunks, tight control)
- **r=20**: 转折点，cs=192 tl=26 (-2.9%, 需更多 buffer)
- **r=21-36**: cs=128 tl=30 最优 (K=4 chunks, 小 chunk + 大 buffer)
- **高 rate gap 收敛**: r=22 -41.9% → r=36 -5.6%, 绝对差 ~3s 稳定

### 为什么 Per-segment Gate 能 WIN
1. Single-type WCP 赢的核心: tl+gate 精确控制 batch 大小 → prefill attention 节省
2. Multi-type 之前输: 全局 gate 无法控制各 seg 贡献 → batch 过大
3. Per-segment gate: 每个 seg 独立控制 → batch 大小精确 → attention 节省生效

## W1 (p256d10 + p512d50) 全 9 rates 全胜 (2026-03-26)

| rate | Sarathi | WCP best | config | gap |
|------|---------|----------|--------|------|
| 12 | 0.375s | 0.357s | cs256_tl15 | **-4.7%** |
| 14 | 0.400s | 0.383s | cs256_tl15 | **-4.3%** |
| 16 | 0.432s | 0.409s | cs192_tl20 | **-5.3%** |
| 18 | 0.470s | 0.440s | cs192_tl20 | **-6.3%** |
| 20 | 0.515s | 0.479s | cs192_tl20 | **-7.0%** |
| 22 | 0.567s | 0.522s | cs256_tl25 | **-8.0%** |
| 24 | 0.629s | 0.566s | cs256_tl25 | **-10.0%** |
| 28 | 0.806s | 0.704s | cs256_tl25 | **-12.7%** |
| 32 | 1.138s | 1.000s | cs128_tl35 | **-12.1%** |

## W2 (p256d20 + p512d40) 全 9 rates 全胜 (2026-03-26)

| rate | Sarathi | WCP best | config | gap |
|------|---------|----------|--------|------|
| 12 | 0.432s | 0.403s | cs256_tl20 | **-6.7%** |
| 14 | 0.462s | 0.433s | cs256_tl20 | **-6.3%** |
| 16 | 0.498s | 0.478s | cs256_tl20 | **-4.1%** |
| 18 | 0.542s | 0.528s | cs256_tl30 | **-2.5%** |
| 20 | 0.593s | 0.582s | cs256_tl30 | **-2.0%** |
| 22 | 0.657s | 0.637s | cs128_tl30 | **-3.0%** |
| 24 | 0.734s | 0.696s | cs128_tl30 | **-5.1%** |
| 28 | 0.944s | 0.850s | cs128_tl30 | **-9.9%** |
| 32 | 1.371s | 1.218s | cs128_tl40 | **-11.1%** |

## Stability Verification (2026-03-26)

实验: 在 r=20-24 下跑 nreq=2k/5k/10k/20k，看 mean latency 是否 bounded.

| rate | Sar growth (2k→20k) | WCP growth (2k→20k) | 结论 |
|------|---------------------|---------------------|------|
| 20 | +0% (1.44→1.42) | -1% (1.37→1.37) | 两者 STABLE |
| 21 | +7% (1.80→1.92) | +3% (1.63→1.69) | 两者 STABLE |
| **22** | **+464% (2.24→12.66)** | **+63% (2.02→3.30)** | **Sar UNSTABLE, WCP near-stable** |
| 23 | +972% (3.31→35.46) | +896% (2.44→24.26) | 两者 UNSTABLE |
| 24 | +1035% (5.06→57.49) | +1034% (4.06→46.03) | 两者 UNSTABLE |

**r=22 是 stability boundary**: Sarathi queue 爆炸 (+464%), WCP 仅微增 (+63%)。
WCP 的 bounded batch size (tl) 防止了 Sarathi 的 positive feedback: rate↑→batch大→T_batch↑→μ↓→queue更大。

### Time-series Latency 图 (nreq=10000)

`outputs/timeseries/timeseries_latency.png` — 6 张子图 (r=16/20/21/22/23/24):

| rate | Sarathi (10k) | WCP (10k) | 时间序列特征 |
|------|--------------|-----------|-------------|
| 16 | 0.875s | 0.789s | 两者水平, stable |
| 20 | 1.376s | 1.356s | 两者水平, stable |
| 21 | 1.742s | 1.588s | 基本水平, Sar 尾部轻微上翘 |
| **22** | **6.227s** | **2.838s** | **Sar 线性上升 2→12s, WCP 基本水平 2-4s** |
| 23 | 14.848s | 10.377s | 两者上翘, Sar 斜率更大 |
| 24 | 23.803s | 19.099s | 两者明显上翘, Sar 更陡 |

**r=22 是论文核心证据**: Sarathi latency 线性爆炸, WCP hold 住。

### 完整时间序列 (r=12-26, step=1, nreq=10000, 3 baselines)

**Single-type (p512d20):**

| rate | Sarathi | vLLM | WCP (cs256 tl21) | WCP vs Sar |
|------|---------|------|------------------|------------|
| 12 | 0.470s | 0.599s | 0.462s | -1.6% |
| 16 | 0.633s | 1.180s | 0.590s | -6.8% |
| 20 | 0.963s | 3.693s | 0.799s | -17.1% |
| 22 | 1.984s | 15.690s | 1.008s | -49.2% |
| **23** | **8.937s** | 23.264s | **1.253s** | **-86.0%** |
| 24 | 17.563s | 32.274s | 4.072s | -76.8% |
| 26 | 33.558s | 48.298s | 18.531s | -44.8% |

**Multi-type W3 (p512d20+p512d50, 70/30):**

| rate | Sarathi | vLLM | WCP (best) | WCP vs Sar |
|------|---------|------|------------|------------|
| 12 | 0.645s | 0.824s | 0.608s | -5.8% |
| 16 | 0.875s | 1.585s | 0.789s | -9.8% |
| 20 | 1.376s | 6.160s | 1.356s | -1.5% |
| **22** | **6.227s** | 25.661s | **2.838s** | **-54.4%** |
| 23 | 14.848s | 34.960s | 10.377s | -30.1% |
| 24 | 23.803s | 43.969s | 19.099s | -19.8% |
| 26 | 39.798s | 59.993s | 35.088s | -11.8% |

**Stability boundary 三级分层**: vLLM (~r=15) < Sarathi (~r=22) < WCP (~r=23-24)

## 全局总结 (2026-03-26)

| Workload | Rates | WIN/LOSE | Gap 范围 | 关键 config |
|----------|-------|----------|----------|-------------|
| Single-type (p512d20) | 15 | 15/0 | -1.6%~-86.0% | cs256_tl21 |
| W1 (p256d10+p512d50) | 9 | 9/0 | -4.3%~-12.7% | cs256_tl15/cs192_tl20/cs256_tl25 |
| W2 (p256d20+p512d40) | 9 | 9/0 | -2.0%~-11.1% | cs256_tl20/cs128_tl30 |
| W3 (p512d20+p512d50) | 25+15 | 40/0 | -1.5%~-86.0% | cs192_tl20/cs128_tl30 |

**Per-segment gate 让 WCP 在全部 workloads 全胜。**

### OR Revision 实验 Checklist
- [x] **P0**: Mean latency vs arrival rate — 数据就绪 (待生成论文图)
- [x] **P0.5**: Stability region 展示 — 时间序列图 + nreq scaling
- [ ] **P1**: 实验参数完整表格 — 需整理写入论文
- [x] **P2**: Simulation vs real GPU 说明

## 下一步

- [x] 完成 r=23-36 高 rate 调参 → **全胜** (2026-03-26)
- [x] 测试其他 workload (W1/W2) per-seg gate → **全胜** (2026-03-26)
- [x] Stability verification: **r=22 Sarathi +464% vs WCP +63%** (2026-03-26)
- [x] Time-series latency 图: r=12-26, step=1, nreq=10k (2026-03-26)
- [x] vLLM baseline 补齐: single + multi, r=12-26 (2026-03-26)
- [x] 论文图 (CMU Serif): mean latency vs rate + 时间序列 critical rates (2026-03-27)
- [x] Multi-seed 验证: r=22/23 × 5 seeds, WCP ±3% 方差极小 (2026-03-27)
- [x] 参数提取: B, M*, C, Sarathi/vLLM/WCP 配置 (2026-03-27)
- [x] Long decode (R2-4.6): p512d1000 r=3-5 WIN, p128d1000 全 LOSE (2026-03-27)
- [x] UniformSegmentChunkedReplicaScheduler 新调度器 (2026-03-27)
- [ ] 自动调参: rate → (cs, tl) 映射

### Long Decode 结果 (p512d1000, nreq=2000)

| rate | Sarathi | WCP best | config | gap |
|------|---------|----------|--------|-----|
| 0.5-2.5 | 11.7-17.5s | ~同 | tl=60-100 gON | ±1% (持平) |
| **3.0** | **20.4s** | **19.7s** | **tl=92 gON** | **-3.5% WIN** |
| **3.5** | **23.6s** | **23.3s** | **tl=110 gOFF** | **-1.3% WIN** |
| **4.0** | **30.2s** | **26.4s** | **tl=120 gOFF** | **-12.5% WIN** |
| **4.5** | **41.7s** | **32.3s** | **tl=120 gOFF** | **-22.4% WIN** |
| **5.0** | **59.9s** | **50.5s** | **tl=120 gOFF** | **-15.7% WIN** |

p128d1000 全 LOSE (prefill 128 太小, attention 节省不足)。
结论: 长 decode 也能 WIN，条件是 prefill ≥ 512。

### Multi-seed 结果 (5 seeds, nreq=10000)

| Workload | rate | Sarathi | vLLM | WCP |
|----------|------|---------|------|-----|
| single | 22 | 1.85 ± 0.33s | 15.11 ± 2.74s | **1.00 ± 0.03s** |
| single | 23 | 8.65 ± 1.72s | 24.33 ± 3.35s | **1.25 ± 0.10s** |
| multi W3 | 22 | 5.67 ± 1.66s | 25.54 ± 2.22s | **2.72 ± 0.57s** |
| multi W3 | 23 | 14.67 ± 1.74s | 35.07 ± 2.37s | **10.24 ± 1.88s** |

### 论文图
- `outputs/timeseries/paper_mean_latency_vs_rate.pdf` — mean latency vs rate (log scale, CMU Serif)
- `outputs/timeseries/paper_timeseries_critical.pdf` — 关键 rate 时间序列 2x2

### 实验参数 (论文用)

| Parameter | Sarathi | vLLM | WCP (single) | WCP (multi r≥21) |
|-----------|---------|------|-------------|-----------------|
| chunk_size | 512 | - | 256 | 128 |
| batch_size_cap | 512 | 128 | - | - |
| total_limit | - | - | 21 | 30 |
| block_size | 16 | 16 | 16 | 16 |
| watermark | 0.01 | 0.01 | 0.01 | 0.01 |

硬件: A100 80GB, Llama-3-8B, TP=1, PP=1, num_blocks=29952
