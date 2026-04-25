# Vidur 可靠性验证完整计划

## Reviewer 对 Vidur 的具体关切

### Reviewer 2 的关切

1. **Simulation 准确性** (Section 5.2)
   - "Vidur simulation在大batch场景下可能不准确"
   - **验证要求**:
     - [ ] 在真实GPU (A100)上验证
     - [ ] 提供simulated vs real processing time对比图
     - [ ] 在abstract中说明是simulation而非actual GPU

### Reviewer 3 的关切 (Decision Letter)

2. **Unstable Regime 问题** (Line 81)
   - "All simulations in Section 6 appear to be in unstable regimes"
   - "Later jobs experienced greater latency, implying buildup of the queues"
   - **验证要求**:
     - [ ] 添加stable regime下的实验
     - [ ] 展示mean latency vs arrival rate标准排队论图
     - [ ] 标记各算法的stability region boundary

3. **Memory Constraint 现实性** (Line 88)
   - "Memory constraint seems to apply only to jobs in the batch currently being served"
   - 质疑preempted jobs的KV cache保留是否现实
   - "Moving memory between GPU and other locations would be time consuming"
   - **验证要求**:
     - [ ] 明确memory constraint覆盖范围
     - [ ] 讨论memory movement overhead
     - [ ] 提供数据支持或修改模型

4. **Throughput 定义** (Line 79)
   - Open system中throughput应等于arrival rate
   - 应改为"increasing maximum throughput"
   - **验证要求**:
     - [ ] 验证throughput测量方法
     - [ ] 区分throughput vs maximum throughput

---

## 验证任务清单

### A. Paper Model 假设验证 (τ = d₀ + d₁·M)

**状态**: ✅ 已完成

**方法**:
- 分析Vidur profiling数据 (58,632 samples)
- 线性回归: d₀ = 0.035ms, d₁ = 4×10⁻⁶ ms/token
- R² = 0.5252 (仅attention decode组件)

**输出**:
- `outputs/gpu_validation/REVIEWER2_COMPLETE_VALIDATION.md`

---

### B. Vidur Profiling 数据来源验证

**状态**: ✅ 已完成

**方法**:
- 确认profiling数据直接来自A100真实测量
- Batch size覆盖: 1-128
- Model: Llama-2-7B, Llama-3-8B等

**证据**:
- `data/profiling/compute/a100/meta-llama/Llama-2-7b-hf/attention.csv` (58,632行)
- `data/profiling/compute/a100/meta-llama/Llama-2-7b-hf/mlp.csv` (1,044行)

---

### C. Real GPU vs Simulation 对比验证

**状态**: ⏳ 等待Llama-2下载

**方法**:
1. 使用vLLM在A100上运行Llama-2-7B
2. 测量不同batch size下的iteration time
3. 与Vidur预测值对比

**参数**:
- Batch sizes: [1, 4, 8, 16, 32, 64]
- Prefill length: 256/512
- Decode length: 20/100

**输出**:
- Simulated vs Real processing time对比图
- MAPE (Mean Absolute Percentage Error)

---

### D. Stability Region 验证

**状态**: ✅ 已有数据，需整理

**方法**:
1. 使用现有timeseries数据
2. 生成mean latency vs arrival rate图
3. 标记各算法的stability boundary

**已有数据**:
- `outputs/timeseries/paper_mean_latency_vs_rate.png`
- `outputs/timeseries/timeseries_single.png`
- `outputs/timeseries/timeseries_multi.png`

**发现**:
- WCP stability region > Sarathi > vLLM
- WCP在r=23-24仍稳定，Sarathi在r=22已不稳定

---

### E. Memory Constraint 现实性验证

**状态**: ❌ 待完成

**方法**:
1. 检查Vidur中memory constraint的实现
2. 确认preempted requests的KV cache处理方式
3. 测量memory movement开销

**需要验证的问题**:
- [ ] Memory constraint是否覆盖所有GPU上的requests？
- [ ] Preempted requests的KV cache是否保留在GPU？
- [ ] 是否有memory movement到CPU/RAM/SSD？

---

### F. Throughput 测量验证

**状态**: ❌ 待完成

**方法**:
1. 验证open system中throughput = arrival rate (when stable)
2. 区分throughput vs max throughput
3. 检查论文中的throughput计算方式

---

## 当前进展总结

| 验证项 | Reviewer | 状态 | 优先级 |
|--------|----------|------|--------|
| Paper Model假设 | R2 | ✅ 完成 | P0 |
| Profiling数据来源 | R2 | ✅ 完成 | P0 |
| Real GPU对比 | R2 | ⏳ 等待下载 | P0 |
| Stability Region | R3 | ✅ 已有数据 | P0 |
| Memory Constraint | R3 | ❌ 未开始 | P1 |
| Throughput测量 | R3 | ❌ 未开始 | P1 |

---

## 下一步行动

1. **等待Llama-2下载完成** (9.3GB/13GB, ~72%)
2. **运行Real GPU vs Simulation对比**
3. **检查Vidur memory constraint实现**
4. **整理Stability Region数据**

---

**更新日期**: 2026-04-07
