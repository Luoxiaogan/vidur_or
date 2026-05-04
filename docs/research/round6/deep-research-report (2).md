# 学术稿件大修审计报告

## 执行摘要

本轮修订是**实质性重写**，而不是表面修补。作者确实响应了首轮中最核心的一批问题：把原稿中将开放系统“吞吐优化”写成固定到达率下的目标函数，改写为**稳定域/有效吞吐/延迟/TTFT**的表述；删除了误导性的“heavy traffic”表述；把内存约束从“当前 batch”澄清为**所有 GPU 常驻 KV cache**；重写了第 2 节的模型与记号；把实验从“时间轴 throughput/累计 prompt latency”改成了**到达率—延迟/有效完成率**曲线，并补充了 A100 定时验证、真实 GPU 实验、长输出负载、wait-vs-no-wait 比较和重复运行稳定性检查。就“是否比原稿显著更清楚、更可外审”而言，答案是**是**。fileciteturn0file1 fileciteturn0file4 fileciteturn0file7

但若问题是“**是否已经达到低风险 resubmission 状态**”，我的判断是：**还没有**。当前版本最主要的残余风险不在于“粗疏记号”这一类初级问题，而在于更高层次的**可接受性门槛**：其一，论文现在虽然更诚实地重述了理论定位，但**OR 层面的理论新意/显著性**仍未完全讲透；其二，延迟证据虽明显改善，但仍主要是**有限时域、经验性过渡点**而非稳态/准稳态的系统延迟图景；其三，Equation (1) 的线性时间模型虽被限缩到 decode-dominant regime 并做了 A100 验证，但**外推范围仍偏窄**；其四，作者方法在真实数据实验里做了**随到达率调参的网格选择**，而基线主要使用默认设置，这在高负载区会带来比较公平性与可复现性的疑问。这些问题未必要求“方法论推倒重来”，但足以使下一轮在高标准期刊中依然面临较高拒稿风险。fileciteturn0file2 fileciteturn0file4 fileciteturn0file7

**总体结论：**  
- 若标准是“是否比原稿显著前进并值得继续处理”，答案是**是**。  
- 若标准是“是否现在就可以以较高把握送回期刊/外审”，答案是**否，仍建议先做一轮定向大修**。  
- AE 决策上，我的首选是：**Major Revision（再次大修）**，而不是 Accept/Minor；只有在期刊不愿再给一轮而又坚持当前 OR-level 显著性门槛时，Reject 才是可辩护的次选。fileciteturn0file2 fileciteturn0file7

**我认为当前最关键的 5 个问题**是：

1. **理论新意/显著性仍不足够“主文中自证”**：作者已把“heavy traffic”改正，也解释了 threshold/boundary queue 的降维思路，但“为什么这不只是标准正再生/稳定性结论 + 一个直观 pipeline rule”依然没有被彻底讲成一个强而新的 OR 故事。位置：修订稿摘要、第 1.1 节、第 4.3 节、第 5.2 节。fileciteturn0file0  
2. **延迟证据仍偏有限时域、经验阈值化**：第 6 节现在比原稿好很多，但“λ* 为观测到的 near-overloaded→overloaded transition”本质仍是经验定义；超载区“仅对完成请求计算延迟”也容易让读者质疑比较口径。位置：修订稿第 31–39 页，尤其第 31、34–39 页。fileciteturn0file0  
3. **Equation (1) 的外部有效性仍偏窄**：主文和附录把作用域说明为 decode-dominant，且做了单 GPU/单模型验证；但仍缺少跨 regime（长 prefill、mixed prefill-decode、第二种 GPU 或第二种模型）的敏感性佐证。位置：修订稿第 10–12 页与第 80–82 页。fileciteturn0file0  
4. **实验公平性与复现性仍有一处高风险点**：WAIT/Nested WAIT 在真实数据实验中按到达率从网格中选择 `tl` 和 segment 数，而基线采用默认/固定配置。这不是错误，但需要更明确地做“同预算调参”或把结论改写为“对默认工业配置基线的比较”。位置：修订稿第 32 页、第 37–38 页、第 83 页表 3。fileciteturn0file0  
5. **模型现实性已明显改善但仍有边界条件未充分外显**：内存约束现在覆盖所有常驻 KV cache，这是正确修补；但 LIFO eviction + restart、无 swap-in/out 延迟、无 offloading 策略比较，意味着模型仍服务于一类特定 serving 机制。位置：修订稿第 12–14 页、第 18 页、第 85 页。fileciteturn0file0

