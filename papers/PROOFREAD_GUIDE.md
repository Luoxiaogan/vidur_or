# Proofread Guide — OPRE-2025-04-1885

**配套文档**: `REVISION_PLAN.md`（顶层规划）, `REVISION_CHECKLIST.md`（行动清单）
**原始 AI 审查报告**: `review_ai_traces.md`（逐文件具体项目）

> 本文档给出**全局**写作打磨原则与可执行 checklist。具体到某一节/某一段的打磨在 `review_ai_traces.md` 已列，本文档提供统一的标准和 workflow。

---

## 1. 核心原则（来自 AE / Reviewer 3）

AE 明确指出：
> "the quality of exposition is very significantly below expectations"
> "if these issues persist, I expect that the paper will be rejected"

写作打磨**不是可选项**。Phase B 的目标：让 Reviewer 读起来像一篇被认真对待的 OR 论文，而不是"深度 + AI 辅助"的混合产物。

---

## 1.5 Author conventions（session 反馈沉淀）

以下规则来自作者在 polish session 中反复强调的偏好，**每次 polish 前必须 check 一遍**，避免重复讨论。

### 1.5.1 Abstract 规则

- **单段**，不分段（OR/INFORMS 期刊惯例）
- **不使用任何强调**：无 `\textbf{}` / `\emph{}` / `\textit{}`（OR abstract 纯文本）
- **开场必须带 importance 信号**：经济规模、GPU cost 数量级、或 production 部署痕迹
- **必须为 OR/OM reader 定义 LLM 术语**：
  - "inference" 首次出现时要写成 "running inference, the process of generating a response token by token"
  - "KV cache" 展开为 "the intermediate attention state reused across output tokens"
- **必须显式提到 unknown output → cascade**：unknown output 场景下 naive policy 触发 cascading eviction 是 paper 的 core risk
- **baseline 必须上下文化**：vLLM / Sarathi 第一次出现要带 "two widely used open-source LLM inference servers"（不能裸引）
- **长度 target**：250–320 词。覆盖 importance + problem + algorithm + theory + experiments 全部内容

### 1.5.2 核心 framing 词汇

以下是作者钦定的 **named concept**，revision 全文应反复出现、风格一致：

| 概念 | 必须使用 | 避免 |
|---|---|---|
| 我们优化的吞吐 | **effective throughput**（the completion rate net of evictions） | 裸 "throughput"——R3 会打回 |
| latency advantage 范围 | **across underloaded, near-capacity, and overloaded regimes** | "near the boundary" 单一 regime |
| 算法技术内核 | **dimensionality reduction**（算法带来的 tractability） | 藏在 proof detail 里 |
| 两个 tractability 轴 | across types（decouple types）+ within each type（discrete-time recursion） | 单一轴 |
| 稳定性框架 | **stability region**, **long-horizon regime**, **equilibrium** | "heavy traffic", "stable" 裸用 |
| 算法和 fluid 关系 | **approaching load balance** / **near the fluid equilibrium** | "close to optimal" |
| **M\*** 的定义 | **the equilibrium memory level required for stability at the boundary of the stability region** | ❌ "throughput-optimal memory level" — open system 里 throughput = arrival rate，更多 memory 不会优化 throughput。M\* 是 sustain stability 的 memory 下限，不是 optimize throughput 的 memory 选择。 |
| 容量充分但不稳定 | "capacity is **theoretically sufficient for stability**" | "otherwise feasible system"（"feasible" 在 queueing 里歧义）|
| FCFS cascade 数字 | 一般叙述用 **"by as much as 20%"**；具体 example 中 derivation 的 25% 可保留 | "12–25%"（看着像随便写的范围；实际是 derivation 的上下界，但写成 "by as much as 20%" 更谨慎）|
| 内存术语 | **memory consumption**（动态量，"grows during decoding"）/ **memory level $M^*$**（静态值）| ❌ "memory footprint"（systems-CS 词汇，OR 读者不熟） |

### 1.5.3 Framing 禁忌（defensive writing）

R3 对 paper novelty 有批评，但 response 不能**防御性写作**。以下句式被作者明确否决：

- ❌ **"not X, but Y"** 句式 —— 暗示我们在和隐藏 reviewer 吵架
- ❌ **"The key technical contribution is..."** —— Rule 4 meta-discourse，announce novelty 而非陈述
- ❌ **"standard coupling analysis / standard queueing analysis"** —— 把自己工具贬低，反而让 reviewer 觉得 paper novelty 弱
- ❌ **"this reduced system" / "on the reduction"**（被动语气）—— 让简化听起来像天然存在的，掩盖了算法的贡献
- ❌ **"bridges X and Y" / "provides a theoretically grounded framework"** —— AI 套话

