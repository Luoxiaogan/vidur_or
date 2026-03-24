# Multi-type Nested WAIT: seg_margin + 动态 per-stage limit + WAIT 机制 - 2026-03-24

## 状态
🚧 进行中

## 概要
为 multi-type workload 实现了三个关键改进：(1) `seg_margin` 参数控制 segment 间分配比例，对齐 paper 的 $n_{k+1}/n_k > p_k$ 约束；(2) 动态 per-stage limit 分配 + rotation 避免死锁；(3) WAIT 机制——segment 需满足 "总数达标" 或 "入口积累够" 才进 batch。

## 完成内容

### 1. seg_margin 参数 (Paper 约束对齐)

**问题发现**: 代码原有的加权分配公式 `weight = count × arrival_sum` 导致 $n_{k+1}/n_k = p_k$（恰好在 paper 约束边界上），paper 要求严格大于 $p_k$ 才有 O(1) latency 保证。

**解决方案**: 新增 `seg_margin` 参数，控制 $n_{k+1}/n_k = p_k + \text{seg\_margin}$。
- 从 `total_limit` 反推各 segment 的 $n_k$ (per-stage limit)
- `seg_margin=0.0` 退化为原行为（边界）
- `seg_margin > 0` 给后续 segment 更多 per-stage budget

**代码**: `vidur/config/config.py` — `GeneralNestedBookingLimitSchedulerConfig.seg_margin`

### 2. 动态 per-stage limit + Rotation

**问题发现**: 当 `seg_total_limit < num_stages` 时（如 seg_tl=9, 10 stages），整数分配导致部分 stage 的 per_stage_limit=0。原代码在 init 时固定分配，limit=0 的 stage 永远不推进请求。

**解决方案**:
- per-stage limit 每 batch **动态计算**，不在 init 时固定
- `budget = seg_total_limit`, `base = budget // num_stages`, `remainder = budget % num_stages`
- **Rotation**: `offset = batch_count % num_stages`，轮换哪些 stage 拿 `base+1`
- 保证任意两个 stage 的 per-batch limit 差 ≤ 1

**代码**: `general_nested_booking_limit_replica_scheduler.py` 和 `general_nested_chunked_replica_scheduler.py` 的 `_get_next_batch`

### 3. WAIT 机制

**问题**: 原代码没有 paper 中 "等到 $n_{j0} \geq n_j$ 才发 batch" 的 WAIT 语义，pipeline 一直在流。

**实现**: 每个 segment 需满足以下**任一**条件才纳入 batch：
1. **seg 总数 ≥ seg_total_limit**: segment 内请求总数已达上限
2. **入口 stage 请求数 ≥ max_per_stage**: 入口积累够了（类似 paper 的 $n_{j0} \geq n_j$）

都不满足则 WAIT（该 segment 不进 batch）。

**代码**: 两个 scheduler 的 `_get_next_batch` 中的 `seg_full` / `entry_ready` 检查

### 4. metrics_store 修复

- `store_plots=False` 时跳过所有画图函数（`_store_batch_metrics` 等），只写 CSV
- 避免缺少 `kaleido` 时崩溃

### 5. Sweep 脚本

- `scripts/sweep_seg_margin.py`: sweep seg_margin × tl × rate
- 用 `tempfile.mkdtemp` 隔离每次 run 的输出，避免并发写冲突
- 带 stderr 诊断

## 代码变更

| 类型 | 数量 |
|------|------|
| 修改文件 | 4 |
| 新增文件 | 1 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `vidur/config/config.py` | 修改 | 新增 `seg_margin` 配置参数 |
| `vidur/scheduler/replica_scheduler/general_nested_booking_limit_replica_scheduler.py` | 修改 | seg_margin 分配公式 + 动态 per-stage + WAIT 机制 |
| `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py` | 修改 | 动态 per-stage + WAIT 机制 (decode section) |
| `vidur/metrics/metrics_store.py` | 修改 | store_plots=False 跳过画图 |
| `scripts/sweep_seg_margin.py` | 新增 | seg_margin sweep 实验脚本 |

## 初步实验结果 (B2 2-type, r=12)

| tl | seg_margin | latency | vs Sarathi(0.375s) |
|---|---|---|---|
| 30 | 0.0 | 0.918s | +145% |
| 30 | 0.3 | 0.698s | +86% (tl=30 最优) |
| 50 | 0.0 | 0.550s | +47% |
| 50 | 0.1 | 0.490s | +31% |

