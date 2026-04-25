# OR论文修订计划

**论文**: Optimizing LLM Inference: Fluid-Based Online Scheduling under Memory Constraints
**Manuscript ID**: OPRE-2025-04-1885
**目标期刊**: Operations Research (INFORMS)
**状态**: Major Revision

---

## 核心文档
- `revision_summary.md` - 审稿意见和9个Decisions
- `response_draft.md` - Response Letter草稿和修改记录
- `.claude/CLAUDE.md` - Claude Code项目规范

---

## 修订进度

### ✅ 已完成
- [x] 符号系统统一 (k→s, Table 1)
- [x] Policy space Π定义
- [x] FCFS cascading failure例子
- [x] Proof sketch (3-step framework)
- [x] On-the-fly classification说明
- [x] Safety buffer直观解释
- [x] Concurrent Theoretical Work段落
- [x] Remark精简 (C≥M*, Terminology)
- [x] AI化语言润色
- [x] Introduction复杂性来源
- [x] G1.1: Dimensionality reduction段落 (known_type.tex L61-62)
- [x] G1.2: Load balance表述 (已存在于known_type.tex L186)
- [x] G1.3: PD分离系统讨论 (已存在于introduction.tex L45)
- [x] G2: Minor items确认 (无需修改)
- [x] H1.2: introduction.tex "heavy-traffic analysis" → "asymptotic analysis"
- [x] H1.3: model.tex 拼写错误 "algortihms" → "algorithms"
- [x] I1: CLAUDE.md 添加reviewer PDF说明
- [x] I2: revision_summary.md 添加审稿源文件引用
- [x] J1.1: pf_thm_nested.tex 添加Kingman citation (lines 35, 58)
- [x] J1.1: pf_thm_timevarying.tex 添加Kingman citation (lines 45, 67, 77)
- [x] J1.2: pf_thm_nested.tex 添加Doob citation (line 91)
- [x] J2: model.tex 语法修复 "each prompts are" → "each prompt is"
- [x] J5: conclusion.tex 加强核心论点连接 (memory constraint, eviction, asymptotic regime)
- [x] L1: unknown_type.tex 添加M^π语义解释 (Line 109)
- [x] L2: pf_thm_nested.tex 改进Proof Outline和Notation段落 (Lines 7-16)
- [x] L3: pf_thm_nested.tex M^π定义添加正文引用 (Line 118-120)
- [x] L4: pf_thm_nested.tex 修复下标错误 k→j (Line 127)
- [x] L5: pf_thm_wait.tex 取消注释Proof Outline (Lines 7-13)
- [x] M1: known_type.tex FCFS cascade内容前移至算法描述后 (Lines 61-94)
- [x] M2: known_type.tex Proof sketch简化为自然语言flow (Lines 177-179)
- [x] M3: unknown_type.tex 去AI化 "Key Insight:" 标题 (Line 66)
- [x] M4: CLAUDE.md 添加修改同步要求和去AI化检查清单
- [x] N1: model.tex 删除Remark[Applicability of Linear Model]格式，融入正文 (L102)
- [x] N2: unknown_type.tex 删除"\textbf{Understanding the Safety Buffer.}"标题 (L138)
- [x] O1: pf_thm_nested.tex segment index j→k (Lines 117-127)
- [x] O2: pf_thm_timevarying.tex 注释中s→b (Lines 19-20)
- [x] O3: Appendix.tex 恢复4个Proposition证明 (prop:large_rate, throughput upper bound, FCFS lower bound, unknown lower bound)
- [x] Q1: Notation consistency - known_type.tex `type-$k$` → `other types'` (L61)
- [x] Q2: Notation consistency - fluid.tex stage index `k` → `s` (L20, L27)
- [x] Q3: Notation consistency - pf_thm_nested.tex dummy var `k` → `i` (L119)
- [x] Q4: Notation consistency - unknown_type.tex segment index unified to `i` (L105-109)
- [x] Q5: Notation consistency - extension.tex segment index unified (L76-90, L115)
- [x] Q6: Notation table update - model.tex Table 1 统一使用 k 作为segment index
- [x] Q7: Segment index全面统一为k - unknown_type.tex, extension.tex (时变+L-segment两部分)
- [x] R1: unknown_type.tex - 添加Example 2 (Unknown Output Lengths)作为Example 1的延续
- [x] R2: unknown_type.tex - 重组proof sketch，强调dimensionality reduction + safety buffer
- [x] R3: extension.tex - 添加简短proof sketch (时变定理 + L-segment定理)
- [x] R4: unknown_type.tex - 修复notation consistency (segment index统一为k, stage index统一为s)
- [x] R5: unknown_type.tex - 算法框notation改进 (n_{k,s}→Q_{k,s}避免与threshold n_k混淆)
- [x] R6: unknown_type.tex + extension.tex - batch notation统一 (S→B, s→b)
- [x] S1: abstract.tex - 重写abstract，加入eviction/OOM/cascading failure主题
- [x] T1: revision_summary.md + CLAUDE.md - 添加核心论点#12: Exploit Memory to Improve Throughput
- [x] T2: revision_summary.md - 在Wait vs No-Wait讨论中添加exploit memory论据
- [x] U1: 系统性去AI化polish - 8个section全面润色
  - introduction.tex: 删除7×AI套话，拆分长句，改善逻辑流
  - model.tex: 添加Example 2.1 (FCFS cascading failure), 替换僵尸名词
  - unknown_type.tex: 修复术语("reveal output"), 拆分276词段落
  - known_type.tex: 5处编辑，改善表达直接性
  - numerical.tex: 4处被动→主动语态
  - extension.tex: 3处改善清晰度
  - conclusion.tex: 2处删除AI套话
  - fluid.tex: 2处使用alternative expressions

