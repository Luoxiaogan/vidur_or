# OPRE 修回包最终审计报告

## Executive verdict

**总体结论：`needs targeted revision`。**  
这套修回材料相比原稿已经有**实质性改进**，而且改动方向与编辑、AE 和三位审稿人的核心批评高度对齐：原稿中最危险的几处——把固定负载下的长时域缩放写成 heavy traffic、把开放系统里的 throughput 写成单点“优化目标”、把内存约束写成只约束当前 batch、以及用“Prompt Number / Time Horizon”而不是 arrival-rate 视角展示延迟——在修订稿中都被明显纠正了；response letter 也基本能逐项对应这些修改。fileciteturn0file1 fileciteturn0file2 fileciteturn0file3

但从 **OPRE / Management Science** 的终稿标准看，这一版仍有几处**编辑性高风险**：最重要的不是“再做实验”，而是**再做一轮有针对性的定稿清理**——把 framing、术语、证明导读、实验口径与 claim strength 全部再收紧一次。编辑部在 decision letter 里已经把这一轮修回定性为一次**“risky” major revision**，并明确警告如果 exposition 问题延续，下轮可能直接拒稿；AE 也把“complete expositional overhaul”列为第一优先级。以这个标准看，当前版本已经脱离“方法性重做”的危险区，但还没完全到“可以放心送审终版”的状态。fileciteturn0file5 fileciteturn0file0

我的审计判断是：**不需要新实验**；当前主要缺口是**文字、定位、术语一致性、claim 收缩和 proof-roadmap 清晰度**。如果作者能按下文的 targeted edits 做一次强力定稿，这包材料就有机会从“很强的修回稿”变成“可提交终稿”。fileciteturn0file2 fileciteturn0file3

## Major remaining risks, ordered by severity

1. **顶层 framing 仍未完全统一。**  
   修订稿已经把 Section 2.4 改成了 exogenous-arrival 下的 effective throughput / stability-region 口径，也在 Section 6 解释了“稳定区内 completion rate 应贴着 offered load”，这是关键进步；但 abstract、introduction、theorem surrounding text、conclusion 里，仍会不时滑回“throughput optimization / asymptotically optimal algorithms”这种容易让负面审稿人再次抓住的说法。对一个开放系统论文来说，这种措辞如果不彻底收紧，编辑会担心作者“conceptually fixed but rhetorically unfinished”。fileciteturn0file5 fileciteturn0file2

2. **主文中的理论导读仍不够“AE 级可验证”。**  
   修订稿确实比原稿好很多：Theorem 1/2 前后增加了解释段，Appendix D–H 也比原来更有结构，并明确接到了 Lindley recursion、Kingman 等标准工具；但 skeptical reader 仍会觉得 main text 对“为什么这里不是 routine positive-recurrence argument”的说明**还差半步**。尤其 Theorem 1 周围对 \(M^*\)、\(M_\pi\)、\(M^{(\zeta,\pi)}_{\text{req}}\)、service-normalized delay 的切换仍偏密。AE 最担心的并不是 appendix 里没证明，而是 main text 是否让审稿人**愿意相信证明方向是对的**；这一点现在是“明显改善，但尚未完全过关”。fileciteturn0file0 fileciteturn0file5 fileciteturn0file2

3. **实验叙述虽已透明很多，但还需要更清楚地区分“empirical existence result”与“deployable online policy”。**  
   尤其 Section 6.2 的 real-data 实验，是对每个 arrival rate 在预设网格上选择 best-performing configuration；文中其实已经诚实写出来了，这一点很好，但主叙述仍会让人不小心把它读成“一套通用参数就能跑得最好”。这不是方法硬伤，而是需要更明确地写成：**这是 rate-aware offline calibration**，不是自适应在线 tuning theorem。fileciteturn0file2

