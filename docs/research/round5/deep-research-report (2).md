# OPRE/MS 修回包审计报告

## 总体结论

这次修回**是实质性大修，不是表面修补**。作者确实针对首轮最关键的三类问题动了“骨架”：一是把问题从原稿里容易误导人的“固定到达率下追求 throughput”改写为**外生到达、稳定域、有效完成服务与驱逐重启**；二是把内存约束从“当前 batch”改成了**所有 GPU-resident KV cache**；三是把实验从原稿中容易落入“不稳定区间看时间横轴/请求序号”的展示，改成了**随到达率变化的 latency + effective completion rate 曲线**。这些都正中 AE 和最强负面审稿人的核心批评。对比原稿与修订稿，这一轮已经足以证明作者认真回应了“complete expositional overhaul”“model realism”“throughput in an open system”“latency interpretation”等主问题。（AE报告，第1页29–40行；第2页20–27行；第3页17–35行；原稿，第11页41–48行、第12页7–17行、第17页39–42行、第26–29页图示；修订稿，第12页41–56行、第13–14页、第22–23页、第31–38页）

但我的结论不是“已经稳了”，而是：**有资格进入严肃复审，但仍然是高风险修回**。如果现在直接按此版本再投，我认为它更像“能过初步门槛、但仍可能在二轮收到较强 pushback”的包，尤其是在以下几项上：**实验调参公平性、unknown-output-length 的实际信息假设、过载区 latency 的解释、以及理论延迟量与实验延迟量之间的口径桥接**。这些问题不再像原稿那样“致命到看不下去”，但依然足以触发再一次 major revision，甚至在遇到最苛刻审稿人时重新转向 reject。决定信已经明确把本轮定性为 **“risky major revision”**，并特别提醒“**Throughput is one goal, but not the only one**”；这句话在当前修订稿里虽然被部分吸收，但还没有完全消化成一套无歧义的叙述与证据链。（决定信上传文本；回应信，第15–17页；修订稿，第31页4–11行、第38页59–61行）

我的一句话判断是：**修回充分“显示诚意与进步”，但尚不足以“封口所有关键异议”**。

## 对 AE、审稿人和决定信意见的回应是否充分

先说正面结论：**大部分一轮核心批评都被正面回应了，而且回应方向基本正确。**

**写作与 exposition** 方面，作者确实做了 AE 要求的“coherent rewrite”，而不是只修 typo。AE 原话是这部分是“**most critical issue**”，还批评原稿“difficult to digest”“prevent a full assessment of the contribution”，并且特别点名原稿把 proof summary 写成“**The proof employs the coupling technique...**”这种对 OR 读者无用的高空概述、附录像“deposit boxes”。修订稿则在正文里加入了 Example 1/2/3、Objective and Policy Space、Theorem interpretation paragraphs，并且把附录重构成标准工具 + theorem-specific proof sections；这与 AE 的指令高度对位。原稿第19页还停留在“Detailed proofs are available in Appendix B”这一层，修订稿第23页和第30页已经开始解释“为什么不是平凡的 positive recurrence”“为什么 boundary queue 是关键 reduction”。这一项我给“**充分回应**”。（AE报告，第2页33–41行；第3页1–10行；原稿，第19页13–19行；修订稿，第20–23页、第30页15–25行、第52页起附录结构）

**open system / throughput / stability-region** 方面，最强负面审稿人的批评基本被吸收了。原稿第12页还是“max E[Throughput(T,π)] s.t. latency/TTFT constraints”的写法，原稿第17页还把分析叫作“Heavy Traffic Analysis”；决定信中的长评则明确指出：这是**open system**，稳定系统下 completion rate 就等于 arrival rate，因此核心问题应是**稳定域/可维持的到达率范围**，而不是固定 arrival vector 下“再提高 throughput”。回应信第15页明确承认这一点：稳定系统只能完成 offered load，相关 operational question 是“which arrival rates a policy can stabilize”；修订稿第14页和第31页也确实改成了“effective throughput capped by offered load”“With exogenous arrivals at rate λ, a stable policy completes requests at that rate in steady state”。这项我也给“**基本充分回应**”。（原稿，第12页7–17行、第17页39–42行；回应信，第15页19–39行；修订稿，第14页5–10行、第31页4–11行）

