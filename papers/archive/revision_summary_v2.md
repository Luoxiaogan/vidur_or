# Revision Summary: OPRE-2025-04-1885

**Paper Title**: Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints

**Decision**: Major Revision (Area Editor: Prof. Neil Walton)

**AE Recommendation**: Reject-and-Resubmit (但Area Editor给了Major Revision)

**Deadline**: 12 months from decision date

---

## 审稿源文件

| 文件 | 内容 |
|------|------|
| `AE_report.pdf` | Area Editor综合报告（3页）- 修改优先级指导 |
| `Review_for__Optimizing_LLM_Inference__Fluid_Guided_Online_Scheduling_with_Memory_Constraints_.pdf` | Reviewer 2详细评审（6页）- 最正面，含公式修正 |
| `Review_OPRE-2025-04-1885.pdf` | Reviewer 1评审（2页）- 符号问题和OOM机制 |
| `decision_letter.md` | 决定信原文（含Reviewer 3评审） |

---

## Executive Summary

论文研究LLM推理的调度优化问题，提出了基于fluid model的WAIT和Nested WAIT算法。三位审稿人一致认为**问题重要且及时**，但对**写作质量**、**模型假设的现实性**和**理论贡献的清晰度**提出严重关切。

### 风险警告 (来自Area Editor)
> "If these issues persist, I expect that the paper will be rejected by the team in the next round."

---

## Reviewer Summary

| Reviewer | Overall Tone | Key Concern |
|----------|--------------|-------------|
| Reviewer 1 (PDF) | Major Revision | 符号不一致、OOM机制、线性假设 |
| Reviewer 2 (PDF) | Positive | Eq(1)建模、理论证明细节、实验设置 |
| Reviewer 3 (决定信) | Negative | 排队论概念错误、贡献不显著、写作不清 |

---

## 核心论点总结 (Revision的行文指导)

**以下是反复强调、必须贯穿全文的核心points：**

### 1. Memory Constraint是核心问题
- KV cache随decode**动态增长**，这是与传统scheduling的根本区别
- 不是固定job size，而是memory在运行过程中不断增加
- 这导致**eviction风险**：即使capacity足够，不好的算法也会OOM

### 2. Eviction Prevention是关键创新
- 核心不只是throughput optimization，而是**避免eviction导致的cascading failure**
- **FCFS例子**：即使C≥M*（理论上stable），FCFS因eviction cascade导致系统unstable
- 本来stable的系统，因为算法不好也会变unstable

### 3. 算法让问题变得可分析（非问题本身简单）
- 系统本身**不是标准queueing**：memory grows, **multiple types相互影响**, eviction risk
- 不是简单的random walk，有多种type的复杂交互
- 是我们的**threshold mechanism实现了降维和decoupling**：复杂的multi-stage decode → tractable analysis
- 看似standard的分析，背后是算法设计的巧妙
- **注意**：降维是技术细节，introduction应强调高层insights（load balance, memory exploitation, eviction prevention）

### 4. Fluid Dynamics提供根本性洞见（高层次framing）
- **Fluid model的三大贡献**：
  1. 揭示equilibrium state（arrivals和completions平衡的状态）
  2. 刻画optimal steady-state memory M*（最大化throughput）
  3. 阐明memory exploitation机制（larger batch → 更高throughput）
- **Fluid equilibrium作为目标**：stochastic算法设计的指导原则
- 当stochastic system接近fluid equilibrium时：高throughput + 无eviction
- **这是introduction应强调的**：fluid insights → algorithm design

### 5. Approaching Load Balance的算法设计原则
- 核心原则：让stochastic system**尽可能接近fluid equilibrium**
- Threshold-based admission控制系统不drift away from balance
- 通过避免eviction，在不损失太多latency的情况下fully exploit throughput
- Baseline频繁eviction → 远离equilibrium；WAIT维持接近equilibrium
- 这是将fluid insights转化为实际算法的bridge

### 6. On-the-fly Classification处理Unknown Output
- Nested WAIT的核心创新：**不需要预测output length**
- Prompts在segment边界**自然分类**：短的完成，长的继续
- 短prompts快速完成，不被长prompts拖累
- **Safety buffer (Eq.16)**：显式机制hedge unknown output的uncertainty

### 7. 直接适用于PD分离系统
- 在Prefill-Decode Disaggregation系统中，decode端是**decode-only**
- Eq(1)的线性假设**完全成立**（无prefill attention项）
- 算法和分析直接适用，增强practical relevance

### 8. 与其他理论工作的对比定位
- **Zijie Zhou系列** (Jaillet, Wang, Chen)：假设τ=1（常数iteration time），focus on combinatorial scheduling
- **我们的工作**：显式建模memory bandwidth through KV-cache loading time
- 建模深度不同：我们捕获了memory constraint的核心特征

### 9. 贡献是建模insight，不只是数学技巧
- AE认可："properly establishing the connection between a novel domain (LLM inference) and a standard stochastic model is a significant contribution itself"
- 贡献在于：识别LLM inference的核心challenge (memory + eviction) 并设计算法使其tractable
- 数学看似standard是因为算法设计得好，不是问题本身简单

### 10. 即使Overloaded Regime也有效
- 理论分析focus on near-capacity regime (C ≥ M*)
- 但实验表明：**即使overloaded (C < M*)，算法仍显著优于baseline**
- 因为核心是eviction prevention，这在任何regime都有价值

### 11. Asymptotic Regime（非Heavy Traffic）
- 术语修改：将"heavy traffic"改为**"asymptotic regime"**
- 实际上是infinite-horizon limit（固定load，scale时间horizon）
- 不是传统heavy-traffic limit（load增加到stability边界）

### 12. Segment-wise设计的实用性 (2025-12-14新增)
- **Segment-wise Nested WAIT**：将m个type分组为更少的L个segments
- **两个目的**：
  1. 应对varying或uncertain的type distribution
  2. 对于long decode length，**无法保证每个stage都有prompt**，分组更稳定
- 这是实际部署时推荐的形式，理论保证相似

### 13. Exploit Memory to Improve Throughput (2025-12-14新增)
- **Linear time model**: τ = d₀ + d₁ × Memory，throughput ∝ batch size
- **Memory是资源，不只是约束**: 更大的batch → 每iteration处理更多prompts → 更高throughput
- 与eviction prevention是"一体两面"：
  - 一方面要**避免overflow**（eviction prevention）
  - 另一方面要**充分利用memory**来maximize throughput