4. **模拟到真机的 validation 方向是对的，但 claim scope 还要更谨慎。**  
   修订稿新增了 Appendix H.2 的 A100 / SGLang 校准和 GPU 端到端实验，这是高价值改进；但 main simulator comparisons 仍然主要是 Vidur 上的 vLLM / Sarathi / WAIT / Nested WAIT，真机端并没有把所有 baseline 一一搬过去。因此 response letter 和 paper 都应更明确地表述：**real-GPU evidence validates the model regime and the feasibility/direction of WAIT, not every simulator-side baseline comparison end-to-end**。否则容易被理解成“所有主实验都被真机验证过”。fileciteturn0file2 fileciteturn0file3

5. **写作层面仍有一些“机械、重复、略 AI-like”的地方。**  
   这主要出现在 response letter，也部分出现在主文 theorem-interpretation 与 related-work 段落：句式常是 “This suggestion led us… / This point is well taken… / The theorem rests on…” 的重复模板，信息密度不低，但 editorial finish 不够。对 OPRE 读者，更需要的是**一次就讲明白核心经济/排队直觉**，而不是用多段近似同义的阐释堆出“认真修改过”的印象。fileciteturn0file3 fileciteturn0file2

6. **仍有个别可以被视为“careless”的小问题。**  
   最明显的一处是 revised paper related-work 段把 **Splitwise** 写成 “Splitwise (Patel 2023)”，但参考文献里真正的 Splitwise 论文是 **Patel et al. (2024)**，而 Patel (2023) 是 Semianalysis 的成本博客。这种引用失配不影响主结果，但在经历过一轮“careless errors”批评后，属于必须清掉的信号型问题。fileciteturn0file2

## Checklist table mapping each review concern to response-letter coverage and manuscript coverage