**内存语义 / OOM / KV-cache** 方面，修订稿比原稿进步很大。原稿第11页的内存约束只约束当前 batch \(B_t\)；而 AE 和审稿意见都明显担心“等待中的 resident jobs 怎么算内存”“是否会 OOM”“preempted jobs 的 cache 放哪”。修订稿第12页把 GPU 内存集合改成 \(G_t\)，明确包括当前 batch 之外、但 KV cache 仍 resident 的请求；并显式建模如果 constraint 无法满足，就触发 LIFO eviction + restart。回应信第18页对这一点也写得很清楚：不依赖零成本 swap-out，超限时就驱逐并重启。就“是否正面处理了 reviewer concern”而言，这一项是**明显解决了原稿歧义**。当然，LIFO 是否是最合适的真实机制、以及对其他 eviction policy 是否稳健，是下一层问题；但至少“原稿没说清楚”这个毛病，这一轮修掉了。（原稿，第11页41–48行；修订稿，第12页41–56行、第14页24–29行、第21页13–15行、第27页44–45行；回应信，第18页4–23行）

**Equation (1) 的线性时间模型** 方面，修订稿也做了实质增强。审稿报告要求作者明确自己到底在对应哪种 regime，并补做真实 GPU 验证。修订稿第10–12页现在明确把式 (1) 定位为 **decode-dominated** 近似，承认 prefill-dominant 或 mixed regime 可能需要 richer calibrated service-time curve；同时把原稿的 L20 图换成了 A100 80GB 的 Figure 3，并在附录 H.2 补了 Vidur–A100 calibration 与 real-GPU end-to-end runs。回应信第1页与第13–14页对这一点的描述，和修订稿实际内容是一致的。我认为这项属于“**回应到位，但证据仍偏窄**”。（审稿报告1，第2页65–69行；第3页1–3行；回应信，第1页24–36行；第13–14页；修订稿，第10页25–38行、第11页4–34行、第12页30–35行、第79–83页）

**理论新颖性 / positive recurrence** 方面，回应是“部分充分”。回应信第16页现在明确说：“难点不是 stable queue finite delay 这一常识，而是如何在 memory-growth + eviction risk 下把高维过程约化到 threshold/boundary queues”；修订稿第23页和第30页也确实把 proof logic 说清楚了不少。这比原稿好很多，也符合 AE“如果贡献在 modeling 而不是 in new math, 就直说”的要求。但说实话，最强审稿人可能仍然会追问：你现在讲清了“为什么不完全平凡”，但是否已经讲清了“为什么足以到 OR/Management Science 的方法力度”？这个问题，我认为修订稿**缩小了争议，但没有完全封口**。所以这一项是“**改进显著，但未必彻底说服所有人**”。（AE报告，第3页29–35行；回应信，第16页5–40行；修订稿，第23页13–26行、第30页15–25行）

## 仍然高风险的问题

这里我只说**最可能继续引发拒稿或再大修**的问题，而不是一般性建议。

**第一，实验比较的“调参对称性/公平性”仍然危险。** 修订稿第32页和第37页写得很诚实：WAIT/Nested WAIT 在实验里会根据 **offered arrival rate** 用预设网格选择 \(tl\)、\(L\) 等参数，甚至在 real-data runs 里“**use the lowest-latency configuration on this prespecified grid for each offered arrival rate**”；而基线则是“default Vidur configurations”加一个共同的 1% buffer rule。也就是说，目前的比较实际上更接近“**ours after rate-aware grid calibration vs baselines with default settings**”，而不是对三者都做同等强度的调参比较。这个设计本身并非不合法，但如果正文仍用较强的 comparative language，而没有把这种不对称 tuning 讲得更醒目，下一轮很容易被抓住说“经验结果偏向所提方法”。这是我认为当前最像 **P0** 的点之一。（修订稿，第31页21–32行；第32页25–37行；第37页27–34行）

