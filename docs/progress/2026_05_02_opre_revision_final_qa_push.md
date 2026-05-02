# OPRE Revision Final QA and Push Preparation - 2026-05-02

## 状态
✅ 已完成

## 概要
本轮完成 OPRE revision package 的最终一致性检查：主文、response letter、Section 6 figures、time-varying extension、related-work positioning 和 real-data provenance 口径已同步。唯一保留的开放项是 lmsys Figure D 的完整 per-arrival-rate provenance/rerun；当前正文和 response letter 保持保守表述，因此该项不阻塞当前提交。

## 完成内容

### 主要功能
- **Response letter / paper consistency**: 逐条核对 response letter 与当前正文，确认 real-data、A100 validation、memory cap、\(\mathrm{tl}\) grid、eviction/restart、related work 口径一致。
- **Section 6 QA**: 确认 Figure D PDF 轴标签为 `Arrival rate \(\lambda\)` 和 `Effective completion rate`，正文 caption 恢复直接 latency-comparison wording，正文 paragraph 保持更 neutral 的 observed-grid 叙述。
- **Proof / extension QA**: 确认 main WAIT 和 Nested WAIT proof 没有新的 blocker；time-varying extension 已将 throughput/memory guarantee 与 service-normalized delay 的 first-segment waiting condition 分开。
- **Negative search**: 在 active paper/letter source 和 compiled PDFs 上搜索 stale phrases，未发现 `tl=400/1000`、`Arrival rate QPS`、旧 `1.5%` validation、`direct vLLM measurements`、`in-flight limit`、`threshold collection` 等残留。

### 改进优化
- 更新 `docs/paper_state/opre_revision/r2_detailed_items_checklist.md`，记录 post-caption-restore consistency pass。
- 更新 `docs/paper_state/opre_revision/changelog.md`，记录 Figure D caption 还原和最终 QA 状态。
- 保留 `docs/paper_state/opre_revision/real_data_remeasurement_checklist.md` 中的开放 provenance 项，防止后续误把 lmsys Figure D 升级成 sharp stability-boundary claim。

### Bug 修复
- 修正 changelog 中“caption 也 neutralized”的记录，使其与当前正文一致：正文 paragraph neutral，Figure D caption 恢复直接 latency comparison。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 |
| 修改文件 | 多个 active paper / revision-state 文件 |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/numerical.tex` | 修改 | Figure D caption 恢复直接比较，real-data results paragraph 保持 neutral observed-grid 叙述 |
| `papers/response_letter.tex` | 检查 | 确认 Section 6 / A100 / memory cap / real-data claims 与正文一致 |
| `papers/extension.tex` | 检查 | 确认 time-varying extension 对 delay 的 first-segment waiting condition 已保留 |
| `docs/paper_state/opre_revision/r2_detailed_items_checklist.md` | 修改 | 记录最终 consistency pass 和唯一开放项 |
| `docs/paper_state/opre_revision/changelog.md` | 修改 | 记录 final QA 和 caption 口径 |

## 相关 Commits

```
eafb587 docs: record section 6 revision provenance
9116e2d Add real-data provenance rerun grid
d88c490 docs: add VM real-data tuning investigation prompt
```

## 遇到的问题与解决

### 问题 1: lmsys Figure D provenance 仍不完整
**现象**: SQL provenance 只覆盖 QPS \(10,20,50,60\)，不能重建完整 Figure D grid。  
**原因**: 历史调参记录没有完整保存 per-rate winning configs。  
**解决**: 当前 paper/letter 只报告 finite-grid calibration 和 plotted-rate comparison，不声称 sharp real-data stability boundary 或完整 per-rate provenance table；后续若强化 claim，必须先 rerun/reconstruct。

### 问题 2: Worktree 包含大量无关生成物
**现象**: `git status` 中存在 `.DS_Store`、LaTeX aux、`tmp/`、临时数据库和历史输出。  
**原因**: 多轮编译、figure generation、local forensic/rerun artifacts 混在同一工作树。  
**解决**: push 前使用白名单 staging，仅提交 active paper-facing / revision-state / progress docs 和必要图表脚本输出，不提交无关系统文件或临时产物。

## 测试情况

- [x] `latexmk -pdf -interaction=nonstopmode LLM_or.tex` up-to-date
- [x] `latexmk -pdf -interaction=nonstopmode response_letter.tex` up-to-date
- [x] Active source stale-term search clean
- [x] Compiled PDF stale-term search clean except reviewer-response contexts and bibliography title

## 下一步计划

- [ ] 按白名单 commit 并 push 到 `origin/revision`
- [ ] 如提交前还要收敛包大小，单独清理或 ignore `.DS_Store` / LaTeX aux / tmp artifacts
- [ ] 若要强化 lmsys Figure D claim，先完成 full per-arrival-rate provenance rerun

## 相关文档

- `docs/paper_state/opre_revision/r2_detailed_items_checklist.md`
- `docs/paper_state/opre_revision/response_letter_claim_audit.md`
- `docs/paper_state/opre_revision/real_data_remeasurement_checklist.md`
- `docs/progress/2026_05_02_real_data_provenance_audit.md`

---

**作者**: Codex
**审核**: 待审核