| 关切 | 来源 | response letter 覆盖 | 修订稿覆盖 | 审计结论 |
|---|---|---|---|---|
| 写作质量、符号混乱、缺少直觉、appendix 难核查 | AE、编辑部、R1、R3 都把 exposition 列为首要风险。fileciteturn0file0 fileciteturn0file5 fileciteturn0file8 | 明确宣称重写 Sections 2–6、增加 Notation Summary、algorithm examples、theorem-interpretation、proof modularization。fileciteturn0file3 | Section 2 叙述化建模、Section 2.4 新增 policy space、Appendix B notation summary、Appendix D–H 重组均已出现。fileciteturn0file2 | **部分解决**。改善显著，但 Sections 3–5 与 response letter 仍需再压缩、再提炼。 |
| heavy traffic 误用 | R3 明确指出这其实是 fixed-load 下的 long-horizon / infinite-horizon scaling，不是经典 heavy traffic。fileciteturn0file5 | 明确承认并说已移除 heavy-traffic framing。fileciteturn0file3 | 修订稿主文不再以 heavy traffic 作为 narrative framing；原稿 Section 4.2 仍明显写着 “Heavy Traffic Analysis”。fileciteturn0file1 fileciteturn0file2 | **基本解决**。这是最成功的修正之一。 |
| 开放系统里 throughput 的概念性 framing 不对 | R3 指出稳定系统的 completed work 由 arrival rate 决定，关键是 stability region / useful completed service。fileciteturn0file5 | 回复信把目标改写为 stability-region expansion、effective throughput net of evictions。fileciteturn0file3 | 原稿 Section 2.4 是“maximize throughput subject to latency/TTFT”; 修订稿改为 effective throughput + offered-load cap + stability-region 口径。fileciteturn0file1 fileciteturn0file2 | **大体解决，但需进一步统一措辞**。abstract / conclusion 仍应更一致。 |
| 延迟实验主要落在不稳定区、解释力不足 | decision letter 与 R3 都强调 latency 不能只在 unstable regime 里比较。fileciteturn0file5 | 回复信称 Section 6 已改为 arrival-rate curves，并配 effective completion rate。fileciteturn0file3 | 修订稿 Section 6 确已改为 arrival-rate grids，解释了 underloaded / near-capacity / overloaded 三段，并补充 long-horizon validation、repeated-run variability。fileciteturn0file2 | **基本解决**。当前不需要新实验，只要再把口径写得更“queueing-native”即可。 |
| 内存约束是否只约束当前 batch；preempted jobs 的 KV cache 怎么算 | R3、AE、R1/R2 都抓到这个点。fileciteturn0file0 fileciteturn0file5 fileciteturn0file8 | 回复信明确说已改成“all in-system resident KV caches on GPU”。fileciteturn0file3 | 原稿目标式约束是 \(\sum_{i\in B_t}\le C\)；修订稿 Section 2.3 明确改成 \(G_t\) 上所有 resident caches，Section 2.4 也明确 preemption=pause while retaining GPU cache。fileciteturn0file1 fileciteturn0file2 | **实质解决**。这是对模型 realism 最关键的一项修复。 |
| OOM / eviction / restart safeguard，尤其未知输出长度下如何避免 overflow | R1 直接问 OOM safeguard；AE 也强调 uncertain output lengths 下 OOM 风险。fileciteturn0file0 fileciteturn0file8 | 回复信逐点回应，并强调 WAIT / Nested WAIT 的 threshold + safety buffer。fileciteturn0file3 | 修订稿增补了 Section 2.3 memory-growth example、Example 2/3、Theorem 2 的 logarithmic safety buffer、Section 6 long-decode eviction diagnostic。fileciteturn0file2 | **解决**。而且在叙事上比原稿清楚很多。 |
| Equation (1) 的线性/仿射时间模型是否过强 | AE、R1、R2 都要求更明确的 operating regime 和 justification。fileciteturn0file0 fileciteturn0file7 fileciteturn0file8 | 回复信承认模型是 decode-dominant approximation，并补 A100 validation、PD discussion。fileciteturn0file3 | 修订稿在 Section 2.2 写清 decode-dominant scope，Figure 3 用 A100 80GB profiling，Appendix H.2 做 Vidur vs SGLang/A100 校准，H.4 加 PD-disaggregated study。fileciteturn0file2 | **基本解决**。但 abstract / conclusion 仍需把“under the affine decode-centered model”说得更显性。 |
| policy space \(\Pi\)、batching 操作、preemption 是否允许 | R1、R2 都要求更清楚定义。fileciteturn0file7 fileciteturn0file8 | 回复信称已新增 objective and policy-space subsection。fileciteturn0file3 | 修订稿 Section 2.4 的确补了 non-anticipating policy、admit/batch/preempt/evict 的定义。fileciteturn0file2 | **解决**。 |
| WAIT / Nested WAIT 的“新意”与 proof difficulty 是否只是标准稳定性论证 | AE 和 R3 都把理论新意的说明不足视为核心问题。fileciteturn0file0 fileciteturn0file5 | 回复信把贡献定位改成“modeling + dimensionality reduction + memory-growth control”。fileciteturn0file3 | 修订稿 Theorem 1/2 前后的解释确实强调“难点不是 recurrence per se，而是 overflow 前的 structure design”；Appendix D 也更明确接到 Lindley / Kingman。fileciteturn0file2 | **部分解决**。方向对，但 main text 仍可更精炼、更像 proof roadmap。 |
| proof appendix 应更多依赖标准 stochastic tools，而不是 first principles 堆砌 | AE 明确提出要更显式接到 established theory。fileciteturn0file0 | 回复信说已按 theorem-specific sections 重组，并引用标准工具。fileciteturn0file3 | 修订稿 Appendix D 开头确实点名 Lindley recursion、Kingman、random walk results；proof 组织也比原稿好。fileciteturn0file2 | **部分解决**。但 Proposition 2 在主文里仍显得过于“benchmark-theorem 化”。 |
| unknown/long output lengths 下逐长度分段是否可实现 | R2 要求解释 segment-wise design。fileciteturn0file7 | 回复信称主 theorem 写 clean case，Extensions appendix 写 coarser segmentation。fileciteturn0file3 | 修订稿 Appendix A.2 与 Section 6.2 都已实现基于 segment 的设计与经验 continuation probabilities。fileciteturn0file2 | **解决**。 |
| 实验参数、memory cap、baseline 配置、reproducibility | R2 要求明确 batch size/memory/baseline/Sarathi settings；编辑部也要 latency curve by arrival rate。fileciteturn0file5 fileciteturn0file7 | 回复信详细列出硬件、memory-cap 计算、baseline config、grid choices、replications。fileciteturn0file3 | 修订稿 Section 6 与 Appendix H 现在确有 A100 80GB、1.37e5-token cap、Sarathi chunk=512、10 replications、Table 3 GPU settings 等细节。fileciteturn0file2 | **解决**。 |
| simulator fidelity / real-GPU validation | R2 明确要求真机校准。fileciteturn0file7 | 回复信说已加 A100 calibration 与 end-to-end GPU experiments。fileciteturn0file3 | Appendix H.2 确有 Vidur-vs-A100/SGLang 校准、single-type GPU runs、real-data GPU runs。fileciteturn0file2 | **解决，但需收紧 claim scope**。 |
| long-output regime 与近容量诊断 | R2 要求 >1000 tokens 情况。fileciteturn0file7 | 回复信说已加 p512d1000 和 restart-rate table。fileciteturn0file3 | 修订稿 Section 6.1 已新增 p512d1000、Figure 9、Table 1。fileciteturn0file2 | **解决**。 |
| related work positioning / concurrent theory papers / PD systems | AE 要求更好连接 stochastic-modeling & scheduling literature。fileciteturn0file0 | 回复信说已补 concurrent LLM scheduling theory 与 PD systems。fileciteturn0file3 | 修订稿确已加入 Jaillet/Wang/Chen/Bari/Li 等并区分 information/timing models，也加了 PD discussion。fileciteturn0file2 | **基本解决**，但 related-work 仍稍显罗列式。 |
| typo / notation consistency / careless errors | R1、R2、AE 都提到。fileciteturn0file0 fileciteturn0file7 fileciteturn0file8 | 回复信说已系统检查。fileciteturn0file3 | 大部分显著问题已清掉；但 related work 中 “Splitwise (Patel 2023)” 仍是明显引用失配。fileciteturn0file2 | **未完全解决**。这一类信号问题在回审时必须归零。 |