**第二，“unknown output lengths” 的 claim 仍然有范围滑移。** 修订稿第24页第12–13行写“**This section removes that information assumption**”，第24–25页也把 Nested WAIT 写成 admission 时不知道个体输出长度、只沿 decode path 揭示；这在 request-level 上是对的。但真正落到 real-data implementation，第37页又清楚写了：Nested WAIT 是 **distribution-aware** 的，阈值来自**经验 workload distribution + offered arrival rate**，并且按每个 arrival rate 做网格选型。也就是说，它不是“对未知长度完全无先验”的算法，而是“**单个请求长度未知，但总体分布与负载规模可估/可调**”的算法。这个口径在回应信里其实写得比论文更谨慎；论文正文、尤其第5节开头和摘要，最好也同步收紧，否则很容易被说成 scope overclaim。这是第二个 **P0**。(回应信，第13页21–28行；修订稿，第24页11–15行、第25页13–20行、第37页7–34行)

**第三，latency interpretation 虽然大幅改进，但在 overload 区间仍有统计口径风险。** 修订稿第31页第9–11行明确说明：超过观察到的可持续区间后，“latency is then computed over the requests that complete during the run”。这是比原稿诚实得多，但也意味着 overloaded 区的 latency 不是标准 steady-state mean latency，而是**条件于完成样本**的 run-based 指标。对“观察稳定域边界附近的行为”它有价值；但如果正文或摘要把 overload 区的 latency improvement 说得太像常规 queueing latency superiority，就还是容易被挑刺。更重要的是，论文把 TTFT 作为核心指标和理论对象反复强调，但数值实验几乎不报 TTFT。这会让“throughput is not the only one / latency and TTFT guarantees”这一线显得经验支撑不对称。对 OPRE/MS 这类顶刊，**delay 的口径和支撑必须非常干净**。这至少是 **P0/P1 边缘** 问题。（决定信上传文本；修订稿，第14页11–16行、第22–23页、第31页4–11行、第38页59–61行）

**第四，theory-to-experiment bridge 仍有一层没有完全搭平。** 修订稿第25页承认 Theorem 2 的主分析为清晰起见采用 common prefill length \(l\)；第47页再补充 heterogeneous prefill length 的 sufficient memory condition 与 segmented extension。这个处理已经比原稿好很多，但真实数据实验第35–38页显然是 heterogeneous prefill + coarse segmentation + per-rate calibration。对于“论文主定理到底对应到实验哪一层”这一点，当前仍需要作者更直白地告诉读者：**哪些现象是 theorem-covered，哪些只是 theorem-inspired implementation**。否则读者会自然滑到“实证 = 主定理直接落地”的理解。这是我倾向放在 **P1** 的高风险项。（修订稿，第25页27–29行、第47页50–53行、第48页12–18行；第35–38页）

**第五，real-GPU validation 解决了‘完全没有真实硬件证据’的问题，但还没到‘足以封顶’。** 附录 H.2 的校准做得不错：A100 80GB，MAPE 1.93%，\(R^2=0.9943\)，外加单类型和 real-data 的 end-to-end GPU runs。但这仍主要是：一，**simulator fidelity**；二，**WAIT 相对一个 SGLang baseline** 的实现验证。它不是对主文三方排序（WAIT / vLLM / Sarathi）的完整实卡复现，也不是多硬件、多负载形态的 robustness check。因此，“支持 simulator accuracy”是成立的，但若据此把主文的所有 comparative claims 一并抬到“真实硬件已充分验证”，就会过界。这个更适合列为 **P1**。（修订稿，第79页15–20行；第80页41–53行；第82页24–27行；第83页23–25行）

## 回复信是否准确，有没有“说得比做得多”

我的判断是：**回复信总体准确，没有明显虚报修改；真正的问题在于个别地方仍然“讲得比范围更宽”**。

