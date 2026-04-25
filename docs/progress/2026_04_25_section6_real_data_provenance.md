# Section 6 real-data provenance and figure polish - 2026-04-25

## 状态
🚧 进行中

## 概要
This update records the Section 6 polish state after the long-decode figure/table pass and the real-data provenance audit. The main outcome is that the synthetic and long-decode figures are now visually aligned with the paper narrative, while the lmsys real-data subsection is explicitly marked as needing source-of-truth reconstruction before final paper claims are locked.

## 完成内容

### Section 6 figure and table consistency
- **Long-decode Figure G**: iteratively redesigned the latency/throughput layout so the low-load region, near-boundary gaps, transition markers, and legend remain readable at manuscript scale.
- **Long-decode table**: aligned the latency row with the corresponding Figure G baseline-memory values and kept eviction evidence as a supplementary near-capacity diagnostic.
- **Synthetic figures**: checked stylized throughput panels against latency knees and corrected mismatched transition-point locations.
- **Figure style rules**: extracted reusable page-scale figure refinement rules into `docs/research/paper_figure_style_rules.md`.

### Real-data provenance audit
- **SQL audit**: confirmed that local `experiments.db.real_data` does not contain the full lmsys QPS 10--150 tuning grid; it only preserves a partial early sweep.
- **Script audit**: confirmed that the paper-facing Vidur tuning scripts use `meta-llama/Meta-Llama-3-8B`, while GPU validation/Figure A uses Llama-2-7B.
- **Config provenance**: recorded that progress notes preserve the full plotted real-data latency grid but not the complete per-QPS winning Nested WAIT configs.
- **VM prompt**: added a dedicated prompt for investigating VM-side stdout logs, SQL files, shell history, and surviving Vidur artifacts.

### Paper-state synchronization
- **State docs**: initialized and updated `docs/paper_state/opre_revision/` to track Section 6 decisions, figure/table status, terminology locks, and real-data remeasurement items.
- **Archive cleanup**: moved old revision planning files under `papers/archive/` to separate active paper files from historical working notes.
- **Appendix alignment**: updated simulator-fidelity/configuration text to reduce stale fixed-parameter claims while the real-data provenance remains unresolved.

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增进度/状态文档 | 5+ |
| 修改论文源文件 | 多个 Section 6 / appendix files |
| 修改绘图脚本 | 4 |
| 生成/更新论文图 | 4 main Section 6 PDFs |
| 归档旧工作文档 | 8 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/numerical.tex` | 修改 | Section 6 paragraph-by-paragraph polish, long-decode and real-data text updates |
| `papers/appendix_sim_fidelity.tex` | 修改 | Experimental configuration wording synchronized with current Section 6 caveats |
| `scripts/plot_figure_G_long_decode.py` | 修改 | Long-decode figure redesign and transition-marker layout |
| `scripts/plot_figure_B_compare.py` | 修改 | Synthetic single-type transition-point alignment |
| `scripts/plot_figure_C_multi_type.py` | 修改 | Synthetic two-type transition-point alignment |
| `scripts/plot_figure_D_lmsys.py` | 修改 | Real-data figure table now reflects recorded 14/15 raw result rather than all-win smoothing |
| `docs/progress/2026_04_25_real_data_parameter_audit.md` | 新增 | Source-chain audit for lmsys tuning parameters |
| `docs/progress/2026_04_25_vm_real_data_tuning_investigation_prompt.md` | 新增 | VM-side investigation prompt for recovering missing configs |
| `docs/research/paper_figure_style_rules.md` | 新增 | Reusable figure-polish rules from Figure G iteration |
| `docs/paper_state/opre_revision/` | 新增 | Active OPRE revision state bundle |

## 相关 Commits

```
d88c490 docs: add VM real-data tuning investigation prompt
```

This report is being committed together with the current Section 6 paper and documentation state.

## 遇到的问题与解决

### 问题 1: Real-data Figure D lacks a durable SQL source of truth
**现象**: The plotted QPS 10--150 values are recorded in progress docs and plotting arrays, but the SQL database does not preserve the complete per-QPS winning Nested WAIT configurations.
**原因**: The original real-data tuning scripts printed filtered candidate rows and deleted temporary output directories instead of writing all trials to SQLite.
**解决**: Added a provenance audit and a VM investigation prompt. Final real-data claims should be locked only after VM logs/SQL are inspected or the grid is rerun with durable logging.

### 问题 2: Model naming is inconsistent across paper-facing experiments
**现象**: Active Section 6 text says Llama-2-7B, but the paper-facing Vidur tuning scripts use `meta-llama/Meta-Llama-3-8B`; GPU validation/Figure A uses Llama-2-7B.
**原因**: Simulation experiments and GPU-validation experiments evolved on different tracks.
**解决**: Recorded the inconsistency. The paper must either distinguish the two tracks explicitly or rerun/realign the validation and simulation model claims.

### 问题 3: Segment-count language was conflated with workload bins
**现象**: Earlier real-data prose risked treating `50 bins` as an algorithmic segment-count parameter.
**原因**: In the code, bins discretize the workload, while `segment_size` only applies to `uniform_segment_chunked`; `general_nested_chunked` induces segments from unique decode lengths in prompt types.
**解决**: Rewrote the audit note and marked the current segment-ablation interpretation as unresolved unless raw evidence is recovered or the experiment is rerun.

## 测试情况

- [x] Paper compilation was run during the Section 6 polishing loop.
- [x] Figure PDFs were regenerated and inspected at manuscript scale.
- [x] SQLite schemas and row coverage were manually queried.
- [ ] Full real-data grid rerun is not yet complete.
- [ ] VM-side stdout/job-log recovery is pending.

## 下一步计划

- [ ] Run the VM investigation prompt and recover any missing real-data tuning logs.
- [ ] If logs are incomplete, write a SQL-logged lmsys rerun script and rerun the minimal QPS/config grid.
- [ ] Resolve the Llama-2 versus Llama-3 wording before finalizing Section 6 and Appendix A.
- [ ] Continue paragraph-by-paragraph polish of the real-data subsection only after provenance is settled.
- [ ] Recompile the full paper after the next Section 6 text pass.

## 相关文档

- `docs/progress/2026_04_25_real_data_parameter_audit.md`
- `docs/progress/2026_04_25_vm_real_data_tuning_investigation_prompt.md`
- `docs/progress/2026_04_25_long_decode_figure_polish.md`
- `docs/paper_state/opre_revision/real_data_remeasurement_checklist.md`
- `docs/research/paper_figure_style_rules.md`

---

**作者**: Codex
**审核**: 待审核