## Specific edits recommended for the response letter

response letter 的**完成度很高**，而且总体语气是专业、尊重、非对抗性的；我没有看到会激怒编辑或审稿人的防御性措辞。真正的问题不在“态度”，而在**风格与证据组织**：它现在更像一份认真但偏长、偏模板化的“修订说明”，还没完全变成一份让 AE 一眼看出“改到了哪里、还剩什么风险”的 editorial brief。fileciteturn0file3

建议做以下几处高收益改写。  
第一，**把开头的六个 bullet 压缩成三个，并加入精确落点**。现在开头 bullets 覆盖面很全，但有一定重复。建议改成三类：framing、model/memory、evidence；每类一句后直接加 “Sections 2.4/3/6 and Appendix H” 这类锚点。这样更像 AE 想看的 map，而不是 narrative summary。fileciteturn0file3

第二，**把“fully addressing / substantially different / professionalized the exposition”类表达收紧为证据式表述**。这些说法本身不算失当，但在这个稿件的历史语境里，编辑团队最在意的是“你们是否还在高估自己修得有多彻底”。用更克制的表述反而更有说服力。fileciteturn0file5 fileciteturn0file3

第三，**在实验相关回应里加一句主动限定**：real-data curves 是 **offered-arrival-rate-aware offline calibration**，而 GPU 端到端验证主要对应 WAIT / SGLang implementation，而不是把主文所有 baseline 都 end-to-end 落到真机。你们其实已在正文里披露了这些事实；response letter 只差把这点说得更显性，能预先拆掉“fairness / scope overclaim”的潜在追问。fileciteturn0file2 fileciteturn0file3