先说准确的部分。回应信第一页列出的几项“most significant changes”——重构 objective 与 queueing interpretation、把内存约束改成 all resident KV caches、去掉 heavy traffic 叙述、补 A100/real-GPU、改成 arrival-rate curves——在修订稿里都能一一对上。比如，回应信说“now uses token-level effective throughput … and plots latency as a function of the arrival rate”，修订稿第14页、第31–38页确实已经这样写；回应信说“memory constraint applies to all in-system requests retained on the GPU”，修订稿第12页第41–56行和第21页第13–15行明确兑现；回应信说“removed the misleading ‘heavy traffic’ terminology”，修订稿正文里已把第4节改为“Asymptotic Guarantees”，相关 heavy-traffic 术语只剩参考文献；回应信说“added real-GPU validation”，修订稿附录 H.2 也确实存在。就“有没有把没做的事写成做了”而言，我没有看到严重问题。（回应信，第1页12–43行；修订稿，第12页41–56行、第22页5–26行、第31–38页、第79–83页）

但我会指出两个**轻度 overstatement / 口径不够窄**的地方。

第一，论文正文第24页写“this section removes that information assumption”，这比回应信本身更大胆。因为从实现和实验看，Nested WAIT 仍然依赖 workload distribution 与 offered arrival rate 的预先校准。换言之，**去掉的是“单个请求输出长度先验已知”的假设，不是去掉所有分布与负载信息假设**。回应信在第13页其实已经把这一点写得更准确；建议正文和摘要跟回应信对齐，而不是反过来。（回应信，第13页21–28行；修订稿，第24页11–15行、第37页7–34行）

第二，回应信把 real-GPU validation 说成“implementation validation as well as support for the simulator’s accuracy”。这句话并不假，但如果不加限定，容易让人误以为**主文的全部比较排名**都已被真实 GPU 复核。事实上，附录 H.2 更像 calibration + limited implementation check，而不是全文 comparative claims 的逐一硬件复现。这里我不认为回复信“失实”，但我认为它**仍带一点宣传腔**，最好在回复信和文中同步加一句限定：real-GPU evidence validates the timing model and one deployed scheduler implementation, not the entire tri-way benchmark ordering.（回应信，第1页26–36行；修订稿，第80页41–53行、第82–83页）

总之，**回复信比修订稿更谨慎、更像审稿口径；真正需要再收紧的是论文正文自身的几处表述**。

## 关键 claim 的 scope 审计

**Open-system throughput / stability-region 语言。** 这一项从“明显有问题”变成了“基本合格”。原稿确实把问题写得像固定 arrival vector 下追 throughput；修订稿现在正面写出“stable policy completes requests at that rate”并把实验转成 effective completion rate vs arrival rate，这是正确方向。我不认为这还会是最主要拒稿点。残余问题只是：摘要和个别段落里仍有“performance comparable to the fluid benchmark”“enlarge the empirically observed stable operating range”之类较强概括，最好继续统一成“effective completed service / empirically observed operating range under the tested calibration”。（原稿，第12页7–17行；修订稿，第14页5–10行、第31页4–11行、第1页22–33行）

**Latency 解释。** 原稿最大的问题是拿明显不稳定的系统画 latency vs prompt number；修订稿已经改成了 latency vs λ，并说明了 \(\lambda^\*\) 的 operational meaning，这一步很关键，属于真正对症下药。但修订稿自己也承认，超过该范围后 latency 只在“完成的请求”上计算，这让 overloaded 区域的 latency 更像补充运行指标，而不是标准排队性能指标。如果作者想保住 OPRE/MS 审稿人，建议把 overloaded 区的图例、caption、正文解释再压实一些，甚至把“overloaded latency”显式命名为 conditional-on-completion latency。此外，TTFT 仍然缺实验，这让 latency 线的经验支撑仍不完整。（决定信上传文本；回应信，第16–17页；修订稿，第31页4–11行、第33–38页图注）

