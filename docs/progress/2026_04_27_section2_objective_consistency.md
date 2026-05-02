# Section 2 Objective Consistency and Model Polish - 2026-04-27

## 状态
✅ 已完成

## 概要
本轮完成 Section 2 model/objective 口径整理，统一了理论中的 token-level effective throughput、实验中的 request-level effective completion rate，以及 TTFT 的服务质量含义。重点把 objective 段从抽象的 "throughput maximization" 改成 OR/queueing 风格的 offered-load cap、loss channels、admission-control balance 叙述，为继续 polish Section 3 做准备。

## 完成内容

### Section 2 model polish
- **Notation relocation**: 将正文 notation table 移到 appendix notation summary，正文改为 narratively 引入符号，并在首次出现处引用 Appendix notation table。
- **Inference process**: 重写 prefill/decode、stage、KV cache growth 描述，使第一次读者能直接理解 \(s=0\)、decode stage、resident KV cache memory 的含义。
- **Batching and iteration time**: 用连续 batching 的运营逻辑重写 batch 叙述，突出固定 overhead、larger batches、iteration time、memory pressure 的 tradeoff。
- **Memory example**: 将 toy example 统一为 "Hello" -> "Hi"，明确 prefill/decode 的 memory accounting，并解释 eviction cascade。
- **Objective and policy space**: 合并 performance metrics 与 policy space，先定义 finite-horizon metrics，再定义 admissible online policies 和 actions。

### Throughput / completion-rate consistency
- **Theory metric**: `\throughput^{(T,\pi)}` 和 `\throughput^{(\zeta,\pi)}` 统一解释为 completed decode tokens per unit time；被 evicted before completion 的 decode work 不计入 throughput。
- **Experiment metric**: Section 6 和 Figure B/C/D/G 的右图统一为 `effective completion rate`，即 completed requests/queries per second net of eviction-induced restarts。
- **Bridge sentence**: Numerical opening 明确说明实验中的 request-level diagnostic 是 theory token-level effective throughput 在 fixed workload distribution 下的实验对应物。
- **Notation table**: `papers/appendix_notation.tex` 补充 `\throughput^{(T,\pi)}`, `\Latency^{(T,\pi)}`, `\TTFT^{(T,\pi)}` 和 `\throughput^*` 的口径。

### Objective paragraph final wording
- **Offered-load cap**: 用 "For a fixed arrival process, effective throughput is capped by the offered decode-token load" 替换抽象的 "not unconstrained throughput maximization"。
- **Loss channels**: 明确 policy 低于上界的两类原因是 leaving capacity idle 或 admitting work that later restarts instead of completing。
- **Admission-control balance**: 将核心控制问题写成 utilization 与 memory feasibility 的平衡，解释其如何扩大 stability region，并在 overload 下接近 usable capacity。
- **TTFT role**: 明确 TTFT 防止 policy 为维持 aggregate completion counts 而反复优先 short prompts，导致 long prompts 的 first service 被长期推迟。

### Writing-advisor feedback capture
- **Captured pattern**: 记录 "offered-load cap -> loss channels -> admission-control balance" 的写作模式到 `comments/projects/vidur_or.md`。
- **Advisor rule**: 新增 theory rule `State the Offered-Load Cap Before the Control Implication`，供后续 Section 3/4 polish 复用。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 progress report + 1 appendix notation file |
| 修改文件 | Section 2/3/6 LaTeX, figure scripts, figure PDFs, paper-state docs |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `papers/model.tex` | 修改 | Section 2 重写：model setup, batching, memory cascade, objective/policy space |
| `papers/appendix_notation.tex` | 新增/修改 | 集中 notation table，并补充 finite-horizon performance metrics |
| `papers/known_type.tex` | 修改 | WAIT 理论段 throughput 口径改为 effective throughput / completed decode tokens |
| `papers/numerical.tex` | 修改 | 实验右图和正文统一为 effective completion rate，并解释 request-level vs token-level 口径 |
| `scripts/plot_figure_B_compare.py` | 修改 | Figure B 右图 label 改为 effective completion rate |
| `scripts/plot_figure_C_multi_type.py` | 修改 | Figure C 右图 label 改为 effective completion rate |
| `scripts/plot_figure_D_lmsys.py` | 修改 | Figure D 右图 label 改为 effective completion rate |
| `scripts/plot_figure_G_long_decode.py` | 修改 | Figure G 右图 label 改为 effective completion rate |
| `papers/Experiments_pdf/figure_B_single_type.pdf` | 修改 | 重新生成主文 Figure B |
| `papers/Experiments_pdf/figure_C_multi_type.pdf` | 修改 | 重新生成主文 Figure C |
| `papers/Experiments_pdf/figure_D_lmsys_real.pdf` | 修改 | 重新生成主文 Figure D |
| `papers/Experiments_pdf/figure_G_long_decode.pdf` | 修改 | 重新生成主文 Figure G |

## 测试情况

- [x] 重新生成 Figure B/C/D/G 对应 PDFs
- [x] 编译主文：`cd papers && latexmk -pdf -interaction=nonstopmode LLM_or.tex`
- [x] 编译产物：`papers/LLM_or.pdf`，79 pages
- [ ] 未运行 Vidur simulation；本轮是 writing/consistency/figure-label 更新

## 遇到的问题与解决

### 问题 1: throughput 在 theory 和 experiments 中单位不同
**现象**: Theory 使用 decode-token throughput，实验右图实际画的是 completed requests/queries per second。  
**原因**: 稳定性诊断在 fixed workload distribution 下等价，但文字和 axis label 不能混用同一个 throughput 术语。  
**解决**: Theory 保留 token-level `effective throughput`；experiments 改为 request-level `effective completion rate`，并在 numerical opening 中明确两者关系。

### 问题 2: Objective 段过早引用 fluid benchmark
**现象**: Section 2 objective 段在 Section 3 前使用 fluid throughput benchmark，读者尚未看到定义。  
**原因**: 叙述顺序把后文 formal object 提前当成已知对象。  
**解决**: Section 2 只讲 offered-load cap、memory-feasible operation、admission-control balance；段尾改为 "Later sections introduce the fluid reference system..."。

### 问题 3: Objective language 过于 AI/抽象
**现象**: 原句使用 "the relevant question is whether..."、"mechanism by which..." 等抽象表达。  
**原因**: 没有先给 OR/queueing 读者熟悉的 upper bound 和 concrete loss channels。  
**解决**: 改成 "offered-load cap -> idle/restart losses -> utilization/memory-feasibility balance" 的三步叙述，并 capture 为 writing-advisor rule。

## 下一步计划

- [ ] 继续逐段 polish Section 3，优先检查是否过早使用 Section 2 尚未正式引入的 benchmark/notation。
- [ ] 将 Section 3 中 `throughput`, `completion`, `fluid benchmark`, `stability region` 的口径与 Section 2 新定义对齐。
- [ ] 检查 theorem 前后的 interpretation 段，避免 generic "maximize throughput" 叙述。
- [ ] 在下一轮较大改动后重新编译主文并检查 Section 2-3 的 page flow。

## 相关文档

- `docs/paper_state/opre_revision/changelog.md`
- `docs/paper_state/opre_revision/consistency_log.md`
- `docs/paper_state/opre_revision/symbols.md`
- `papers/appendix_notation.tex`

---

**作者**: Codex
**审核**: 待审核
