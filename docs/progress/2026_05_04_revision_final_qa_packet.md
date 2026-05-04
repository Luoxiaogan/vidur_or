# OPRE Revision Final QA Packet - 2026-05-04

## 状态
✅ 已完成

## 概要
完成 OPRE major-revision 当前版本的 final QA pass：主文与 response letter 已重新编译，PDF 文本层面的高风险措辞和 unresolved-marker 检查通过，并生成新的 AE/reviewer-style audit packet。当前仅保留一个刻意开放但不阻塞提交的 lmsys per-arrival-rate provenance 项。

## 完成内容

### Revision Paper / Response Letter
- **主文编译确认**: `papers/LLM_or.pdf` 已更新并编译通过，当前为 87 pages。
- **Response letter 编译确认**: `papers/response_letter.pdf` 已更新并编译通过，当前为 20 pages。
- **证明语言收口**: WAIT proof 现在使用 `auxiliary embedded full-threshold process` 和 `sample path coupling`，避免 `comparison clock` / 自造 proof-technique wording。
- **Response-letter 语气收口**: 删除 `review team` 泛称，改为 `reports and decision letter`, `referees`, `referees and editors`, `requested in the reports` 等具体来源。

### Final QA Checks
- **PDF 文本检查通过**: 主文和 response letter 中未检出 `??`, `TODO`, `PLACEHOLDER`, `tl=400/1000`, `review team`, `steady-state mean latency`, `decode-centered`, `affine`, `resident population`, `comparison clock`, `sample-path block argument`, `binomial thinning law`, `completed-work deficit`。
- **Scope wording 检查**: 当前正文本身保留保守口径：real-GPU validation 是 appendix supplemental validation / implementation evidence / support for simulator accuracy，不声称主文所有 Vidur comparisons 已被实卡完整复现。
- **Checklist 状态确认**: R2 detailed-item checklist 只剩一个 open item，即 lmsys Figure D 完整 per-arrival-rate winning-configuration provenance；当前保守 claim strength 下不阻塞。

### Packet
- **最新 audit packet**: `docs/revision/native_ae_reviewer_audit_packet_20260504_1835.zip`
- **Packet 内容**:
  - `00_prompt.md`
  - `01_original_submission.pdf`
  - `02_revised_paper.pdf`
  - `03_response_letter.pdf`
  - `04_AE_report.pdf`
  - `05_review_report_1.pdf`
  - `06_review_report_2.pdf`
  - `07_decision_letter.md`
- **Prompt 口径**: 不额外提示模型已有结论，只要求以 AE/reviewer 角色审阅 original submission、revision、response letter 和 review materials。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 progress report + 1 latest packet directory/zip |
| 修改文件 | paper/letter/state docs 多个 |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/LLM_or.pdf` | 修改 | 最新 revised manuscript 编译产物 |
| `papers/response_letter.pdf` | 修改 | 最新 response letter 编译产物 |
| `papers/pf_thm_wait.tex` | 修改 | WAIT proof coupling 语言向 queueing-theory 原文表达靠拢 |
| `papers/Appendix.tex` | 修改 | Lower-bound proof prose 改为更保守的 sample-path/block/filtration 表述 |
| `papers/response_letter.tex` | 修改 | 删除 `review team` 泛称并同步 proof/scoping wording |
| `docs/revision/native_ae_reviewer_audit_packet_20260504_1835.zip` | 新增 | 当前最新 AE/reviewer audit upload packet |

## 相关 Commits

```text
9992a07 chore: track final local metadata change
26ce1be chore: track remaining local artifacts
9f92a81 docs: finalize OPRE revision QA package
a7d99ae docs: record section 6 revision provenance
```

## 遇到的问题与解决

### 问题 1: Packet 早于当前 PDF
**现象**: `native_ae_reviewer_audit_packet_20260504.zip` 的生成时间早于当前 `LLM_or.pdf` 和 `response_letter.pdf`。
**原因**: proof language 和 response-letter wording 在 packet 后继续微调。
**解决**: 新建 `native_ae_reviewer_audit_packet_20260504_1835/` 并重新打包 zip，使用当前最新 PDF。

### 问题 2: Queueing proof phrase 不能假装是原文
**现象**: `sample-path block argument`、`binomial thinning law` 等 compound phrases 不一定是 queueing paper 原文。
**原因**: 它们是 field-compatible 组合表达，但不是可确认的 source-backed terminology。
**解决**: 改为 `sample path coupling`, `embedded process`, `observed at iteration epochs`, `condition on the policy's filtration`, `survivor count is binomial conditional on \mathcal F` 等更稳妥表达。

### 问题 3: Response-letter 泛称不够正式
**现象**: `review team` 听起来不像正式 journal response letter。
**原因**: 该说法过于泛化，弱化了 AE/referee/decision-letter 的具体来源。
**解决**: 替换为 `Area Editor, Associate Editor, and referees`, `reports and decision letter`, `referees`, `requested in the reports`。

## 测试情况

- [x] `latexmk -pdf -interaction=nonstopmode LLM_or.tex`
- [x] `latexmk -pdf -interaction=nonstopmode response_letter.tex`
- [x] PDF text grep for unresolved markers and stale/high-risk wording
- [x] Packet file list and PDF metadata check

## 下一步计划

- [ ] 如果需要继续外部 audit，上传 `docs/revision/native_ae_reviewer_audit_packet_20260504_1835.zip`。
- [ ] 不扩大 lmsys real-data stability-boundary / per-rate configuration claims，除非先完成 durable provenance rerun。
- [ ] 若准备正式提交，做最后一次 `git status` 分类，避免把 cache/pycache/DS_Store 等本地 artifacts 混入提交。

## 相关文档

- `docs/paper_state/opre_revision/r2_detailed_items_checklist.md`
- `docs/paper_state/opre_revision/response_letter_claim_audit.md`
- `docs/paper_state/opre_revision/results.md`
- `docs/revision/native_ae_reviewer_audit_packet_20260504_1835.zip`

---

**作者**: Codex
**审核**: 待审核