**GPU memory / KV-cache / eviction semantics。** 这项修得最好。新的内存定义、resident set \(G_t\)、LIFO eviction、restart semantics、eviction cascade example，都让论文终于能回答“waiting jobs 算不算内存”“OOM 怎么发生”“为什么 throughput 会掉到 offered-load 以下”这些一轮中的硬问题。残余问题不在“是否说清”，而在“是否对 LIFO / no-swap 的特殊建模过于依赖”。从 AE 的措辞看，这类问题只要诚实交代适用边界，并不一定致命；但如果作者想更稳，可以加一小段 sensitivity discussion，说明更换 eviction policy 后哪些结论预计不变、哪些可能变化。（AE报告，第3页17–27行；修订稿，第12页41–56行、第13页4–29行、第14页24–29行）

**Simulator vs real-GPU validation。** 目前已经从“没有”变成“有，而且不弱”。A100 校准图和 SGLang end-to-end 跑法都能明显缓解“Vidur may no longer accurately capture real GPU behavior”的一轮担忧。但它仍不足以支撑所有 comparative claims 的硬件普适性；尤其是 H.2 的真实 GPU 比较对照的是一个 SGLang baseline，而不是主文里完整的 vLLM / Sarathi / WAIT 排位。因此，这一项我会表述为：**足以消除‘完全没有真实验证’这一 objection，但不足以完全代替主文模拟对比的外部有效性讨论。**（审稿报告1，第6页7–12行；修订稿，第80页41–53行、第82–83页）

**Known vs unknown output lengths。** 从理论写法看，Nested WAIT 的核心思想是合理的：个体输出长度 admission 时未知，只在 boundary 逐步揭示；这已经比原稿清晰得多。但从真正可部署角度看，实验版 Nested WAIT 仍需要 workload distribution 和 offered arrival rate 来设阈值、定 segment、做 per-rate grid selection。于是“unknown output lengths”这一 headline 必须补上限定语，否则会让审稿人误会成“不需要任何先验分布信息”。这件事在回应信里已经说对了，正文需要跟上。（修订稿，第24–25页；第37页7–34行；回应信，第13页21–28行）

**Proof coverage / theorem-proposition consistency。** 原稿的 proof summary 确实空泛；修订稿这方面好很多，主文开始能告诉读者 queue reduction 到底是什么，也把 Kingman/Lindley/Doob 等标准工具拉进了附录。形式上一致性现在明显强于原稿。真正残余的问题有两个：第一，定理里的 delay 主要是 **service-normalized delays**，而正文与实验展示的是 calendar-time latency，二者桥接虽有，但仍足够技术性，容易被非专门读者错读；第二，Nested WAIT 的主定理为了透明性使用共同 prefill length，而真实异构实验靠 Appendix A 的 extension 与 implementation heuristic 衔接。二者都不是“错误”，但都还需要更直白的 scope fence。（修订稿，第22页22–25行、第23页13–26行、第25页27–29行、第47页50–53行、第48页12–18行）

**Numerical experiment transparency。** 相较原稿，透明度已经显著提高：GPU 型号、KV-cap 计算、baseline config、调参网格、重复次数、近边界重跑，全都补了。这一项的最大残留问题不是“透明度不足”，而是“**透明之后暴露出比较框架并不完全对称**”——也就是前面说的 ours 做 per-rate best-grid，baselines 基本用默认值。作者现在至少没有藏着掖着，这很好；但下一步要做的是要么把基线也系统调参，要么把主结论的措辞降到与目前实验设计严格匹配。（修订稿，第31页13–32行、第32页25–37行、第37页27–34行、第83页29–44行）

## 文风与语言质量审计

这版英文比原稿好很多，结构也更像 OPRE/MS 的稿子了；但仍有几句会让严苛读者觉得“宣传化”“泛化得太快”或“像 AI 帮你润过但没有完全落到学术精确度”。

第一句，修订稿第5页第17–19行：**“memory is a resource to exploit rather than merely a constraint”**。这类句子在商学院/OR 顶刊里很容易显得像口号。更好的写法应直接落为：larger batches can improve utilization, but only if the induced resident KV-cache population remains feasible. 这样更可证、也更少宣传味。（修订稿，第5页12–19行）

第二句，修订稿第32页第35行：**“This pattern matches the paper’s mechanism.”** 这句太空。应该具体说“the gain here comes from threshold-based admission keeping the resident population near the balanced composition, not from type separation”，而不是笼统说 matches the mechanism。现在的写法像作者在替自己做 commentary，而不是在给审稿人可检验解释。（修订稿，第32页31–37行）

