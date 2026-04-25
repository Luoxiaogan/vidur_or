# OR Revision: Section 6 Editorial Polish - 2026-04-23

## 状态
🚧 进行中（Section 6 段落级打磨持续推进）

## 概要
本轮工作从整节重写转入 paragraph-by-paragraph 精修，重点是把 Section 6 的实验 setting、`tl` 机制、baseline 描述和 OR 叙述口径写得更自然、更具体。同步完成了 equation warning 关闭、`KV cache` 术语统一、paper state 初始化与持续维护。

## 完成内容

### Section 6 prose polish
- 重写了 `papers/numerical.tex` 的 opening/setup 段落，去掉过强的 systems-jargon，改成更接近 OR 论文的实验叙述。
- 明确了 baseline 口径：
  - vLLM 与 Sarathi 都按 FCFS admission 叙述
  - Sarathi 的 `chunked prefill` 被解释为把长 prefill 切成较小块，避免单个大 prefill 长时间占住 batch
  - 不再在正文里强调具体 scheduler 名称或实现细节
- 明确了 WAIT / Nested WAIT 的 `tl` 机制：
  - `tl` 是全局 in-system hard cap
  - threshold 未满但 admit 当前等待请求后会把系统补满到 `tl` 时，也允许提前 admit
  - 加入了一个小例子解释 `tl` 与 threshold 如何共同起作用
- 把 real lmsys workload 的 `tl` grid 统一写成等差数列形式 `\{20,25,\ldots,40\}`。

### Cross-section consistency cleanup
- 将 `KV cache` 在 active paper 中统一为无连字符写法。
- 把 iteration-time model 的 A100 calibration 说明从 Section 6 挪回 `papers/model.tex` 的公式解释位置，并在 Section 6 保留简洁指针。
- 在 `papers/model.tex` 中补充说明 prefill-decode disaggregation 指 prefill 与 decode 在不同设备上执行。
- 关闭了 `papers/eqndefns-left.sty` 的 displayed-equation 宽度 warning box，避免 main 编译时持续弹出红框提示。

### Paper-state maintenance
- 初始化并开始维护 `docs/paper_state/opre_revision/`。
- 已同步更新：
  - `changelog.md`
  - `overview.md`
  - `framing.md`
  - `consistency_log.md`

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 |
| 修改文件 | 8 |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/numerical.tex` | 修改 | Section 6 opening/setup 段落持续精修，补清 `tl` admission 机制与例子 |
| `papers/model.tex` | 修改 | iteration-time model 解释与 applicability prose polish |
| `papers/appendix_sim_fidelity.tex` | 修改 | Section 6 参数口径与 real-workload `tl` grid 同步 |
| `papers/eqndefns-left.sty` | 修改 | 关闭 equation-width warning boxes |
| `papers/introduction.tex` | 修改 | `KV cache` 术语统一 |
| `papers/conclusion.tex` | 修改 | `KV cache` 术语统一 |
| `docs/paper_state/opre_revision/*` | 修改 | 记录 Section 6 当前锁定写法与同步状态 |

## 相关 Commits

```
4c59249 Update GPU real-trace wait-gate progress
c95a886 feat: Appendix B — additional experiments for reviewer comments
7b9344b docs: Section 6 rewrite progress + CLAUDE.md sync
8a84b46 feat: Section 6 figures D/E + integrated tex draft (numerical_v2)
```

## 遇到的问题与解决

### 问题 1: `tl` 机制在正文里写得像实现说明
**现象**: `entry stage is released`、`operator-level parameter`、`algorithm-level thresholds` 这类说法读起来更像系统文档，不像 OR 论文。
**原因**: 早期写法过于贴近 scheduler implementation，而没有把 admission logic 抽象成 paper prose。
**解决**: 改成统一的 admission rule 叙述，并加入小例子说明 threshold 与 `tl` 如何共同决定是否 admit。

### 问题 2: Section 6 内部口径不一致
**现象**: 同一节中同时出现 `tuned per QPS`、`selected value`、`segment-wise limit` 等不同口径。
**原因**: 文字来源于多轮 rewrite，旧说法残留。
**解决**: 统一为单一 global `tl` 输入、per-QPS 从 grid 中选取、segment thresholds/budgets 由 `tl` 派生。

### 问题 3: 编译期 warning 打断论文打磨
**现象**: displayed equation 超列宽红框 warning 在 main 编译中频繁弹出。
**原因**: `eqndefns-left.sty` 默认启用了 equation validation。
**解决**: 将其默认值改为关闭，先保证 revision prose/editing 工作流顺畅。

## 测试情况

- [ ] 单元测试通过
- [ ] 集成测试通过
- [x] 手动检查关键 `.tex` / state-doc 口径一致性

## 下一步计划

- [ ] 继续按段打磨 `papers/numerical.tex` Section 6 其余段落
- [ ] 检查 `papers/numerical.tex` 中与 real workload 相关的 `per-type / per-segment` 表述是否仍需进一步收紧
- [ ] 编译一次 main paper，确认最新 prose 修改没有引入新的排版问题

## 相关文档

- [Section 6 rewrite progress](./2026_04_17_numerical_section_rewrite.md)
- [Main experiments section](../../papers/numerical.tex)
- [Model discussion](../../papers/model.tex)
- [Experimental configuration appendix](../../papers/appendix_sim_fidelity.tex)
- [Paper state overview](../paper_state/opre_revision/overview.md)

---

**作者**: 自动生成（update-progress workflow + 当前编辑轮次）
**审核**: 待审核