**正确做法**：
- 直接陈述算法做了什么（active verb："decouples", "replaces", "performs a dimensionality reduction"）
- 结论用 declarative 句式（"Both algorithms are asymptotically optimal."）
- 不解释 novelty 是什么，让动词和结构自己承担 novelty 重量
- **Give the reader credit**——不要怕读者看不懂 novelty

### 1.5.4 OR/OM 语言 vs CS 语言

作者明确要求向 OR/OM 读者倾斜。审稿人是 queueing theorist，不是 ML engineer。

| CS-flavored | OR/OM-flavored |
|---|---|
| "high-performance inference engine" | "open-source LLM inference server" |
| "on-the-fly" | "during execution" / "at segment boundaries" |
| "engineering solutions" | （在 literature review 里可保留） |
| "GPU memory" without context | "KV cache memory" with capacity constraint |
| "throughput" 单独 | **effective throughput** or "maximum sustainable arrival rate" |
| "we propose" (CS) | "we study" / "we analyze" / "we characterize" (OR) |
| "memory footprint" | "memory consumption" / "memory level" |
| "delineate the stability region" | "identify the stability region" / "characterize the stability region" |
| "throughput-optimal memory $M^*$" | "equilibrium memory level $M^*$ required for stability" |
| "optimal 4 completions" / "optimal throughput" 泛指 | "the 4 completions sustained at the fluid equilibrium" / formal $\text{Throughput}^*$ 数学符号保留 |

### 1.5.5 Workflow rules（作者反复强调）

- **"每进行一点就跟我讨论"**：每次提议修改**先给 diff/drafts**，不要直接 apply。重要段落尤其如此。
- **Context vs apply**：研究 / 规划（如下载参考 paper、建索引）可以直接执行；**字面修改 intro/abstract/contribution 段需先得到 OK**
- **不要叠加复杂 edit**：一轮 polish 1–3 个 surgical edits 即可，避免一次改太多看不清
- **一直调用 `/polish-paper`**：不仅 mandate 跑 advisor 规则，也作为**每轮的 checkpoint**

---

## 2. 必须消除的 AI 痕迹

### 2.1 高频词/短语黑名单

| 套话 | 替换 |
|---|---|
| "key insight" / "central insight" / "key observation" | 直接陈述该 insight，或用 "We find that..." / "This shows..." |
| "bridges X and Y" | 直接 "applies X to Y" / "combines X with Y" |
| "theoretically grounded framework" | 直接描述 framework 本身 |
| "indispensable" | "essential" / "fundamental" / "has become standard in" |
| "pivotal" / "paramount" | "important" / 具体说明重要性 |
| "important avenue for future research" | 具体写下一步做什么、为什么现在做不了 |
| "promising direction" | 同上 |
| "poses a significant challenge" | 具体说 challenge 是什么 |
| "paves the way for" | 具体说 enable 了什么 |
| "In this paper, we propose..." 开头 | 先讲 motivation，再 propose |
| "It is worth noting that" / "It should be emphasized that" | 直接说 |
| "In particular" / "Furthermore" 过度使用 | 删掉或换连接词 |

### 2.2 AI 句式特征（整段替换）

- **三段式排比**："First X. Second Y. Third Z."（过度对称）→ 自然段落
- **"not only...but also"** 过度使用 → 拆成两句
- **每段以总结句收尾** → 不是所有段都需要总结
- **列表 + emoji** → 学术写作不用 emoji
- **过度强调 novelty 的形容词**："novel", "innovative", "groundbreaking" → 具体说明差异
- **"to the best of our knowledge"** → 谨慎使用（只在真有把握时）

---

## 3. OR 期刊写作规范（AE 隐含要求）

### 3.1 段落结构
- **每段有 topic sentence** 说明段落功能
- **从直觉到严格**：定义/定理前先给 intuition，再形式化
- **数学与文字平衡**：连续两个公式之间必须有文字解释
- **具体例子支撑抽象概念**：FCFS cascading failure 是好例子（已用），各 Remark 之后考虑是否需要

