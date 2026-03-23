# WAIT CP 调度器优化 - 2026-03-18

## 状态
🚧 进行中（低 rate 接近 Sarathi，高 rate 待验证）

## 概要

对 GeneralNestedChunked (WAIT CP) 调度器进行了四步优化，将 low arrival rate 下的 mean latency 从 1.350s 降至 0.775s（vs Sarathi-512 的 0.724s，gap 从 86% 缩小到 7%）。同时新增了模拟专用内存管理器和 d₀/d₁ 拟合工具。

## 完成内容

### 主要优化（四步）

1. **Bug Fix: Stage 0 → Stage 1 推进**
   - 问题：prefill 完成后请求永远卡在 Stage 0，decode pipeline 为空
   - 修复：分组时自动检测 `is_prefill_complete` 并 `advance_stage()`

2. **Stage 0 limit 改用 remain**
   - 问题：`per_stage_limit=1` 导致每 batch 只处理 1 个 Stage 0 请求
   - 修复：Stage 0 用 `remain = total_limit - occupied` 做准入控制

3. **Decode-First + Direct Preempt**
   - 问题：按 stage 顺序迭代 + preempted 经 queue 中转增加延迟
   - 修复：重写 `_get_next_batch()`，三步调度：
     - Step 1: preempted decode 直接进 batch（消除 preemption_time）
     - Step 2: running prefills 继续 chunk
     - Step 3: 新请求用剩余 chunk 预算

4. **Decode tokens 计入 chunk 预算**
   - 问题：Sarathi 把 decode tokens 计入 `num_batch_tokens`，WAIT CP 没有，导致 batch 偏大
   - 修复：`num_batch_tokens += 1` for each decode request
   - 效果：batch 组成完全对齐 Sarathi（7.57 requests, 231 tokens, 25.28ms/batch）

### 自适应 total_limit 探索

- **Little's Law 自适应** (`n* = λ × W`)：实现了在线 EMA 估计 λ 和 W
- **发现鸡蛋问题**：W_observed 包含排队延迟 → n* 偏高 → 系统锁在高平衡点
- **结论**：观测 W 不可靠，需要用 processing time 或理论 W_ideal

### 基础设施

- **SimulationMemoryManager**：周期性清理 `_event_trace`/`_event_chrome_trace`，防止长时间模拟内存增长
- **d₀/d₁ 拟合脚本**：用 execution time predictor 拟合 batch 延迟模型

## 实验结果

### Rate=14 优化进度

| 版本 | E2E | vs Sarathi-512 |
|------|-----|---------------|
| 原始 (stage-iter, limit=20) | 1.350s | +86% |
| +Stage 推进 + remain | (同上量级) | — |
| +Decode-first + direct preempt | 0.869s | +20% |
| +Decode in chunk budget | **0.775s** | **+7%** |
| Sarathi-512 baseline | 0.724s | — |

### Rate=14 Breakdown 对比

```
              execution   sched_delay   preemption   e2e
WAIT CP:      0.660s      0.114s        0.000s       0.775s
Sarathi-512:  0.638s      0.086s        0.000s       0.724s
差值:         +0.022s     +0.028s       0            +0.051s
```

### Batch 组成对比（优化后完全对齐）

```
              batch_size  tokens  prefill  decode  exec_time
WAIT CP:      7.57       231.1   224.3    6.8     25.28ms
Sarathi:      7.57       231.1   224.3    6.8     25.28ms
```

### 全 Rate 对比（Sarathi chunk=512/256，优化前 WAIT CP）

| Rate | WAIT CP (limit=20) | Sarathi-512 | Sarathi-256 |
|------|---------------------|-------------|-------------|
| 14 | 1.350s | **0.724s** | 0.807s |
| 15 | 1.472s | **0.819s** | 1.245s |
| 16 | 2.805s | **0.954s** | 10.795s |
| 17 | 18.194s | **1.170s** | 26.743s |
| 18 | 38.088s | **2.407s** | 41.439s |
| 19 | 55.610s | **12.671s** | 54.588s |
| 20 | 60.202s | **24.343s** | 66.422s |
| 21 | 61.810s | **35.050s** | 77.129s |