第四，**把 related-work 与 theoretical novelty 的回应写得更“差异化”而不是更“全面”**。现在 response letter 已经列出了 concurrent papers，但仍可再加一句统一的对比句，例如：你们与现有工作的区别主要在三轴——信息集、service-time model、eviction/restart handling——其中你们最核心的是第三轴。这样比逐条提 paper name 更像一个 editorial answer。fileciteturn0file3

第五，**closing 段建议加入一句“what remains limited”**。例如承认：formal guarantees 仍建立在 affine decode-centered model 和 rate-aware calibration setting 下。这样的克制会增加可信度，尤其面对把这轮修回定义为 risky major revision 的编辑部。fileciteturn0file5 fileciteturn0file3

## Specific edits recommended for the revised paper

最关键的不是再加内容，而是**把已有内容再打磨成一个更加稳定的一致口径**。修订稿已经把几乎所有“大方向错误”修掉了；现在需要做的是让 skeptical reader **没法从措辞、节奏和局部小错误里重新质疑你们是否真正懂开放系统与 OR framing**。fileciteturn0file2

最优先的一项，是**统一 objective/stability/throughput 口径**。建议从 abstract、Introduction summary of contributions、Section 3 末尾、Conclusion 四个位置同步收紧：  
- 用“effective throughput net of evictions”时，要紧跟一句“under exogenous arrivals, the key question is the arrival vectors or load range a policy can stabilize without restart waste”；  
- 避免让读者把贡献读成“在固定 \(\lambda\) 下提高 long-run throughput”，因为这是负面审稿人最敏感的神经点。fileciteturn0file5 fileciteturn0file2

第二，**把 Proposition 2 降格或重命名**。现在它仍以 theorem-like proposition 的形式陈列“任何 online policy 的 throughput 不超过 offered decode-token load”，这在概念上已经被修订稿自己解释成开放系统里的基本 accounting upper bound。保留它并非错误，但它仍会让 R3 式读者觉得“作者在把平凡事实 theorem-化”。建议把它改成 remark / benchmark identity，或者至少在 proposition 前直接写明“this is an accounting upper bound, included only to fix notation for the fluid benchmark”。fileciteturn0file5 fileciteturn0file2

第三，**给 \(M^*\)、\(M_\pi\)、\(M^{(\zeta,\pi)}_{\mathrm{req}}\) 加一个 one-paragraph glossary**。这三个量在修订稿中都定义了，但首次出现时对第一次阅读者仍太快。最省力的办法是在 Section 4.3 和 Section 5.2 各加一句 plain-English mapping：  
- \(M^*\)：fluid equilibrium 需要的参考内存；  
- \(M_\pi\)：阈值策略的基础批量内存；  
- \(M^{(\zeta,\pi)}_{\text{req}}\)：为 finite horizon/high-probability no-overflow 而加了 buffer 的物理内存需求。  
这是非常典型的 OR 会喜欢的“符号-机制映射”。fileciteturn0file2

第四，**明确“preemption”的语义**。Section 2.4 已经好很多，但建议再补一句：“preemption here means scheduler-side pausing with the KV cache remaining GPU-resident; the model does not include swap-out/swap-in latency.” 这样能彻底切断读者把 preemption 理解成 costless offloading 的可能。fileciteturn0file2

第五，**在 Section 6.2 把 tuning disclosure 再显眼一点**。文中已经诚实写了“per plotted arrival rate choose best-performing configuration on a prespecified grid”。建议再补一句：“the resulting curve should be read as rate-aware calibrated performance rather than a claim that one fixed parameterization is uniformly best.” 这是一句很值得放到正文里的防御性澄清。fileciteturn0file2

第六，**把 real-GPU validation 的作用范围写清**。Appendix H.2 的内容是高价值加分项，但 main text 最好明确：它验证了仿真 time model 的 operating regime，并给出 WAIT implementation 的真机可行性与方向性证据；主 baseline league table 仍主要依赖 simulator。这样 claim 会更稳。fileciteturn0file2