- 算法目标：在safe limits内**最大化memory利用率**
- 这是"approaching load balance"的另一层含义：尽可能接近equilibrium batch size M*

---

**行文修改原则**：每个section都应围绕上述points展开，确保reviewer能清晰理解：
- 问题的独特性（不是标准scheduling，有memory growth + eviction + multiple types）
- 算法的核心思想（threshold → dimensionality reduction → eviction prevention → approaching load balance）
- 为什么看似simple的算法解决了non-trivial的问题
- 贡献是建模insight + 算法设计，不只是数学分析

---

## I. 最关键问题：写作质量 (所有审稿人)

### 1.1 符号不一致问题

**具体位置**:
- Page 8, line 26: `k` 定义为 decoding stage index
- Page 9, line 15: `k_i` 表示 prefill phase 的 input length
- Page 9, line 19: `k_i` 又重新定义为 decode phase 生成的 token 数
- Page 10, line 42: `k_i^t` 表示 current processing stage (不清楚具体含义)

**修改要求**:
- 统一或明确区分这些符号
- 提供符号表 (summary table of symbols)

### 1.2 Policy空间定义缺失

**问题**: π 在 Section 2.4 (page 11, lines 7-15) 首次出现，但没有正式定义 policy space Π。

**修改要求**:
- 严格定义 π 和 Π
- 在 Algorithm 1 之前提供直观解释

### 1.3 缺乏直觉和解释

**具体问题**:
- Fluid model 从未完全定义
- 公式结果没有解释 (如 throughput 公式的物理含义)
- Algorithm 1 之后缺少解释性文字
- 定理证明总结过于高层 ("The proof employs the coupling technique...")

**修改要求**:
- 在关键定义后添加直观解释
- 在主文提供证明的清晰逻辑框架
- 将部分证明移至主文或清晰sketch证明逻辑

### 1.4 具体Typos

| 位置 | 原文 | 修改 |
|------|------|------|
| Page 9, line 50 | `d` | `d_1` |
| LLM_or.tex line 125 | `\throughput` → "Thoughput" | "Throughput" |
| Page 35, line 4 | "Asmussen S, Asmussen S, Asmussen S" | 删除重复 |
| Page 39, line 38 | ".Consider" | ". Consider" |
| Page 39, line 40 | "type 2 with l_2 = 1" | 检查上下文 |

---

## II. 模型现实性问题

### 2.1 Equation (1) 的线性假设

**当前模型**:
```
τ = d_0 + d_1 · (Σ k_i + Σ s_i')
```

**Reviewer 2 建议的完整公式**:
```
τ = d_0 + d_1 · (Σ k_i + Σ s_i')     [KV-cache loading]
  + O(Σ k_i + n_2)                    [linear layer]
  + O(Σ k_i²)                         [attention (prefill)]
  + O(Σ s_i')                         [attention (decode)]
```

