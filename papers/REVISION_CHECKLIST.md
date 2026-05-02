# Revision Checklist — OPRE-2025-04-1885

**配套文档**: `REVISION_PLAN.md`（顶层规划）, `PROOFREAD_GUIDE.md`（写作打磨指导）
**状态约定**: ✅ 完成 / ⚠️ 部分完成 / ❌ 未开始 / 🔄 进行中

---

## 🔁 RECURRING CONSISTENCY SWEEP（每次进新 section 前必 revoke）

**用法**：每次开始一个新 section 的 polish（或新增内容落盘前），对该文件跑一遍下面的 grep 扫描 + 逐条过规则。

```bash
# 一键扫描（在 papers/ 目录）
grep -nE "memory footprint|throughput-optimal|otherwise feasible|fluid dynamics|key insight|central insight|fundamental insight|---|delineate|Llama-7B|Llama-13B|Llama2-7B|heavy.traffic|\b12.?25%|standard (coupling|queueing) analysis|not .{1,30}, but" <section>.tex
```

| # | ❌ 错误 pattern | ✅ 正确写法 / 原则 | 来源 |
|---|---|---|---|
| 1 | `memory footprint` | "memory consumption"（动态量）/ "memory level $M^*$"（静态值）| User 2026-04-21: OR 读者不熟 CS jargon |
| 2 | `throughput-optimal memory $M^*$` | "equilibrium memory $M^*$ required for stability (at the boundary of the stability region)" | User 2026-04-21: open system 里更多 memory 不会 optimize throughput |
| 3 | `otherwise feasible system` | "a system whose capacity is theoretically sufficient for stability" | User 2026-04-21: "feasible" 在 queueing 里歧义 |
| 4 | `fluid dynamics` (body text) | "fluid model" / "fluid approximation" / "fluid analysis" | User 2026-04-21: 和主文一致 |
| 5 | `key insight` / `central insight` / `fundamental insight` | 删除或换为 "principle" / 直接陈述 | Rule 4 (meta-discourse), PROOFREAD_GUIDE §2.1 |
| 6 | em-dash `---` | 换成 `,` / `:` / `.` / `()` | Rule 12, AI writing signal |
| 7 | `not X, but Y` defensive | 直接正面陈述算法做了什么 | User 2026-04-18: 不和 reviewer 吵架 |
| 8 | `standard coupling analysis` / `standard queueing analysis`（自褒贬义时） | 描述工具做了什么，不贴 "standard" 标签 | User 2026-04-20: 不贬低自己工具 |
| 9 | `delineate` | "identify" / "characterize" / 省略 | User 2026-04-21: 不常用词 |
| 10 | `Llama-7B` / `Llama-13B` / `Llama2-7B` | `Llama-2-7B` / `Llama-2-13B` | P3 consistency |
| 11 | `heavy traffic` / `heavy-traffic` (body text; label names OK) | "asymptotic regime" / "long-horizon regime" | R3 (1)(a) objection |
| 12 | 裸 `throughput` 在 narrative prose | "effective throughput"（首次使用附定义 "the completion rate net of evictions"）| User 2026-04-20: eviction 让 throughput 和 effective throughput 不同 |
| 13 | `12-25%` / `12--25%` FCFS cascade 数字 | 一般叙述："by as much as 20%"；derivation-specific 可保留 25% | User 2026-04-21: 12-25% 看着像随便写的 |
| 14 | abstract 里 `\textbf{}` / `\emph{}` | OR abstract 纯文本 | User 2026-04-20: INFORMS 惯例 |
| 15 | single-regime latency 叙述（只提 near-boundary）| "across the underloaded, near-capacity, and overloaded regimes" | User 2026-04-18: 回应 R3 "unstable latency 没意义" |
| 16 | "this reduced system" / "the reduction (as if natural)" | active voice："the algorithm reduces X to Y" | User 2026-04-20: 不让 reduction 听起来天然存在 |
| 17 | M\* 裸用不解释 | 首次使用时：描述 + equation ref + "required for stability at the boundary of the stability region" | PROOFREAD_GUIDE §1.5.2 |
| 18 | `\throughput^*` 在 narrative 裸用 | narrative 用 "effective throughput"；formal theorem 才用数学符号 | User 2026-04-21 |

**Sweep protocol**:

1. `cd papers/ && grep -nE "..." section.tex` — 跑上面的 grep
2. 逐条过 18 条规则，flag false positive（如 label names、数学符号上下文）
3. 应用修改，**每个 edit 标注触发规则编号**
4. Re-run grep 确认清零
5. Update this checklist section entry marker（e.g. "fluid.tex [consistency sweep 2026-04-21 ✅]"）

