# WAIT-CP 实验验证与假象排查 - 2026-03-21

## 状态
🚧 进行中（发现公平性问题，需要重新设计对比方案）

## 概要

对 per-request chunk 重写后的 "全胜 -89%" 结果进行系统性验证，发现是不公平对比的假象。WCP 的 batch 总 tokens 是 Sarathi 的 2-4 倍，胜出源于 batch 规模不对等而非算法优势。

## 验证步骤与发现

### 1. 隔离 chunk 效应 vs booking limit 效应

| rate | Sarathi(128) | Sarathi(512) | WCP(c128,tl50) | WCP(c128,tl700) |
|------|-------------|-------------|----------------|-----------------|
| 14 | 15.9s | 0.8s | 1.8s | 2.1s |
| 16 | 26.7s | 1.0s | 4.0s | 6.4s |
| 18 | 35.2s | 1.8s | 10.2s | 29.7s |
| 20 | 42.0s | 6.2s | 17.3s | 37.5s |

**结论:**
- vs Sarathi(128): -89% WIN → 但 Sarathi(128) 是极弱 baseline
- vs Sarathi(512 最优): +128%~+462% LOSE → WCP 输给最优 Sarathi
- chunk 效应 (tl=700 vs Sar128): -87%~-11% → per-request chunk 本身的贡献
- BL 效应 (tl=50 vs tl=700): -15%~-66% → booking limit 有额外贡献，但不够

### 2. 公平对比 WCP(per-req chunk=512) vs Sarathi(512)

| rate | Sarathi(512) | WCP(c512,tl20) | WCP(c512,tl50) | WCP(c512,tl100) |
|------|-------------|----------------|----------------|-----------------|
| 12 | 0.602s | +61% | +83% | +96% |
| 13 | 0.677s | +78% | +113% | +132% |
| 14 | 0.770s | +102% | +145% | +186% |

**全部 LOSE。** 同 chunk_size 下 per-request chunk 让 batch 膨胀 → 更慢。

### 3. WCP(small chunk) vs Sarathi(512)

chunk=64/128/256 per-req, tl=50/100 vs Sarathi(512):
**全部 LOSE (+93%~+648%)**

### 4. WCP vs Sarathi(256)

| config | r=12 | r=14 | r=16 | r=18 | r=20 |
|--------|------|------|------|------|------|
| c128t50 | +60% | +91% | +61% | **-2%** | +1% |
| c256t50 | +68% | +97% | +47% | **-15%** | **-5%** |

**仅在 rate=18-20 + chunk=256 时小幅赢 Sarathi(256)。**

### 5. Batch 总 tokens 不对等分析（根因）

```
Sarathi(chunk=512 total-budget):
  in-system ≈ 11
  batch = 10 decode (10 tokens) + 1 prefill (502 tokens) = 512 tokens

WCP(chunk=128 per-req, tl=50):
  in-system = 50
  K=5, P=2, prefill_running = P×K = 10
  batch = 40 decode (40 tokens) + 10 prefill (10×128 = 1280 tokens) = 1320 tokens

WCP batch 是 Sarathi 的 2.6 倍！
```

| 配置 | in-system | batch tokens | 倍数 vs Sar512 |
|------|-----------|-------------|---------------|
| Sarathi(512) | 11 | **512** | 1.0x |
| WCP(c64, tl50) | 50 | **~1120** | 2.2x |
| WCP(c128, tl50) | 50 | **~1320** | 2.6x |
| WCP(c256, tl50) | 50 | **~1835** | 3.6x |

**所有 "WIN" 都是因为 batch 规模不对等，不是算法优势。**

## 数据存储

所有实验结果已存入 SQLite: `experiments.db`

```sql
SELECT algorithm, chunk_semantics, chunk_size, total_limit,
       arrival_rate, mean_latency, p99_latency
FROM experiments
ORDER BY algorithm, chunk_size, arrival_rate;
```

## 遇到的问题

### 问题 1: chunk_size 语义差异导致不公平对比
**现象**: WCP(per-req chunk=128) 看似大幅赢 Sarathi(chunk=128)
**原因**: WCP 每 batch 处理 ~1320 tokens, Sarathi 只处理 128 tokens, 规模差 10x
**影响**: 之前报告的 -89% WIN 全部无效

### 问题 2: 之前固定 tl 扫描的 -65% WIN 也是假象
**原因**: 当时 _adapt() 代码运行时修改了 tl，污染了固定 tl 实验结果

## 当前理解

1. **Sarathi 的 total-budget chunk 设计控制了 batch 大小在高效区间**
2. **WCP 的 per-request chunk 让 batch 膨胀（每个 running prefill 各得一个 chunk）**
3. **要公平对比必须控制 batch 总 tokens 相同**
4. **booking limit 有独立贡献（-15%~-66%），但不够抵消 batch 膨胀的代价**

## 下一步

- [ ] 公平对比：匹配 batch 总 tokens (Sarathi chunk≈WCP batch)
- [ ] 或者：让 WCP 也有 batch 总 token 预算限制（per-request chunk + total budget cap）
- [ ] 或者：调 tl 让 WCP 的 in-system ≈ Sarathi 的 in-system（≈11）

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-21
