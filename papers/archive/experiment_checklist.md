# OR Revision 实验 Checklist

**Paper**: Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints
**Manuscript ID**: OPRE-2025-04-1885
**创建日期**: 2026-03-22

---

## A. 现有实验补全（Reviewer 要求的参数/说明）

| # | 任务 | Reviewer | 当前状态 | 优先级 | 难度 | 完成 |
|---|------|----------|---------|--------|------|------|
| A1 | 统一模型名称：abstract "Llama-7B" vs intro "Llama2-7B" | R2 | 不一致 | **P0** | 1min | [ ] |
| A2 | 列出 WAIT 实验完整参数表 (B, M*, C, d₀, d₁) | R2 | 缺失 | **P1** | 30min | [ ] |
| A3 | 列出 Nested WAIT 实验参数表 (n₁...n₁₀, segment boundaries) | R2 | 部分（ratio 已有） | **P1** | 30min | [ ] |
| A4 | Baseline 配置说明 (Sarathi chunk size, vLLM watermark, reserved memory) | R2 | 缺失 | **P1** | 30min | [ ] |
| A5 | Figure 7 caption: 解释 "Prompt Number" 含义 | R2 | 不清楚 | **P2** | 5min | [ ] |
| A6 | 说明 validation GPU (L20) vs experiment GPU (A100 simulated) 的区别 | R2 | 未说明 | **P2** | 10min | [ ] |

## B. 新增实验：Mean Latency vs Arrival Rate（核心要求）

| # | 任务 | Reviewer | 当前状态 | 优先级 | 难度 | 完成 |
|---|------|----------|---------|--------|------|------|
| B1 | **Single type, known output**: mean latency vs λ 曲线 (WAIT vs vLLM vs Sarathi) | R3 | 未做 | **P0** | Large | [ ] |
| B2 | **Multi type, known output**: mean latency vs λ 曲线 | R3 | 未做 | **P0** | Large | [ ] |
| B3 | **Multi type, unknown output**: mean latency vs λ 曲线 (Nested WAIT vs vLLM vs Sarathi) | R3 | 未做 | **P0** | Large | [ ] |
| B4 | 从图中标出各算法的 **stability region boundary** (latency diverge 的 λ) | R3 | 未做 | **P0** | Medium | [ ] |
| B5 | 说明 WAIT 的 stability region 大于 vLLM（因 eviction 缩小 vLLM 的 stable region） | R3 | 未做 | **P1** | Medium | [ ] |

## C. Near-Boundary 行为验证

| # | 任务 | Reviewer | 当前状态 | 优先级 | 难度 | 完成 |
|---|------|----------|---------|--------|------|------|
| C1 | Near-capacity (C ≈ M*) latency-time curve: 展示 vLLM eviction cascade | R3 | 未做 | **P1** | Medium | [ ] |
| C2 | Memory usage vs time 曲线：对比 WAIT (stable) vs vLLM (spike → eviction) | R3 | 未做 | **P2** | Medium | [ ] |

## D. 可选增强实验

| # | 任务 | Reviewer | 当前状态 | 优先级 | 难度 | 完成 |
|---|------|----------|---------|--------|------|------|
| D1 | 真实 GPU (A100) 验证：simulated vs real processing time 对比 | R2 | 未做 | **P3** | Large | [ ] |
| D2 | Underloaded regime 实验：展示 stable 时 throughput = arrival rate | R3 | 未做 | **P3** | Medium | [ ] |
| D3 | WAIT-CP (chunked prefill) 结果整合到论文 | 自身 | revision branch 已有数据 | **P3** | Medium | [ ] |

## E. 文本修改（实验相关）

| # | 任务 | 来源 | 当前状态 | 优先级 | 难度 | 完成 |
|---|------|------|---------|--------|------|------|
| E1 | 实验节开头添加参数总表 (Table) | R2 | 缺失 | **P1** | 1hr | [ ] |
| E2 | 讨论 unstable regime 的合理性 + 新增 stable regime 对比 | R3 | 缺失 | **P1** | 30min | [ ] |
| E3 | 解释为什么 throughput 差异 = stability region 差异 | R3 | 缺失 | **P1** | 20min | [ ] |

---

## F. 一致性修复（非实验）

| # | 任务 | 来源 | 优先级 | 完成 |
|---|------|------|--------|------|
| F1 | 修复 broken cross-refs: `\ref{sec:numerical}` → `\ref{sec:experiments}` 等 5+ 处 | Pipeline | **P1** | [ ] |
| F2 | 添加 ΔT, θ_k, p_k 到 notation Table 1 (model.tex) | Pipeline | **P1** | [ ] |
| F3 | 标准化 appendix label 前缀 (统一为 `appendix:`) | Pipeline | **P2** | [ ] |
| F4 | AI 痕迹: "leveraging" (pf_thm_wait.tex), "promising direction" (conclusion.tex) | Pipeline | **P3** | [ ] |

---

## 建议执行顺序

1. **A1** (模型名统一) — 立刻可做
2. **B1-B4** (mean latency vs arrival rate) — **最关键**，需要跑模拟
3. **A2-A4, E1** (参数表) — 跑实验时同步整理
4. **F1-F2** (cross-ref + 符号) — 快速修复
5. **C1-C2** (near-boundary) — 用 B 的数据即可提取
6. **E2-E3** (文本补充) — 有数据后写
7. **D1-D3** (可选) — 视时间而定

---

## Reviewer 原文引用

### R3 关于 mean latency vs arrival rate (最关键)
> "A more meaningful comparison would show, for example, infinite(-or-long-enough)-horizon mean latency as a function of arrival rate, which is a standard type of plot in queueing theory. (This would also show the stability region: policies with lower maximum throughput would have mean latency diverge to infinity at lower arrival rates.)"

### R2 关于参数设置
> "Section 6.1: batch size B, memory bound M*, capacity C — 当 n_1 = n_2 = n_3 = 1 时, B ≥ 600?"
> "Section 6.2: n_1, ..., n_10 的具体值"

### R3 关于 unstable regime
> "All of the simulations in Section 6 appear to be in regimes where the systems are unstable... Testing an unstable regime is appropriate for drawing out throughput differences... But it is not especially meaningful for latency."