第三句，修订稿第37页第33–34行：**“The selected setting is therefore the best tradeoff on this grid for the workload and arrival rate.”** 这句话容易让人误读成“最优 tradeoff 已被找到”，但其实只是“在作者设定的 prespecified grid 上，按 latency 选出来的局部最好点”。建议改成 strictly local phrasing：best observed configuration on the prespecified grid。否则会被认为措辞过满。（修订稿，第37页27–34行）

第四句，修订稿第80页第52–53行：**“This agreement supports the use of Vidur for the latency and operating-range comparisons in Section 6.”** 本意没问题，但最好加限定语，比如 “in the profiled decode-centered regime studied here”。否则会被读成对广泛负载形态和所有结论的一次性背书。（修订稿，第80页47–53行）

第五句，修订稿第84页第17–18行：**“the same threshold rule continues to improve decode-side delay.”** 这句话应加上 tested setting 限定。因为这里是 PD-disaggregated、decode-only、特定 workload 的实验，不宜写得像一般性命题。（修订稿，第84页11–18行）

第六句，修订稿第24页第12–13行：**“This section removes that information assumption.”** 这是本稿里我最想删掉或重写的一句。更精确的说法应是：removes the assumption that each request’s final output length is known at admission, while retaining distributional information for threshold calibration. 这样才能和第37页的 distribution-aware implementation 自洽。（修订稿，第24页11–15行；第37页7–34行）

这些都不是“英文差”，而是**OPRE/MS 审稿会盯的那种 scope precision 问题**。改掉之后，整稿的可信度会再上一个台阶。

## 与原稿相比，这次修回是否“足够 substantial”

我认为答案是**是，明显 substantial**。

不是因为页数从 58 页涨到了 84 页，而是因为作者真正重写了论文的**问题定义、核心状态、实验逻辑和证明叙述方式**。最能说明问题的四个对照是：

原稿把内存约束写成“当前 batch 的 token 和不能超过 \(C\)”；修订稿则明确为“所有 GPU-resident KV caches 的总量不能超过 \(C\)”，并把 eviction/restart 写进模型。这不是 cosmetic edit，而是 reviewer criticism 直接改变了状态空间定义。（原稿，第11页41–48行；修订稿，第12页41–56行）

原稿把第2.4节写成“max throughput subject to latency and TTFT constraints”；修订稿改成“effective throughput + latency/TTFT + policy space + nonanticipation + eviction/preemption semantics”，并在第31页直接承认 stable policy 在外生 arrival 下 completion rate 就等于 arrival rate。这个改动触及的是 queueing interpretation 的根部。（原稿，第12页7–17行；修订稿，第13页32行至第14页30行、第31页4–11行）

原稿大张旗鼓写“heavy traffic”，并在正文只给抽象 proof summary；修订稿把 narrative 改成 asymptotic scaling，并在正文先解释 reduction object 再让读者去附录。这正是 AE 要的“professionalize the mathematical presentation”。（原稿，第2页24–26行、第6页20–23行、第17页39–42行、第19页13–19行；修订稿，第22页5–26行、第23页13–26行、第30页15–25行）

原稿实验图主要是 “Throughput vs Time Horizon”“Latency vs Prompt Number”，很容易被审稿人当成在 unstable region 上做不合适的对比；修订稿改为 arrival-rate sweep + effective completion rate，并加了 near-capacity/overload 解释、long-horizon check、repeated-run variability、A100/real-GPU appendix。这也是结构性重做，而非补图。（原稿，第26–30页图示；修订稿，第31–38页、第79–84页）

所以，如果你的第6个任务是问“相对 review team concerns，这轮是否 substantial enough？”我的答案是：**充分显示了 substantial revision；问题在于它仍未完全完成 closing argument**。换句话说：**足够 substantial 去支持继续送审，但未必足够 polished 去直接说服所有一轮审稿人。**

## 优先级清单

