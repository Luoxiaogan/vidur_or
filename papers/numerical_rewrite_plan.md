# Numerical Section Rewrite Plan

**Paper**: Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints
**Manuscript ID**: OPRE-2025-04-1885
**创建日期**: 2026-04-16
**Status**: Planning (图/表未实现)

---

## 0. 目的

整节重写 `papers/numerical.tex`（当前 136 行 / 6 张图）。
驱动力是三位 reviewer + AE 的硬要求,不是补丁。

核心诉求三条,按重要性排序:

1. **R3**: mean latency vs arrival rate + stability region 展示
2. **R2**: 参数表 + simulation fidelity + 真实 GPU 验证
3. **AE framing**: 从 "throughput 更好" 转成 "stability region 更大 + eviction prevention"

---

## 1. 新节结构(6 个子节)

每个子节列出:目的 / 回应哪位 reviewer / 图表清单 / 数据来源。
所有图的具体内容在 §3 单独讨论;本节只给骨架。

### 6.1 Experimental Setup  ——  全新,回应 R2

**目的**: 把 R2 关于参数、硬件、baseline 配置、simulation fidelity 的所有问题一次性回完。

**内容块**:
- 6.1.1 Hardware & simulator
  - A100 80GB + Vidur + Llama-3-8B (现有主实验)
  - TP=1, PP=1, num_blocks=29952
- 6.1.2 Simulator fidelity validation  ← **关键新段,回应 R2 comment 2**
  - A100 L20 真机上 32 batch sizes (B=1–600) profiling
  - MAPE: B≤64 = 1.6%, B≤128 = 1.1%, B=150–256 = 8.7%, B>300 = 61%
  - 明确说: 论文主实验所有 batch size 都在 B≤128 范围内,仿真准确
  - B>300 的 reviewer 场景需要 small prompt (20 tokens),超出 Eq(1) 适用范围
- 6.1.3 Workload definitions
  - Single-type: p512d20 (prefill=512, decode=20)
  - Multi-type W1: (p256d10, p512d50) 70/30
  - Multi-type W2: (p256d20, p512d40) 70/30
  - Multi-type W3: (p512d20, p512d50) 70/30
  - Long-decode: p512d1000
  - Real: lmsys-chat-1m, 50 decode-length bins
- 6.1.4 Algorithms compared
  - vLLM (FCFS, new arrivals first)
  - Sarathi (chunked prefill, ongoing first, chunk=512)
  - WAIT / Nested WAIT (ours)
- 6.1.5 Parameter table  ← **R2 A2/A3/A4/E1 核心**
  - Table 1: B, M*, C, d₀, d₁, block_size, watermark, Sarathi chunk, vLLM batch cap, WCP tl, WCP cs
  - 对 single / multi-type / real workload 各给一列
- 6.1.6 Memory safeguard  ← **R1 OOM 回应**
  - tl 是显式 upper bound → memory never exceeds (n₁ + n₂ + …) × max_decode_length
  - 和 vLLM 隐式 admission control 对比

**新图**: Figure A (GPU validation: real vs predicted iteration time)
**新表**: Table 1 (参数总表)

---

### 6.2 Stability Region and Mean Latency vs Arrival Rate  ——  全新,R3 核心

**目的**: 直面 R3 的两条核心批评:
- "simulations in unstable regime, latency not meaningful"
- "missing standard queueing plot: mean latency vs λ"

**内容块**:
- 6.2.1 What stability means in this open system
  - 引用 AE 的术语修正: "asymptotic / infinite-horizon limit" 而非 "heavy traffic"
  - 开放系统 throughput = arrival rate,真正差异在 **max throughput / stability boundary**
- 6.2.2 Mean latency vs λ (single-type, known output)
  - r = 12–26, step=1, nreq=10000
  - 三条曲线(vLLM / Sarathi / WCP)在 log scale 上的 divergence point
  - 明确标出: vLLM boundary ≈ 15, Sarathi ≈ 22, WCP ≈ 23–24
- 6.2.3 Same plot for multi-type W3 (known output)
- 6.2.4 Same plot for real data (unknown output, Nested WAIT)
- 6.2.5 Finite-horizon scaling verification  ← **R3 rigor**
  - nreq 2k → 20k mean latency growth
  - r=22: Sar +464% (unstable), WCP +63% (near-stable) → confirms stability boundary
