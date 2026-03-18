# WAIT CP 流量平衡设计文档

> 日期: 2026-03-17 ~ 03-18
> 状态: 实验进行中

---

## 1. 问题背景

WAIT CP（GeneralNestedChunked 调度器）在 **low arrival rate** 下的 mean latency 输给 baseline Sarathi。

实验配置:
- 模型: `meta-llama/Meta-Llama-3-8B`, A100
- l₀=630 (prefill tokens), l₁=20 (decode tokens)
- WAIT CP: chunk_size=512
- 测试 arrival rates: 14-21 req/s

---

## 2. 已实施的代码修复

### 2.1 Bug Fix: Stage 0 → Stage 1 推进

**问题**: WAIT CP 的 Stage 0 不调用 `advance_stage()`，prefill 完成后请求永远卡在 Stage 0。

**修复**: 在分组阶段自动推进 prefill 完成的请求：
```python
if stage == 0 and req.is_prefill_complete:
    req.advance_stage()
    stage = req.current_stage
```

### 2.2 Stage 0 limit 改用 remain

**问题**: per_stage_limit=1 导致每 batch 只处理 1 个 Stage 0 请求。

**修复**: Stage 0 用 `remain` 做准入，chunk_size 做计算量限制：
```python
for _ in range(remain):  # 原来是 range(limit=1)
```

### 2.3 自适应 total_limit (Little's Law)

**实现**: `n* = λ̂ × Ŵ`，在线估计到达率和服务时间，动态更新 total_limit。

代码位置: `general_nested_chunked_replica_scheduler.py`

---

## 3. 实验结果

### 3.1 WAIT CP (fixed limit) vs Sarathi（公平 baseline）

**条件**: 6000 请求, 掐头 50%, Sarathi chunk=512/256

| Rate | WAIT CP (limit=20) | Sarathi-512 | gap | Sarathi-256 | gap |
|------|---------------------|-------------|-----|-------------|-----|
| 14 | 1.350s | **0.724s** | +86% | 0.807s | +67% |
| 15 | 1.472s | **0.819s** | +80% | 1.245s | +18% |
| 16 | 2.805s | **0.954s** | +194% | 10.795s | -74% |
| 17 | 18.194s | **1.170s** | +1455% | 26.743s | -32% |
| 18 | 38.088s | **2.407s** | +1482% | 41.439s | -8% |
| 19 | 55.610s | **12.671s** | +339% | 54.588s | +2% |
| 20 | 60.202s | **24.343s** | +147% | 66.422s | -9% |
| 21 | 61.810s | **35.050s** | +76% | 77.129s | -20% |

**发现**:
- Sarathi-512 全面碾压 WAIT CP
- WAIT CP 从 rate=16 开始爆炸（total_limit 从 40 跳到 100/525）
- Sarathi-256 从 rate=16 也爆了（chunk=256 overhead 太大）
- WAIT CP 在高 rate (19-21) 比 Sarathi-256 好（booking limit 稳定作用）

### 3.2 自适应 WAIT CP

**条件**: n_max=725, Little's Law 自适应

| Rate | Adaptive WAIT CP | Fixed limit=20 | Sarathi-512 |
|------|-----------------|----------------|-------------|
| 14 | 1.336s | 1.350s | 0.724s |

**发现**: 自适应收敛到 n*≈56，比 fixed=20 还大。没有改善。

**原因**: 鸡蛋问题 — W 受 total_limit 影响（limit 大 → batch 大 → W 大 → n* 大 → limit 更大）。观测到的 W 反映的是 WAIT 膨胀后的服务时间，而非理想服务时间。

---

## 4. 根因分析（深层）

### 4.1 WAIT CP vs Sarathi 的本质差异

**Sarathi**: 无准入控制，请求到了直接进。低 rate 下在飞数 = λ × W_ideal ≈ 10。

**WAIT CP**: booking limit 强制在飞数 = total_limit。即使系统空闲，pipeline 结构维持 ~total_limit 个在飞请求，膨胀了 batch → 增加了每个 batch 的执行时间 → 增加了 per-request latency。

### 4.2 排队延迟公式

```
E2E latency ≈ n/(2λ) + (K+l₁) × ΔT(n)
            = n/(2λ) + 22 × (d₀ + d₁×n)
```

rate=14, total_limit=20:
- 排队: 20/(2×14) ≈ 0.71s
- 处理: 22 × 47ms ≈ 1.04s
- 总计: ≈ 1.75s（实测 1.35s，偏高因为管道不是严格等凑满）

### 4.3 d₀, d₁ 拟合结果

```
模型: ΔT(batch) = d₀ + d₁ × n_decode  (with chunk=512 prefill)
d₀ = 44.3 ms  (batch 固定开销，含 prefill chunk)
d₁ = 0.223 ms/req  (每增一个 decode 请求的边际开销)
R² = 0.94
```

**注意**: d₀ 依赖 chunk_size 和 prefill tokens 数量。不同 workload 下 d₀ 不同。

### 4.4 自适应的鸡蛋问题

Little's Law: n* = λ × W

但 W 本身依赖 n*（通过 batch 大小影响 ΔT）：
```
W(n) = (K+l₁) × (d₀ + d₁×n)  +  queuing_delay(n, λ)
```

自适应观测到的 W 是 W(n_current)，而非 W(n_optimal)。系统锁定在高平衡点。

---

## 5. 待探索方向

### 5.1 理想 W 估计

不用观测 W，用理论下界：
- W_ideal ≈ (K+l₁) × d₀ = 22 × 44.3ms ≈ 0.975s（无排队、batch size=1 的纯处理时间）
- n*_ideal = λ × W_ideal = 14 × 0.975 ≈ 14
- 这接近 Sarathi 的自然在飞数

### 5.2 从 Sarathi 借鉴

Sarathi 的优势：
1. 无准入控制 → 请求即到即进
2. Decode-first → 先处理 decode（低开销），再用剩余预算做 prefill
3. Batch 大小由自然在飞数决定（不人为膨胀）

WAIT CP 能否保留 booking limit 的稳定性优势，同时在低负载下退化到 Sarathi 行为？

### 5.3 可能的新机制

1. **total_limit = n_ideal = λ × W_ideal**: 用理论下界，不依赖观测 W
2. **去掉 booking limit 的等待机制**: 用 remain + chunk_size 做流控就够，不需要凑批
3. **Decode-first 调度**: 参考 Sarathi，先调度 decode，再用 chunk 做 prefill
4. **动态切换**: 低负载用 Sarathi 模式，高负载切 WAIT 模式

### 5.4 需要回答的关键问题

- [ ] per_stage_limit 在 decode 阶段是否必要？如果每个 stage 都处理所有请求（不限制），会怎样？
- [ ] WAIT 相对 Sarathi 的本质优势到底在哪个 rate 范围体现？
- [ ] 如果 Sarathi-512 全面赢 WAIT CP，WAIT 的 contribution 如何定位？

---

## 6. 代码修改汇总

### 已修改文件

| 文件 | 修改内容 |
|------|---------|
| `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py` | Stage 0 推进 + remain 流控 + 自适应 n* |
| `vidur/utils/memory_manager.py` | 新增：模拟专用内存管理器 |
| `vidur/simulator.py` | 接入 memory manager |
| `docs_for_claude_code/wait_cp_flow_balance_design.md` | 本文档 |
| `scripts/fit_d0_d1.py` | d₀, d₁ 拟合脚本 |

---

*最后更新: 2026-03-18*
