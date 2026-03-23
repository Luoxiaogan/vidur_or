# WAIT-CP 全 Rate 全胜确认 - 2026-03-23

## 状态
✅ 已完成

## 概要

WAIT-CP (tl=21, cs=256, gate=ON) 在全部 7 个 arrival rates (12-24) 上超过 Sarathi(512)，改善幅度 -2.4% 到 -71.9%。rate=16 经 5 组种子验证稳定为 -7.3%。

## 最终实验结果

**配置**: tl=21, cs=256, gate=ON, l₀=512, l₁=20, nreq=5000, A100, Llama-3-8B

| rate | Sarathi(512) | WCP | gap | 验证 |
|------|-------------|-----|-----|------|
| 12 | 0.480s | 0.469s | **-2.4%** | |
| 14 | 0.552s | 0.528s | **-4.3%** | |
| 16 | 0.650s | 0.603s | **-7.3%** | 5 seeds 一致 |
| 18 | 0.784s | 0.699s | **-10.8%** | |
| 20 | 0.987s | 0.824s | **-16.5%** | |
| 22 | 1.853s | 1.025s | **-44.7%** | |
| 24 | 9.865s | 2.775s | **-71.9%** | |

## 三参数设计

| 参数 | 值 | 含义 |
|------|-----|------|
| tl | 21 | booking limit (in-system 总数) |
| cs | 256 | per-request prefill chunk size |
| gate | ON | total_budget = P×(l₀+l₁) = 508 限制 batch tokens |

**派生量**: K=2, P=0.955, pipeline=22, batch_est=508

## 为什么全赢

1. **batch tokens ≈ Sarathi (508 vs 512)**: gate=ON 保证 batch 不膨胀
2. **prefill attention -48%**: 2×256² = 131k vs 502² = 252k
3. **P < 1**: throughput 略低但 per-batch 更快 → 净赢
4. **高 rate 优势放大**: Sarathi 过载时 WCP 仍稳定

## 关键发现

- **gate=ON 是必要条件**: gate=OFF 同配置 +32.8% LOSE
- **tl=21 是唯一甜点**: tl=22 全输, tl=30 全输
- **cs=256 (K=2) 是最优**: K=1 (cs=512) 无 attention 优势, K≥3 overhead 太大
- **rate=16 之前误报 +6.3%**: 旧代码版本的错误数据, 实际 -7.3%

## 数据存储

所有结果存入 `experiments.db` (159 rows)

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-23