**观察**: tl 越大越好，seg_margin=0.3 附近最优。tl=30/50 全面 LOSE，需要更大 tl。

## 遇到的问题与解决

### 问题 1: per_stage_limit=0 导致死锁
**现象**: seg_total_limit < num_stages 时部分 stage limit=0，请求永远卡死
**原因**: init 时固定分配，不会动态轮换
**解决**: 动态计算 + rotation

### 问题 2: sweep 脚本间歇性失败
**现象**: CSV 文件找不到，只有 config.json
**原因**: 多个残留 subprocess 并发写 `simulator_output/` 目录
**解决**: 每次 run 用独立 tmpdir + 递归 glob

### 问题 3: store_plots=False 不完全
**现象**: `_store_batch_metrics` 等仍调 `plot_cdf` 导致崩溃
**解决**: 在 `plot()` 中整体跳过非 request_metrics 的 store 函数

## Single-type 兼容性

改动对 single-type 完全兼容：
- `seg_margin=0.0` 默认值，single-type 下无效（只有 1 个 segment）
- WAIT 条件: tl=21 时 max_per_stage=1，stage 0 有 ≥1 请求就触发，基本不 WAIT
- 之前的最佳结果 (tl=21, cs=256, gate=ON) 不受影响

## 完整实验结果

### Sarathi B2 Profiling (r=12-40)

| rate | ALL | short (p256d10) | sched | long (p512d50) | sched |
|------|-----|-----------------|-------|----------------|-------|
| 12 | 0.375s | 0.185s | 13ms | 0.823s | 13ms |
| 20 | 0.515s | 0.260s | 26ms | 1.114s | 25ms |
| 30 | 0.929s | 0.511s | 137ms | 1.914s | 143ms |
| 34 | 2.502s | 1.977s | 1.52s | 3.736s | 1.53s |
| 38 | 10.44s | 9.876s | 9.42s | 11.76s | 9.56s |

Sarathi stability region 边界在 r≈32-34。

### WCP Multi-type 实验结论

**测试了 200+ 配置组合，无一 WIN Sarathi。**

| 设计 | 最佳 (r=12) | 最佳 (r=20) | 问题 |
|------|------------|------------|------|
| Per-stage limit (全 stage 限流) | +4.0% | +9.6% | 限流太紧 |
| Entry gate + free flow + WAIT | +3.1% | +8.0% | WAIT 冻结 pipeline |
| Entry gate + free flow, no WAIT | +3.1% | +8.0% | segment 边界开销 |
| 退化到 Sarathi (tl=9999,gate=OFF) | +3.7% | — | segment 固有开销 |

### 根本问题分析

1. **低 rate 下系统太空**：r=12 时 in-system 只有 ~4.5 个请求（Little's law），WCP 和 Sarathi 的 batch 一样小，没有 prefill attention 压缩空间
2. **Segment 边界 ~4% 固有开销**：即使 tl=9999 gate=OFF，segment 结构仍有 3.7% 开销
3. **WAIT + free-flow 矛盾**：free flow 快速 drain segment → WAIT 条件难满足 → 频繁冻结
4. **batch_est 不是瓶颈**：实际 batch 远小于 gate 预算

## 下一步计划

- [x] Sarathi profiling across all rates (r=12-40)
- [x] 完整 tl sweep (tl=3-100)
- [x] 2D sweep (tl × sm) for r=20
- [x] cs sweep (cs=64-512)
- [x] 负 seg_margin 测试
- [x] wait_gate 参数化
- [ ] **Overnight 3D grid**: 5 workloads × 4 rates × 72 WCP configs (running)
- [ ] 分析不同 workload 类型（closer decode, same prefill 等）是否改变结论

## 理论参数关系

| 参数 | Paper 对应 | 代码实现 |
|------|-----------|---------|
| tl | $\sum_k n_k \cdot \text{count}_k$ | `total_limit` |
| seg_margin | $n_{k+1}/n_k - p_k$ 的裕量 | `seg_margin` |
| cs | per-request prefill chunk | `chunk_size` |
| gate | batch token 限制 | `WAIT_CP_GATE` env |
| WAIT | $n_{j0} \geq n_j$ threshold | `seg_full \|\| entry_ready` |

---

**作者**: 自动生成
**分支**: revision
