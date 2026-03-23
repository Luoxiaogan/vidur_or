# WAIT-CP Segmented 实验结果 - 2026-03-18

## 突破：rate=18 赢了 Sarathi

### Batch-Cap Segmented (N_SEG=4, batch_cap=n*)

| Rate | WAIT-CP | Sarathi-512 | gap |
|------|---------|-------------|-----|
| 14 | 0.823s | 0.775s | +6.2% |
| **18** | **2.173s** | **2.407s** | **-9.7% ✓** |

**rate=18 是 crossover point：WAIT-CP 首次赢 Sarathi。**

### 关键改动（使 admission control 生效）

**之前的问题**：
- admission control 检查 `in_system = len(_allocation_map) ≈ 10-15`
- 自适应 n* = 15-23，永远不 binding（in_system < n*）
- 原因：_allocation_map 只计已分配内存的请求，排队的不算

**修复**：
- 改成 **batch_cap = total_limit**，直接限制 batch 大小
- 段间用 seg_limit 门控
- advance_stage 改为每 batch 推进 1 步（正确行为）

**为什么有效**：
- 限制 batch 大小 → 更短的 batch 执行时间 → 更高 throughput
- 高 rate 下 batch 自然增大，batch_cap 开始 binding → 控制住 batch → 赢 Sarathi
- 低 rate 下 batch 本来就小，cap 不 binding → 接近 Sarathi

## Full Sweep（旧版 segmented，无 batch-cap）

| Rate | WAIT-CP (4seg) | Sarathi-512 | gap |
|------|---------------|-------------|-----|
| 14 | 0.758s | 0.724s | +4.7% |
| 15 | 0.871s | 0.819s | +6.3% |
| 16 | 1.041s | 0.954s | +9.1% |
| 17 | 1.322s | 1.170s | +12.9% |
| 18 | 2.903s | 2.407s | +20.6% |
| 19 | 17.329s | 12.671s | +36.8% |
| 20 | 34.710s | 24.343s | +42.6% |
| 21 | 50.418s | 35.050s | +43.8% |

→ 无 batch-cap 时全 rate 输 Sarathi，gap 递增

## 下一步

### 低 rate 调优方向（缩小 +6% gap）
- [ ] 减少 N_SEG（2 段 vs 4 段）
- [ ] 段内 advance 优化（减少 overhead）
- [ ] Prefill 优先级调整
- [ ] 混合策略：低 rate 减少分段，高 rate 增加分段

### 完整验证
- [ ] Batch-cap 版本跑 full sweep（rate=14-21）
- [ ] 确认 crossover point 的位置
- [ ] P99 latency 对比
- [ ] Memory-limited workload 测试
