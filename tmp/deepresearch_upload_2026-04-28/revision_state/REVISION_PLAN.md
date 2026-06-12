# Revision Plan — OPRE-2025-04-1885

**Paper**: Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints
**Decision**: Major Revision (AE: Prof. Neil Walton)
**AE warning**: "risky" major revision — 下一轮若问题未消化可能 reject
**Source documents**:
- `decision_letter.md` — AE 决定信 + Reviewer 3 全文
- `Review_OPRE-2025-04-1885.pdf` — Reviewer 1
- `Review_for__...__.pdf` — Reviewer 2
- `AE_report.pdf` — AE 综合报告

---

## 1. Reviewer 态度与核心诉求

| Reviewer | Tone | 主要 concern | 回应策略 |
|---|---|---|---|
| R1 | 🟡 中性 | 符号不一致、OOM 机制、线性假设 | 技术性修复（符号表 + Remark） |
| R2 | 🟢 Positive | Eq(1) 适用性、证明细节、实验参数 | 承认局限 + 详细 justify + 补参数 |
| R3 | 🔴 Negative | "heavy-traffic" 术语误用、贡献不显著、写作不清 | **重新 framing 贡献**（eviction prevention + dimensionality reduction） |

---

## 2. 核心论点（revision 全文的 narrative backbone）

（从 `archive/revision_summary_v2.md` §核心论点总结提炼，每处 revision 都应围绕这几条展开）

1. **Memory Constraint 是独特 challenge** — KV cache 动态增长 + eviction 风险，不是传统 queue
2. **Eviction Prevention 是核心创新** — FCFS 即使 C≥M* 也会因 cascading failure 变 unstable
3. **Threshold = Dimensionality Reduction** — 算法让问题变得可分析，不是问题本身简单；两个轴：
   - *Across types*: threshold 切断 multi-type 之间的 coupling
   - *Within each type*: stage-level threshold 把连续增长的 memory 化成离散时间 recursion
4. **Fluid Model 提供 framing** — equilibrium state + optimal memory M* + 算法设计目标是"逼近 equilibrium"
5. **On-the-fly Classification** — Nested WAIT 不需要预测 output length，segment 边界自然分类
6. **PD 分离直接适用** — decode-only 端 Eq(1) 线性假设完全成立
7. **Asymptotic Regime（不是 Heavy Traffic）** — 固定 load 下 scale 时间 horizon，术语已全局替换
8. **贡献是 modeling + algorithm design，不是 math novelty** — AE 认可 "establishing connection to standard stochastic model is significant"

### 2.5 回应 R3 的 framing 增补（2026-04-18 / 2026-04-21 新增）

这几条是 intro/abstract polish session 中明确 anchor 进正文的 framing，configure 了 R3 的每条攻击：

9. **Effective throughput（not throughput）** — 在 eviction 存在时 throughput 和 effective throughput 不同。R3 (1)(c) 的 "throughput = arrival rate" 评论只在裸 throughput 上成立；**effective throughput = completion rate net of evictions**，naive policy 可以让这个值远小于 arrival rate。Paper 全局用这个术语
10. **三-regime latency advantage** — Latency 优于 baseline **across underloaded / near-capacity / overloaded 三个 regime**，不是只在 near-boundary。这直接回应 R3 "unstable regime latency 没意义" 的批评：underloaded 下我们也更快，说明 advantage 不是 trivial 的 "throughput → latency"，而是 load balance 本身带来的
11. **Importance motivation 必须在 abstract/intro 首句** — OR/OM reader 不知道 LLM inference 是什么，也不会 a priori 觉得这是重要问题。开头必须给出 economic scale signal（e.g. "$700K/day"）+ 定义 inference = "generating a response token by token"
12. **Unknown output 下的 cascade 要明示** — Unknown output length 是导致 eviction cascade 的 key amplifier，必须在 abstract 和 intro 里显性提
13. **M\* 是 "维持 stability 的 memory 下限"，不是 "throughput-optimal memory"** — open system 里 throughput = arrival rate（when stable），更多 memory 不会提高 throughput。M\* 是 fluid 均衡下 sustain stability region boundary 所需的 memory level。描述 M\* 时统一使用 **"the equilibrium memory level required for stability at the boundary of the stability region"** 或等价表述，**避免 "throughput-optimal memory"** 这种让人误解算法在 optimize memory 的 wording
14. **"Theoretically sufficient capacity" 作统一措辞** — FCFS cascade example 的核心是 "capacity 看似够但实际系统 crash"。全文用 **"a system whose capacity is theoretically sufficient for stability"** 这个固定短语，避免 "otherwise feasible"（"feasible" 在 queueing 里歧义）
15. **Memory 术语 consumption vs level** — 动态增长的量用 **"memory consumption"**；具体 steady-state 值用 **"memory level $M^*$"**；**不用 "memory footprint"**（CS jargon）

