# 修回包小修就绪度审计

## Verdict

**结论：Ready after minor edits（小修后即可提交；保守分档也至多是 minor revision）。** 我认为这套修回材料已经跨过了“还需要再来一次大修”的门槛。原稿之所以被置于“高风险大修”，核心不是单一技术点，而是若干结构性问题叠加：开放系统下吞吐量目标表述不当、“heavy traffic”表述失准、内存约束似乎只作用于当前 batch、证明主文过于抽象且附录不易核验、实验把吞吐量-时域图和“按 prompt 编号的延迟图”混在一起，难以支撑稳定区间与延迟判断。现在的修订版与response letter，已经把这些关键风险逐项改成了可核验、可解释、且与原始批评对应的版本：目标重写为外生到达下的稳定区间/有效完成率问题；内存约束明确覆盖所有保留在GPU上的KV cache并写清 eviction/restart 机制；线性迭代时间模型被限定作用域并补了A100/SGLang校准；“heavy traffic”改成明确的渐近缩放；实验重构为“延迟 vs 到达率”并配对 effective completion rate、真实数据下的 \(M^*(\lambda)\) 表、重复运行与真实GPU补充验证。以“决策风险”而非“愿望清单”标准看，剩余问题已经主要是表述打磨，而不是有效性或可验证性风险。fileciteturn0file7L29-L54 fileciteturn0file7L62-L118 fileciteturn0file0L4-L6 fileciteturn0file0L62-L81 fileciteturn0file6L679-L738 fileciteturn0file6L1147-L1159 fileciteturn0file6L1255-L1267 fileciteturn0file6L1764-L1841 fileciteturn0file3L13-L44 fileciteturn0file3L48-L78 fileciteturn0file2L395-L516 fileciteturn0file2L618-L700 fileciteturn0file2L888-L925 fileciteturn0file2L1236-L1291

## True Blockers, If Any

**未见真正的P0阻断项。** 目前我没有看到任何剩余问题会实质性动摇论文有效性、削弱response letter可信度，或让AE/审稿人仍无法判断“原始关切是否被处理”。 例如，关于是否必须把模型扩展到swap/更复杂非线性时间模型，AE原本就明确表示不必为了回应每条批评而强行复杂化模型，关键是要把适用范围、限制与机制讲清楚；而修订版现在已经把“GPU-resident/recompute、不做零成本swap、线性时间模型是特定工作区间的一阶近似”说清，并补了A100与SGLang的补充证据。换言之，这些现在更像是**已显式承认的范围限制**，不是会阻止 resubmit 的隐藏缺陷。fileciteturn0file7L100-L118 fileciteturn0file3L949-L972 fileciteturn0file2L380-L393 fileciteturn0file2L510-L516 fileciteturn0file2L3873-L3897

## Minor Edits Before Submission

- **给response letter补“精确定位信息”**：每个主问题后建议再加上精确页码/定理/图号/附录位置，而不仅是“Section 6”“Appendix H”这类较粗引用。现在回信内容本身是到位的，但对AE/审稿人二次核验来说，还可以更“审稿友好”。fileciteturn0file3L108-L140 fileciteturn0file3L653-L726 fileciteturn0file3L782-L816

- **用一句话彻底统一“token-level effective throughput”与“request-level effective completion rate”的分工**：理论部分主要谈完成的decode-token服务；实验主图在开放系统语境下主要用 request-level effective completion rate 配合 latency-vs-\(\lambda\) 看可持续负载。现在两者都出现了，方向是对的，但可以在Section 2.4或Section 6开头再加一句更显眼的统一说明，减少读者在术语层面的二次推断。fileciteturn0file3L13-L23 fileciteturn0file3L787-L816 fileciteturn0file2L485-L500 fileciteturn0file2L1247-L1257