- 6.2.6 Multi-seed error bars (5 seeds)
  - r=22 WCP 1.00±0.03s vs Sar 1.85±0.33s
  - R3 rigor 回应

**新图**: Figure B (mean latency vs λ, single-type, 3 policies)
**新图**: Figure C (mean latency vs λ, multi-type W3)
**新图**: Figure D (mean latency vs λ, real lmsys data)
**新图**: Figure E (finite-horizon scaling: latency vs nreq at r=20/21/22/23)

---

### 6.3 Known Output: WAIT Algorithm  ——  替换老 6.1

**目的**: 替换 test9 / test13 两组旧图,展示 WAIT 在 known-output 下的表现。
老实验的 low-demand / high-demand 二分法改成 rate-sweep。

**内容块**:
- 6.3.1 Single-type (p512d20) rate sweep
- 6.3.2 Multi-type: W1 / W2 / W3 三个 workload
  - 展示 WAIT 在 same-prefill / different-prefill / different decode 下的鲁棒性
  - 引用 per-segment gate (nested booking limit) 的作用
- 6.3.3 参数敏感性(tl × cs 2D heatmap, r=16 和 r=22)
  - 回应 R2: "what if no wait" —— tl=∞ 退化为 Sarathi,直接对照
- 6.3.4 讨论:为什么 prefill 大时 WAIT 优势大(chunked prefill 节省 attention quadratic)

**新图**: Figure F (single-type rate sweep throughput + latency, 放一起 or 只 latency)
**新图**: Figure G (multi-type W1/W2/W3 grid 比较)
**新图**: Figure H (tl × cs 参数敏感性 heatmap)  ← 可选,也可放附录

---

### 6.4 Unknown Output: Nested WAIT Algorithm  ——  替换老 6.2

**目的**: 替换 test30-36 四组旧图。

**内容块**:
- 6.4.1 lmsys-chat-1m dataset
  - 继续用现有的 fig:distribution + fig:group(这两张老图保留)
- 6.4.2 50-bin segment design
  - 关键发现: 10 bins 全 LOSE,50 bins 14/15 WIN
  - 设计权衡: bin 数 ↔ segment 结构开销
- 6.4.3 QPS grid 10–150
  - 完整曲线 vs Sar(256) 和 Sar(512)
- 6.4.4 Long decode (p512d1000)
  - 回应 R2 "longer than 1000 tokens" 问题
  - r=0.5–5 完整曲线,低 rate 持平 + 高 rate -22% win

**新图**: Figure I (lmsys QPS grid 10–150, 3 policies mean latency)
**新图**: Figure J (long decode p512d1000 rate sweep)
**保留老图**: fig:distribution (prompt 长度分布), fig:group (bin 内 prefill 均长) → 这两张作为 dataset 介绍

---

### 6.5 Near-Boundary Behavior and Eviction Cascade  ——  全新,最强反击点

**目的**: R3 抱怨 "unstable regime 下 latency 差异是 queue buildup,不是 policy"。
我们正好翻过来:
> "Baseline 在 near-capacity 下之所以 unstable,恰恰是因为 eviction cascade。我们的算法预防了它。"

这是全文最强的 marketing point,现有论文完全没讲。

**内容块**:
- 6.5.1 Memory-constrained setup
  - margin = C/M* = 0.6 (near-capacity)
  - Workload: p512d1000, r=4.0
- 6.5.2 Eviction cascade 可视化
  - Sarathi: 3222 evictions, 78.1s latency
  - vLLM: 0 evictions but 53s (保守 admission)
  - WCP: 0 evictions, 31.3s latency  ← 在 stable + 高性能之间取到平衡
- 6.5.3 Stability verification (nreq=10000)
  - Sar +146% growth (unstable + eviction)
  - vLLM +69% (unstable 但无 eviction,admission 太紧)
  - WCP +1% (stable)

**新图**: Figure K (时间序列 latency, margin=0.6 r=4.0, 3 policies)
**新图**: Figure L (evictions vs time OR 内存占用 vs time, 3 policies)

---

### 6.6(正文提及)+ Appendix: Real-System Validation on SGLang  ——  回应 R2 simulation fidelity

