# OR Revision: Long-Decode Figure/Table Polish - 2026-04-25

## 状态
✅ 已完成

## 概要
本轮工作集中收敛了 Section 6 中 long-decode 段落、Figure G 与 eviction table 的口径一致性，并反复迭代主文图的页面级视觉效果。最终锁定为：正文与 table 的 latency 主比较都沿用 figure 对应的 baseline-memory 数字，而 eviction 只作为同一 arrival rate 下的 near-capacity 补充诊断保留；同时，这轮也沉淀出一组更重要的 figure 美化原则，适合后续主文图继续复用。

## 完成内容

### Long-decode narrative alignment
- 将 `papers/numerical.tex` 中 long-decode 段落的主口径恢复为与 Figure~`\ref{fig:long_decode}` 一致的 baseline-memory latency 比较：
  - Sarathi `30.2`\,s
  - WAIT `26.4`\,s
- 保留同一 `\lambda=4.0` 下的 tightened-memory eviction 诊断，但不再让该诊断覆盖主文 latency 口径。
- 将机制表述统一为：
  - 机制层面使用 `eviction`
  - 表格指标使用可观测的 `eviction-induced restart rate`

### Figure G visual refinement
- 将 `scripts/plot_figure_G_long_decode.py` 重构为与 synthetic section 更接近的双栏布局：
  - 左图为 stretched nonlinear latency axis
  - 右图为 stylized effective-throughput panel
- 为三条曲线加入轻微 horizontal dodge，使相同 arrival rate 的 marker 不再重合。
- 明确标出 transition points，并在多轮视觉迭代后解决页面级 overlap：
  - 左图 `Transition points` callout 移到上中部空白区，不再与 legend 冲突
  - 右图 `\lambda=4.0` 处的 baseline transition rings 进一步错开
  - legend 间距略收紧，缩到正文页宽后仍可读

### Figure 美化心得（本轮稳定下来的经验）
- **先看 page-scale，再看 standalone**:
  真正会暴露问题的是主文页宽下的缩放效果，不是脚本刚生成出来的单图预览；legend、callout、marker 的冲突必须在编译后的 `papers/LLM_or.pdf` 里检查。
- **不要为了“更好看”去改结果**:
  这轮反复确认后，保留了原始 long-decode latency 数据，只通过轴变换、布局、标注位置和轻微 marker dodge 提高可读性；视觉优化不能以篡改结果为代价。
- **优先用主轴设计解决可读性，不要轻易加 zoom inset**:
  对这张图来说，zoom 既没有真正解决低载区分辨率问题，也让整体版式更乱。更有效的是直接调整主轴的 nonlinear stretch，让低载区和 near-boundary 区同时可读。
- **transition points 要显式标，但标注系统必须服从留白**:
  仅靠正文解释不够，transition points 在图上必须直接可见；但 callout 盒子、箭头和圈点一旦挤占 legend 或主曲线，就会破坏阅读路径，所以要优先把标注锚定到天然留白区。
- **同一 arrival rate 的多策略点位必须有轻微分离**:
  当三条曲线在低载区非常接近时，完全重合的 marker 会让“几乎无差别”和“根本看不见”混为一谈。轻微 horizontal dodge 是诚实且有效的处理，因为它不改变数值，只改善辨识度。
- **右图语义必须和左图 takeoff 对得上**:
  throughput panel 可以是 stylized 的，但 knee / plateau 位置必须和左图 latency takeoff 的边界一致；否则读者会先看到视觉矛盾，再去怀疑整张图。
- **caption 不要替代图本身**:
  如果必须靠 caption 解释“这两个点其实不重合”或“这里其实有优势”，说明图还没画好。caption 应该只概括读图结论，而不是替图补视觉缺陷。

### Consistency checks carried along this round
- 校正了 synthetic figures 的 stylized throughput boundary，使其与 latency takeoff 更一致：
  - `scripts/plot_figure_B_compare.py` 中 Sarathi boundary 调整为 `22`
  - `scripts/plot_figure_C_multi_type.py` 中 Sarathi boundary 调整为 `21`
