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

**r=12-22 全 11 个 rate 全胜 (-2.9% ~ -41.9%)。**

### 调参规律
- **r=12-19**: cs=192 tl=20 最优 (K=3 chunks)
- **r=20**: 转折点，需 tl=26
- **r=21-22**: cs=128 tl=30 最优 (K=4 chunks, 更小 chunk 更好)
- **高 rate → 更小 cs + 更大 tl**

### 为什么 Per-segment Gate 能 WIN
1. Single-type WCP 赢的核心: tl+gate 精确控制 batch 大小 → prefill attention 节省
2. Multi-type 之前输: 全局 gate 无法控制各 seg 贡献 → batch 过大
3. Per-segment gate: 每个 seg 独立控制 → batch 大小精确 → attention 节省生效

## 下一步

- [ ] 完成 r=23-36 高 rate 调参 (running)
- [ ] Multi-seed 验证关键 rate 点
- [ ] 测试其他 workload (W1/W2) 是否也能用 per-seg gate WIN
- [ ] 自动调参: rate → (cs, tl) 映射