## 输入完备性与审查口径

本次审计所需材料基本齐备：**原稿、修订稿、回复信、AE 报告、两份独立审稿报告、决定信**均已提供；其中**最负面的第三位审稿人意见没有单独 PDF，而是完整嵌入在决定信中**。Associate Editor 在决定信中显示“无额外评论”；因此不存在可供比对的独立 AE-to-author 额外文本。换言之，当前评估所依据的“原始关切集合”来自：AE 报告、Review 1、Review 2，以及决定信内嵌的 Referee 3。fileciteturn0file2 fileciteturn0file5 fileciteturn0file6 fileciteturn0file7

下面的判定口径分为三档：  
- **Adequate**：回复与稿件改动基本解决原关切；  
- **Partial**：方向正确、证据增强，但仍留有接受风险；  
- **Inadequate**：核心疑点仍未被真正消除，或回复与稿件不够一致。  

## 优先级发现

| 严重性 | 发现 | 位置 | 为什么重要 | 具体修复建议 |
|---|---|---|---|---|
| **Critical** | **理论新意/显著性仍不够“OR-ready”**。作者已经把工作从“heavy-traffic theorem”改成“fluid-guided threshold control / dimensionality reduction”，但主文仍没有把“哪些部分是标准稳定性后果，哪些部分才是此文真正新东西”讲得足够锋利。 | 修订稿摘要与贡献段（p.1, p.5–6）、Theorem 1 讨论（p.22–24）、Theorem 2 讨论（p.27–31）；AE 报告“Clarifying Theoretical Novelty”；Referee 3 对 positive recurrence / pipeline-bubble / significance 的质疑。fileciteturn0file0 fileciteturn0file2 fileciteturn0file7 | 这直接关系到**能否达到 OR 的发表门槛**，而不只是“有没有修 typo”。如果编辑/审稿人仍认为理论主张主要是标准 drift/positive recurrence 的重新包装，则即使模型更清楚，也可能因“贡献分量不够”被拒。 | 在主文新增一个专门小节或一段 boxed paragraph，标题可用：**“What is new beyond standard stability arguments?”**。建议明确写成三点：**(i)** endogeneous KV-cache growth makes service requirements state-dependent; **(ii)** unknown output lengths create downstream boundary queues absent in standard open queues; **(iii)** WAIT/Nested WAIT’s novelty is the policy-induced reduction from full resident-stage state to threshold/boundary queues. 同时把 Theorem 1/2 的标准负漂移后果收缩为一句，强化“降维构造”本身。 |
| **Critical** | **延迟证据仍不是稳态/准稳态的标准 queueing 证据**。虽然作者已按审稿意见把实验改为 arrival-rate curves，并加了 long-horizon check，但主文仍使用“observed transition λ*”来界定 near-overloaded→overloaded；而超载区“只对完成请求算延迟”容易引发口径争议。 | 修订稿 §6（p.31–39），尤其 p.31 对 λ* 的定义，p.34–39 的图 7–12；回复信 D.4；决定信中 Referee 3(1d)。fileciteturn0file0 fileciteturn0file2 fileciteturn0file4 | 这关系到论文现在强调的“**latency**”是否真的得到充分支撑。若延迟证据主要来自过载区有限时域统计，则“我们改善延迟”容易被看成 throughput 改善的附带结果，而非更强的 queueing 结论。 | 在 **stable / near-stable 区间**（例如低于 λ* 的多个点）补充更长 horizon、带 warm-up 的平均延迟与 TTFT 曲线，报告置信区间，并单独列出“未完成请求比例”。正文措辞建议把“stable operating range”改为 **“empirically observed finite-horizon operating range”**。超载区则建议并列报告：完成率、未完成率、eviction rate、conditional latency。 |
| **High** | **Equation (1) 的适用域虽已澄清，但证据仍偏单一**。作者现在明确这是 decode-dominant affine model，并增加了 A100 校准与真实 GPU 对比，这是显著进步；但支持证据仍集中在 Llama-2-7B + A100 + 近似 decode-dominant 工作负载。 | 修订稿 §2.2–2.3（p.10–12），Figure 3（p.12），Appendix H.2（p.80–82）；Review 1/2 对 Eq. (1) 的关切；AE 报告 model realism。fileciteturn0file0 fileciteturn0file5 fileciteturn0file6 fileciteturn0file7 | 模型的外部有效性决定理论结论能否被读者接受为“有操作意义的 proxy”，还是只是一种局部近似。当前版本已经从“未说明”变成“限定说明”，但尚未从“局部可用”变成“令人信服地稳健”。 | 二选一：**要么补证据，要么再收窄 claims**。补证据方案：增加一个长 prefill / mixed prefill-decode 的灵敏度实验，或第二种模型/GPU 上的定性复现。收窄 claims 方案：在摘要、结论、贡献中加入明确句子：**“All formal guarantees are for decode-dominant affine timing models; beyond this regime our policy should be viewed as a scheduling heuristic inspired by the same control principle.”** |
| **High** | **实验公平性与调参口径仍需更透明**。作者方法在 §6 中按 workload distribution 和 offered arrival rate，从 `tl`、segment 数等网格中选“最低延迟配置”；基线则用默认 Vidur 配置和固定 chunk/pre-reserve 规则。 | 修订稿第 32 页“WAIT and Nested WAIT settings”，第 37–38 页真实数据调参描述，第 83 页表 3；Review 1 的 reproducibility concerns；Response R2.8。fileciteturn0file0 fileciteturn0file4 fileciteturn0file5 | 这不是“无效比较”，但会影响说服力：读者可能质疑作者方法获得了**rate-aware tuning advantage**，而基线未被给予同等调参预算。对高负载区的小差异尤其敏感。 | 建议新增一个“**fair tuning protocol**”段落：对 vLLM / Sarathi 也给出有限网格调参（如 chunk size、memory margin、admission cap），或明确声明本文比较对象是“默认工业配置 baseline”。至少要在正文中把结论收束为：**“outperforms the tested baseline configurations”**，而不是泛称“outperforms vLLM and Sarathi”。 |
| **Medium** | **内存与 eviction 机制的现实性问题已大幅改善，但仍是 stylized model**。现在稿件已明确所有 GPU 常驻 KV cache 都计入约束，并不再暗含无成本 swap；这点是对原稿的关键修补。但仍采用 LIFO eviction + restart，不建模 swap-out/in latency，也没有做 eviction policy/swap penalty 灵敏度分析。 | 修订稿 §2.3–2.4（p.12–14）、§5.1（p.25）、Appendix H.4（p.85）；Referee 3(2b) 与 AE “Model: Modification or Better Justification”。fileciteturn0file0 fileciteturn0file2 fileciteturn0file7 | 这影响的是**模型边界与 claim scope**，而非当下是否存在明显数学错误。若不写清楚，读者会把结果误读成对更广泛 serving stack 的结论。 | 在 §2.4 或结论新增限制段：**“We model restart-on-eviction without CPU/SSD offloading; systems with swap-based recovery or non-LIFO eviction may have different quantitative trade-offs.”** 如果篇幅允许，加一个简短敏感性实验：改用 FIFO/random eviction，或加固定 swap latency penalty，看排序是否稳健。 |
| **Medium** | **理论—实验指标仍存在轻微口径错位**。理论主文强调的是 decode-token effective throughput；大多数实验主图画的是 request-level effective completion rate。作者解释了原因，但桥接仍不够显眼。 | 修订稿 §2.4（p.13–14）、§6（p.31–39）；Response 开头“effective throughput / effective completion rate”重写。fileciteturn0file0 fileciteturn0file4 | 这不会推翻结果，但会让审稿人继续追问“理论 benchmark 与图里指标是否同一件事”。 | 在 §6 开头加一句明确桥接：**“Theory uses token-level effective throughput; experiments report request-level effective completion rate for comparability across heterogeneous decode lengths; Appendix X additionally reports token-level goodput.”** 若能补一张 token-level goodput 图，最佳。 |
| **Medium** | **TTFT 仍主要停留于理论，没有对应实验面**。稿件把 TTFT 放在目标和理论保证里，但数值部分几乎只展示 latency/completion rate。 | 修订稿 §2.4、§4.3、§5.2；决定信指出“latency is not the only goal”。fileciteturn0file0 fileciteturn0file2 | 若作者主张“throughput + latency + TTFT”三者并重，那么实验只测两者会显得证据链不完整。 | 在主文或附录补上 **TTFT vs λ** 曲线，至少给 single-type 和 real-data workload 两组。若不补，建议在摘要和贡献处删弱 TTFT 的实验暗示。 |

