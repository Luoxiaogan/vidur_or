# WAIT-CP 参数语义与 Batch 计算量分析

## 可调参数

| 参数 | 符号 | 含义 | 示例 |
|------|------|------|------|
| `total_limit` | tl | booking limit，控制系统内总请求数 | 21 |
| `chunk_size` | cs | 每个 prefill 请求每 batch 处理的 new tokens 数 | 256 |

## 派生量

| 量 | 公式 | 含义 | 示例 (tl=21, cs=256, l₀=512, l₁=20) |
|----|------|------|------|
| K | ceil(l₀/cs) | 每个 prefill 需要多少个 batch 完成 | ceil(512/256) = 2 |
| pipeline_depth | K + l₁ | 一个请求从 admit 到 complete 经过的 batch 数 | 2 + 20 = 22 |
| P | tl / pipeline_depth | 每 batch 完成 prefill 的请求数 (per-stage throughput) | 21/22 = 0.955 |
| running_prefill | P × K | 稳态下正在做 prefill 的请求数 | 0.955 × 2 ≈ 2 |
| running_decode | P × l₁ | 稳态下正在做 decode 的请求数 | 0.955 × 20 ≈ 19 |
| in_system | tl | 系统内总请求数 (= running_prefill + running_decode) | 21 |
| per_stage | P | 每个 stage 的平均请求数 | ≈ 0.955 |

## Batch 组成

每个 batch 包含 in_system 个请求，全部处理：

```
Batch 组成 (tl=21, cs=256):
  decode: 19 个请求 × 1 new token = 19 new tokens
  prefill: 2 个请求 × 256 new tokens = 512 new tokens
  total_num_tokens (new) = 531
  total requests = 21
```

## Batch 实际计算量分解

### 1. Prefill Attention (O(n²) per request)

每个 prefill 请求的 attention 成本与 chunk_size² 成正比：

```
WCP (tl=21, cs=256):
  2 requests × 256² = 131,072

Sarathi (1 prefill × 502 tokens):
  1 request × 502² = 252,004

WCP 节省: (252,004 - 131,072) / 252,004 = 48%
```

这是 WCP 赢的主要来源。

### 2. Decode Attention (linear per request × kv_cache_size)

每个 decode 请求需要扫描整个 KV cache：

```
l₀=512, decode stage s: kv_cache = 512 + s tokens

WCP (19 decode, stages 1-20):
  Σ(512+s) for s=1..19 ≈ 19 × 522 = 9,918

Sarathi (10 decode, stages 1-20 均匀采样):
  Σ ≈ 10 × 522 = 5,220

WCP 多了: 4,698 (多 9 个 decode 请求)
```

这是 WCP 的额外开销。

### 3. MLP / Norm / 其他线性计算

与 total_num_tokens (new tokens) 成正比：

```
WCP:    531 tokens
Sarathi: 512 tokens
差异: +3.7% (几乎一样)
```

### 4. CPU Overhead (per-request 固定开销)

scheduling, sampling, input preparation 等，与 batch 中 request 数成正比：

```
WCP:    21 requests
Sarathi: 11 requests
差异: +91% (接近 2 倍!)
```

### 5. 总计算量对比

| 组件 | WCP (tl=21) | Sarathi | WCP 优势 |
|------|------------|---------|---------|
| prefill attention | 131,072 | 252,004 | **-48%** ← 主要优势 |
| decode attention | 9,918 | 5,220 | +90% ← 劣势 |
| MLP/norm | ~531 | ~512 | +4% |
| CPU overhead | 21 req | 11 req | +91% |

**净效果**: prefill attention 大幅节省 > decode attention + CPU 开销增加 → 小幅净赢 (-4%)

## tl 调大为什么更差

```
tl=21 → 22 → 25 → 30:
  decode requests: 19 → 20 → 23 → 27 (线性增长)
  prefill requests: 2 → 2 → 2.3 → 2.7 (几乎不变, 因为 K=2)

  prefill attention 节省: 固定 ~120k (因为 prefill requests ≈ 2, 不变)
  decode attention 增加: +522 per extra decode request
  CPU overhead 增加: 线性增长
  MLP/norm: 线性增长

  tl=21→30 新增 9 decode:
    + 9 × 522 = 4,698 decode attention
    + 9 requests CPU overhead
    + ~60 new tokens MLP
    总增加 >> 固定的 120k 节省
```

**prefill attention 节省是固定的 (由 K 和 cs 决定)，但 decode/CPU 开销随 tl 线性增长。** tl=21 刚好在收支平衡点，多一点就亏。

## 为什么 tl=21 是甜点

```
P = tl/(K+l₁) < 1 ← 关键条件

P < 1 意味着:
  in_system = tl < pipeline_depth = 22
  batch 中 decode 数 < 20 (Sarathi 的 decode 数 ≈ 20 when P=1)
  batch new tokens < Sarathi 的 512
  → 整体 batch 执行时间 < Sarathi
  → throughput ≥ Sarathi
  → latency ≤ Sarathi

P ≥ 1 (tl ≥ 22) 意味着:
  in_system ≥ pipeline_depth
  batch 更大 → 执行时间更长
  → throughput < Sarathi
  → 高 rate 下 queue 积压 → latency 爆炸
```

## Sarathi (作为 special case) 的 Batch 分析

```
Sarathi(chunk=512), l₀=512:
  K=1 (一个 batch 完成 prefill)
  in_system ≈ 1 + 20 = 21 (1 prefill + 20 decode)
  batch: 10 decode + 1 prefill(502 tokens) = 512 new tokens, 11 requests

注意: Sarathi 只有 ~10 decode (不是 20)!
因为 Sarathi 的 total-budget(512) 限制了每 batch 的 new tokens,
导致实际 throughput P ≈ 0.5 (每 2 batch 完成 1 个 prefill),
所以 decode in-system ≈ 0.5 × 20 = 10, 不是 20。
total in-system ≈ 11, 不是 21。
```

**关键发现: Sarathi 的 in-system ≈ 11 (不是 21!)，因为 total-budget chunk 限制了 throughput。WCP(tl=21) 的 in-system = 21 (比 Sarathi 多 10 个 decode)，但 batch 执行更快 (attention 节省)。**

## 实验验证的最佳配置

| 配置 | 结果 (vs Sarathi 512) |
|------|------|
| tl=21 cs=256 | r=12:-2.4%, r=14:-4.3%, r=16:+6.3%, r=18:-10.8%, r=20:-16.5%, r=22:-44.7% |
| tl=22 cs=256 | 全 LOSE (+14% ~ +1265%) |
| tl=25 cs=256 | 全 LOSE (+20% ~ +1097%) |
| tl=30 cs=256 | 全 LOSE (+21% ~ +995%) |
| tl=30 cs=47 | +31% LOSE (attention -90% 但 30 req overhead 太大) |

---
**日期**: 2026-03-23
