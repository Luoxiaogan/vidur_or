# WAIT-CP 参数空间扫描 - 2026-03-20

## 状态
🚧 进行中（发现 booking limit 有效的参数区间，待设计自适应逻辑）

## 概要

系统性扫描了 WAIT-CP 的三个可调参数（chunk_size, total_limit, N_SEG）在 rate=20 下的表现。发现 **booking limit 在非最优 chunk_size 配置下能大幅超过 Sarathi（-65%）**，但在 Sarathi 最优 chunk_size 下只能 TIE。

## 完成内容

### 1. 全参数梳理

系统性列出了所有可调参数：
- **Workload**: l₀(prefill), l₁(decode), arrival_rate, num_requests
- **调度器**: chunk_size, total_limit, N_SEG, block_size, watermark, batch_size_cap
- **硬件**: device, model, memory_margin, num_blocks

核心发现：**K = ceil(l₀/chunk_size)** 决定了 pipeline 结构和 in-system 上限。

### 2. chunk_size × total_limit 扫描 (rate=20, l₀=630, l₁=20)

**Sarathi baselines**:
| chunk | K | Sarathi mean |
|-------|---|-------------|
| 256 | 3 | 21.189s |
| 512 | 2 | **7.385s** (最优) |
| 1024 | 1 | 21.189s |

**WAIT-CP gap vs Sarathi (%)**:
| chunk | K | tl=5 | tl=10 | tl=15 | tl=20 | tl=30 | tl=50 | tl=100 |
|-------|---|------|-------|-------|-------|-------|-------|--------|
| 256 | 3 | **-65%** | **-11%** | +548% | +49% | 0% | 0% | 0% |
| 512 | 2 | +187% | +187% | +1840% | +414% | +156% | +92% | 0% |
| 1024 | 1 | **-65%** | **-65%** | +677% | +160% | +64% | +49% | +9% |

### 3. l₀=512 验证 (chunk=512, K=1)

Sarathi mean=1.021s (K=1 极高效)。WAIT-CP 所有 tl 都更差或 TIE。

### 4. Booking limit 有效性条件

确认 booking limit 在以下条件下生效：
1. chunk_size 非最优 → Sarathi 过载
2. total_limit 足够小 → 限制 in-system → 稳定系统
3. tl=15 左右是灾难点（稳定/不稳定边界）

## 关键发现

### 为什么 chunk 预算是 admission 瓶颈

```
自然 in-system ≈ 1 + l₁/K (独立于 arrival rate)
chunk=512: K=2 → n ≈ 11
chunk=256: K=3 → n ≈ 8
chunk=1024: K=1 → n ≈ 21

即使 rate=1000，in-system 也不会超过这个上限
因为 chunk 预算每 batch 只能 admit 1 个新 prefill
```

### 为什么 tl=5 在 chunk=256 下赢 65%

```
Sarathi (chunk=256, 无 booking limit):
  - in-system ≈ 8, rate=20 >> throughput ≈ 11/s → 过载 → 21.189s

WAIT-CP (chunk=256, tl=5):
  - in-system = 5, batch 更小 → 步进更快 → 系统稳定 → 7.385s
  - 等效于 Sarathi chunk=512 的性能！
```

### 参数空间结构

```
tl 太小 (< 5):   → 极低 throughput → 更差
tl 刚好 (5-10):  → 稳定系统 → 可能赢（如果 Sarathi 过载）
tl 中间 (15):    → 稳定/不稳定边界 → 灾难
tl 足够大 (30+): → 不 binding → = Sarathi
```

## 代码变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `general_nested_chunked_replica_scheduler.py` | 未变 | 已有的 peek-based 统一调度器 |
| `.claude/CLAUDE.md` | 修改 | 添加实验状态章节 |

## 下一步计划

- [ ] 设计 total_limit 自适应逻辑（根据系统负载动态调整）
- [ ] 设计 N_SEG 自适应逻辑
- [ ] 在多个 rate (14, 16, 18, 20) 下验证最佳 (chunk, tl) 组合
- [ ] 确定 paper 实验的 workload 配置（l₀, l₁, chunk_size）

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-20
