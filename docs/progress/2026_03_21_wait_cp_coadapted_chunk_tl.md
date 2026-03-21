# WAIT-CP chunk_size + total_limit 协同调参 - 2026-03-21

## 状态
🚧 进行中（发现核心洞察：chunk 和 tl 必须协同，正在验证）

## 概要

系统性扫描发现：小 chunk 下 booking limit 被 chunk 预算架空（in-system 锁死在 ~8），任何 tl 调整都无效。用户提出关键洞察：**chunk_size 应与 total_limit 协同调整**，使 booking limit 成为真正的 admission 控制器。

## 完成内容

### 1. 干净的 rate × tl 扫描 (chunk=256, _adapt 禁用)

| rate | Sarathi | tl=5 | tl=8 | tl=10 | tl=700 | 最优 |
|------|---------|------|------|-------|--------|------|
| 12 | 0.629s | +13662% | +1249% | +39% | 0% | tl=700 |
| 14 | 0.894s | +11610% | +2879% | +134% | 0% | tl=700 |
| 16 | 2.698s | +4285% | +1392% | +366% | 0% | tl=700 |
| 18 | 12.717s | +914% | +300% | +82% | 0% | tl=700 |
| 20 | 21.189s | +548% | +180% | +49% | 0% | tl=700 |

**结论：chunk=256 下任何 binding 的 tl 都更差。之前 -65% 的 WIN 是被旧自适应代码污染的假象。**

### 2. 自适应 total_limit 尝试（4 个版本全部失败）

| 版本 | 策略 | 结果 |
|------|------|------|
| v1 n*(λ) 公式 | 基于到达率设 tl | rate=14 误收紧 +1537% |
| v2 仅过载收紧 | 默认 700, 过载时用 n* | 全 TIE (n* 太高不 binding) |
| v3 即时跳转 | 过载时直接跳到 n* | 全 TIE (同上) |
| v4 激进减半 | 过载时 tl=in_sys/2 | rate=14-16 +22327% (正反馈崩溃) |

**根因：降 tl 既减 batch 时间（收益）又降 throughput（成本），成本在中低 rate 下总是 > 收益。**

### 3. 核心洞察：chunk 预算架空 booking limit

```
chunk=256, l₀=630 → K=3
每 batch 只能 admit 1 个新 prefill（chunk 预算满）
→ in-system ≈ 1 + l₁/K = 8（结构性上限，与 rate 无关）
→ 任何 tl ≥ 8 不 binding → = Sarathi
→ 任何 tl < 8 降 throughput → 更差
```

### 4. 突破方向：chunk + tl 协同

用户洞察：**per-stage limit = tl/l₁，chunk 应允许每 batch admit 这么多 prefill**

```
chunk_size ≈ (tl/l₁) × l₀ + tl

tl=50:  chunk=1940  (~3 prefills/batch)
tl=100: chunk=3250  (~5 prefills/batch)
tl=200: chunk=6500  (~10 prefills/batch)

大 chunk 下:
  Sarathi: in-system 膨胀到内存上限 (~460) → batch 巨大且慢
  WCP:     in-system 控制在 tl → batch 更小更快 → booking limit 真正发挥作用
```

**正在测试中。**

## 遇到的问题与解决

### 问题 1: 之前 -65% WIN 是假象
**现象**: rate=20 chunk=256 tl=5 曾显示 7.385s vs Sarathi 21.189s
**原因**: 运行时自适应代码修改了 tl 值，污染了固定 tl 实验
**解决**: 禁用 _adapt() (return)，重新跑干净实验 → 结果为 +548%

### 问题 2: 自适应正反馈崩溃
**现象**: rate=14 下激进减半导致 +22327%
**原因**: 降 tl → 降 throughput → 队列增长 → 检测到过载 → 继续降 tl → 崩溃
**解决**: 未完全解决，需要更好的过载检测信号（如 batch_time 追踪）

## 下一步计划

- [ ] 验证 chunk+tl 协同调参（大 chunk + booking limit）
- [ ] 测试 rate={14..20} × co-adapted (tl, chunk) 组合
- [ ] 如果协同调参有效，设计自适应 chunk+tl 联合调整逻辑

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-21