**三种渐近regime**:
1. **Long output / large batch size**: τ ≈ d_0 + O(Σ s_i')
2. **Long input context**: τ ≈ d_0 + O(Σ k_i²)
3. **Moderate input, batch, output**: τ ≈ d_0 + O(Σ k_i + n_2)

**修改要求**:
- 明确说明论文针对哪种scenario (似乎是scenario 1)
- 讨论线性假设在不同GPU架构上的局限性
- Figure 3 需说明具体的 {k_i, s_i'} 数值和实验设置

### 2.2 OOM (Out-of-Memory) 问题

**核心问题**:
- 如何保证KV cache使用不超过capacity constraint?
- output length不确定时如何防止OOM?
- 等待的jobs占用的内存是否计入constraint?

**Reviewer 3 的具体质疑**:
> Memory constraint seems to apply only to jobs in the batch currently being served. But jobs can be preempted and their KV caches can be preserved. Is this realistic? Moving memory between GPU and other locations would be time consuming.

**修改要求**:
- 明确讨论preemption是否允许 (理解是yes，保留unevicted KV-cache)
- 讨论memory移动开销是否可忽略，或提供数据支持
- 考虑是否需要将memory constraint应用于所有jobs (not just current batch)

### 2.3 假设 C ≥ M* 的现实性

**Reviewer 2 指出**:
> Consider a prompt type that produces 1000 output tokens; this implies at least a batch size of 1000 and a KV-cache of order 500K tokens even for n_j = 1. A 40GB A100 can maintain at most ~200K tokens of KV-cache for Llama3.1-8B.

**修改要求**:
- 明确说明这个假设不如表面看起来那么benign
- 在实验中说明是否满足这个假设

---

## III. 理论贡献问题 (Reviewer 3)

### 3.1 "Heavy Traffic"分析的误称

**问题**: 论文中的"heavy traffic"分析实际上是**infinite-horizon limit** (固定load下scale时间horizon)，而非真正的heavy-traffic limit (load增加到stability region边界)。

**修改要求**:
- 澄清使用的asymptotic regime
- 考虑使用更准确的术语

### 3.2 Throughput结果过于复杂

**Reviewer 3 指出**:
> The system is open, so if stable, throughput equals arrival rate. See the last line of equation (8) which can be obtained immediately. "Increasing throughput" might be better phrased as "increasing maximum throughput" or "maintaining stability throughout the entire stability region."

**回应策略** (Decision补充):
- **不改变整体optimization目标**，但可以用"maximizing stability region"作为一种interpretation
- **核心论点**：在接近overloaded的系统中，如何exploit throughput同时避免eviction/OOM导致system crash
- **关键例子**：如果算法不好，**本来stable的系统也会变unstable**（FCFS cascading failure）
- 这就是为什么我们的贡献不只是"throughput = arrival rate when stable"这么简单

### 3.3 Latency结果不显著

**问题**: Latency bounds主要来自Markov chain的positive recurrence，这在stable queues中是标准结果。

**回应策略** (Decision补充):
- **这不是标准的positive recurrence问题**
- 是我们通过**巧妙的算法设计**将系统转换到能用queueing theory分析的形式
- 看似standard，背后隐含的是：
  1. **降维** (dimensionality reduction through thresholds)
  2. **处理unknown output** (on-the-fly classification)
  3. **避免eviction/OOM** (controlled admission)
- **核心论点**：不是问题本身容易，是**算法让问题变得可分析**

### 3.4 算法创新性问题

**Reviewer 3 的理解**:
> The WAIT algorithm essentially has a pipeline for each job type, and at each decision point, WAIT advances a given job type's pipeline if and only if there are enough not-yet-started jobs to keep the pipeline full.

**修改要求**:
- 明确陈述算法的核心创新点
- 讨论与标准"prevent pipeline bubbles"思想的关系和区别

---

## IV. 理论证明问题 (Reviewer 2)

### 4.1 Theorem 1 证明缺失decoding-stage分析

**具体问题**: Lemma 1 假设 `W^{t+1} = W^t + X^t - λ·1(W^t + X^t ≥ λ)`，但如果有 l' decoding stages，需要等待 l' batch executions才有requests completing。

**回应策略** (Decision补充):
- **是我们的算法让这个简化成立**
- Threshold机制保证每个stage都有足够的prompts
- **核心论点**：是算法设计让系统看起来容易分析变成了"standard"，而不是问题本身容易
- **修改时要点**：把每个步骤说清楚，不要跳步，让reviewer能follow为什么简化是合理的

### 4.2 Heavy-traffic假设的作用

**问题**: Heavy-traffic假设似乎只在证明末尾使用。

**修改要求**:
- 明确heavy-traffic假设在分析中的具体作用
- 讨论能否部分去除这个假设

### 4.3 Minor公式错误 (需逐一核实)

| 位置 | 问题 |
|------|------|
| Page 12, line 19 | 应为 λ_j d_1(l'_j+1)(l_j + l'_j/2)? d_0应为d_1? |
| Page 13, Eq.(4) | throughput公式检查 |
| Page 13, line 46 | (d_0 + d_1 M*)λ_j = n*_j/(l'_j+1)? |
| Page 14, line 20 | Σ^n_{j=1} 应为 Σ^m_{j=1}? 确保包含d_1 |
| Page 14, line 23 | 应为 Σ^m_{j=1} λ_j l'_j? |
| Page 17, line 26 | 澄清 n_j 表示 n*_j/(l'_j+1) 而非 n*_j |
| Page 17, line 37 | M* 在 Eq.(9) 中的位置? |
| Page 17, line 52 | ΔT_{[1,...,m]} 未定义 |

---

## V. 实验问题 (Reviewer 2 & Reviewer 3)

### 5.1 参数设置不清

**需要明确的参数**:
- Section 6.1: batch size B, memory bound M*, capacity C
- 当 n_1 = n_2 = n_3 = 1 时，B ≥ 600?
- Section 6.2: n_1, ..., n_10 的具体值

### 5.2 仿真vs真实GPU验证

**问题**: Vidur simulation在大batch场景下可能不准确。

**修改要求**:
- 建议在真实GPU (如A100)上验证
- 提供simulated vs real processing time的对比图
- 在abstract中说明是simulation而非actual GPU

### 5.3 不稳定系统中的Latency测量

**Reviewer 3 指出**:
> All simulations appear to be in unstable regimes (visible from buildup in latency plots). Testing unstable regime is appropriate for throughput differences, but not meaningful for latency.

**修改要求**:
- 考虑添加标准排队论图: mean latency vs arrival rate
- 展示stability region的差异

### 5.4 Baseline配置

**问题**: Sarathi的配置 (chunk size, reserved memory allocation等) 未说明。

**修改要求**:
- 详细说明所有baseline的配置参数
- 确保可复现性

### 5.5 Figure 7 说明

**问题**: "Prompt Number"的含义不清楚。

---

## VI. AE的修改优先级

### Priority 1: Complete Expositional Overhaul

1. **不仅仅修复typos**，需要coherent rewrite
2. **证明呈现**:
   - 在主文提供清晰的proof logic sketch
   - 连接到标准stochastic literature (避免从first principles证明已知结果，如用Cauchy-Schwarz证明random walk性质)
3. **效率提升**:
   - 简化关于zero drift的knife-edge case讨论
   - 利用已知结果：reflecting boundary random walk在negative drift下O(1)，zero drift下O(√T)

### Priority 2: Model Justification

**选择**:
- Option A: 保留现有模型，有说服力地论证为何是有用的proxy
- Option B: 添加最有意义的特征而不显著复杂化分析

**无论选择哪个**: 必须transparent about limitations
- 如果不考虑hard memory constraints (swapping/OOM)，明确讨论假设成立和失效的场景

### Priority 3: Clarify Theoretical Novelty

- 明确WAIT和coupling analysis的核心创新点
- 如果贡献主要在modeling而非math，清楚陈述
- 建立novel domain (LLM inference) 与standard stochastic model的连接本身是significant contribution

---

## VII. 修改清单 (Checklist)

### 写作
- [x] 统一符号定义，提供符号表 (model.tex Table 1, k→s)
- [x] 正式定义policy space Π (model.tex Section 2.5)
- [x] 在关键定义和算法后添加直观解释 (proof sketch, on-the-fly, safety buffer)
- [x] 修复所有typos (Throughput, d_0→d_1)
- [x] 在主文sketch证明逻辑 (known_type.tex 3-step proof sketch)
- [x] 连接到标准stochastic literature (Asmussen 2003, Strait 1974, Kingman)

### 模型
- [x] 明确Eq(1)针对的asymptotic regime (model.tex Remark 1)
- [x] 讨论线性假设的局限性 (Remark 1: PD disaggregation)
- [x] 明确OOM防护机制 (introduction.tex eviction paragraph)
- [x] 澄清preemption和memory constraint的范围 (model.tex)
- [x] 讨论C ≥ M*假设的现实性 (known_type.tex Remark 4.0已添加)

### 理论
- [x] 补充decoding-stage分析 (proof sketch说明threshold如何decouple)
- [x] 核实所有公式 (fluid.tex line 20: d_0→d_1)
- [x] 澄清heavy-traffic假设的作用 (改为asymptotic regime + Remark)
- [x] 重新表述throughput优化目标 (eviction prevention framing)
- [x] 明确算法核心创新点 (FCFS例子, dimensionality reduction)

### Related Work
- [x] 添加Concurrent Theoretical Work段落 (introduction.tex: Zhou系列d_1=0, known/adversarial output)
- [x] 修订Li et al.描述 (general batch processing time, complements our batch-level analysis)

### Appendix重组
- [x] 创建pf_thm_timevarying.tex (Theorem 3证明)
- [x] 模块化Appendix.tex为\input结构 (pf_thm_wait, pf_thm_nested, pf_thm_timevarying, pf_lemmas)

### LaTeX编译
- [x] 修复duplicate \newtheorem定义 (remark, example - 已在informs4.cls定义)
- [x] 修复conflicting packages (subcaption, subfigure, caption与informs4.cls冲突)

### 实验 (跳过 - 用户要求)
- [ ] 完整列出所有参数设置
- [ ] 考虑真实GPU验证
  - 先做vidur可以做的. 
- [ ] 添加mean latency vs arrival rate图
- [ ] 详细说明baseline配置
- [ ] 解释Figure 7中的"Prompt Number"
- [ ] near boundary (For Nested WAIT)
  - near boundary直接画latency-time curve
  - 横轴是arrival rate, 纵轴是稳态的throughput or latency or memory usage. 这样的一个dependent on arrival rate的一个region.

---

## VIII. 参考文献 (审稿人推荐)

1. Agrawal et al. (2024). Sarathi-Serve. OSDI 2024.
2. Bari et al. (2025). Optimal scheduling algorithms for LLM inference. arXiv:2508.01002.
3. Li, Dai & Peng (2025). Throughput-optimal scheduling algorithms. arXiv:2504.07347.
4. LMCache. KV cache size calculator. https://lmcache.ai/kv_cache_calculator.html

---

---

## IX. 修订决定记录

### 决定 1: 符号系统重构 (2025-12-13)

**方案确认**:
- 用 $s$ 统一表示stage：$s=0$ 表示prefill，$s=1,...,l_j'$ 表示decode
- 用 $s_i^t$ 表示prompt $i$在时刻$t$的stage（替代原来的$k_i^t$）
- 保留每个prompt的详细描述（Eq.1中保留对batch内prompt的详细表述）
- Threshold符号保留 $n_j$（不改为$\theta_j$）
- 在Section 2开头添加符号表

**具体修改**:
```latex
% Eq(1) 修改为：
τ = d_0 + d_1 · (Σ_{i∈prefill} l_{j(i)} + Σ_{i∈decode} (l_{j(i)} + s_i))
```

### 决定 2: Equation (1) 线性假设的处理 (2025-12-13)

**处理策略**:
1. **承认局限性**: 明确说明使用simplified model，目的是使iteration-level算法的理论分析更tractable，提供insight
2. **引用general formula**: 在文中讨论完整公式（含linear layer、attention prefill/decode项）
3. **说明适用场景**: 给出model成立的现实scenario（memory-bound / large batch / long decode）
4. **实验佐证**: 引用 `inference_time_comparison.pdf`，承认不代表所有情形

**与相关工作对比 (关键论点)**:

| Paper | Iteration Time假设 | 细节程度 |
|-------|------------------|---------|
| Jaillet et al. 2025 | τ = 1 (常数) | 完全抽象 |
| Wang et al. 2025 | τ = 1 (常数) | 完全抽象 |
| Chen et al. 2025 | τ = 1 (常数) | 完全抽象 |
| **Our paper** | τ = d₀ + d₁·(KV-cache) | **更详细** |

**回复要点**:
> "Recent theoretical work on LLM inference scheduling [Jaillet et al. 2025, Wang et al. 2025, Chen et al. 2025] abstracts iteration time to a unit constant, focusing purely on combinatorial scheduling. In contrast, our work explicitly models the memory bandwidth bottleneck through the KV-cache loading term, which is critical for throughput optimization under memory constraints."

5. **PD分离系统的完美适用性** (关键论点):
   - 在Prefill-Decode Disaggregation系统中，decode端是**decode-only**
   - **不存在prefill term**，Reviewer 2担心的O(Σk_i²) attention根本不出现
   - Eq(1)的线性假设在decode端**完全成立**
   - 这是当前LLM serving的重要趋势（Splitwise, DistServe等）

**需要添加的引用**:
- Bari et al. (2025) arXiv:2508.01002
- Li, Dai & Peng (2025) arXiv:2504.07347
- Jaillet et al. (2025), Wang et al. (2025), Chen et al. (2025) - Zijie Zhou系列
- PD分离相关: Splitwise, DistServe等

### 决定 4: "Heavy Traffic"术语与理论贡献 (2025-12-13)

**术语修改**:
- 将 "heavy traffic" 改为 **"asymptotic regime"**
- 需要全文搜索替换相关表述

**核心理论贡献的clarification**:

1. **问题的独特性 - Eviction/OOM问题**:
   - KV cache随decode不断增长，这是与传统scheduling问题的根本区别
   - 特别是unknown output length时，eviction风险更大
   - **关键insight**: 即使系统capacity允许no-eviction且理论上stable，**不好的算法也会导致OOM并最终unstable**

   **FCFS Cascading Failure 具体例子** (来自 llm_short.pdf slides 18-19):
   - 设置: "Hi"→"Hello", prefill占1 memory, decode占2 (累计), C=12
   - Balanced state [4,4]: 稳定，每轮4 completions
   - 从 [6,3] (稍微不平衡) 出发:
     ```
     [6,3] → 3 complete → [6,0]
     [6,0] → 6 advance → overflow → 6 evictions → [0,6]
     [0,6] → 6 complete, 12 admit → [12,0]
     [12,0] → 6 advance → overflow → 6 evictions → [0,6]
     ... 循环 ...
     ```
   - 结果: 3 completions/iter vs balanced的4 completions/iter
   - **即使C≥M*，FCFS因eviction cascade导致系统unstable**

2. **算法设计的核心思想**:
   - 目标：避免eviction，防止本可stable的系统crash
   - 方法：逐步handle unknown output length
   - WAIT/Nested WAIT看起来intuitive，但设计思路是让stochastic系统逼近balanced fluid dynamics

3. **证明技术的创新**:
   - 核心难点：如何在unknown output情况下让stochastic系统逼近fluid equilibrium
   - 技术路线：**先decoupling，再构造coupling**
   - 这不是标准的positive recurrence证明，而是针对LLM inference特有的memory dynamics

**在revision中需要强调的对比**:

| 传统Scheduling | LLM Inference Scheduling |
|---------------|-------------------------|
| 固定job size | KV cache动态增长 |
| 无memory eviction问题 | Eviction导致cascading failure |
| Stability = 标准条件 | Stability需要careful admission control |

**回复审稿人要点**:
> "Our contribution lies not in heavy-traffic analysis per se, but in addressing the unique challenge of **dynamic memory growth** in LLM inference. Unlike traditional queueing, where job sizes are fixed, KV caches grow during decode, creating eviction risks. We show that even when the system has sufficient capacity for stability, naive policies (e.g., FCFS) can trigger cascading failures. Our algorithms are designed to approach the balanced fluid dynamics while preventing such failures, especially under unknown output lengths. The decoupling-then-coupling proof technique is tailored to this memory-constrained stochastic setting."

4. **直接适用于PD分离系统**:
   - 在Prefill-Decode Disaggregation系统中，我们的算法和建模**直接适用于decode端**
   - Decode端是纯decode-only，没有prefill term
   - Reviewer 2/3关心的prefill attention O(k²)问题在这类系统完全不存在
   - 这进一步强化了我们理论贡献的实际价值

---

### 决定 3: OOM机制与Memory Constraint (2025-12-13)

**Clarification要点**:

1. **Memory constraint范围**: 针对**所有已经被admit到GPU的requests**，不只是当前batch
   - 没有进入GPU做prefill的prompts：不占用memory
   - 已做过prefill但当前不在batch中的prompts：**仍然占用GPU memory**（KV cache保留）

2. **WAIT算法的memory管理**:
   - Waiting queue中未admit的prompts：不计入GPU memory
   - 已prefill的prompts（无论是否在当前batch）：计入GPU memory
   - 这就是为什么算法需要threshold控制admit数量

3. **Nested WAIT的safety buffer** (已有讨论 - Theorem 2, Eq.16):
   ```
   M^{(ζ,π)} ≥ M^π + Σ(l + l_{j-1}')(n_j + θ_j^{-1} ln(mζS/δ))
   ```
   - 第一项 M^π：基本equilibrium memory
   - 第二项：**safety buffer for unknown output length**
   - 保证memory不超出的概率至少 1-δ

**需要在model.tex中澄清的内容**:
- 明确说明memory constraint覆盖所有GPU上的KV cache（不只是当前batch）
- 强调WAIT的threshold机制本身就是OOM prevention
- 引用Nested WAIT的safety buffer作为unknown output length情况下的保护

**关于C ≥ M*假设的补充论点**:

虽然理论分析聚焦于near overloaded regime (C ≥ M*)，但实验表明：
- **即使在overloaded regime**，能避免OOM的算法也显著优于baseline
- **核心思想**：通过避免eviction，在不损失太多latency的情况下让系统**尽可能接近load-balanced状态**
- 这个**approaching load balance**的思想是算法的精髓
- Baseline在overloaded时频繁eviction → cascading failure → 远离load balance
- WAIT/Nested WAIT通过threshold控制 → 维持接近equilibrium → fully exploit throughput

**回复审稿人要点**:
> "The memory constraint applies to all requests that have been admitted to the GPU, not just the current batch. Prompts waiting in the queue (before prefill) do not consume GPU memory, but once admitted, their KV caches remain on GPU even when not actively processed. The threshold mechanism in WAIT inherently prevents OOM by controlling admission. For unknown output lengths, Nested WAIT (Theorem 2) provides an explicit safety buffer with high-probability guarantees."

> "While our theoretical analysis focuses on the near-capacity regime (C ≥ M*), our experiments demonstrate that even in overloaded regimes, algorithms designed to avoid eviction significantly outperform baselines. The key insight is that by preventing eviction, our algorithms keep the system close to a **load-balanced state**, fully exploiting throughput without sacrificing latency. This 'approaching load balance' principle is central to our algorithm design."

---

### 决定 5: 实验参数与设置 (2025-12-13)

**5.1 参数补充清单**:

| 参数 | Section 6.1 | Section 6.2 | 需补充说明 |
|------|-------------|-------------|-----------|
| Batch size B | 需明确 | 需明确 | 如何选择 |
| Memory bound M* | 需计算 | 需计算 | 公式计算结果 |
| Capacity C | 需明确 | 需明确 | GPU实际值 |
| n_j (thresholds) | n_j = B·ρ_j/(l'_j+1) | 66:43:32:24:17:11:7:4:2:1 | 列出具体数值 |
| Arrival rates λ | (600,400,200) | 55 qps total | 已有，需更清晰 |
| Prefill lengths | (20,20,20) | 分布 (见Figure) | 需明确 |
| Output lengths | (100,200,300) | [1-50],...,[451-500] | 需明确 |

**5.2 真实GPU验证**:
- 计划在真实GPU (H100/A100)上运行验证
- 提供 simulated vs real processing time 对比
- 已有 llm_short.pdf slide 9 的线性假设验证数据可引用

**5.3 Unstable Regime的回应策略**:

核心论点：
1. **即使在传统queueing认为trivial的regime，eviction带来的损失不可忽略**
   - 这恰恰是文章的重点：不是传统的stability analysis
   - 重点是：**如何避免eviction导致的cascading failure**

2. **实际系统常处于overloaded状态**
   - 需要cite相关文献说明 production LLM systems 经常 overloaded
   - 我们的算法在这些regime下依然有效

3. **补充 underloaded 实验** (TODO)
   - 添加 stable regime 下的实验
   - 展示 mean latency vs arrival rate 曲线
   - 对比不同算法的 stability region

**5.4 Figure 7 "Prompt Number" 说明**:
- 需要clarify：x轴表示第N个到达的prompt的cumulative average latency
- 考虑修改figure或添加更清晰的caption

---

### 决定 6: 证明重组与理论呈现 (2025-12-14)

**核心问题**: 如何在论文中清晰呈现理论贡献，区分WAIT和Nested WAIT各自的独特贡献点。

---

#### 6.1 WAIT Section (Section 4 - Known Types) 的理论要点

**强调的创新点**:

1. **Threshold-based Dimensionality Reduction** (核心算法思想)
   - 原问题：复杂的multi-stage decode + KV-cache动态增长
   - 简化：每个type用一个queue分析，threshold条件 $n_{j0}^t \geq n_j$ 保证 arrivals ≤ completions
   - 意义：将intractable的系统转化为tractable的分析框架
   - **这是算法精妙之处，需要在revision中突出**

2. **自然避免Eviction的设计**
   - Threshold机制**同时**解决两个问题：throughput optimization + eviction prevention
   - 不需要显式的eviction handling，算法结构本身就避免了cascading failure
   - **这是与naive policies的本质区别**

3. **FCFS Cascading Failure对比** (Proposition 3.4)
   - 通过具体例子（slides 18-19）展示：即使C≥M*，FCFS仍会因eviction cascade而unstable
   - 这不是trivial的positive recurrence证明，而是针对LLM特有的memory dynamics
   - **建议在Section 4.3添加简化版cascading failure例子**

4. **Proof Technique: Coupling**
   - 构造stochastic process dominating real dynamics
   - 关键：证明threshold条件下系统逼近fluid equilibrium
   - **主文需要proof sketch，clarify核心步骤**

**Section 4 Revision Checklist**:
- [ ] 在Algorithm 1后添加直观解释，强调dimensionality reduction
- [ ] 添加FCFS cascading failure的简化例子（2-3行的concrete scenario）
- [ ] 明确threshold设计如何同时实现throughput + eviction prevention
- [ ] 添加proof sketch（coupling构造的核心思路）

---

#### 6.2 Nested WAIT Section (Section 5 - Unknown Types) 的理论要点

**强调的创新点**:

1. **Nested Segments + On-the-fly Classification** (核心创新)
   - 将processing分成m个nested segments，对应累积output length boundaries
   - 关键insight：**prompts在每个segment边界自然分类** - short prompts完成，long prompts继续
   - **不需要预测output length，类型在执行过程中自然显现**
   - **这是对unknown output length问题的elegant solution**

2. **短prompts不被长prompts拖累**
   - 传统方法：假设worst-case length，导致严重资源浪费
   - Nested WAIT：短prompts快速完成，长prompts在后续segments继续
   - **Paper slides 19-25的例子清晰展示这一点**
   - 例：P1-P6 with Threshold₁=4, Threshold₂=3，短prompts标"Good"快速完成

3. **Safety Buffer for Unknown Output** (Theorem 2, Eq.16)
   - 需要额外memory buffer来hedge uncertainty
   - 公式：$M^{(\zeta,\pi)} \geq M^\pi + \sum_{j=2}^m (l + l_{j-1}')(n_j + \theta_j^{-1}\ln(m\zeta S/\delta))$
   - 高概率保证 (1-δ) 不overflow
   - **这是处理uncertainty的explicit mechanism**

4. **Descending Thresholds with Ratio Condition**
   - 条件：$n_{i+1}/n_i > p_i$ where $p_i = (\sum_{j=i+1}^m\lambda_j)/(\sum_{j=i}^m\lambda_j)$
   - 意义：保证后续segments有足够prompts形成batch
   - **与WAIT的fixed threshold不同，这里需要careful设计threshold递减关系**

5. **Lower Bound (Proposition 5.1)**
   - 当C = M*时，任何non-predictive policy都有Ω(1) throughput gap
   - 证明：unknown output length + 刚好够用的memory = 必然有overflow或under-utilization
   - **这justify了safety buffer的必要性**

6. **Performance Independence from m**
   - 算法性能主要取决于arrival rates，不是type数量
   - 即使m很大（如连续output length分布），算法仍有效
   - **这增强了practical applicability**

**Section 5 Revision Checklist**:
- [ ] 在Algorithm 2后添加详细例子（参考slides 19-25）
- [ ] 强调on-the-fly classification的insight
- [ ] 明确说明短prompts快速完成、不被长prompts block的优势
- [ ] 解释safety buffer的intuition（不只是数学公式）
- [ ] 添加proof sketch（与Lindley process和Doob's inequality的连接）

---

#### 6.3 两个Section的共同框架

**Unified Story**:
1. **Problem**: KV cache动态增长 + eviction风险 → 传统scheduling方法失效
2. **Solution**: Threshold-based dimensionality reduction → 复杂系统变tractable
3. **WAIT (known)**: 每个type一个queue，threshold控制batch formation
4. **Nested WAIT (unknown)**: Nested segments + on-the-fly classification + safety buffer
5. **Contribution**: 不是heavy-traffic novelty，而是addressing LLM-specific memory dynamics

**与审稿人的对应**:

| Reviewer 3 Concern | Response |
|-------------------|----------|
| "Algorithm idea is relatively simple" | Simplicity is a feature - dimensionality reduction makes intractable system tractable |
| "Positive recurrence is not surprising" | 核心不是recurrence本身，是在presence of eviction risk下的stability |
| "Latency results are standard" | 同上，关键是eviction prevention，不是标准queueing |
| "Memory constraint only for current batch?" | 明确：constraint covers all GPU-admitted requests |

**回复审稿人要点（Section 4 & 5 共用）**:
> "The apparent simplicity of our threshold mechanism is intentional and reflects the core contribution: **dimensionality reduction**. By using thresholds, we transform the complex multi-stage decode problem with dynamic KV-cache growth into a tractable single-queue analysis per type. This reduction is not merely a proof technique but the algorithm's fundamental design principle. It naturally prevents eviction cascades (which can destabilize even capacity-sufficient systems under naive policies like FCFS) while achieving asymptotic throughput optimality. The Nested WAIT extension addresses unknown output lengths through on-the-fly classification: prompts reveal their types as they complete decode stages, allowing short prompts to finish quickly without waiting for long ones."

---

### 决定 7: Introduction和Model Section重写方向 (2025-12-14)

#### 7.1 Introduction的核心Message

**Main Thesis** (区分本文与其他文献):
1. **Memory Constraint是核心问题** - 这也是Zijie Zhou系列 (Jaillet, Wang, Chen) 专注address的
2. **Eviction Prevention under Unknown Output** - 这是本文最distinguish的贡献

**Introduction需要明确阐述**:
- LLM inference的memory constraint来源（KV cache动态增长）
- 为什么memory constraint在这里比传统scheduling更challenging（eviction risk）
- 本文的approach：threshold-based dimensionality reduction
- 与Zijie Zhou系列的关系：他们focus on known output，我们extend到unknown output

**建议的Introduction结构**:
1. LLM inference背景和重要性
2. **Memory constraint challenge** (核心问题定位)
3. Why existing scheduling methods fail (eviction cascade)
4. Our approach: threshold-based algorithms
5. Contribution summary (WAIT + Nested WAIT)
6. Paper organization

---

#### 7.2 Model Section重组建议

**当前问题**:
- 符号散乱（k多重定义）
- Memory constraint未被凸显为核心
- 缺少符号表

**建议的新结构**:

```
Section 2: Model

2.1 Preliminaries and Notation (新增)
    - 符号表 (Table 1)
    - Stage定义：s=0 prefill, s=1,...,l'_j decode
    - 基本记号统一

2.2 LLM Inference Process
    - Prompts and tokens
    - Two-phase processing (prefill + decode)
    - KV cache growth dynamics
    - [Figure: batching example - 保留]

2.3 Memory Constraint and Challenges (重点强化)
    - GPU memory capacity C
    - KV cache随decode增长
    - **Eviction问题**: 当memory不足时必须evict某些prompts
    - **Core challenge**: 如何在unknown output length下avoid eviction
    - [可加入简化的cascading failure示意]

2.4 Iteration Time Model
    - Eq(1): τ = d_0 + d_1·(memory)
    - 适用regime说明
    - 与PD分离系统的关系
    - [Figure: inference time validation - 保留]

2.5 Performance Metrics and Optimization
    - Throughput, Latency, TTFT定义
    - Optimization formulation
    - Policy space Π的正式定义 (审稿人要求)
```

**关键变化**:
1. 前置符号表，统一notation
2. 把Memory Constraint单独成节，强调eviction challenge
3. Policy space Π在这里正式定义（而非等到Algorithm 1）
4. Iteration time model加入适用性讨论

---

#### 7.3 Related Work补充

**必须添加的内容**:

1. **Zijie Zhou系列对比**:
   ```
   Recent theoretical work [Jaillet et al. 2025, Wang et al. 2025, Chen et al. 2025]
   studies LLM inference scheduling with unit iteration time, focusing on
   combinatorial aspects. Our work differs in two key aspects: (1) we explicitly
   model memory bandwidth through KV-cache loading time; (2) we address unknown
   output lengths through nested threshold mechanisms.
   ```

2. **PD分离系统适用性**:
   ```
   Our algorithms and analysis are directly applicable to Prefill-Decode
   Disaggregated systems [Splitwise, DistServe], where the decode server
   performs decode-only operations. In such systems, the linear iteration
   time model (Equation 1) holds exactly without the prefill attention term.
   ```

3. **需要cite的文献**:
   - Jaillet et al. (2025) - scheduling with known output
   - Wang et al. (2025) - pipeline parallelism
   - Chen et al. (2025) - robust scheduling
   - Zhong et al. (2024) - DistServe (PD分离)
   - Patel et al. (2024) - Splitwise (PD分离)

---

### 决定 8: Response Letter写作策略 (2025-12-14)

**整体Tone**: 非常积极、感谢、谦虚、开放讨论

#### ⚠️ 写作语气指导

- ✅ **正常justify** - 论文中必须justify贡献和方法选择
- ❌ **避免defensive辩护** - 不要像在"反驳"reviewer，以开放态度讨论
- ✅ **保持conciliatory** - 缓和、友好
- ❌ **避免贬低他人工作** - 客观陈述区别，用"differs"、"complements"等中性词
- 不要指名道姓批评相关工作，保持学术礼貌

**开场白框架**:
> We are deeply grateful to the Area Editor and all three reviewers for their thorough and constructive feedback. The detailed comments have been invaluable in identifying areas where our exposition was unclear, our assumptions required better justification, and our theoretical contributions needed sharper articulation. We genuinely appreciate the time and effort invested in reviewing our work, and we are pleased to have received such comprehensive guidance for improvement.

**核心态度**:
1. **真诚感谢** - 所有feedback对academic paper的improvement都非常重要
2. **承认不足** - 坦诚acknowledge写作、符号、证明呈现等方面的问题
3. **逐一回应** - 每个concern都有对应的修改和解释
4. **持续改进意愿** - 表达希望继续完善论文的诚意

**对不同Reviewer的回应策略**:

| Reviewer | Tone | 重点 |
|----------|------|------|
| Reviewer 1 | 感谢+详细回应 | 符号统一、OOM机制澄清、实验参数补充 |
| Reviewer 2 | 感谢+技术讨论 | Eq(1)适用性、证明细节、公式核实 |
| Reviewer 3 | 感谢+重新定位贡献 | 澄清非heavy-traffic novelty，强调eviction prevention |

**对Reviewer 3的特别处理**:

虽然Reviewer 3评价较负面，但response中应：
- 感谢指出queueing theory概念的不精确使用
- 承认"heavy traffic"命名的misleading
- **重新框架贡献**：不是heavy-traffic analysis novelty，而是addressing LLM-specific memory dynamics
- 用具体例子（FCFS cascading failure）展示问题的non-trivial性
- 强调unknown output length下的eviction prevention是核心创新

**Response Letter结构**:
```
1. Cover Letter (1页)
   - 感谢语
   - 修改概述
   - 主要改进点

2. Point-by-Point Response
   - Reviewer 1 Comments
   - Reviewer 2 Comments
   - Reviewer 3 Comments

3. Summary of Changes (可选)
   - 列出主要修改的sections和内容
```

**语言**: 英文

---

### 待办: Reviewer 2 详细问题清单 (逐Section修改时检查)

#### 写作与表述问题

| 位置 | 问题 | 状态 |
|------|------|------|
| Page 7, lines 40-44 | 句子flow需改进 | [?] 需确认具体位置 |
| Page 10, line 42 | 澄清 k_i^t = 0 是否表示prefill stage | [x] 已改为s=0表示prefill (model.tex Table 1) |
| Page 10, line 48 | 添加footnote说明prefill throughput不计入 | [x] model.tex line 127已说明"decode phase" |
| Page 11, lines 17-22 | Π定义为non-preemptive但后面允许preemption，需澄清 | [x] model.tex line 143已澄清preemption allowed |
| Page 11, line 55 | 考虑在single-type fluid model中去掉下标j | [ ] 保留j因为分析type j |

#### 理论分析问题

| 问题 | 描述 | 状态 |
|------|------|------|
| Alternative algorithms | 如果不wait但仍用threshold n_j会怎样？讨论理论和实践影响 | [x] 已补wait-on vs wait-off数值比较，结论为scenario-dependent tradeoff |
| Output > 1000 tokens | 讨论算法在超长output情况下的行为 | [x] extension.tex有segment design处理 |
| Threshold without waiting | 是否可作为alternative来缓解memory constraints | [x] 可以，在long-decode / memory-limited / highly heterogeneous场景更有优势 |

#### Appendix证明问题

| 位置 | 问题 | 状态 |
|------|------|------|
| Page 39, Prop 4 proof | 澄清为什么"equilibrium batch"是optimal | [ ] 待review |
| Page 41, line 35 | "booking limiting policy" 未定义 | [x] pf_thm_wait.tex line 25改称WAIT/threshold-based |
| Page 41, line 41 | time step t? | [x] pf_thm_wait.tex使用batch index s |
| Page 41, Lemma 1 | 澄清从main problem到lemma setting的reduction | [ ] 待review |
| Page 42, Lemma 4 | S^k 未定义 | [x] pf_thm_wait.tex line 44已定义S^k |
| Page 43, line 9 | Heavy-traffic regime讨论需expand | [x] 已改为Asymptotic Regime |
| Page 43, line 32 | 解释为什么 Arrival_j ≤ Completion_j | [x] pf_thm_wait.tex line 77有解释 |
| Page 43, line 36 | 应该是 M^π = M*? | [ ] 需要核实 |
| Page 44, line 14 | W_t 和 W̃_t 在events之间的定义 | [ ] 待review |
| Page 44, line 18 | Appendix E.3证明 - Reviewer建议了alternative proof | [ ] 待考虑 |
| Page 44, line 52 | 需cite Kingman | [x] pf_thm_wait.tex line 108已添加citation |
| Appendix B.0.1 | Cauchy-Schwarz证明random walk性质 - **AE特别指出可简化** | [x] pf_thm_wait.tex line 55-56已简化 |

---

### 待办: AE特别指出的效率改进

1. **Knife-edge case简化**:
   - Theorem 1和Proposition 3中大量讨论zero drift情况
   - 标准结果：reflecting boundary random walk在negative drift下O(1)，zero drift下O(√T)
   - **可直接引用标准文献，不需要从first principles证明**

2. **Appendix重组**:
   - 当前proofs像"deposit boxes"而非给readers读的sections
   - 选择：(1)移部分proof到主文，或(2)在主文清晰sketch proof logic
   - 对于留在appendix的证明，添加解释并连接到标准stochastic literature

---

### 待办: 公式核实清单 (逐Section修改时检查)

| 位置 | 问题描述 | 状态 |
|------|---------|------|
| Page 9, line 50 | `d` 应为 `d_1`? | [ ] |
| Page 12, line 19 (fluid.tex line 20) | `d_0` 应为 `d_1` | [x] 已修复 |
| Page 13, Eq.(4) | throughput公式检查 | [x] fluid.tex line 76-78公式正确 |
| Page 13, line 46 | (d_0 + d_1 M*)λ_j = n*_j/(l'_j+1)? | [x] fluid.tex line 47公式正确 |
| Page 14, line 20 (fluid.tex line 122) | Σ^n → Σ^m, 添加d_1 | [x] 已修复 |
| Page 14, line 23 | 应为 Σ^m_{j=1} λ_j l'_j 还是 λ_j(l'_j+1)? | [x] fluid.tex line 123是λ_j(l'_j+1)正确 |
| Page 17, line 26 | 澄清 n_j 表示 n*_j/(l'_j+1) 还是 n*_j | [x] known_type.tex说明n_j是每stage阈值 |
| Page 17, line 37 | M* 在 Eq.(9) 中的位置? | [x] known_type.tex eq定义M^π非M* |
| Page 17, line 52 | ΔT_{[1,...,m]} 未定义 - 需要在使用前定义 | [x] known_type.tex line 108已引用定义 |
| Eq.(5) 后的公式 | Reviewer 3指出右边应与(2)一致 | [ ] 需核实 |

**修改原则**: 逐section修改时对照此表核实，修复后打勾。

### 待办: Reviewer 2 遗漏的Minor Items

| 位置 | 问题 | 状态 |
|------|------|------|
| Page 12, line 30 | "requires" → "at least requires" | [ ] 待修改 |
| Page 14, Proposition 2 | clarify: 是否只是说 throughput ≤ expected arriving tokens | [x] Prop 2说明C≥M*时throughput≤Throughput* |
| Page 35, line 4 | "Asmussen S, Asmussen S, Asmussen S" 重复引用修复 | [x] main.bib已修复 |
| Page 39, line 38 | ".Consider" → ". Consider" | [x] 当前pf_*.tex文件中不存在此问题 |
| Page 39, line 40 | "type 2 with l_2 = 1" 检查上下文 | [ ] 待核实 |
| Page 41, line 41 | "time step t?" clarify | [x] pf_thm_wait.tex使用batch index s |
| Page 42, line 35 | 应为 W̃^T ≥ W^T + λ 而非 W̃^T ≥ λ^T? | [x] pf_thm_wait.tex line 50正确: W̃^T ≥ λ^T |

---

---

### 决定 9: 证明简化与补充讨论 (2025-12-14)

#### 9.1 Appendix证明简化策略

**原则**: 部分可简化，但要强调系统的非标准性

**系统为什么不是标准queue**:
1. Memory grows with decode + eviction风险
2. **Multiple types** - 不是完全的simple random walk
3. 是算法的threshold设计实现了**降维和decouple**

**修改方式**:
- 对于可简化的部分（如单type分析中的某些步骤），引用标准结果
- **但必须保留**处理multiple types、coupling构造等非标准部分
- 主文proof sketch强调：算法如何使非标准系统变得可分析

#### 9.2 Wait vs No-Wait Tradeoff讨论

**Updated conclusion from SQL-backed experiments**:
- The comparison now has dedicated scenario runs stored in `experiments.db` (`wait_vs_nowait_*` tables).
- The correct framing is **not uniform dominance**, but a **scenario-dependent tradeoff**.

**Observed pattern**:
- `wait_on` is better in more regular regimes:
  - single-type short decode,
  - balanced multi-type workloads,
  - settings with similar prefills and moderate heterogeneity.
- `wait_off` is better in more extreme regimes:
  - very long decode,
  - memory-limited settings,
  - highly heterogeneous multi-type workloads.

**Interpretation**:
- Waiting trades admission delay for cleaner batch formation and steadier memory usage.
- This helps when batching structure is predictable enough that accumulating requests improves service efficiency.
- Without waiting, the scheduler remains more flexible in long-tail regimes where extra waiting mostly delays requests that are already ready to progress.

**Response-letter angle**:
- We can answer the reviewer with a nuanced statement:
  - threshold-without-waiting is a meaningful alternative,
  - but its advantage depends on the operating regime,
  - while WAIT is preferable when structured batching gains dominate.

#### 9.3 超长Output处理

**已有覆盖**: Extension section - segment-wise和aggregate Nested WAIT

---

## X. 修订Decision总结

| Decision | 主题 | 状态 |
|----------|------|------|
| 1 | 符号系统重构 (k→s统一) | ✓ 已决定 |
| 2 | Eq(1)线性假设处理 | ✓ 已决定 |
| 3 | OOM机制与Memory Constraint | ✓ 已决定 |
| 4 | Heavy Traffic术语与理论贡献 | ✓ 已决定 |
| 5 | 实验参数与设置 | ✓ 已决定 |
| 6 | 证明重组 (WAIT vs Nested WAIT) | ✓ 已决定 |
| 7 | Introduction和Model Section重写 | ✓ 已决定 |
| 8 | Response Letter写作策略 | ✓ 已决定 |
| 9 | 证明简化与补充讨论 | ✓ 已决定 |

**下一步**: 按todo list逐section修改

---

**文档版本**: v2.0
**创建日期**: 2025-12-13
**最后更新**: 2025-12-14
**状态**: Q&A完成，所有Decision已记录，准备逐Section修改
