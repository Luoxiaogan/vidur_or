# Vidur validation and real-data grid sync - 2026-05-02

## 状态

✅ 已完成

## 概要

本次更新把 Reviewer 2 相关的 Vidur / A100 validation 口径重新锁定：Llama-2-7B A100 的原始 Vidur profiling 覆盖到 batch size \(B\le 128\)，\(B=256\) 作为单点外推校验报告。同步将 real-data Nested WAIT 的 paper-facing 参数网格收窄为 \(\mathrm{tl}\in\{20,40,\ldots,200\}\)，避免与 A100 memory-capacity 讨论冲突。

## 完成内容

### Validation provenance

- 新增 `scripts/validate_llama2_b256_vidur.py`，用于复现当前 Llama-2-7B / A100 validation 口径。
- 脚本确认原始 Vidur attention profiling 的 Llama-2-7B A100 batch range 为 \(B\le128\)，没有 \(B=256\) 原始 profiling row。
- 脚本使用 `outputs/validation_database/vidur_validation.db` 中记录的 A100 \(B=256\), prompt length 256, output length 20 measurement，与 \(B\le128\) fitted affine predictor 对比。
- 当前 \(B=256\) 单点结果为 measured \(1146.54\) ms、predicted \(1090.07\) ms、absolute error \(4.93\%\)。
- 可选 `--run-vidur-predictor` 路径记录 direct Vidur RF predictor 的单 decode-iteration estimate；该值不是 full-generation A100 measurement，不能与 1146 ms 直接比较。

### Paper / response letter sync

- `papers/numerical.tex` 说明主 calibration 使用 profiled range \(B\le128\)，并在 appendix 中报告 \(B=256\) extrapolation check。
- `papers/appendix_b_additional.tex` 将 simulator-vs-GPU validation 改为 profiled-range validation plus \(B=256\) single extrapolation check，避免暗示 Vidur 原始 profiling 已覆盖 \(B=256\)。
- `papers/response_letter.tex` 同步修改 Reviewer 2 validation 回复，区分 raw Vidur profiling coverage 和 \(B=256\) external A100 check。
- `papers/numerical.tex` 和 response letter 中 real-data Nested WAIT grid 统一为 \(\mathrm{tl}\in\{20,40,\ldots,200\}\), \(L\in\{1,2,3,4,5,10,20\}\), \(\eta=0.05\)。

### State docs sync

- 更新 `docs/paper_state/opre_revision/r2_detailed_items_checklist.md`，记录 \(B\le128\) primary validation 与 \(B=256\) 4.93% extrapolation check。
- 更新 `docs/paper_state/opre_revision/overview.md`, `framing.md`, `response_letter_claim_audit.md`, `real_data_remeasurement_checklist.md`，统一 real-data grid 为 `20,40,...,200`。
- 更新 `docs/paper_state/opre_revision/changelog.md` 和 `consistency_log.md`，记录本轮 validation 口径和 grid lock。

## 代码变更

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| 新增脚本 | 1 | `scripts/validate_llama2_b256_vidur.py` |
| 修改论文/letter 源文件 | 3 | `papers/numerical.tex`, `papers/appendix_b_additional.tex`, `papers/response_letter.tex` |
| 修改 paper-state 文档 | 7 | OPRE revision state / checklist / consistency docs |
| 重新生成 PDF | 2 | `papers/LLM_or.pdf`, `papers/response_letter.pdf` |

## 关键文件

| 文件 | 变更类型 | 说明 |
| --- | --- | --- |
| `scripts/validate_llama2_b256_vidur.py` | 新增 | Refit \(B\le128\) affine predictor, check \(B=256\) A100 measurement, optionally run Vidur predictor |
| `papers/numerical.tex` | 修改 | Section 6 validation and real-data grid wording |
| `papers/appendix_b_additional.tex` | 修改 | Appendix validation figure/caption wording |
| `papers/response_letter.tex` | 修改 | Reviewer 2 validation and experimental-parameter responses |
| `docs/paper_state/opre_revision/r2_detailed_items_checklist.md` | 修改 | R2 validation checklist updated to current evidence |
| `docs/paper_state/opre_revision/consistency_log.md` | 修改 | Current terminology/config lock |

## 验证情况

- `python scripts/validate_llama2_b256_vidur.py`
  - Confirms Llama-2-7B raw profiling max batch size \(128\).
  - Reports \(B=256\) A100 extrapolation-check error \(4.93\%\).
- `python scripts/validate_llama2_b256_vidur.py --run-vidur-predictor`
  - Runs direct Vidur predictor path for a pure decode-iteration estimate.
  - Kept as diagnostic only because it is not the same quantity as full-generation validation.
- `cd papers && latexmk -pdf -interaction=nonstopmode LLM_or.tex`
  - Main paper compiles successfully.
- `cd papers && latexmk -pdf -interaction=nonstopmode response_letter.tex`
  - Response letter compiles successfully.

## 遇到的问题与解决

### 问题 1: \(B=256\) 是否属于原始 Vidur profiling 覆盖范围

**现象**: 之前图文可能被读成 Llama-2-7B A100 profiling 覆盖到 \(B=256\)。

**原因**: `attention.csv` 原始 profiling rows 对 Llama-2-7B 只到 \(B=128\)；\(B=256\) 是 validation database 中的 external A100 measurement，对 \(B\le128\) fitted predictor 做外推校验。

**解决**: 正文、appendix、response letter 都改为 “profiled range \(B\le128\) plus one \(B=256\) extrapolation check”。

### 问题 2: real-data `tl` 上限与 A100 memory-capacity 讨论冲突

**现象**: 旧口径中出现过 `tl` up to 300/400 的记录，容易与 long-decode memory cap 讨论产生冲突。

**原因**: 早期 provenance / tuning 文档记录了更宽的 exploratory grid，但 paper-facing revision 不需要保留这个上限。

**解决**: 当前 paper/letter/state 统一写作 \(\mathrm{tl}\in\{20,40,\ldots,200\}\)，并保留 \(L\) 和 \(\eta\) 的明确设置。

## 下一步计划

- 如果继续强化 Appendix validation，可以只把 \(B\le128\) 作为主证据，\(B=256\) 明确为 extrapolation sanity check。
- 若需要更强的 \(B=256\) 证据，应在 A100 上重新跑与 Vidur predictor 同口径的 per-iteration measurement，而不是混用 full-generation measurement。
- 下一轮 response-letter audit 时，重点检查是否仍有 “raw profiling covers \(B=256\)” 或旧 `tl=300/400` 的残留表述。

## 相关文档

- `docs/paper_state/opre_revision/r2_detailed_items_checklist.md`
- `docs/paper_state/opre_revision/consistency_log.md`
- `docs/paper_state/opre_revision/changelog.md`
- `outputs/validation_database/vidur_validation.db`

---

**作者**: Codex
**审核**: 待审核