### 📋 待办（低优先级 - 用户跳过）
- [ ] 实验参数补充
- [ ] Figure 7 caption clarification
- [ ] Underloaded实验（可选）
- [x] **Wait vs No-Wait (Threshold without waiting) 数值比较** - 已补代表性scenario比较、SQL记录与response wording
- [x] extension.tex Line ~90: 删除多余句号 ".." ✅
- [x] M5: 移除known_type.tex Wait vs No-Wait Remark（记录为待办数值实验）

---

## 下次继续时的提示

1. 读取此文件了解当前进度
2. 检查response_draft.md获取详细修改记录
3. 继续执行"进行中"的任务

---

## 详细修改记录

见 `response_draft.md` 中的Section 3.x系列

---

**最后更新**: 2025-12-16 (Part U: 完成全文8个section的去AI化comprehensive polish)

---

## 全文验证结论 (Part P)

### AE三个优先级验证结果

| 优先级 | 要求 | 状态 |
|--------|------|------|
| **Priority 1** | Complete Expositional Overhaul | ✅ 完成 |
| **Priority 2** | Model Justification | ✅ 完成 |
| **Priority 3** | Clarify Theoretical Novelty | ✅ 完成 |

### 核心修订内容确认

**写作质量**:
- ✅ 符号表 Table 1 (model.tex)
- ✅ Proof outlines (所有appendix文件)
- ✅ Notation paragraphs (所有proof文件)
- ✅ 标准文献连接 (Kingman, Asmussen, Doob)
- ✅ Appendix符号统一 (pf_thm_nested.tex segment index, pf_thm_timevarying.tex batch index)
- ✅ Proposition证明恢复 (Appendix.tex, 4个证明: large_rate, throughput upper bound, FCFS, unknown)

**模型合理性**:
- ✅ Eq(1)适用性说明 (model.tex Remark)
- ✅ C≥M*假设讨论 (known_type.tex Remark 4.0)
- ✅ OOM/eviction机制 (introduction.tex)
- ✅ PD分离适用性 (introduction + model)

**理论贡献**:
- ✅ FCFS cascading failure例子 (known_type.tex Example 4.1)
- ✅ Dimensionality reduction说明 (known_type.tex)
- ✅ On-the-fly classification (unknown_type.tex)
- ✅ Safety buffer直观解释 (unknown_type.tex)
- ✅ Zhou系列对比 (introduction.tex)

### 下一步: Response Letter准备

论文修订实质性完成，可开始撰写Response Letter

---

## Final Polish记录 (2025-12-14)

| 文件 | 位置 | 修改内容 |
|------|------|----------|
| extension.tex | L90 | 修复断句结构 |
| introduction.tex | L29 | 移除AI化表达 "This observation motivates" |
| model.tex | L44 | 语法修正 "single GPU" → "a single GPU" |
| known_type.tex | L4 | 语法修正 "tries optimizes" → "optimizes" |
| known_type.tex | L159 | 移除AI化表达 + typo "matche" → "match" |
| conclusion.tex | L3 | 改善awkward phrasing |

详见 `response_draft.md` Section 3.11