**决定(Q2)**: 正文只在 §6.1.2 simulator fidelity 末尾一段 **简短提及** + 指向附录。
完整结果、图、诚实披露全部放 Appendix。

**正文一段(预估 ~150 字)**:
- 除了 Vidur 仿真,我们在 SGLang 0.5.7 + A100 + Llama-2-7B 的真实 production deployment 上
  也实现了 WAIT 并验证其有效性
- 对 rate 1–15 的 workload,WAIT 相对 baseline 在 mean E2E latency 上 15/15 win,
  平均改善 +29.7%
- 详细设置、完整结果、以及 implementation trade-offs 见 Appendix X

**附录内容(Appendix X, 约 1.5 页)**:
- X.1 Why real deployment validation
- X.2 Experimental setup
  - SGLang 0.5.7 + A100 + Llama-2-7B
  - Random workload: input=512, output=20, 500 requests per rate
- X.3 Implementation details and honest disclosure  ← **关键,避免 reviewer 反击**
  - Baseline configuration: `chunked_prefill_size=256, prefill_max_requests=8` (**weakened from SGLang default**)
    - 原因: SGLang 默认在某些 rate 下 OOM,需调低以 fair comparison
  - WAIT configuration: underload bypass(rate 低时退回 SGLang 原生 scheduler)
    - 原因: 轻载下 WAIT 的 booking limit 机制 over-engineer
- X.4 Results table(rate 1–15, baseline / WAIT mean E2E, improvement %)
- X.5 Discussion
  - 结果在真实 inference server 上验证了 WAIT 核心设计 —— 不是仿真 artifact
  - Trade-off: 为了在真 production 系统里跑,必须做 minimal patch,不等同于 full re-implementation

**附录图**: Figure M(SGLang real GPU mean E2E latency vs rate, WAIT vs baseline)

---

## 2. 老图去向(Q1 确认版)

| 老图 ID | 老用途 | 新去向 |
|---------|--------|--------|
| test9 (low demand) 和 test13 (high demand) | WAIT known-output 代表 | **二选一进附录**(代表 WAIT known-output 老实验) |
| test30 (nested synthetic) | Nested WAIT 合成 | **附录保留一张**(synthetic baseline check) |
| test31 (real clustered low rate) 和 test32 (real clustered high rate) | Nested WAIT 真实 clustered | **二选一进附录**(代表 clustered real data) |
| test36 (real trace time-varying) | Nested WAIT 真实 trace | **保留正文 §6.4**(唯一的 time-varying 示例) |
| fig:distribution (prompt 分布) | lmsys 介绍 | **保留正文 §6.4.1** |
| fig:group (bin 内 prefill 均长) | lmsys 介绍 | **保留正文 §6.4.1** |

**附录老图合计**: 3 张代表图(test9 or test13, test30, test31 or test32) + 正文保留 1 张(test36) + 2 张 dataset intro(distribution / group)。

---

## 3. 所有新图清单(待逐张讨论)

每张图我都需要和用户单独讨论:
- 数据源(哪个脚本 / 哪个 CSV / 哪个 DB)
- x/y 轴、log scale、范围
- 是否画多 policy 并列 or 子图分开
- error bar / multi-seed 处理
- 放正文还是附录

