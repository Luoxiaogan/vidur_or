# WAIT-CP 调度器完整优化记录 - 2026-03-17 ~ 03-19

## 状态
🚧 进行中（分段调度框架已搭建，需换 workload 验证优势）

## 概要

对 WAIT-CP（GeneralNestedChunked）调度器进行了系统性优化和实验，探索了 decode-first、分段调度、自适应 n* 等多种机制，最终确定了 **分段调度 + 自适应 batch_cap** 的方向。在当前 throughput-limited workload (l₀=630, l₁=20) 下低 rate 与 Sarathi 持平，高 rate 仍待 memory-limited workload 验证。

## 完成内容

### Bug 修复
- **Stage 0 → Stage 1 推进 fix**：prefill 完成后请求自动 advance_stage()，不再卡在 Stage 0
- **per_stage_limit=1 瓶颈修复**：Stage 0 改用 remain 做准入控制

### 架构演进（5 个版本）

| 版本 | 描述 | rate=14 e2e | vs Sarathi |
|------|------|------------|-----------|
| v0 原始 | 按 stage 迭代, limit=20 | 1.350s | +86% |
| v1 Decode-First | 重写为三步调度 | 0.869s | +20% |
| v2 +Direct Preempt | preempted 不经 queue | 0.869→0.775s | +0%~7% |
| v3 +Decode in Chunk | decode 计入 chunk 预算 | 0.775s | ≈0% |
| v4 Segmented | 分段门控 + batch_cap | 0.775~0.823s | 0%~+6% |

### 分段调度框架（当前版本）
- **N_SEG 可配置**（1=decode-first, 20=full per-stage）
- **段内自由推进，段间 booking limit 门控**
- **自适应 n*(λ)**：基于 d₀/d₁ 公式在线调整 total_limit
- **batch_cap = total_limit**：限制 batch 大小（高 rate 时 binding）
- **Direct preempt**：preempted 请求直接分组，不经 queue 中转

### 基础设施
- **SimulationMemoryManager**：按完成请求数清理 event trace（每 500 completions）
- **d₀/d₁ 拟合脚本**：`scripts/fit_d0_d1.py`

## 代码变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py` | 重写 | 分段调度 + 自适应 n* + direct preempt |
| `vidur/simulator.py` | 修改 | 接入 memory manager |
| `vidur/utils/memory_manager.py` | 新增 | 按完成请求数触发清理 |
| `scripts/fit_d0_d1.py` | 新增 | batch 执行时间模型拟合 |
| `docs_for_claude_code/wait_cp_flow_balance_design.md` | 新增 | 流量平衡设计文档 |
| `docs_for_claude_code/wait_cp_adaptive_findings.md` | 新增 | 自适应实验发现 |
| `docs_for_claude_code/wait_cp_segmented_results.md` | 新增 | 分段实验结果 |
| `docs_for_claude_code/wait_cp_status_0319.md` | 新增 | 当前状态总结 |
| `docs/progress/2026_03_18_wait_cp_optimization.md` | 新增 | 优化进度报告 |

## 关键实验结果

### 全 Rate Sweep（Segmented N_SEG=4, direct preempt, 6000 req, skip 50%）

| Rate | WAIT-CP | Sarathi-512 | gap |
|------|---------|-------------|-----|
| 14 | 0.724s | 0.724s | 0.0% |
| 15 | 0.819s | 0.819s | 0.0% |
| 16 | 0.954s | 0.954s | 0.0% |
| 17 | 1.170s | 1.170s | 0.0% |
| 18 | 2.407s | 2.407s | 0.0% |
| 19 | 12.671s | 12.671s | 0.0% |
| 20 | 24.343s | 24.343s | 0.0% |
| 21 | 35.050s | 35.050s | 0.0% |

**结论**：direct preempt 让 WAIT-CP 完全退化为 Sarathi（精确到小数点后 6 位）。分段门控对 preempted 请求不生效。

### 不经 queue 中转时（preempted → queue → batch）

| Rate | WAIT-CP | Sarathi | gap |
|------|---------|---------|-----|
| 14 | 0.758s | 0.724s | +4.7% |
| 18 | 2.903s | 2.407s | +20.6% |

分段门控生效但有 overhead。

## 遇到的问题与解决

### 问题 1: 请求卡在 Stage 0
**解决**: 分组时自动 advance_stage()

### 问题 2: per_stage_limit=1 串行化
**解决**: Stage 0 用 remain 替代 per_stage_limit

### 问题 3: Preemption overhead（0.131s）
**解决**: preempted decode 直接进 batch，不经 queue

### 问题 4: Batch 偏大（比 Sarathi 多 31 prefill tokens）
**解决**: decode tokens 计入 chunk 预算

### 问题 5: 自适应 n* 鸡蛋问题
**解决**: 改用 d₀/d₁ 公式（硬件常数，不依赖 observed W）

### 问题 6: Admission control 不 binding
**原因**: 当前 workload throughput-limited（in_system ≈ 10-15 << capacity 725）
**状态**: 未解决，需换 memory-limited workload

### 问题 7: 分段门控 vs 性能的根本矛盾
**描述**: preempted 经门控 → +6% overhead；不经门控 → = Sarathi 无 contribution
**状态**: 核心未解决问题

### 问题 8: "preemption" 命名误导
**说明**: `_preempted_requests` 实际是"上一 batch 的未完成请求"，不是真正的抢占驱逐。Sarathi 也一样。真正的 preemption (restart) 只在内存不足时发生。

## 理论发现

### d₀/d₁ 拟合
```
ΔT(batch) = d₀ + d₁ × n_decode  (with chunk=512 prefill)
d₀ = 44.3ms, d₁ = 0.223ms/req, R²=0.94
注: d₀ 依赖 chunk_size 和 prefill tokens
```

### 自适应 n* 公式
```
n*(λ) = (K+l₁) × d₀ × λ / (1 - (K+l₁) × d₁ × λ)
K = ceil(l₀/chunk_size), pipeline_depth = K + l₁
```

### 系统特性分析
- 当前 workload (l₀=630, l₁=20): **throughput-limited**
  - GPU 容量 725 slots, 自然在飞 ~10-15, 内存利用 2%
  - Admission control 无用武之地
- Memory-limited 需要: l₀=4096+ 或更小 GPU

## 下一步计划

- [ ] **换 memory-limited workload**（l₀=4096, l₁=20），验证分段在内存紧张下的优势
- [ ] 解决分段门控 vs 性能矛盾（让 preempted 走门控但不经 queue）
- [ ] 不同 N_SEG 在不同 rate 下的最优选择
- [ ] Paper 的 story 确定：理论 flow balance + memory-limited 实验

---

**作者**: Claude Code + 用户协作
**日期**: 2026-03-17 ~ 2026-03-19