## 详细映射表

> 说明：为避免表格过度膨胀，逐行 typo / 公式小修正被归并为“记号与细部勘误”一行；这不影响对所有**实质性关切**的覆盖。

| 来源 | 原始关切 | 作者回复概要 | 稿件改动（位置＋摘录/差异） | 评估 | 建议修复 |
|---|---|---|---|---|---|
| AE / 决定信 | **需要 complete expositional overhaul**；原文写作、符号、直觉、附录组织都不达标。fileciteturn0file2 fileciteturn0file7 | 回复信称：重写第 2–5 节，增加 notation summary、算法前例子、定理解释段、按 theorem modularize appendix。fileciteturn0file4 | 修订稿第 9–14 页现在依次写 prompts、batching、Eq.(1)、memory constraint、objective/policy space；第 19–31 页算法与定理前后均有解释段；附录 H 明显按功能拆分。fileciteturn0file0 | **Adequate** | 无需再做“大改式重写”；只需在理论定位与实验口径上继续精准化。 |
| Review 2 / Review 1 | **Section 2 记号冲突、政策空间 Π 不清、Algorithm 1 后缺乏直觉解释、typo 较多。**fileciteturn0file5 fileciteturn0file6 | 回复信逐条说已统一 stage 记号、增加 policy class、notation appendix、示例与机制段，并修正 `Thoughput` / `d` vs `d1` 等。fileciteturn0file4 | 修订稿 §2.1 用 `s` 表示 stage；§2.4 正式定义 Π 和可观测信息；`Thoughput` 拼写及 `d0/d1` 错误已修正。原稿 p.12 仍写着“maximize throughput subject to latency constraints”，且“non-preemptive”与“preemption allowed”并存；修订稿 p.14 已重写。fileciteturn0file1 fileciteturn0file0 | **Adequate** | 可再做一轮 copy-edit，但不再是决定性问题。 |
| AE / Review 1 / Review 2 | **Equation (1) 是否现实？作用域是什么？不同 GPU / regime 可能非线性。**fileciteturn0file5 fileciteturn0file6 fileciteturn0file7 | 回复信把 Eq.(1) 明确为 decode-dominant affine approximation，并增加 A100 校准与真实 GPU 实验。fileciteturn0file4 | 修订稿 p.10–12 清楚说明 affine form 的 decode-centered scope；Figure 3 在 A100 80GB / Llama-2-7B 上给出线性拟合；附录 H.2 给出 simulator-vs-GPU 误差。fileciteturn0file0 | **Partial** | 增加一个非 decode-dominant regime 的敏感性实验，或把摘要/结论 claims 再收窄。 |
| AE / Review 2 / Referee 3 | **内存约束原稿似乎只作用于当前 batch；preempted jobs 的 KV cache 是否也算；OOM/eviction 如何处理；swap 是否被忽略。**fileciteturn0file2 fileciteturn0file6 fileciteturn0file7 | 回复信称已把 memory constraint 改为所有 GPU-resident KV caches，并把 eviction 建模为 restart，不依赖无成本 CPU/SSD swap。fileciteturn0file4 | 修订稿 Eq.(2) 明确 `Gt` 是所有常驻 GPU 的 prompts；p.12–14 明确 evict-and-restart、LIFO；p.25 进一步说明 resident boundary queues 也算内存。fileciteturn0file0 | **Partial** | 该问题已从“模型错误/模糊”变为“模型风格化/边界有限”。需增加 limitation paragraph 或敏感性分析。 |
| Referee 3(1a) | **“heavy traffic” 实际上是 fixed-load / infinite-horizon scaling，不是 classical heavy traffic。**fileciteturn0file2 | 回复信承认术语错误并称已删除 heavy-traffic 叙事。fileciteturn0file4 | 原稿 p.17–19 明确写 “Heavy Traffic Analysis”；修订稿 p.21–23 改为 asymptotic scaling / scaled delay metrics，全文主叙事不再用 heavy traffic。fileciteturn0file1 fileciteturn0file0 | **Adequate** | 无。 |
| Referee 3(1c) | **开放系统下 throughput 在稳定区等于 arrivals；更合理的问题是 stability region / useful completed work，而不是固定载荷下“最大化吞吐”。**fileciteturn0file2 | 回复信称已重写 objective：稳定系统完成率受 offered load 上界约束，核心是稳定域与有效吞吐。fileciteturn0file4 | 原稿 p.12 的目标函数是 `max E[Throughput(T,π)] s.t. ...`；修订稿 p.13–18 把 throughput 改成 effective throughput，并在 p.17–18 明言 `Throughput* = Σ λ_j l'_j` 与 fluid stability region。fileciteturn0file1 fileciteturn0file0 | **Mostly Adequate** | 建议在摘要也更明确写“stability-region / finite-horizon goodput”而非泛泛“optimize throughput”。 |
| Referee 3(1d) | **原实验明显大多在 unstable regimes，导致 latency 比较意义不足；建议画 latency vs arrival rate。**fileciteturn0file2 | 回复信称已改为 arrival-rate curves，并补 long-horizon check、重复运行分析。fileciteturn0file4 | 修订稿 p.31–39 的 Fig.7–12 已全部改为 arrival rate vs latency / effective completion rate；p.36 增加 near-transition long-horizon check；附录 H.3 增加重复运行表。fileciteturn0file0 | **Partial** | 方向完全正确，但仍建议补 stable 区的近稳态延迟/TTFT 与未完成率，以消除“只在超载区更低延迟”的疑问。 |
| Referee 3(1b) / AE | **理论结果是否只是正再生/标准漂移论证的直接后果？如果困难在证明之前的 policy construction，就必须在主文讲清。**fileciteturn0file2 fileciteturn0file7 | 回复信将新意重新定位为：endogenous memory growth + threshold-induced dimensionality reduction，而非新 diffusion/heavy-traffic theorem。fileciteturn0file4 | 修订稿 p.22–24、p.27–31 确有更好的 theorem interpretation，也多次出现 threshold queues / boundary queues / dimensionality reduction 的表述。fileciteturn0file0 | **Partial / 接近 Inadequate** | 这是当前最重要的 acceptance risk。必须再补一个“new beyond standard stability”主文段落，必要时删弱 theorem-level heroic wording。 |
| Referee 3(2a) | **WAIT 像 pipeline-bubble prevention，直觉上并不复杂；真正有趣的是 latency 影响。**fileciteturn0file2 | 回复信通过 Example 2/3、arrival-rate latency curves、threshold-without-waiting ablation 来反驳“只是 pipeline filling”。fileciteturn0file4 | 修订稿 p.19–21 用 FCFS eviction cascade 解释 why naive scheduling fails；附录 H.1（p.80–81）专门做 wait-vs-no-wait。fileciteturn0file0 | **Mostly Adequate** | 若要更稳，可在主文加一句对 H.1 的总结，不要把关键辩护完全放附录。 |
| Referee 3(2b) | **原内存模型似乎绕开了“等待作业的缓存占用”和“swap 成本”这些关键难点。**fileciteturn0file2 | 回复信称已把 resident waiting jobs 的 KV cache 计入，并不再假设零成本 swap。fileciteturn0file4 | 修订稿 p.12–14、p.18、p.25 已明确 resident queues count against memory。fileciteturn0file0 | **Mostly Adequate** | 仍需 limitation paragraph，说明为何采用 LIFO+restart，并指出何种系统不适用。 |
| Review 1 | **`C ≥ M*` 不是 benign assumption，长输出下可能极不现实；实验需说明是否满足该条件。**fileciteturn0file5 | 回复信把 `M*` 解释成 fluid stabilizability requirement，并增加长输出/near-overloaded 实验。fileciteturn0file4 | 修订稿 p.15–18 明确 `M* ≤ C` 是 fluid stability region 条件；p.34–36 新增 p512d1000 与 eviction diagnostic。fileciteturn0file0 | **Mostly Adequate** | 建议在实验小节每次明确标注：该 workload/arrival-rate 是否在 `M* ≤ C` 区、是否故意超载。 |
| Review 1 | **Theorem 1 proof 中 decode-stage dynamics 似乎没有说清，waiting-threshold 才是关键；能否明确 batch index 与 stage index？**fileciteturn0file5 | 回复信称已在主文与附录中分离 batch index / stage index，解释 threshold-sized flows across decode stages。fileciteturn0file4 | 修订稿 p.22–24 确实把 threshold queues 讲清了不少；回复信也声称附录按 theorem 重写。fileciteturn0file0 fileciteturn0file4 | **Partial** | 从可读性上改进明显；但若 AE 仍担心 proof verifiability，建议要求作者在主文补一个 5–8 行 proof roadmap，明确“why l′ stages collapse into threshold queues”。 |
| Review 1 / Review 2 | **实验复现：batch size、capacity、Sarathi 配置、长输出、GPU fidelity、真实数据参数等需公开。**fileciteturn0file5 fileciteturn0file6 | 回复信称已补硬件说明、KV-cap 计算、baseline config、rate-specific settings、真实 GPU 细节与 Table 3。fileciteturn0file4 | 修订稿 p.31–38 与附录 H.2–H.3 显著增强了参数可见性。fileciteturn0file0 | **Adequate（但公平性另列）** | 建议再加一个统一 configuration table（放主文或补充材料），方便复查。 |
| Review 1 | **如果只设 threshold 不 waiting，会怎样？**fileciteturn0file5 | 回复信称已在附录加 WAIT-no-wait。fileciteturn0file4 | 修订稿 Appendix H.1（p.80–81）确已加入。fileciteturn0file0 | **Adequate** | 最好在主文第 6 节一句话前置结论。 |
| Referee 3 / 决定信 | **写作中 fluid model 的解释仍可能不够充分；结果解释要更多，不只是列公式。**fileciteturn0file2 | 作者在回复与修订中确实增加了每个关键公式后的 operational interpretation。fileciteturn0file4 | 修订稿 p.15–18（fluid equilibrium / `M*` / `Throughput*`）比原稿清晰明显。fileciteturn0file1 fileciteturn0file0 | **Mostly Adequate** | 目前不再是首要风险。 |
| 本次审计新增 | **响应信与主文存在轻微 scope overclaim**：例如把 Fig.7–12 的 λ* 现象称为“stable operating range / stability region expansion”，以及理论用 token-level effective throughput、实验常报 request-level completion rate。 | 回复信多处使用“stability region / effective throughput”扩大表述。fileciteturn0file4 | 修订稿 p.31 明确 λ* 是 observed transition；但摘要、结论和若干段落仍有容易被读者读成更强结论的措辞。fileciteturn0file0 | **Inadequate（措辞层面）** | 把所有“stability region”“outperforms X”改为更审慎表述：**“empirically observed finite-horizon operating range”**、**“outperforms the tested baseline configurations”**。 |