**Sections 已 swept**:
- [x] `abstract.tex` (2026-04-20/21)
- [x] `introduction.tex` **including §Other Related Work L63-71 polish 2nd pass** (2026-04-21 late evening)
- [x] `conclusion.tex` (2026-04-21)
- [x] `model.tex` (2026-04-21)
- [x] `fluid.tex` (2026-04-21)
- [x] `known_type.tex` (2026-04-21)
- [x] `unknown_type.tex` (2026-04-21)
- [x] `extension.tex` (2026-04-21)
- [x] `pf_thm_wait.tex` (2026-04-21)
- [x] `numerical.tex` (2026-04-21 evening) — merged from numerical_v2.tex, full sweep clean
- [x] `appendix_sim_fidelity.tex` (2026-04-07, GPU validation)
- [x] `appendix_b_additional.tex` (2026-04-17)
- [x] `pf_thm_nested.tex` (2026-04-21 evening) — 2 hits 都是 label names (`thm:nested_wait_heavy_traffic`), 不 render, body clean
- [x] `pf_thm_timevarying.tex` (2026-04-21 evening) — 3 hits 都是 label refs, 不 render, body clean
- [x] `pf_lemmas.tex` (2026-04-21 evening) — 0 hits ✅
- [x] `Appendix.tex` (2026-04-21 evening) — 16 hits 全部 `% ---` 注释分隔符, body text 全 clean（M\* consistently "equilibrium memory"; throughput uses `\throughput^*` 数学符号）
- N/A `related.tex` — 文件是空的，related work 在 `introduction.tex` §Other Related Work（已 swept）
- [ ] `response_letter_draft.md`（未来）— 写成时 sweep

---

## P0 — 必须闭环的项目

### P0.1 Reviewer 3 回应的 framing 一致性
- [x] 全文检查 "heavy traffic" 残留，统一为 "asymptotic regime" (2026-04-18)
- [x] 检查 throughput narrative 是否统一为 "effective throughput / stability region" (2026-04-21)
- [x] 证明 sketch 明确强调：不是 heavy-traffic novelty，是 eviction prevention + dimensionality reduction (2026-04-20)
- [x] M\* 描述统一为 "equilibrium memory required for stability"（消除 "throughput-optimal memory" 误导）(2026-04-21)

### P0.2 写作质量全局打磨（见 `PROOFREAD_GUIDE.md`）
- [x] Abstract 集中润色 (2026-04-20, converged)
- [x] Introduction 集中润色 (2026-04-21, converged — 4 轮 polish)
- [x] Conclusion 集中润色 (2026-04-21, converged — 按 Zhou/Jasin 范文风格重写)
- [ ] AI 套话清理（`review_ai_traces.md` 列出的所有项）(剩余：fluid.tex / known_type.tex 次要段落)
- [ ] "key insight" 重复使用消除 (剩余：theory 章节)

### P0.3 numerical.tex 合并
- [x] `numerical_v2.tex` merge 回 `numerical.tex` (2026-04-21 evening) — v2 内容完整覆盖，原 `numerical.tex` 备份至 `archive/numerical_tex_original_preMerge.tex.bak`，`numerical_v2.tex` 移至 `archive/numerical_v2.tex`
- [x] 9 个 internal labels 全部唯一；8 个 external refs（alg:nested_wait, alg:wait, app:sim_fidelity, eq:nested_wait_thresholds, eq:time_consump, eq:wait_thresholds, fig:sim_fidelity, thm:nested_wait_heavy_traffic）在 active paper 各有恰好 1 次定义 ✅
- [x] Consistency sweep：body clean (仅 label names hit); Llama-2-7B consistent; 无 em-dash / key insight / footprint
- [x] Appendix A (sim fidelity) 和 Appendix B (additional experiments) 已 `\input` 进 `Appendix.tex`（2026-04-21 evening）—— LLM_or.tex 通过 `\input{Appendix}` 链式加载。Labels `app:sim_fidelity`, `app:pd_disagg`, `app:no_wait`, `app:sglang`, `app:additional_experiments` 全部 resolve

### P0.4 Appendix B §Threshold without waiting 叙述 + GPU 实验整合
- [x] VM 实验完成 (2026-04-21 GPU lmsys real-trace, native SGLang)
- [x] **GPU 内容统一 wrap 进新 §app:gpu_validation**（取代旧 §app:sglang），3 段：
  - Simulator vs GPU（迁自 appendix_sim_fidelity）
  - Single-type GPU sweep (λ=1-15, mirror §6.1, +29.7% mean)
  - Real-data GPU sweep (λ=0.1-0.7 lmsys, mirror §6.2, peak +9.2% at λ=0.4)