### 2.6 写作风格约束（作者偏好）

详细见 `PROOFREAD_GUIDE.md` §1.5。高层 3 条：

- **Abstract**：单段 / 无强调 / 250–320 词 / baseline 要上下文化
- **Framing**：不用 "not X, but Y" 防御句式；不用 "standard coupling" 贬低自己；"dimensionality reduction" 作 named concept 展示
- **OR/OM 词汇**："effective throughput", "stability region", "long-horizon regime", "fluid equilibrium" > CS jargon

---

## 3. 文件级 revision 状态

（粗粒度；细节见 `REVISION_CHECKLIST.md`）

| 文件 | 主要修改 | 状态 |
|---|---|---|
| `abstract.tex` | OR-style opener + effective throughput + M\* framing | ✅ **converged** (2026-04-21) |
| `introduction.tex` | Eviction framing, three-regime latency, dimensionality reduction, M\* framing, footprint sweep | ✅ **converged** (2026-04-21) |
| `model.tex` | Table 1 符号表, Π 正式定义, Eq(1) Remark, OOM 机制；FCFS cascade 数字 + effective throughput 已对齐 | ⚠️ 主体完成，剩余 footprint 术语 sweep + 个别段落可打磨 |
| `fluid.tex` | 符号统一 (k→s), 公式修正 (d₀→d₁), 物理解释 | ⚠️ 公式细节 5-8 处待核对；M\* 措辞一致 |
| `known_type.tex` | FCFS cascading example, proof sketch, PD disaggregation；effective throughput + 25% 数字已对齐 | ✅ 主体完成，少量段落打磨 |
| `unknown_type.tex` | On-the-fly classification, safety buffer 解释 | ✅ 完成 |
| `extension.tex` | Segment-wise Nested WAIT | ✅ 完成 |
| `numerical.tex` → `numerical_v2.tex` | 整节重写：Fig A/B/C/D/E + §6.1/§6.2 | ⚠️ 需 merge 回 numerical.tex |
| `conclusion.tex` | 按 Zhou/Jasin 范文风格重写：recap + First/Second/Finally 枚举，MoE+multi-GPU 合并段 | ✅ **converged** (2026-04-21) |
| `related.tex` | Zhou 系列 + PD 分离引用 | ✅ 完成 |
| `pf_thm_wait.tex` / `pf_thm_nested.tex` / `pf_thm_timevarying.tex` / `pf_lemmas.tex` | 证明 sketch + 直觉段落 + martingale 动机 | ✅ 完成，需 R2 细项核对 |
| `appendix_sim_fidelity.tex` | Reviewer 2 GPU 验证 | ✅ 完成 |
| `appendix_b_additional.tex` | Long decode, PD, SGLang, multi-seed, wait-vs-nowait | ⚠️ wait-vs-nowait 叙述待 VM 实验更新 |

---

## 4. Revision 三阶段

### Phase A — 结构与内容修复（大部分已完成）
- Reviewer 1/2 的技术性 comments
- Section 6 整节重写（响应 R3 的 latency vs rate 要求）
- GPU 验证（响应 R2 对 Vidur fidelity 的质疑）

### Phase B — 写作打磨（**当前焦点**）
- AI 痕迹、套话、"key insight" 泛滥
- 符号/术语一致性全局 sweep
- 证明呈现：连接到标准文献，避免 first principles 证明已知结果
- 详细指南见 `PROOFREAD_GUIDE.md`

### Phase C — Response Letter 收尾
- 整理 `response_letter_draft.md`（给审稿人的回信，不包含内部修改日志）
- Cover letter + point-by-point response

---

## 5. 关键外部资产

- `experiments.db` — SQLite，所有实验数据
- `outputs/validation_database/` — GPU 验证 (Reviewer 2)
- `docs/progress/` — 实验 session 记录（保留不归档，供查阅）
- `docs/research/` — 参数语义 + 研究笔记（保留）
- `docs/claude_code_context/` — 操作指南（保留）

---

**Document Version**: v1.2
**Last Updated**: 2026-04-21
**Owner**: Revision 规划总览

---

## Changelog

- **v1.2 (2026-04-21)**: §2.5 新增 3 条 framing（#13 M\* 是 stability 所需 memory 下限、#14 "theoretically sufficient capacity" 统一措辞、#15 memory consumption vs level）；§3 更新文件状态：abstract/intro/conclusion 均 converged，known_type/model 主体完成。合并自 conclusion recap polish session
- **v1.1 (2026-04-18)**: 新增 §2.5（R3 response framing：effective throughput / 三-regime latency / importance motivation / unknown output cascade）和 §2.6（作者写作风格约束速查）
- **v1.0 (2026-04-17)**: 初稿