## 推荐的 AE 决策

### 首选建议

**Major Revision（再次大修）**

**理由：**  
这份修订稿已经**明显超过“仅做表面改稿”**的程度，许多首轮意见——尤其是写作清晰度、模型定义、开放系统 throughput 定位、内存约束、arrival-rate latency 图、A100 校验、长输出与 waiting ablation——都得到了认真且可见的响应。就“是否值得继续推进到下一轮”而言，我的判断是**值得**。fileciteturn0file4 fileciteturn0file0

但我**不支持 Accept 或 Minor Revision**。原因不是“还有一些 typo”，而是仍有两类高阶问题会决定是否能过 OR 门槛：  
- 理论新意/显著性是否足够强，是否真正超出了“标准稳定性 + 直观阈值规则”；  
- 延迟与实验设计是否已经足以支持作者现在更强调的 latency story。  
这些都不是一句 rebuttal 能替代的，仍需要主文和实验层面的增补。fileciteturn0file2 fileciteturn0file7

### 其他选项的可支持度

| 选项 | 是否支持 | 说明 |
|---|---|---|
| **Accept** | **不支持** | 当前仍有显著 acceptance risk，特别是理论显著性与实验口径。 |
| **Minor Revision** | **不支持** | 剩余问题不是 copy-edit 级别，而是需补主文定位、实验与 claims。 |
| **Major Revision** | **支持（首选）** | 稿件有明显进步，也显示作者愿意认真改；剩余问题可通过定向补强解决。 |
| **Reject** | **保留为次选** | 若 AE 判断 OR 对理论显著性的要求在本轮已经必须达标、且不愿再给一轮，则 reject 也可辩护；但基于当前修订质量，我更倾向再给一轮 major。 |

### 对“是否 ready for resubmission”的一句话判断

**如果作者尚未正式回投：我建议先补完上面 5 个高优先项再投；以当前版本直接 resubmit 仍属高风险。**  
**如果作者已经正式提交了该修订版：我建议 AE 进入下一轮评估，但结论应为 major revision，而非 accept/minor。**

## 开放问题与局限

本次审计依据的是已提供材料；**未见独立的 Referee 3 PDF**，其意见来自决定信内嵌文本。由于时间与材料形态限制，我没有逐行重做所有附录证明，也没有对仿真代码做可执行复现，因此对“是否存在隐藏数学漏洞/实现 bug”的结论只能是：**修订稿已修复此前显见的公式与定义层错误，但附录验证风险仍未完全消失**。这也是我不建议直接以当前版本作为“低风险 resubmission”的原因之一。fileciteturn0file2 fileciteturn0file4