- [x] **Table~\ref{tab:sglang_realtrace} 去 wait_gate column**，只保留 (λ, TL, improvement)
- [x] **appendix_sim_fidelity 不再单独输入**；supplemental experiments 统一放入 §app:additional_experiments，sim validation 内容已迁出
- [x] §app:no_wait conclusion 软化为 "regime-dependent"，cross-ref 新 §app:gpu_validation
- [x] numerical.tex cross-refs 更新到 app:gpu_validation 或 app:additional_experiments
- [x] Active app labels resolve（gpu_validation / long_decode / multi_seed / no_wait / pd_disagg / additional_experiments）

### P0.5 Footprint / delineate 术语 sweep（2026-04-21）
- [x] abstract/intro/conclusion: "memory footprint" → "memory consumption / memory level" (2026-04-21)
- [x] abstract/intro/conclusion: "delineate" → 更简单动词 or 省略 (2026-04-21)
- [x] model.tex (3 处)、fluid.tex (1 处)、unknown_type.tex (1 处)、numerical_v2.tex (1 处) 全清 (2026-04-21)

### P0.6 Active paper 全文 consistency sweep（2026-04-21 完成）
- [x] **em-dash** (Rule 12)：abstract/intro/model/fluid/known_type/unknown_type/extension/conclusion/pf_thm_wait 全部清零
- [x] **"key insight" / "central insight" 套话**：model.tex L114、known_type.tex L44+L172、extension.tex L9、pf_thm_wait.tex L23 全部清除
- [x] **"fluid dynamics" → "fluid model"**：fluid.tex 章节标题 + known_type.tex 2 处
- [x] **"not X, but Y" defensive framing**：known_type.tex L44+L172、pf_thm_wait.tex L23 全部清除
- [x] **"standard queueing analysis" undersell**：known_type.tex L44 改为 "classical drift analysis"（反义表达 OK），L172 的 "apply standard techniques" 改为 "Lindley-style drift analysis"
- [x] **M\* 描述全文一致**：均为 "equilibrium memory (required for stability)"，无 "throughput-optimal memory"
- [x] **Effective throughput + 20% 数字一致**：intro L34、model.tex L154、known_type.tex L34（25% 为 derivation-specific）
- [x] **Llama naming 全文统一**：model.tex L110 figure caption + L119 → "Llama-2-7B and Llama-2-13B"（用户确认实验用的是 Llama 2）(2026-04-21 pm)

---

## P1 — Reviewer 2 公式细项核对

（来自 `archive/revision_summary_v2.md` §VII 和 §公式核实清单，逐条在 tex 中核对）

- [ ] Page 9, line 50: `d` → `d_1`?
- [ ] Page 17, line 37: M* 在 Eq.(9) 中的位置
- [ ] Eq.(5) 后的公式：右边应与 Eq.(2) 一致（Reviewer 3 指出）
- [ ] Page 12, line 30: "requires" → "at least requires"
- [ ] Page 39, line 40: "type 2 with l_2 = 1" 上下文核实
- [ ] Page 39, Prop 4 proof: 澄清为什么 "equilibrium batch" 是 optimal
- [ ] Page 41, Lemma 1: 从 main problem 到 lemma setting 的 reduction
- [ ] Page 43, line 36: M^π = M* 核实
- [ ] Page 44, line 14: W_t 和 W̃_t 在 events 之间的定义
- [ ] Page 44, line 18 (Appendix E.3): Reviewer 建议的 alternative proof（考虑）

---

## P2 — 文件级写作打磨

（按写作需要的深度排序；细则见 `PROOFREAD_GUIDE.md`）

### 主体章节
- [x] `abstract.tex` — OR-style opener + effective throughput + M\* framing ✅ converged (2026-04-21)
- [x] `introduction.tex` — Three-regime latency + dimensionality reduction + footprint sweep ✅ converged (2026-04-21)
- [x] `model.tex` — Consistency sweep 完成（footprint / key insight / em-dash / 20% 数字 / Llama 名称 flagged）⚠️ 剩余段落可打磨，主体 consistent (2026-04-21)
- [x] `fluid.tex` — Consistency sweep 完成（章节标题 fluid model / 多处 em-dash / footprint）⚠️ Reviewer 3 要求的公式后物理解释待增补
- [x] `known_type.tex` — Consistency sweep 完成（key insight 清除 / defensive 清除 / fluid dynamics→fluid model / em-dash / 25% 数字）
- [x] `unknown_type.tex` — Consistency sweep 完成（footprint / em-dash）
- [x] `extension.tex` — Consistency sweep 完成（key insight 清除）
- [ ] `numerical.tex` — merge 后的 narrative 流畅性
- [x] `conclusion.tex` — Zhou/Jasin 范文风格重写 ✅ converged (2026-04-21)
- [x] `pf_thm_wait.tex` — Consistency sweep 完成（key insight 清除 / defensive "not X" 清除 / em-dash）

### 证明 Appendix
- [ ] `pf_thm_wait.tex` — 整体 structure 和 transition
- [ ] `pf_thm_nested.tex` — martingale 动机段落
- [ ] `pf_thm_timevarying.tex` — worst-case domination 解释
- [ ] `pf_lemmas.tex` — Lemma 5 (martingale solution) 可读性