- **把模型范围限制再前置半步**：修订版已经说明线性迭代时间模型的适用区间、单GPU主理论、以及不建模零成本swap；我建议在摘要末句、引言贡献段或结论里再加一句更醒目的scope sentence，明确“真实GPU实验是校准与实现证据，不是对所有系统栈/所有工作区间的普适外推”。这仍是纯文本层面的稳健化，不需要新实验。fileciteturn0file3L31-L44 fileciteturn0file3L68-L78 fileciteturn0file2L23-L35 fileciteturn0file2L380-L393 fileciteturn0file2L3873-L3897 fileciteturn0file2L1656-L1670

- **把Table 2与Figure 12的对应关系写得再直接一点**：现在文本已经说 \(M^*(\lambda)\) 在 \(\lambda=70\) 与 \(80\) 之间跨过 \(C\)，并与真实数据延迟曲线从 near-overloaded 向 overloaded 的转折一致；建议把这句再短促、醒目地放到图注或结果段首句，进一步提升“理论-实验对照”的可读性。fileciteturn0file2L1591-L1606 fileciteturn0file2L1609-L1652

## Response Letter Assessment

response letter总体上是**准确、专业、且与修订稿高度对齐**的。它没有回避最敏感的原始批评，而是把“开放系统吞吐量解释”“heavy traffic误称”“positive recurrence并非真正难点”“GPU内存机制与preemption/eviction关系”“延迟证据应该按到达率展示”“实验参数和GPU验证要更透明”这些关键问题放到了最前面，并给出了与正文/附录可对应的修改说明。从我核对的主要点看，回信中的核心陈述基本都能在修订稿中找到对应文本、图表或附录位置，没有明显“回信说改了、正文其实没落地”的失配。它唯一还可改进的地方不是内容真实性，而是**可检索性**：回信偏长，如果加上更具体的页码/图号，将更利于AE和审稿人快速确认。fileciteturn0file3L5-L23 fileciteturn0file3L48-L78 fileciteturn0file3L84-L105 fileciteturn0file3L760-L779 fileciteturn0file3L782-L816 fileciteturn0file3L829-L863 fileciteturn0file3L875-L905 fileciteturn0file3L949-L972 fileciteturn0file3L1002-L1009 fileciteturn0file2L395-L516 fileciteturn0file2L888-L925 fileciteturn0file2L1236-L1291

## Original Concern Coverage

- **开放系统吞吐量与目标函数**：原始批评指出，外生到达的开放系统里，稳定时吞吐量本质上等于到达率，真正该讨论的是可维持的稳定区域，而不是固定到达率下“优化吞吐量”；原稿也确实把问题写成“max throughput subject to latency/TTFT constraints”。修订版已把 Section 2.4 与 Section 3 改写为：在稳定区内处理 offered load，核心问题是通过控制内生内存增长和eviction/restart来扩张可持续到达率范围，并用 \(M^*\) 与稳定区域来解释这一点。这一项我认为已被**实质覆盖**。fileciteturn0file0L64-L81 fileciteturn0file6L713-L738 fileciteturn0file3L782-L816 fileciteturn0file2L485-L516 fileciteturn0file2L526-L536 fileciteturn0file2L660-L700

- **延迟证据必须改成 latency-vs-arrival-rate**：原稿主要画“throughput vs time horizon”和“latency vs prompt number”，这正是Referee 3认为不足以说明稳定边界和延迟含义的地方。修订版已经把 Section 6 重建为 arrival-rate sweeps，并把 latency 与 effective completion rate 配对展示；同时补了 near-transition 的长时域检查、重复运行方差检查，以及真实数据下的 \(M^*(\lambda)\) 对照。该项已从“核心缺口”降到“做法合理且足够”。fileciteturn0file0L81-L81 fileciteturn0file6L1764-L1841 fileciteturn0file3L875-L905 fileciteturn0file2L1236-L1257 fileciteturn0file2L1302-L1374 fileciteturn0file2L1412-L1435 fileciteturn0file2L1591-L1652 fileciteturn0file2L3960-L4021

