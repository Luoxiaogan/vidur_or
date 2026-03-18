# WAIT-CP 状态总结 - 2026-03-19

## 当前代码架构

文件：`general_nested_chunked_replica_scheduler.py`

**分段调度 (Segmented WAIT-CP)**:
- N_SEG=4 个 decode 段 + 1 个 prefill 段
- 段内自由推进，段间 seg_limit 门控
- Preempted decode 直接分组（不经 queue 中转）
- 自适应 n*(λ) 基于 d₀/d₁ 公式
- batch_cap = total_limit 限制 batch 大小

## 实验核心发现

### Direct preempt = 完全退化为 Sarathi
当 preempted decode 不经 queue 直接进 batch 时：
- 全 rate 与 Sarathi 精确一致（+0.0%）
- 原因：段间门控对 preempted 请求不生效（直接跳过了分段逻辑）

### 经 queue 中转 = 有分段效果但 +6% overhead
当 preempted decode 经 queue → 分组 → 段间门控时：
- rate=14: +6.2%（overhead）
- rate=18: 也输 Sarathi（之前看到的 -9.7% 是 2000 请求的 warmup 伪影）

### 根本矛盾
```
要 per-stage contribution → preempted 必须经过段间门控 → 有 overhead
要 = Sarathi 性能    → preempted 必须直接进 batch   → 无 contribution
```

## 未解决的问题

1. **如何让分段门控生效但不增加 overhead？**
   - 直接在 preempted 分组时做门控（不经 queue）→ 已实现但门控不 binding
   - seg_limit 太大（> 实际请求数）→ 需要更紧的 limit
   - 但 limit 太紧 → 限制 throughput

2. **在这个 workload (l₀=630, l₁=20) 下是否有可能赢 Sarathi？**
   - 系统是 throughput-limited，内存不是瓶颈
   - 分段结构在 throughput-limited 场景下只有成本没有收益
   - 可能需要 memory-limited workload 才能展示优势

3. **自适应 n* 的值 (15-50) 始终 > 自然在飞数 (~10)**
   - 公式正确但在飞数太小
   - 需要让系统 "更紧张" 才能让 admission control 有用

## 下一步方向

### A. 换 workload
l₀=4096, l₁=20 → 内存更紧 → 可能触发分段优势

### B. 改分段机制
让分段不只做 "门控"，还做 "优先级"：
- 完成度高的请求优先（已实现 reversed 迭代）
- 在过载时 drop/defer 完成度低的请求（新机制）

### C. 理论定位
接受低 rate = Sarathi（0% gap），聚焦：
- Flow balance 的理论保证（deterministic batch, bounded latency）
- Memory-limited 场景下的实际优势
- N_SEG 作为 tunable parameter 的分析

## 2026-03-19 新发现

### WAIT 的"等"机制实验

恢复了 WAIT 的核心：seg_limit 作为下限（凑够才发车），不够就放回 preempted。

**结果**：
- seg_limit=1（最小等待）: rate=14 → 2.44s (Sarathi 0.775s)，大幅变差
- 原因：即使 seg_limit=1，"不够→放回 preempted→下个 batch 重新分组"也多了 1 个 batch cycle 延迟
- 每个请求每经过一个段边界就可能被延迟 1 个 cycle → N_SEG=4 段 → 最多 4 个 cycle 延迟

### "退化成 Sarathi" 的原因确认

之前 direct preempt + 段间门控不 binding → = Sarathi，根因是：
- seg_limit 被当作上限（最多处理多少）而非下限（凑够才发车）
- 应该用作下限，但下限机制的"等+放回"操作本身有延迟成本

### 根本 tradeoff

```
WAIT 的"等"：凑大 batch → 更高效（摊薄 d₀）→ throughput 高
WAIT 的代价：等待时间 → latency 高

净收益 = throughput_gain - latency_cost
- 低 rate: throughput 不是瓶颈 → 净收益 < 0 → WAIT 输 Sarathi
- 高 rate (接近容量): throughput 是瓶颈 → 净收益 > 0 → WAIT 赢
- Memory-limited: Sarathi 过载 preempt → WAIT 的 admission control 赢
```

### Memory-Limited 实验结果 (l₀=4096, l₁=20, capacity≈115)

| Rate | WAIT-CP | Sarathi | gap |
|------|---------|---------|-----|
| 2 | 2.12s | 1.85s | +14.5% |
| **3** | **17.07s** | 17.37s | **-1.7% ✓** |
| **4** | **48.18s** | 48.75s | **-1.2% ✓** |
| **5** | **67.02s** | 67.58s | **-0.8% ✓** |
| **6** | **79.49s** | 80.13s | **-0.8% ✓** |
| **7** | **88.44s** | 89.10s | **-0.7% ✓** |
| **8** | **95.16s** | 95.82s | **-0.7% ✓** |

**Crossover at rate=3。** WAIT-CP 在 memory-limited + 中高负载下赢 Sarathi。
restarts=0（无真正 preemption），赢在更高效的 batching。

### 下一步
- [ ] 原配置（l₀=630, l₁=20）自适应 seg_limit 调优，看能否在 throughput-limited 场景也赢
- [ ] 调 N_SEG 在 memory-limited 下拉大优势
- [ ] 更大的 request 数量验证（掐头去尾更准）