第七，**修掉 remaining careless signal**。至少包括：  
- related work 里的 **Splitwise (Patel 2023)** 需要改成 **Patel et al. (2024)**；  
- 检查所有“known arrival types / unknown arrival types”是否应改成“known output lengths at admission / unknown output lengths at admission”；  
- 检查“effective throughput”与“effective completion rate”是否在 captions 和正文里始终被清楚地区分为 token-level vs request-level。fileciteturn0file2

## Exposition and language audit

下面列出我认为最值得打磨的高影响段落/句子，并给出**建议性英文改写**。这个部分的目标不是 copyedit，而是把最可能影响编辑判断的句子改到“稳、准、像 OPRE”。

### Abstract 里的最强 claims

问题在于：abstract 末尾把理论最优性、稳定区“扩大”、基线改进写得很满；内容并非错，但缺少限定条件，容易把已经修好的 framing 又拉回“generic superiority claim”。fileciteturn0file2

建议改写：

> Under the affine, decode-centered serving model studied here, WAIT achieves the fluid benchmark asymptotically when output lengths are known. For unknown output lengths, Nested WAIT achieves the same benchmark in a long-horizon scaling with an additional logarithmic memory buffer for downstream boundary queues. In our A100/Vidur experiments, both policies expand the empirically realized stable operating range and reduce latency relative to the tested baselines.

### Section 2.4 的 objective paragraph

这一段现在已经比原稿强很多，但仍可再把“开放系统里 throughput 的含义”讲得更经济学/排队论一点，而不是更工程学一点。原稿第 12 页是“maximize throughput subject to latency and TTFT”; 修订稿已经纠正了方向，这是你们最该进一步稳固的段落。fileciteturn0file1 fileciteturn0file2

建议改写：

> With exogenous arrivals, a stable policy cannot complete more useful work than the offered decode-token load. The scheduling problem is therefore to preserve that useful service by avoiding restart waste, while keeping delay controlled. We use effective throughput to measure completed decode-token service net of evictions, and latency and TTFT to measure how that service is delivered to users.

### Section 3 关于 \(M^*\) 的解释

现在的公式解释已经出现，但仍偏“formula-after-formula”；对 OR/MS 读者，更应突出为什么长 decode 会二次地吃掉稳定区。fileciteturn0file2

建议改写：

> The role of \(M^*\) is not to “increase throughput” at a fixed load. Rather, it quantifies how much resident memory is needed to sustain a balanced stage mix. Long outputs are especially expensive because they increase both the number of occupied decode stages and the average cache size carried by each active request. That is why a small amount of long-decode traffic can dominate the memory requirement for stability.

### Theorem 1 后的 proof-intuition paragraph

这段已经朝正确方向走了，但还可以再直白一点：**不是在卖 bounded delay 的 surprise，而是在卖 policy-induced dimensionality reduction**。fileciteturn0file2

建议改写：

> The theorem is not claiming that finite delay is surprising once stability is given. The nontrivial step is earlier: WAIT creates a threshold-queue representation before overflow occurs. By enforcing a balanced cohort at each stage, the policy turns a memory-coupled serving system with restarts into a lower-dimensional queueing problem whose drift and memory feasibility can be checked directly.

### Section 6.2 的 per-rate calibration sentence

这段已经披露了很多细节，但建议更明确地告诉读者：这是 offline, rate-aware calibration。否则一部分读者会默认为“online robust tuning”。fileciteturn0file2

建议改写：

> For each plotted arrival rate, we calibrate the threshold scale on a prespecified grid using the offered load and the empirical length distribution. The resulting comparison should therefore be read as rate-aware calibrated performance, rather than as evidence that one untuned parameterization is uniformly best across all arrival rates.

### Appendix H.4 对 PD 的表述

“closely matches the modeling assumptions”略强，可再收一点。fileciteturn0file2

建议改写：

> The PD architecture aligns more closely with our decode-centered timing model than the mixed prefill-decode setting, because the decode server no longer combines prefill attention with token-by-token decoding.