- **GPU KV-cache 内存机制/OOM问题**：原稿的内存约束写法确实像是只约束当前 batch，且“非抢占”与“允许preemption”并存，容易让人误解。修订版现在明确：约束对象是所有仍驻留在GPU上的KV cache；未被选中的resident prompts仍占GPU内存；preemption只是scheduler-side pause而不是免费swap；如果超内存，按LIFO规则evict并从prefill重启。这个问题现在已经从“模型歧义/可能致命”变成“已明确的建模选择”。fileciteturn0file5L21-L29 fileciteturn0file6L679-L738 fileciteturn0file3L949-L972 fileciteturn0file2L395-L450 fileciteturn0file2L510-L516 fileciteturn0file2L793-L797

- **线性 iteration-time 模型**：原始审稿意见并不是要求作者把模型做得极其复杂，而是要求说明“它到底对应哪个工作区间”、若不普适则要诚实限定，并尽量给出硬件校准。原稿只有L20图与较粗略说明；修订版则明显更成熟：正文限定这是KV-cache驱动区间的一阶模型，讨论了更丰富服务时间曲线与prefill-decode disaggregation，并在A100上给出近线性测量、Vidur-vs-A100校准（\(R^2=0.9943\), MAPE 1.93%）及SGLang端到端补充。就当前轮次而言，这已经足够把它从“模型不够可信”降到“范围明确的简化模型”。fileciteturn0file4L48-L118 fileciteturn0file5L31-L37 fileciteturn0file6L662-L665 fileciteturn0file3L31-L44 fileciteturn0file3L705-L726 fileciteturn0file2L349-L393 fileciteturn0file2L434-L439 fileciteturn0file2L3873-L3897 fileciteturn0file2L4050-L4068

- **证明组织与理论定位**：AE明确批评原稿主文里的证明摘要过于空洞、附录像“deposit boxes”，而Referee 3则质疑某些结论是否只是正再生/稳定性的常规后果。原稿确实只有非常高层的一句“proof employs coupling technique”；修订版现在在主文解释了真正的难点是如何在内生KV增长与eviction风险下，把系统规约成 threshold queues / boundary queues，并在附录D/E开头给了 proof roadmap，且明确调用 Lindley/Kingman/Doob 等标准工具。这一项我判断为**显著改善且足以让本轮审稿继续核验**。fileciteturn0file7L75-L98 fileciteturn0file7L112-L118 fileciteturn0file0L75-L79 fileciteturn0file6L1255-L1267 fileciteturn0file3L829-L863 fileciteturn0file2L908-L925 fileciteturn0file2L2560-L2578 fileciteturn0file2L3020-L3034

- **实验透明度与可复核性**：原始审稿人要求给出批大小、内存上限、容量、Sarathi配置、Nested WAIT参数、以及更直接的GPU验证。修订版现在写清了A100 80GB/Llama-2-7B、KV-cache cap约 \(1.37\times10^5\) tokens、baseline的局部预留规则、WAIT/Nested WAIT 的 tl 与 segment 参数网格、真实数据 \(M^*(\lambda)\) 表、真实GPU参数表、重复实验方差、以及threshold-without-waiting对照。按“审稿人是否能复核关键结论”标准，这一项已经从明显短板修复到基本合格。fileciteturn0file4L151-L186 fileciteturn0file5L61-L81 fileciteturn0file3L653-L726 fileciteturn0file2L1259-L1289 fileciteturn0file2L1583-L1606 fileciteturn0file2L3873-L3958 fileciteturn0file2L3996-L4007

## Final Recommendation

如果上述P1修改能在文字层面补齐，我会把这套材料定为**Ready after minor edits**；即便作者不做全部微调、而只是把若干点保留为明确限制，这一包也应被视为**minor-revision-level resubmission，而不是再次 major revision**。原先“高风险大修”的核心风险——不是因为想法不重要，而是因为关键概念、机制、证明与实证都不够可核验——现在已经基本被化解。就当前证据看，我不会建议“reject / not ready”，也不会建议再来一轮“major revision”。fileciteturn0file0L4-L6 fileciteturn0file7L62-L69 fileciteturn0file3L1002-L1009 fileciteturn0file2L1656-L1670