### 新 Appendix
- [ ] `appendix_sim_fidelity.tex` — GPU 验证报告整合
- [ ] `appendix_b_additional.tex` — 等 wait-vs-nowait 更新

---

## P3 — 一致性与 typo sweep

- [ ] 模型名称：Llama-7B vs Llama2-7B 全局统一
- [ ] 5+ broken cross-references 检查（Reviewer 1 提到）
- [ ] Table 1 是否包含所有符号：ΔT, θ_k, p_k 等
- [ ] `archive/revision_summary_v2.md` §VII.2 列出的具体 typos 全部清零
  - [ ] Page 9 line 50: `d` → `d_1`
  - [ ] Page 35 line 4: "Asmussen S, Asmussen S, Asmussen S" 去重
  - [ ] Page 39 line 38: ".Consider" → ". Consider"
  - [ ] LLM_or.tex line 125: "Thoughput" → "Throughput"

---

## P4 — Response Letter

- [ ] 从 `archive/response_draft_v2.md` 抽取 point-by-point 回应文本
- [ ] 写入 `response_letter_draft.md`
- [ ] 剥离内部修改日志（保留在 archive）
- [ ] Cover letter
- [ ] 对 Reviewer 3 的特别处理段落（重新 framing，不 defensive）

---

## 已完成归档（参考用，不再 action）

（完整日志见 `archive/revision_summary_v2.md` §VII checklist 和 `archive/response_draft_v2.md`）

- ✅ 符号统一 (k→s)、Table 1、Π 正式定义
- ✅ Eq(1) 线性假设 Remark + PD disaggregation
- ✅ OOM 机制说明（eviction prevention 段）
- ✅ Heavy-traffic → asymptotic regime 主替换
- ✅ Proof sketch（3-step framework）
- ✅ On-the-fly classification + safety buffer 解释
- ✅ Section 6 整节重写（Fig A/B/C/D/E）
- ✅ GPU 验证（Reviewer 2，32 batch sizes, R²=0.9957）
- ✅ Wait vs no-wait 实验记录（DB）
- ✅ Concurrent Theoretical Work 段落（Zhou 系列）
- ✅ Kingman / Doob / Asmussen citations
- ✅ Duplicate `\newtheorem` 和 package conflicts 修复

---

**Document Version**: v1.1
**Last Updated**: 2026-04-21

---

## Changelog

- **v1.6 (2026-04-21 late evening)**: **P0.4 wait-vs-nowait 闭环** —— GPU 实验 (2026-04-12 + 2026-04-15 native lmsys real-trace) 完整结果汇入 §app:sglang：扩展为 random + real-trace 两段，新增 Table~\ref{tab:sglang_realtrace} (7 rates 全胜，peak +9.2% at λ=0.4 with wait_gate=on)。§app:no_wait conclusion 软化为 "regime-dependent"，承认 wait component 在 λ=0.4 是最大 win 而非 universally unnecessary
- **v1.5 (2026-04-21 late evening)**: **P0.3 numerical.tex merge 完成** —— v2 覆盖 original，backup 到 archive/；9 internal + 8 external labels 全部 resolve。**Appendix.tex \input 补全** —— 加入 `appendix_sim_fidelity` 和 `appendix_b_additional`，之前这两个 appendix 虽然写好但从未被 LLM_or.tex 编译路径包含
- **v1.4 (2026-04-21 late evening)**: Related work (intro L69/L71) 2nd-pass polish —— 去 belittling, 加 "from theoretical side" (L69) + "takes a different angle" (L71); 4 个 proof/appendix 文件 (pf_thm_nested, pf_thm_timevarying, pf_lemmas, Appendix.tex) sweep complete，all clean at body text level
- **v1.3 (2026-04-21 evening)**: 新增顶层 🔁 **RECURRING CONSISTENCY SWEEP** 区块（18 条规则 + 一键 grep 命令 + sweep protocol + per-section tracker）；Llama naming flag close（确认 Llama 2）
- **v1.2 (2026-04-21 pm)**: P0.5 footprint/delineate sweep theory 章节 4 文件全清；**P0.6 新增（active paper 全文 consistency sweep 完成）**：em-dash / key insight / fluid dynamics / defensive framing / standard X undersell 在 11 个活跃文件全部清零；P2 主体章节 9/10 converged（只剩 numerical.tex merge 和 Llama naming flag）
- **v1.1 (2026-04-21 am)**: P0.1 4 项全部 close；P0.2 abstract/intro/conclusion converged；P0.5 新增 footprint/delineate sweep（主体 3 文件完成，theory 4 文件待做）；P2 文件状态更新
- **v1.0 (2026-04-17)**: 初稿
