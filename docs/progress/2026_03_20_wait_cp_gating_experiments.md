# WAIT-CP 门控机制实验 - 2026-03-20

## 状态
🚧 进行中（原 workload 下门控无法赢 Sarathi，需换场景）

## 概要

系统性测试了 WAIT-CP 的级联门控、AIMD 自适应、segment cap 等机制在原 workload (l₀=630, l₁=20, A100) 下的表现。所有 binding 的门控机制均比 Sarathi 差，不 binding 则 = Sarathi。

## 关键实验结果

### 1. Peek-based 双阈值（零 overhead）
- 全 rate (14-21) × 6 seeds = Sarathi (0.00%)
- 原因：upper_limit cap 永远不 binding

### 2. 级联门控 + 自适应 seg_limit
| α (seg_limit = avg × α) | Mean | vs Sarathi |
|--------------------------|------|-----------|
| 0.50 | 1.446s | +100% |
| 0.70 | 1.156s | +60% |
| 0.80 | 1.049s | +45% |
| 0.90 | 0.987s | +36% |
| 0.95 | 0.970s | +34% |
| 0.99 | 0.970s | +34% ← 收敛 |
| 1.00 (no gate) | 0.724s | 0% = Sarathi |

**严格单调，α=0.95~0.99 收敛到 +34%，与 1.0 之间是 step function**

### 3. AIMD 自适应
| 配置 | Mean | vs Sarathi |
|------|------|-----------|
| 温和 (dec=1, mr=0.95) | 0.724s | 0% |
| 中等 (dec=2, mr=0.8) | 0.903s | +25% |
| 激进 (dec=5, mr=0.5) | 1.240s | +71% |

**严格单调，任何 binding 都更差**

### 4. Chunk size grid
| chunk | WCP | Sarathi | gap |
|-------|-----|---------|-----|
| 128 | 63.4s | 63.4s | 0% |
| 256 | 0.807s | 0.807s | 0% |
| 384 | 0.764s | 0.764s | 0% |
| 512 | 0.724s | 0.724s | 0% (最优) |
| 630 | 1.312s | 1.312s | 0% |
| 1024 | 1.431s | 1.431s | 0% |

**所有 chunk 下 WAIT-CP = Sarathi**

### 5. Multi-seed 验证 (6 seeds × 3 rates)
- rate=14: WCP +11.35% (AIMD 有害)
- rate=16,18: WCP = Sarathi (AIMD 不 binding)
- 禁用 AIMD 后：全 rate 全 seed = Sarathi

## 根因分析

### 为什么门控总是更差
```
d₀ = 44ms (prefill chunk，占 batch 时间 95%)
d₁ = 0.22ms/req (decode 边际成本，极小)

跳过 2 个 decode: 省 0.44ms/batch
那 2 个请求多等 1 cycle: +25ms

成本/收益 = 25 / 0.44 = 57x → 门控每触发一次亏 57 倍
```

### 为什么 α=0.99 有 step function (+34%)
级联倾向 block 最后一段（接近完成的请求，数量最少）。这些请求是最有价值的（已投入最多计算，即将完成释放内存）。delay 它们代价最大。

### 为什么 = Sarathi 如此稳固
当前实现在不 binding 时产生与 Sarathi 完全相同的调度决策（精确到小数点后 6 位），因为：
1. Decode 全部处理（work-conserving）
2. Prefill admission 不限制（total_limit >> in_system）
3. Chunk 预算相同

## 代码改动

| 文件 | 改动 |
|------|------|
| `general_nested_chunked_replica_scheduler.py` | 级联门控 + peek-based + 自适应 seg_limit |
| `custom_prompt_generator.py` | 添加 random.seed 支持 |

## 门控有可能赢的场景（未测完）

1. **Memory-limited workload** (l₀=4096)：已验证 rate≥3 赢 1-3%
2. **多类型 workload**：nested booking limit 的原始设计意图
3. **真实 GPU**：非线性 attention 开销让 d₁ 更大
4. **高并发场景**：batch_size > 50，decode 的边际成本占比更大

## 下一步

- [ ] 换 memory-limited 或多类型 workload 做 paper 实验
- [ ] 或在真实 GPU 上验证（非 Vidur 模拟）
- [ ] 理论分析：门控收益的充要条件（d₁ 的阈值）

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-20