### Response letter 的 opening paragraph

response letter 开头现在信息很多，但仍有模板感。建议更像 editorial memo：先承认最核心的三处缺口，再说对应修改。fileciteturn0file3

建议改写：

> We appreciate the reviewers’ central message that the original manuscript underexplained three issues: the objective in an open queueing system, the memory semantics of resident KV caches, and the source of theoretical difficulty beyond standard stability arguments. The revision therefore focuses on these three points: reframing the objective around useful completed service and stability, rewriting the model so memory applies to all GPU-resident requests, and restructuring the theory and experiments to make the queueing mechanism and empirical scope explicit.

## Any claims that should be softened or backed by additional evidence

最重要的一点是：**这里不需要新实验**；多数风险都可以通过**claim 收缩与口径澄清**解决。下面这些表述建议软化。fileciteturn0file2 fileciteturn0file3

第一，**“Both algorithms are asymptotically optimal”** 应加限定。  
建议写成：**under the affine decode-centered model and the stated long-horizon scaling**。否则读者会默认这是比实际证明更广的 statement。fileciteturn0file2

第二，**“enlarge the realized stability region”** 应加经验性限定。  
最好写成：**in our simulated and supplemental GPU-calibrated experiments**。现在正文多处已暗示这是 empirical，但 abstract/conclusion 还不够显性。fileciteturn0file2

第三，**“The theorem below shows that WAIT realizes this stability in the stochastic system”** 这类话略强。  
Theorem 1 更准确地说是：在给定 scaling 和 threshold conditions 下，WAIT **tracks the fluid benchmark asymptotically while controlling memory growth**。这比“realizes stability”更贴合证明。fileciteturn0file2

第四，**Appendix H.2 里的 “WAIT is consistently lower-latency…”** 最好总是配上 “on the tested grid” 和 “under the feasible SGLang baseline configuration used here”。  
现在 figure caption 其实已经部分这么做了，但正文最好保持同样谨慎。fileciteturn0file2

第五，**Appendix H.4 里 “This architecture closely matches the modeling assumptions in Section 2”** 建议改成 “more closely matches”。  
这纯属文字稳健性，不是实质异议。fileciteturn0file2

第六，response letter 开头若用了类似 **“fully addressing”** 的口气，建议改成 **“substantially addressing”**，并加一句 residual limitations acknowledgment。  
这会让整封信显得更可信，也更符合这轮修回的 editorial context。fileciteturn0file5 fileciteturn0file3

## Final submission-readiness recommendation

**最终建议：`needs targeted revision`。**  
这不是因为论文还缺某个决定性的理论块或实验块；相反，**大部分实质性 reviewer concerns 已经被处理到位**。原稿和修订稿对比后，我的判断是：这次 revision 确实**materially improves the paper in the ways requested**——尤其是 objective/stability framing、resident-memory semantics、arrival-rate latency evidence、GPU calibration、notation/policy-space clarity，这些都不是 cosmetic edits，而是结构性修复。fileciteturn0file1 fileciteturn0file2

但同时，我不建议把它视为“只剩轻微润色”。原因有三：  
- 编辑部已经把这一轮定性为**高风险 major revision**；  
- AE 的最高优先级是**整篇 exposition 的专业化重写**而不是单点补丁；  
- 修订稿仍残留一些会被放大解读的信号：claim 稍满、术语偶有不齐、proof-roadmap 还可更强、个别引用/细节仍显 careless。fileciteturn0file0 fileciteturn0file5 fileciteturn0file2

如果作者按本报告做一轮**定向文字修订**——重点清理 abstract / intro / theorem lead-in / Section 6.2 / conclusion / response letter opening-and-closing——我会把它提升到 **ready after minor edits**。在当前状态下，我不建议直接提交终版；但我同样不认为它需要新模型或新实验。它现在需要的是**最后一轮编辑性收口**，而不是另一轮研究性扩张。fileciteturn0file2 fileciteturn0file3