### 3.2 证明呈现（Reviewer 3 / AE 特别强调）
- **不要从 first principles 证明已知结果**（如用 Cauchy-Schwarz 证明 random walk 性质）→ 引用标准文献（Asmussen 2003, Kingman, Doob）
- **主文提供 proof sketch**，把核心 idea 说清楚；细节 appendix
- **Appendix 证明不是 "deposit box"**：每个 lemma/theorem 之前有"为什么要证这个"的 motivation 段落
- **Knife-edge case (zero drift)** 引用标准结果（reflecting random walk: O(1) under negative drift, O(√T) at zero drift），不要从头证

### 3.3 Narrative 一致性
- "heavy traffic" → **"asymptotic regime"**（全局替换，检查有无遗漏）
- "throughput optimization" → **"maximum throughput / stability region"**（Reviewer 3 要求）
- "positive recurrence" 单独出现时要加 context（不是"显然"的陈述）

---

## 4. 符号 / 术语一致性 Sweep

### 4.1 符号检查（见 `model.tex` Table 1 为 ground truth）
- [ ] `s` 作为 stage index（不是 `k`）——全局搜索 `stage $k$`
- [ ] `l_j` / `l_j'` 含义一致
- [ ] `n_j` 和 `n_{js}` 的区别（per-type vs per-stage threshold）
- [ ] `M*` / `M^π` / `C` 出现时定义清晰
- [ ] `π` / `Π` 只在 `model.tex` §2.5 定义一次
- [ ] `ΔT`, `θ_k`, `p_k` 进 Table 1

### 4.2 模型名称
- [ ] "Llama-7B" vs "Llama2-7B" vs "Llama-2-7B" 全局统一（建议 "Llama-2-7B"）
- [ ] "Vidur" 大小写统一
- [ ] "Sarathi-Serve" vs "Sarathi"

### 4.3 Cross-references
- [ ] 所有 `\ref{}` / `\eqref{}` 解析成功（`\ref{??}` 搜索）
- [ ] 图表 label 与 caption 对应
- [ ] Appendix section 号在主文引用处正确

---

## 5. 文件级重点（补充 `review_ai_traces.md`）

### `abstract.tex`
- 第一句不要用 "Large Language Models (LLMs)..." 这种 AI 开场
- 具体说 paper 解决什么问题、用什么方法、结论是什么
- 避免"bridges operations research and machine learning"式自我夸赞

### `introduction.tex`
- 删除 "indispensable" / "revolutionary" 类强词
- 第一段**直接进入 memory constraint 问题**（不要先综述 LLM）
- FCFS cascading failure 例子保留，是好的具体化手段
- "Our contribution" 段落避免列表堆砌，用段落叙述

### `fluid.tex`
- 每个公式**后面**跟一两句物理解释（Reviewer 3 批评过这里）
- Eq(4) / Eq(8) 的 throughput 公式：加一句"in an open system, throughput = arrival rate when stable"（Reviewer 3 的点）

### `known_type.tex` / `unknown_type.tex`
- Algorithm 1/2 之后的解释段落是否够清楚
- "dimensionality reduction" 这个说法要在主文出现至少一次（而不仅在证明 sketch）

### `conclusion.tex`
- 删除八股文："important avenue" / "promising direction" / "poses a challenge"
- 具体写：哪些 assumption 还没松、下一步哪个实验最紧迫、PD 分离的 full system analysis 等

### 证明 appendix
- Lemma 前加 1-2 句 "proof idea"（已部分完成）
- 使用 `Asmussen 2003` / `Kingman` / `Doob` 等 citation 替代从头证
- Zero-drift case 简化（AE 特别指出）

---

## 6. 打磨 Workflow

### 6.1 Session start（每次进入 polish session 必读）

1. **加载本 GUIDE 的 §1.5**（Author conventions）和 **§2/§3** 规则
2. **加载 `REVISION_PLAN.md` §2–§2.6**（核心 framing 论点和 R3 response）
3. **加载 `REVISION_CHECKLIST.md` 顶层 🔁 RECURRING CONSISTENCY SWEEP 区块**（18 条规则 + 一键 grep 命令）—— **这是每次进新 section 的第一件事**
4. **check 最近的 session 反馈**（`git log --oneline -20 papers/` 看最近改动）
5. **确认目标文件**（user 指定 vs 从 CHECKLIST 选 P0）

### 6.2 Per-file polish（每个 tex 文件执行）