**注**：优化后的 WAIT CP 尚未跑全 rate 对比，仅 rate=14 验证了 0.775s。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 3 |
| 修改文件 | 2 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py` | 修改 | 重写 `_get_next_batch()` + 自适应 n* + stage 推进 fix |
| `vidur/simulator.py` | 修改 | 接入 SimulationMemoryManager |
| `vidur/utils/memory_manager.py` | 新增 | 模拟专用内存管理器 |
| `scripts/fit_d0_d1.py` | 新增 | d₀/d₁ 拟合脚本 |
| `docs_for_claude_code/wait_cp_flow_balance_design.md` | 新增 | 流量平衡设计文档 |

## 理论分析

### d₀/d₁ 拟合结果

```
ΔT(batch) = d₀ + d₁ × n_decode  (with chunk=512 prefill)
d₀ = 44.3 ms  (batch 固定开销)
d₁ = 0.223 ms/req  (每增一个 decode 的边际开销)
R² = 0.94
注: d₀ 依赖 chunk_size 和 prefill tokens
```

### 流量平衡设计

- `remain = seg_total_limit - occupied` 提供自然反压
- Stage 0 入口控制 + chunk_size 计算量控制 = 双层保护
- Decode-first 消除 stage pipeline 的人为膨胀

## 遇到的问题与解决

### 问题 1: 请求卡在 Stage 0
**现象**: Stages 1-19 永远为空，所有请求在 Stage 0 做完 prefill+decode
**原因**: Stage 0 不调用 `advance_stage()`，也没有代码在 prefill 完成后推进
**解决**: 分组时自动检测并推进

### 问题 2: per_stage_limit=1 瓶颈
**现象**: 每 batch 只处理 1 个请求
**原因**: `per_stage_limit = ceil(total_limit/20) = 1`，Stage 0 也被限制
**解决**: Stage 0 用 remain 替代 per_stage_limit

### 问题 3: Preemption 开销
**现象**: preemption_time = 0.131s
**原因**: preempted 请求经 queue 中转增加延迟
**解决**: decode 请求直接从 preempted 进 batch，不经 queue

### 问题 4: Batch 偏大
**现象**: WAIT CP batch 比 Sarathi 多 ~31 prefill tokens
**原因**: decode tokens 没计入 chunk 预算，prefill 多占了空间
**解决**: `num_batch_tokens += 1` for decode

### 问题 5: 自适应 n* 鸡蛋问题
**现象**: Little's Law 自适应收敛到 n*≈122（太高）
**原因**: W_observed 包含排队延迟（由 total_limit 导致）→ 正反馈
**解决**: 暂时关闭自适应，待后续用 execution_time 替代 e2e_time

## 后续进展（03-18 下午）

### 分段调度（Segmented WAIT-CP）

**核心思路**：per-stage（20段）和 decode-first（1段）之间取中间态。

| 版本 | E2E (rate=14) | vs Sarathi | 段间 flow balance |
|------|-------------|------------|------------------|
| Per-stage (20段) | 1.47s | +90% | ✓ 每 stage |
| **Segmented (4段)** | **0.823s** | **+6%** | ✓ 每 4-5 steps |
| Decode-first (1段) | 0.775s | ≈0% | ✗ 无 |
| Sarathi-512 | 0.775s | baseline | ✗ 无 |

### 其他发现

1. **Decode-first + total_limit=725 完全等价 Sarathi**（精确到小数点后 6 位）
2. **自适应 n\* 在原始 workload (l₀=630) 下从不 binding**（系统是 throughput-limited）
3. **Memory manager 改为按完成请求数触发**（每 500 completions 清理一次）

## 下一步计划

- [ ] 用 6000 请求验证分段结果（掐头去尾更准确）
- [ ] 试不同 N_SEG（1,2,3,4,8,20）找最优分段数
- [ ] Memory-limited workload（l₀=4096, l₁=20）验证高 rate 优势
- [ ] 不同 chunk_size (128, 256, 512) 下的 tradeoff
- [ ] 画时间序列图
- [ ] 分段数 N_SEG 的理论最优分析

## 相关文档

- [WAIT CP 流量平衡设计](../../docs_for_claude_code/wait_cp_flow_balance_design.md)
- [GeneralNestedChunked 使用说明](../../docs_for_claude_code/GeneralNestedChunked调度器使用说明.md)
- [实验设计的思考](../../new_experiments_for_revision/exp_1_wait/实验设计的思考.md)

---

**作者**: Claude Code + 用户协作
**日期**: 2026-03-18
