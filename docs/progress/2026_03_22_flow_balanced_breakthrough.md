# WAIT-CP Flow-Balanced 实现突破 - 2026-03-22

## 状态
🚧 进行中（首次真正赢 Sarathi(512)，需多 rate 验证）

## 概要

重新实现 flow-balanced batch 构建，用 (tl, per_req_budget) 双参数控制，total_budget 自动派生保证流量平衡。**首次在公平对比下赢 Sarathi(512): tl=21 prb=256 → -4.3% WIN。**

## 核心设计

```
输入参数:
  tl = 21              # booking limit
  per_req_budget = 256  # 每个 prefill 请求每 batch 的 token 数

派生量:
  K = ceil(512/256) = 2           # prefill 需要 2 个 batch
  P = 21/(2+20) = 0.95            # per-stage throughput
  total_budget = 0.95×(512+20) = 508  # batch 总 token 预算

flow balance:
  每 batch ~1 个 prefill 完成 = ~1 个 decode 完成 = ~1 个新 admit
```

## 关键结果 (rate=14, l₀=512, l₁=20, nreq=5000)

| tl | per_req | K | P | total_budget | mean | vs Sarathi(512) |
|----|---------|---|---|-------------|------|----------------|
| 21 | 512 | 1 | 1.0 | 532 | 0.657s | +19.0% LOSE |
| 42 | 256 | 2 | 1.9 | 1016 | 0.794s | +43.9% LOSE |
| 84 | 128 | 4 | 3.5 | 1862 | 0.794s | +43.8% LOSE |
| **21** | **256** | **2** | **1.0** | **508** | **0.528s** | **-4.3% WIN** |
| 42 | 128 | 4 | 1.8 | 931 | 0.754s | +36.6% LOSE |

**Sarathi(512) baseline: 0.552s**

## 为什么 tl=21 prb=256 赢了

```
WCP:     batch ≈ 508 tokens = 2 prefill × 256 + 20 decode
Sarathi: batch ≈ 512 tokens = 1 prefill × 502 + 10 decode

batch 大小几乎相同！但:
  attention_prefill 二次方成本:
    WCP:     2 × 256² = 131,072
    Sarathi: 1 × 502² = 252,004
    WCP 节省 48% 的 prefill attention 开销!

  代价:
    WCP 多 1 个 request 在 batch (12 vs 11) → 轻微 CPU overhead
    但 attention 节省 >> CPU overhead → 净赢
```

## 为什么其他配置输了

- **tl=21 prb=512 (K=1)**: total_budget=532 ≈ Sarathi, 但只有 1 个 prefill (和 Sarathi 一样) → 无优势 + 代码 overhead → +19%
- **tl=42 prb=256 (P=1.9)**: total_budget=1016 → batch 太大 → 更慢
- **tl=84 prb=128 (P=3.5)**: total_budget=1862 → batch 爆炸 → 更慢

## 甜点条件

```
total_budget ≈ Sarathi's 512 (batch 大小匹配)
K > 1 (才能有多个 prefill 并行 → 二次方优势)
P ≈ 1 (吞吐量匹配)

→ tl ≈ K + l₁ = pipeline_depth (刚好 1 per-stage)
→ per_req_budget ≈ l₀ / K (K 越大, per_req 越小, 二次方优势越大)
→ 但 K 太大 → 太多 running prefills → batch_size 增大 → CPU overhead 反超
```

## 代码改动

`general_nested_chunked_replica_scheduler.py` 完全重写:
- 参数: tl + per_req_budget (chunk_size)
- 自动派生: K, P, total_budget
- Step 1: decode 全处理
- Step 2: running prefill 各 per_req_budget, 受 total_budget 限
- Step 3: new admit 各 per_req_budget, 受 tl + total_budget 双重限

## 下一步

- [ ] 多 rate 验证 (12, 16, 18, 20, 22, 24)
- [ ] 微调 (tl, per_req_budget) 找最优甜点
- [ ] 多 seed 验证统计显著性

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-22
