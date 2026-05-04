# OPRE Revision Final Packet, Abstract, and Layout Pass - 2026-05-02

## 状态
✅ 已完成

## 概要
完成 OPRE revision package 的最后一轮可上传材料整理、abstract 字数压缩、正文 numerical section 排版压缩、以及 appendix 重复图清理。当前 `papers/LLM_or.pdf` 已重新编译，packet 中的 revised paper PDF 已同步更新。

## 完成内容

### Revision Packet
- **GPT-Pro final audit packet**: 新建 `docs/revision/gpt_pro_final_revision_packet_20260502_v2/`，包含 AE report、两份 referee report、decision letter、original submission、revised paper、response letter、internal audit checklist、README 和 web prompt。
- **Packet sync**: 每次重新编译 `papers/LLM_or.pdf` 后，同步更新 packet 中的 `06_revised_paper.pdf`。

### Abstract
- **OPRE 字数限制**: 确认 Operations Research abstract 要求不超过 200 words。
- **Final abstract**: 将 `papers/abstract.tex` 压缩到 196 words 左右，并保留用户指定的核心叙事：
  - LLM inference 的规模与成本动机；
  - token-by-token inference 与 GPU scheduling 重要性；
  - endogenous KV-cache memory growth 与 eviction/restart；
  - introduce a fluid model；
  - guided by the fluid model 设计 WAIT / Nested WAIT；
  - 两个算法与 fluid benchmark 的 asymptotic comparison；
  - Vidur A100 simulation + real-A100 validation；
  - near-overloaded / overloaded regimes 的 latency improvement。

### Main-Text Layout
- **Numerical figures**: 缩小正文 Section 6 主图宽度，尤其 Figure 9 long-decode 图，缓解宽图比例失调。
- **Caption compaction**: 压缩 Section 6 若干长 caption 和开头实验说明，减少正文页数。
- **Page count**: `papers/LLM_or.pdf` 从 85 页降到 83 页；正文 Figure 12 不再漂到 conclusion 后。
- **Long-decode wording**: 删除 `tightened memory` 口径，改为只描述 eviction-induced restart diagnostic。

### Appendix Cleanup
- **Removed duplicate Figure 13**: 删除 appendix extension 中的 old `lambda_list` arrival-rate construction figure。正文 Figure 11 已展示 lmsys prefill/decode distribution，因此该图信息重复。
- **Replacement text**: 保留一句文字说明 segment arrival rates proportional to empirical output-length frequencies。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 3 |
| 修改文件 | 多个 paper / revision docs |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/abstract.tex` | 修改 | Abstract 压缩到 OPRE 200-word limit 内，并恢复更自然的问题动机和 fluid-model 叙事。 |
| `papers/numerical.tex` | 修改 | Section 6 figure sizes / captions / long-decode restart wording 精简。 |
| `papers/extension.tex` | 修改 | 删除重复的 Figure 13 arrival-rate construction 图。 |
| `papers/LLM_or.pdf` | 修改 | 重新编译后的 revised manuscript。 |
| `docs/revision/gpt_pro_final_revision_packet_20260502_v2/` | 新增 | GPT-Pro final audit upload packet。 |
| `docs/progress/2026_05_02_revision_final_packet_abstract_layout.md` | 新增 | 本进度报告。 |

## 测试情况

- [x] `latexmk -pdf -interaction=nonstopmode LLM_or.tex` 编译通过。
- [x] Abstract word-count check 通过 OPRE 200-word limit。
- [x] Packet revised PDF 已同步到 `docs/revision/gpt_pro_final_revision_packet_20260502_v2/06_revised_paper.pdf`。

## 下一步计划

- [ ] 将 packet 上传给 GPT-Pro / Deep Research 做 final external audit。
- [ ] 根据 external audit feedback 做最后一轮 response-letter / manuscript alignment。
- [ ] 如需要提交前归档，运行 `$update-paper-state` 同步 paper-state 文档。
- [ ] 推送前检查不应提交的 generated / system files（`.DS_Store`, `__pycache__`, LaTeX aux/log/fls 等）。

## 相关文档

- `docs/revision/gpt_pro_final_revision_packet_20260502_v2/README.md`
- `docs/revision/gpt_pro_final_revision_packet_20260502_v2/PROMPT.md`
- `docs/revision/final_gpt_pro_audit_checklist_20260502.md`
- `docs/progress/2026_05_02_opre_revision_final_qa_push.md`
- `docs/progress/2026_05_02_vidur_validation_grid_sync.md`

---

**作者**: Codex 自动生成  
**审核**: 待用户确认