1. **🔁 Recurring sweep first**：跑 `REVISION_CHECKLIST.md` 顶层区块的一键 grep 命令，过 18 条规则 → 清掉所有 false positive 以外的命中
2. **读一遍**，标记所有 §2.1/2.2 黑名单词汇和句式
3. **Pre-apply check**（avoid re-discussion）：对照 §1.5 Author conventions 逐条 verify
   - Abstract 是否单段 / 无强调 / 带 importance 开场 / 定义 inference / 提 cascade / 上下文化 baseline？
   - 是否用 "effective throughput" 而非裸 "throughput"？
   - Latency 是否写成 "across underloaded, near-capacity, and overloaded regimes"？
   - 有无 "not X, but Y" / "standard coupling" / "this reduced system" 等 defensive / 贬低句式？
   - 有无 "dimensionality reduction" 作为 named concept 显性化？
   - M\* 描述是否是 "equilibrium memory required for stability"（不是 "throughput-optimal memory"）？
4. **替换/删除** 套话；改写模板化句子
5. **检查** §3.1 段落结构：topic sentence、intuition-first、math-text 平衡
6. **符号/术语**：对照 §4 check
7. **编译**：确认 LaTeX 没有新 error / warning
8. **diff 检查**：`git diff` 看改动是否增加了新的 AI 痕迹（easy trap）
9. **Cross-ref**：检查引用是否 still valid
10. **Update sweep tracker**：在 `REVISION_CHECKLIST.md` 顶层 "Sections 已 swept" 里打 ✅

### 6.3 与 user 的交互规则（来自作者反馈）

- **提议优先于执行**：每轮 1–3 个 surgical edit，**先 draft + 规则 trigger 说明 → user 过目 → 再 apply**
  - 例外：pure grep-and-replace（em-dash sweep）、typo、引用修复等机械操作可直接执行
- **多 option 并列**：改写复杂段落时提 2–3 个 candidate，标注 trade-off（"confident" vs "compressed" vs "illustrative"）
- **用 `/polish-paper` 做 session checkpoint**：即便之前刚跑过，每隔 2-3 轮再 trigger 一次做 advisor 规则 sanity check
- **每轮结束 summarize**：哪些 edit / 触发哪条 rule / 剩余 issue / 下一轮建议焦点

---

## 7. 编辑过程中的常见陷阱

- ❌ **用 AI 润色 AI 痕迹** → 替换掉的"key insight"又被改成"central observation"
- ❌ **删除太激进** → 把 Reviewer 要求的内容也删了
- ❌ **只改表面词** → 句式仍然是 AI 的
- ❌ **破坏 LaTeX 结构** → 改完不编译
- ✅ **改完后读一遍** → 是否像一个人写的
- ✅ **用自己原来的 slides / notes 作为语言参考** → `llm_short.pdf` / CLAUDE.md 里的中文笔记 → 转英文

---

## 8. 打磨优先级

| 优先级 | 文件 | 理由 |
|---|---|---|
| **P0** | `abstract.tex`, `introduction.tex`, `conclusion.tex` | Reviewer 第一眼看的地方；AE 明确点名 |
| **P1** | `fluid.tex`, `known_type.tex`, `unknown_type.tex` | 理论主体；Reviewer 3 批评的呈现问题 |
| **P2** | `pf_*.tex`, `pf_lemmas.tex` | 证明 appendix（已部分打磨，需最终 pass） |
| **P3** | `extension.tex`, `related.tex`, `numerical.tex` | 相对轻量 |
| **P4** | `appendix_*.tex` | 新增内容，检查一致性即可 |

---

**Document Version**: v1.3
**Last Updated**: 2026-04-21 (evening)
**配套工具**: `review_ai_traces.md`（逐文件逐条具体问题）

---

## Changelog

- **v1.3 (2026-04-21 evening)**: §6.1 加入 "加载 REVISION_CHECKLIST 顶层 🔁 RECURRING CONSISTENCY SWEEP" 作为 session start 第 3 步；§6.2 加入 "🔁 Recurring sweep first" 作为 per-file polish 第 1 步 + "Update sweep tracker" 作为最后一步
- **v1.2 (2026-04-21)**: §1.5.2 新增 4 条 framing 词汇（M\* 定义、theoretically sufficient capacity、FCFS cascade 数字、memory consumption vs footprint）；§1.5.4 新增 4 条 CS→OR 替换（memory footprint、delineate、throughput-optimal memory、optimal N completions）。合并自 conclusion recap polish session。
- **v1.1 (2026-04-18)**: 新增 §1.5 Author conventions（session 反馈沉淀：abstract 规则、核心 framing 词汇、framing 禁忌、OR/OM 语言、workflow 规则），扩展 §6 workflow（session start + pre-apply check + 交互规则）
- **v1.0 (2026-04-17)**: 初稿