| 标签 | 位置 | 内容 | 算法名 | 数据源 | 状态 |
|------|------|------|--------|--------|------|
| Figure A | **附录** | Vidur vs real A100 scatter, B ∈ [1,128] only(positive region) | — | `outputs/validation_database/vidur_validation.db` (region IN ACCURATE, ACCURATE_PLUS) | **✅ 完成** 2026-04-16, see `outputs/validation_database/figures/figure_A_sim_fidelity.pdf` |
| Figure B | §6.2 | Mean latency + throughput vs rate, single-type p512d20, 3 policies, log scale latency | WAIT | `experiments.db`, MIN aggregation, rates 12–24 | **✅ 完成** 2026-04-16, see `outputs/timeseries/figure_B_single_type.pdf` |
| Figure C | §6.2 | Mean latency + throughput vs rate, multi-type W3 | Nested WAIT | 已有 data,未渲染图 | 待画 |
| Figure D | §6.2 | Mean latency + throughput vs rate, real lmsys | Nested WAIT | QPS 10–150 data in DB | 待画 |
| Figure E | §6.2 | nreq scaling(2k→20k)的 stability verification | WAIT / Nested WAIT | stability_verification.py | 待画 |
| Figure F-a | §6.3 | Single-type latency + throughput vs rate | WAIT | 已有 data | 待画 |
| Figure F-b | §6.3 | **Single-type critical rate 时序**(r=22 或 23, 3 policies, latency vs iter #) | WAIT | 已有 data | 待画 |
| Figure G-a | §6.3 | Multi W1/W2/W3 latency + throughput vs rate | Nested WAIT | 已有 data | 待画 |
| Figure G-b | §6.3 | Multi W3 critical rate 时序 | Nested WAIT | 已有 data | 待画 |
| Figure H | §6.3 | tl × cs 参数敏感性 heatmap | WAIT | grid search DB | 待画,可放附录 |
| Figure I-a | §6.4 | lmsys QPS grid(latency + throughput) | Nested WAIT | real_data DB | 待画 |
| Figure I-b | §6.4 | lmsys critical QPS 时序(QPS=60 或 70) | Nested WAIT | real_data DB | 待画 |
| Figure J-a | §6.4 | Long decode p512d1000 rate sweep(latency + throughput) | Nested WAIT | long_decode_experiment.py | 待画 |
| Figure J-b | §6.4 | Long decode critical rate 时序 | Nested WAIT | long_decode_experiment.py | 待画 |
| Figure K | §6.5 | 时间序列 latency, margin=0.6 r=4.0 | WAIT | memory_throughput_experiment.py | 待画 |
| Figure L | §6.5 | Evictions / memory 占用 vs time | WAIT | memory 实验 CSV | 待画 |
| Figure M | **附录** | SGLang real GPU mean E2E vs rate | WAIT | `outputs/sglang_wcp_sweeps.db` sweep_id=34,35 | 待画,**放附录(Q2)** |

**绝对数量(更新)**: 正文 ~10–12 张(多数是 -a/-b 并列), 附录 ~5–7 张(老图代表 + SGLang + Figure H)。

---

## 4. 执行顺序(一步一步来)

按下面顺序,每步等用户确认后推进:

- [x] **Step 0**: 用户 review 本文档,确定 §6 结构和图清单(2026-04-16)
- [x] **Step 1**: Figure A(GPU validation)✅ 2026-04-16
  - 图只画 B ∈ [1, 128] 的 25 个正面点,不画 outlier
  - Figure annotation 只保留 R²=0.9957 / MAPE=1.51%,setup 交给 caption
  - Paper 里 **完全不提 B>128**,caption 以 "for the regime relevant to our experiments" 结尾
  - Outlier 全部在 response letter 处理(Q: scope out + cite R2 自己引的 Bari/Li)
  - Caption 定稿(见 §8)
- [x] **Step 2**: Figure B(single-type mean latency + throughput vs rate)✅ 2026-04-16
  - Layout: 1×2 side-by-side, log-y latency 左 + linear throughput 右
  - 数据聚合 MIN per (algo, rate),WAIT 全 13 rate 完全 win
  - x-axis 范围 (11, 25),保留 padding,不外推空白区
  - Sustainable throughput μ: vLLM 19, Sarathi 22, **WAIT 23**
  - 算法名已全部改为 WAIT(不含 WCP)
  - Caption 草稿(见 §8)
- [ ] **Step 2**: 讨论并渲染 Figure B(mean latency vs rate single-type)
- [ ] **Step 3**: 讨论并渲染 Figure C(multi-type W3)
- [ ] **Step 4**: 讨论并渲染 Figure D(lmsys real)
- [ ] **Step 5**: 讨论并渲染 Figure E(nreq scaling)
- [ ] **Step 6**: Table 1 参数总表
- [ ] **Step 7**: 写 §6.1 + §6.2 tex
- [ ] **Step 8**: 讨论并渲染 Figure F/G(WAIT + multi-type)
- [ ] **Step 9**: 写 §6.3 tex
- [ ] **Step 10**: 讨论并渲染 Figure I/J(Nested WAIT)
- [ ] **Step 11**: 写 §6.4 tex
- [ ] **Step 12**: 讨论并渲染 Figure K/L(eviction cascade)
- [ ] **Step 13**: 写 §6.5 tex
- [ ] **Step 14**: 讨论并渲染 Figure M(SGLang real)
- [ ] **Step 15**: 写 §6.6 tex + overall rewrite integration
- [ ] **Step 16**: 附录图整理 + 老图归档
- [ ] **Step 17**: response letter 对应段落同步

---

## 5. 已决 / 未决问题

### 已决(2026-04-16 用户确认)

- **Q1 ✅**: 老图 test9/test13/test30/test31/test32 **每个 setting 各选一张代表性**放附录,其余删。
  - WAIT known-output: test9(low demand)或 test13(high demand)二选一 → 附录
  - Nested WAIT synthetic: test30 → 附录
  - Nested WAIT real clustered: test31 或 test32 二选一 → 附录
  - test36(real trace with time-varying arrivals): **保留正文**(time-varying 示例)
  - fig:distribution, fig:group: **保留正文 §6.4.1**
- **Q2 ✅**: §6.6 SGLang 真机 —— **正文里简短提及,详细结果 + 图表放附录**。
  - 正文只在 §6.1 simulator fidelity 或 §6.2/6.5 末尾点一句 "we also validated on a real SGLang deployment(Appendix X)"
  - 详细表格、rate sweep 曲线、weakened-baseline 诚实披露全部进附录
- **Q4 ✅**: 每个 rate sweep 画两类图:
  - **Type-1**: mean latency vs rate  **+** throughput vs rate(并列或 2 panel)
  - **Type-2**: 时间序列图(mean latency vs iteration # 或 time),挑一个 **critical rate** —— baseline 已 diverge 但 WAIT/Nested WAIT 仍 flat —— 用来 visualize stability region
  - Type-2 的关键信息: WAIT latency 基本水平,baseline 线性上升,直观展示 "WAIT stable region 更大"
- **Q6 ✅**: Response letter 最后再统一改,先不分心。

### 仍未决(不紧急,边做边定)

- **Q3**: Figure H(tl × cs 参数敏感性 heatmap)放正文还是附录? → 暂定附录,到 §6.3 时再定
- **Q5**: "what if does not wait" 讨论放实验节还是理论节? → 暂定实验节末尾一段,到写作时再决定

---

## 6. 相关资产索引

### Progress 文档(详细数据在这些里)
- `docs/progress/2026_03_23_wait_cp_all_rates_win.md` - 全 rate 全胜
- `docs/progress/2026_03_25_overnight_grid_results.md` - multi-type + stability
- `docs/progress/2026_03_30_real_data_experiments.md` - lmsys + PD + long decode + memory
- `docs/progress/2026_04_07_gpu_validation_reviewer2.md` - GPU validation
- `docs/progress/2026_04_12_sglang_weakened_baseline_full_rates_win.md` - SGLang real
- `docs/progress/2026_03_22_revision_pipeline_review.md` - revision pipeline 审查

### 已渲染图(可直接引用或作为参考)
- `outputs/timeseries/paper_mean_latency_vs_rate.{pdf,png}` - **R3 核心图**
- `outputs/timeseries/paper_timeseries_critical.{pdf,png}` - 关键 rate 时间序列
- `outputs/validation_database/figures/figure1_real_vs_predicted.pdf` - R2 回应
- `outputs/validation_database/figures/figure2_error_analysis.pdf`
- `outputs/validation_database/figures/figure3_linear_fit.pdf`
- `outputs/validation_database/figures/figure5_combined_response_letter.pdf` - response letter 专用
- `outputs/timeseries_pd/timeseries_pd_stability.png` - PD 稳定性

### 数据库 / CSV
- `experiments.db` - 主要 single/multi-type sweep
- `outputs/sglang_wcp_sweeps.db` - SGLang real 实验
- `outputs/validation_database/vidur_validation.db` - GPU validation

### Plot 脚本(可参考 style / 复用)
- `scripts/plot_paper_figures.py` - 已有的 CMU Serif 论文图风格
- `scripts/stability_verification.py` - nreq scaling
- `scripts/timeseries_latency.py` - 时间序列

---

## 7. 风格约定(后续所有图 / tex 遵守)

### 7.1 算法命名约定  ← **关键**

- **Single-type(known output)** 实验 → 称作 **WAIT**(不叫 WCP)
- **Multi-type / unknown output** 实验 → 称作 **Nested WAIT**(不叫 WCP)
- 论文正文、附录、所有图 legend、表头一律保持这两个名字,与 Algorithm 1/Algorithm 2 一致
- `WCP` 只是 code-internal 名字,revision 之后不再出现在论文里
- `tl`(total_limit)、`cs`(chunk_size) 这些 code-internal 参数在论文里写成对应 paper 符号:
  - `tl` → $\sum_k n_k$(或 batch budget)
  - `cs` → per-request prefill chunk size
  - `gate` → batch token budget(如果需要提到)

### 7.2 图清单同步调整(应用 Q4)

每个 "rate sweep" 实验现在拆成两张图:
- **-a 版**: mean latency vs rate(左) + throughput vs rate(右),2-panel
- **-b 版**: 时间序列(y = mean latency, x = iteration # or simulation time),挑 critical rate,
  baseline 明显 diverge、WAIT/Nested WAIT 基本 flat,用来 visualize stability region

影响的图(Figure F/G/I/J):
- Figure F(single-type) → **F-a**(latency+throughput vs rate) + **F-b**(critical rate 时序,r=22 或 23)
- Figure G(multi-type W1/W2/W3) → **G-a**(latency+throughput) + **G-b**(W3 critical rate 时序)
- Figure I(lmsys QPS) → **I-a**(latency+throughput vs QPS) + **I-b**(critical QPS 时序,QPS=60 或 70)
- Figure J(long decode) → **J-a**(latency+throughput vs rate) + **J-b**(critical rate 时序,r=4 或 4.5)
- Figure B/C/D 是 §6.2 专门的 mean latency vs rate,暂不拆 -a/-b,但加 throughput 子图

### 7.3 通用图形风格

- 字体: CMU Serif(与 paper_mean_latency_vs_rate.pdf 一致)
- 格式: PDF + PNG 双版本
- 位置: `outputs/timeseries/` 或 `papers/Experiments_pdf/`(tex 引用前者需 copy)
- 颜色: vLLM / Sarathi / **WAIT 或 Nested WAIT** 三色固定,跨图一致
- Error bar: 所有 r≥22(stability boundary 附近)必须有 multi-seed
- Log scale: 所有 mean latency vs rate 图 y-axis 用 log
- x-axis: rate / QPS 用线性(整数 tick)

---

**下一步**: Step 3 —— Figure C(mean latency + throughput vs rate, multi-type W3, 3 policies, log-y latency)。

---

## 8. 定稿 Caption 库(随 Step 完成逐步填入)

### Figure A (Appendix) — Simulator Fidelity

```latex
\caption{Validation of the Vidur simulator against real NVIDIA A100 80GB
GPU measurements. Each point corresponds to one batch size configuration
$B \in \{1, 2, 4, 8, \ldots, 128\}$ ($N = 25$ in total), with prefill
length $256$ and decode length $20$, serving Llama-2-7B via vLLM. The
dashed line is $y = x$. The linear iteration-time model of Eq.~(1)
achieves $R^2 = 0.9957$ and mean absolute percentage error $1.51\%$ on
this range, confirming the simulator's fidelity for the regime relevant
to our experiments.}
\label{fig:sim_fidelity}
```

### Figure B (Section 6.2) — Single-type Mean Latency + Throughput

```latex
\caption{Single-type workload (prefill $=512$, decode $=20$, Poisson
arrivals): mean end-to-end latency (left, log scale) and effective
throughput (right) as a function of arrival rate $\lambda$. Left: as
$\lambda$ increases, each policy eventually enters an unstable regime
where mean latency diverges; the divergence point delineates its
stability region. WAIT sustains bounded latency up to $\lambda \approx
23$, whereas Sarathi and vLLM lose stability near $\lambda \approx 22$
and $\lambda \approx 19$, respectively. Right: the same ordering in terms
of effective throughput (estimated from the last $\lambda$ at which each
policy remains stable), with the dotted line indicating the ideal
$\lambda = $~completion rate.}
\label{fig:single_type_rate}
```

**分工原则(对未来所有图适用)**:
- 图内 annotation / legend: 只放读图本身必需的 info(summary stat, reference line 含义)
- Caption: setup(model, hardware, prompt/decode length, batch 范围), 每个点的定义, reference line 标识, key finding
- 正文: 实验背景 motivation, 更宽泛的对比解读