- 同步把 single-type / two-type 的正文 stability-boundary 文字更新到与图一致。
- 持续同步 `docs/paper_state/opre_revision/changelog.md`，记录这轮口径修正与图形 refinement。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 |
| 修改文件 | 6 |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/numerical.tex` | 修改 | long-decode 段落、Figure G caption、eviction table/caption 口径统一 |
| `scripts/plot_figure_G_long_decode.py` | 修改 | Figure G 双栏重绘、transition callout 与 marker 布局 refinement |
| `scripts/plot_figure_B_compare.py` | 修改 | synthetic single-type throughput boundary 校正 |
| `scripts/plot_figure_C_multi_type.py` | 修改 | synthetic two-type throughput boundary 校正 |
| `papers/Experiments_pdf/figure_G_long_decode.pdf` | 修改 | 主文 long-decode 图替换为最新版本 |
| `docs/paper_state/opre_revision/changelog.md` | 修改 | 记录 long-decode narrative / figure 迭代过程 |

## 相关 Commits

```text
4c59249 Update GPU real-trace wait-gate progress
（本轮为未提交的 working-tree 修改，尚无独立 commit）
```

## 遇到的问题与解决

### 问题 1: 相同 `\lambda=4.0` 下 figure 与 table 的 latency 数字不一致
**现象**: 主文段落和 Figure G 使用 baseline-memory rate sweep，而 table 一度改成 near-capacity latency，导致同一个 arrival rate 下图表口径不一致。
**原因**: eviction diagnostic 与 main latency comparison 被混在同一张表里，叙述口径被带偏。
**解决**: 恢复 table 的 latency 行为 baseline-memory 数字 `30.2`\,s vs `26.4`\,s，只把 `2.88%` vs `0%` 保留为 near-capacity 的 eviction-induced restart diagnostic。

### 问题 2: `eviction` 与 `restart` 术语使用不一致
**现象**: 前文强调的是 eviction 机制，但表格里需要报告的是可测指标，直接混写会显得口径不稳。
**原因**: 机制名词与度量名词没有分开。
**解决**: 统一改为“机制写 eviction，指标写 eviction-induced restart rate”，并在正文说明 last-in-first-out eviction 会导致请求从 prefill 重新开始。

### 问题 3: Figure G 在论文页宽下仍有 overlap
**现象**: 左图 callout 与 legend 抢占同一区域，右图 `\lambda=4.0` 的两个 baseline transition markers 在页宽下显得拥挤。
**原因**: standalone 预览可接受，但缩进论文版面后元素间距不够。
**解决**: 通过 page-scale 反复检查，最终将左图 callout 锚定到上中部空白区，并把右图两个 markers 进一步横向分离。

### 问题 4: 视觉优化容易滑向“caption 解释型修补”
**现象**: 某些版本只有结合 caption 才能理解 transition points、稳定区间和 near-boundary 优势，图本身的信息密度不够。
**原因**: 早期迭代把精力放在加元素，而不是先整理视觉层级与留白。
**解决**: 后续统一改成“图先自解释，caption 再压缩总结”的原则；优先处理轴、布局、marker separation 和 annotation placement，再写 caption。

## 测试情况

- [ ] 单元测试通过
- [ ] 集成测试通过
- [x] 手动核对 `papers/numerical.tex` 段落、caption 与 table 口径一致
- [x] 运行 `python scripts/plot_figure_G_long_decode.py` 重新生成图
- [x] 运行 `latexmk -pdf -interaction=nonstopmode LLM_or.tex` 完成主文编译
- [x] 以页面尺度检查更新后的 `papers/LLM_or.pdf`

## 下一步计划

- [ ] 继续按用户逐段 review 的节奏打磨 Section 6 其余段落
- [ ] 如有需要，再对 Figure G 的 legend / callout 做更轻量的视觉收尾
- [ ] 在下一轮较大文本改动后，继续同步 `docs/paper_state/opre_revision/` 与 `.claude/CLAUDE.md`

## 相关文档

- [Section 6 editorial polish](./2026_04_23_section6_editorial_polish.md)
- [Main experiments section](../../papers/numerical.tex)
- [Figure G plotting script](../../scripts/plot_figure_G_long_decode.py)
- [Paper-state changelog](../paper_state/opre_revision/changelog.md)
- [Main paper PDF](../../papers/LLM_or.pdf)

---

**作者**: 自动生成（update-progress workflow + 当前 long-decode refinement 轮次）
**审核**: 待审核
