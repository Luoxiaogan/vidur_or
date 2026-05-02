# OPRE revision theory/response consistency - 2026-05-01

## 状态
✅ 已完成

## 概要
本轮集中同步了 OPRE revision 中 fluid equilibrium / stability benchmark 口径、WAIT 与 Nested WAIT 的 memory notation、real-data Nested WAIT 参数解释，以及 response letter 中对 \(C\ge M^*\) 评论的回复逻辑。修改后，正文、附录、response letter 与 paper-state 文档对 \(C\)、\(M^*\)、\(M^\pi\)、\(M_{\mathrm{req}}^{(\zeta,\pi)}\) 的含义保持一致。

## 完成内容

### 理论与 notation
- 将正文和 response letter 中的 `ideal-fluid equilibrium` 口径收敛为 `fluid equilibrium`，并保留 `fluid stability benchmark/region` 作为 \(M^*(\lambda)\le C\) 定义的理论稳定性基准。
- 统一 memory notation：\(C\) 仅表示 physical memory capacity，\(M^*\) 表示 fluid-equilibrium memory requirement，\(M^\pi\) 表示 base threshold memory，\(M_{\mathrm{req}}^{(\zeta,\pi)}\) 表示 scaled-policy required memory。
- 对齐 WAIT 与 Nested WAIT 的 \(\zeta\)-scaled notation：WAIT 中 \(M_{\mathrm{req}}^{(\zeta,\pi)}=M^\pi\) 且不依赖 \(\zeta\)；Nested WAIT 中 \(M_{\mathrm{req}}^{(\zeta,\pi)}\) 包含 finite-horizon downstream safety buffer。
- 在 WAIT 和 Nested WAIT theorem 前补充可读解释：\(M^*\le C\) 是 fluid-model stabilizability condition，定理证明阈值策略能在 stochastic system 中实现对应稳定性并控制 memory growth。

### 实验与 Section 6 口径
- 修正 real-data Nested WAIT calibration 的参数解释，避免暗示 \(\mathrm{tl}\) 或 segment count \(L\) 越大越好。
- 当前口径改为 finite-grid tradeoff：太小的 \(\mathrm{tl}\) underuses batching/control，太大的 \(\mathrm{tl}\) 会增加 overflow pressure；太少的 segments 模糊 decode-stage 差异，太多的 segments 会 fragment segment-level caps 并让 prompts 更频繁地在 segment thresholds 等待。
- 移除 `threshold collection` 这类未在正文建立的术语，改为 `first-segment waiting condition` 或 `prompts wait at segment thresholds`。

### Response letter
- R2.3 对 \(C\ge M^*\) 的回复改为更正面、更贴合正文的表述：\(M^*\le C\) 说明 workload 在 fluid model 中 stabilizable，policy question 是 online scheduler 能否在 memory grows over time 的 stochastic system 中实现这种 stability。
- Response letter 现在强调 revision comprehensively evaluates underloaded, near-overloaded, and overloaded regimes across synthetic and heterogeneous workloads，并观察到实验结果与 threshold-based admission 的理论机制一致。

## 关键文件变更

| 文件 | 说明 |
|------|------|
| `papers/known_type.tex` | WAIT theorem 前新增 \(M_{\mathrm{req}}^{(\zeta,\pi)}=M^\pi\) 说明和 fluid-model stabilizability 解释 |
| `papers/unknown_type.tex` | Nested WAIT theorem 前新增 safety-buffer 与 stochastic stability 解释 |
| `papers/numerical.tex` | real-data Nested WAIT 参数段改为非单调 finite-grid tradeoff |
| `papers/response_letter.tex` | R2.3 回复重写为 stability-region / across-regimes validation 口径 |
| `papers/extension.tex` | time-varying extension 用 `first-segment waiting` 替换 `threshold collection` |
| `docs/paper_state/opre_revision/*.md` | 同步 terminology、symbols、framing、overview、consistency log |

## 验证情况

- `rg` 检查：active paper/state 中不再有 `ideal-fluid` 残留。
- `rg` 检查：paper-facing source files 中不再有 `threshold collection` 残留；该短语仅保留在 progress/state 文档中作为已移除术语的记录。
- 已完成 local consistency scan：WAIT / Nested WAIT / extension 中 \(C\)、\(M^\pi\)、\(M_{\mathrm{req}}^{(\zeta,\pi)}\) 的用法一致。

## 下一步计划

- 继续按 reviewer/AE/DE concern checklist 检查 response letter 与 revised paper 的覆盖关系。
- 若需要提交最终版，先运行一次 paper-pipeline quick/status 检查 undefined references、overfull boxes、figure/table labels 和 response-letter consistency。

---

**作者**: Codex
**审核**: 待审核