### P0：再投前必须修

**明确收紧 “unknown output lengths” 的 claim。**  
把摘要、第5节开头、结论等处的表述统一成：**个体输出长度 admission 时未知，但阈值校准使用 workload distribution 与 offered arrival rate（或其估计）**。不要再出现“removes that information assumption”这种容易被读成“完全无需先验”的表述。

**把实验调参公平性讲透，最好做对称化。**  
目前 proposed method 按 arrival rate 在 prespecified grid 上选最低延迟配置，而基线主要是默认配置。至少二选一：  
其一，对基线也提供同等级别的调参；  
其二，非常明确地把主结论降格为“rate-aware calibrated WAIT/Nested WAIT vs default baselines”，并在摘要/实验讨论中保持这个限定。  
这一点如果不补，下一轮非常容易被打。

**把 overload 区 latency 的口径写得更硬。**  
正文和图注里必须更醒目地说明：过载区 latency 是“对 run 中完成请求的条件均值”，不是标准 steady-state mean latency。最好把 near-capacity 与 overloaded 的解释再分开一层，并补一条更典型的 queueing summary（例如把 \(\lambda^\*\) 以下作为主要 latency 比较区间）。

**要么补 TTFT 实验，要么明显降低 TTFT 的经验性 claim。**  
现在 TTFT 在模型、目标、定理、结论里分量很重，但实验部分几乎没有 TTFT 结果。若不补，建议把摘要和结论里关于 TTFT 的语气收紧到“theoretical metric”而非“empirically established user-facing advantage”。

**把 theorem-facing latency wording 再收紧。**  
定理里是 service-normalized delay；实验里是 calendar-time latency。建议在摘要、结论、定理后解释段落里都把这个差别再说透，避免 reviewers 抓“latency guarantees”这个表述做文章。

### P1：强烈建议修

**加强 real-GPU 部分的 scope 标注。**  
目前 H.2 足以验证 timing model 和一种实现，但不足以替代全文三方排名的硬件复现。建议在正文中主动承认这一点，或者把一组更贴近主文 baseline 的真实 GPU 对比上提到正文/补充材料的更显眼位置。

**补一段 eviction policy / swapping semantics 的稳健性讨论。**  
现在 LIFO eviction + no-swap 是清楚的，但仍有模型特定性。建议补一句：主要结论靠的是 resident-population control 与 eviction-restart waste，不依赖 LIFO 的唯一性；若不是，请写明不依赖到什么程度。

**把 theorem-to-experiment bridge 画出来。**  
建议加一张 assumption map：  
主定理覆盖什么；Appendix A 扩展了什么；Section 6 实验用了哪些 implementation heuristic。  
尤其是 heterogeneous prefill、coarse segmentation、per-rate calibration 三者与 Theorem 2/4 的关系，应一页内说清。

**再做一次“删宣传语、补限定语”的语言清洗。**  
重点处理上面列出的几句，并系统搜一遍 “best tradeoff”“supports the use of”“continues to improve”“removes that assumption” 这一类句式。

### P2：可选润色

**把最关键的实验设定做成一个统一 summary table。**  
现在信息是全了，但散在第31–37页与附录 H。做成总表会更符合 OPRE/MS 读者习惯。

**把 \(\lambda^\*\) 的 operational definition 在图注里再标准化一次。**  
现在正文有解释，图注若同步说明，会更自洽。

**把正文里少量“paper’s mechanism / natural state variable / resource to exploit”这类抽象句替换成可验证的机制句。**  
这主要是风格加分项，但也能减少“AI-written”观感。

## 审计边界

我本次审计只基于你上传的材料本身。需要说明的是：决定信 markdown 本地抽取文本对嵌入的长篇 Referee 3 评论存在截断，因此与 Referee 3 相关的判断，我主要综合了**决定信中可见内容**、**回应信 D.1–D.6 的逐条回应**，以及**修订稿对应修改处**来判断。这个边界不影响我对“是否 substantial、是否仍有高风险点”的总体结论，但会让个别 Referee 3 语句无法像 PDF 那样精确给出页行号。