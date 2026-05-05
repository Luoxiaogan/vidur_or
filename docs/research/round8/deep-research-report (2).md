# 学术稿件大修评估报告

## 执行摘要

总体判断：**该稿已显著优于原稿，但我不建议按现稿直接重投；建议在完成少量但关键的再修订后重投。** 原轮“高风险 major revision”的三大核心问题——写作/结构、队列论 framing、实验设计——此次都被**实质性回应**；尤其是作者已把问题从“固定到达率下提高吞吐”改写为“在外生到达下扩大可稳定运行区间并减少 evictions”，并补上了按到达率绘制的延迟/完成率曲线（决定信 l.64–68, 75–81；回复信 p.15, l.19–26；修订稿 §2.4, p.14, 首段 l.5–15；§6, p.32, 首段 l.4–10）。

但仍有三点会继续触发下一轮风险：**模型现实性边界仍偏弱**（未建模 GPU↔CPU/SSD swap-in/out 延迟）、**理论贡献表述仍略满**（对 OR 水平的“新意”仍可能被质疑）、以及**实证优势部分依赖按负载离线调参**（实稿应更明确披露）。因此，我的结论是：**“接近可重投，但须先做一次定向中修”**。若作者按下文高优先级编辑完成修订，我认为稿件即可进入可重投状态；若不修，下一轮仍可能停留在 **major revision** 档位。

## 逐项回复评估

| 原始关切 | 回复信中的直接回应 | 修订稿对应位置 | 评估 | 评语 |
|---|---|---|---|---|
| 写作、符号、结构混乱；缺乏直观解释（AE报告 p.1, l.25–31；审稿人2 p.2, l.8–24） | 作者称已“**Section 2 now introduces notation…**”且“**Added a notation summary**”（回复信 p.3, l.3–7, 10–15） | Appendix B“Notation Summary”（p.54, l.4–20）；§2.4 明确定义 policy class（p.14, 次段 l.22–33） | **完全解决** | 结构、术语和可读性均明显改善；这项是本次修订中最成功的一点。 |
| policy space Π 与批处理操作未清楚定义（审稿人2 p.2, l.10–16） | “**Revised Section 2.4 to define the objective, the policy class**”（回复信 p.7, l.13–16） | §2.4, p.14, 次段 l.22–33 | **完全解决** | 现在读者能在算法前理解 π/Π，而不是事后回推。 |
| 算法与定义后缺乏 intuition（审稿人2 p.2, l.17–24） | “**Section 4 begins with a concrete FCFS failure example** … Section 5 begins with an unknown-output-length example”（回复信 p.7, l.19–23） | §2–§5 均增添机制解释；特别是 WAIT/Nested WAIT 的解释段（如 p.24, 首段 l.4–10） | **基本解决** | 主文已有更强机制叙述；不过 proof-level intuition 仍可再压缩成一张示意图。 |
| “heavy traffic”用词错误（决定信 l.64–65, 75；审稿人1 p.4, l.12–14） | “**removed the misleading ‘heavy traffic’ terminology**”（回复信 p.11, l.24–29；p.15, l.7–12） | 修订稿正文已基本不再以 heavy traffic 定位；改写为 asymptotic/fixed-load framing（§4–§5） | **完全解决** | 这一点作者接受得很彻底。 |
| 外生到达下 throughput 的 framing 不对，应转向 stability region（决定信 l.64, 79） | “**a stable system cannot complete more useful work than the offered load**”（回复信 p.15, l.19–26） | §2.4 改为 effective throughput/stability framing（p.14, 首段 l.5–15）；§3 明确 fluid stability region（p.15, 首段 l.12–21） | **完全解决** | 这是本次最关键的概念性修正；现在理论与实验语义基本对齐。 |
| 原实验在不稳定区比较 latency，意义弱（决定信 l.81；审稿人3同段） | “**main figures now plot mean end-to-end latency versus arrival rate**”（回复信 p.17, l.7–14） | §6 开头明确按 arrival-rate 曲线呈现 latency 与 effective completion rate（p.32, 首段 l.4–10） | **完全解决** | 这直接回应了最负面审稿人的核心批评。 |
| memory constraint 似乎只作用于当前 batch；OOM / eviction 机制不清，preemption 现实性不足（决定信 l.88；审稿人2 p.1, l.16–25；AE报告 p.1, l.33–39） | “**admitted requests that remain active keep their KV caches on the GPU**”（回复信 p.3, l.29–31）；“**memory constraint applies to all in-system KV caches**”（p.3, l.34–35） | §2.3 明确“**not only current batch … but all prompts whose KV caches are resident**”（p.12, l.33–45）；但 §2.4 又写“**We do not model CPU or SSD swap-out with a separate swap-in latency**”（p.14, l.28–31） | **部分解决** | 核心数学对象已澄清；但现实系统中的 swap/transfer 代价仍被抽象掉，这一点下一轮仍可能被追问。 |
| Eq.(1) 线性时间模型范围不清，需解释适用 regime 并做真实 GPU 验证（AE报告 p.1, l.34–37；审稿人1 p.2, l.6–21；审稿人2 p.1, l.26–32） | “**heterogeneous-prefill regimes may require richer calibrated service-time curves**”（回复信 p.3, l.21–25）；并称补了“A100”与“SGLang”验证（p.3, l.26–28；p.14, l.3–13） | §2.2 现明确本文针对 KV-cache-driven regime，并承认非线性/分段线性替代模型（p.11, l.13–18, 31–42）；Appendix H.2 给出 A100 校准，\(R^2=0.9943\), MAPE=1.93%（p.84, l.15–23） | **部分解决** | 说明与验证都更好，但理论仍只覆盖线性模型；GPU 验证主要在附录，主文证据仍以模拟为主。 |
| 理论贡献可能只是 standard positive recurrence / pipeline filling 的再包装（AE报告 p.2, l.7–13, 29–35；决定信 l.77, 86） | “**The difficult step is not that a stable queue has finite delays** …” （回复信 p.16, l.12–27）；“**modeling and algorithm-design contribution**”（p.4, l.10–16） | §4.3 新增 theorem-interpretation，把关键点落在 threshold-induced dimensionality reduction 与 coupling 上（p.24, l.4–10）；结论也加了“**Under the linear multi-stage model…**”（p.40, l.14–17） | **部分解决** | 论文现在更诚实地把贡献定位为“建模+结构化控制”；但是否足以达到 OR 的 novelty bar，仍是下一轮最大不确定性之一。 |
| proof 组织、decode-stage 动力学、以及“不等待会怎样”需要更清楚（审稿人1 p.3, l.34–36；p.4, l.1–14） | 作者称已“**define the batch index separately from the stage index**”（回复信 p.10, l.15–16），并补了“**Threshold without waiting**”（p.11, l.11–17） | 主文对 coupling 逻辑更清楚（p.24, l.4–10）；Appendix H.1 现有 WAIT-no-wait 对比（p.82, l.19–29） | **部分解决** | 技术上已补；但 proof 仍较依赖附录验证，主文若再加一张两型两阶段示意图会更稳。 |
| 参数、基线配置、长输出、真实 GPU、\(C\ge M^*\) 的经验可行性（审稿人1 p.3, l.25–33；p.6, l.3–25） | “**Added long-decode experiments**”（回复信 p.10, l.7–9）；“**Added both forms of validation**”（p.14, l.3–13）；“**real-data \(M^*(\lambda)\) versus \(C\) table**”（p.10, l.6–8） | §6 现给出 A100 80GB、KV-cache cap 与 eviction rule（p.32, l.12–17）；长输出 p512d1000 与重启率表（p.35, l.51–75）；真实数据 \(M^*(\lambda)=C\) 交叉点约 74.1 q/s（p.38, l.42–46） | **基本解决** | 实验透明度已足够支撑重投；不过 \(C\ge M^*\) 的“理论—物理可行性缝隙”仍最好再用一两句更显眼地说明。 |

**补充说明：** 纯 typo / 记号更正项（如 d 与 d1、Throughput 拼写、附录未定义符号）在回复信中逐项承认并已大体修正（回复信 p.8, l.1–4；p.12, l.1–12）。

## 剩余技术、证明、建模、表述与实验风险

| 风险 | 对有效性的潜在影响 | 严重性 | 依据 |
|---|---|---|---|
| **resident-on-GPU preemption 假设仍偏理想化** | 若真实部署依赖 CPU/SSD swap，则延迟与 eviction 代价可能被系统性低估，WAIT 的优势可能被削弱 | **高** | 修订稿显式承认“不建模 swap-in latency”（§2.4, p.14, l.28–31） |
| **线性 iteration-time 模型覆盖面有限** | 结论对 compute-bound、长 prefill、硬件饱和区的外推仍不稳健 | **中高** | 修订稿已承认“mixed prefill-decode batches and hardware saturation can create distinct regimes”（§2.2, p.11, l.31–42），说明风险真实存在 |
| **理论新意在 OR 审稿标准下仍可能被视为“结构化已知工具”** | 即便技术无误，也可能因“贡献定位”而遭保守评价 | **中高** | 回复信与修订稿都把核心卖点转向“dimensionality reduction / boundary queues”（回复信 p.16, l.12–27；修订稿 p.24, l.4–10），这实际上也暴露了其 novelty 边界 |
| **实证改进部分依赖 rate-aware / per-load calibration** | 若读者把结果理解成“单一默认参数即可普遍优于基线”，会高估方法即插即用性 | **中** | 修订稿明写“choose the lowest-latency configuration … for each offered arrival rate”（§6.2, p.38, l.35–41） |
| **proof 仍偏附录驱动** | 新审稿人或时间紧的原审稿人，仍可能难以快速确认 theorem 到机制的映射关系 | **中** | 虽已改善，但关键看点仍主要在附录与 theorem-interpretation 段之间跳转（修订稿 p.24, l.4–10；App. H, p.82） |

## 过度主张与不一致

未见**硬性矛盾**（即“回复信承诺了但稿件没有”的明显失配）；主要问题是**高层 framing 仍比正文证据略强**。

| 项目 | 证据 | 影响评估 |
|---|---|---|
| **摘要对经验优势表述偏满** | 摘要称“**Both algorithms achieve asymptotic performance comparable to the fluid benchmark**”且在 A100 上“**enlarge the empirically observed stable operating range**”（修订稿 p.1, l.35–42）；但真实数据实验又采用“**for each offered arrival rate**”的网格选优（p.38, l.35–41） | **中**。这不是错误，但应更明确写成“under rate-aware calibration / under the tested configurations”。 |
| **“real-GPU validation”在高层位置略显过强** | 回复信其实很谨慎，明说“**The main policy comparisons remain Vidur simulations**”（回复信 p.1, l.28–30；p.14, l.11–13）；而摘要/结论容易让人读成“主证据已是 GPU 结果”（修订稿 p.1, l.38–42；p.40, l.21–24） | **低中**。建议把 real-GPU 统一表述为“supplemental corroboration”，避免引发证据层级误读。 |

## 重投前必须修改

| 优先级 | 位置 | 必改内容 | 建议文字/图表修改 |
|---|---|---|---|
| **高** | 摘要 p.1, l.35–42；结论 p.40, l.14–24 | **弱化外推性表述**，把理论与实验都显式绑定到模型范围与测试配置 | 将摘要相关句改为：**“Under the linear KV-cache-driven service-time model and the stated memory conditions, WAIT and Nested WAIT asymptotically track the fluid benchmark. In rate-aware calibrated experiments on Vidur configured for Llama-2-7B/A100, with supplemental A100/SGLang validation, they improve the observed stable operating range relative to the tested baselines.”** |
| **高** | §6.2, p.38, l.35–41；§6 开头 p.33, l.8–12 | **把 per-\(\lambda\) 离线调参写成主文限制，而非藏在实验细节里** | 在 §6.2 首段加一句：**“Unless otherwise stated, \(t_l\) and \(L\) are selected offline from a prespecified grid separately for each offered arrival rate \(\lambda\); the reported curves therefore represent best calibrated performance at each load, not one-size-fits-all robustness.”** 并最好补一张“固定参数 across \(\lambda\)”鲁棒性图。 |
| **高** | §2.4, p.14, l.28–33；结论限制段 p.40, l.25–31 | **更明确圈定 memory realism 边界** | 在模型假设末尾补一句：**“Our preemption model is GPU-resident pause/resume; we do not model CPU/SSD swap-out or swap-in latency. Hence the theory best matches resident-serving or decode-disaggregated settings rather than general offloading systems.”** |
| **中** | §4.3–§5.2，尤其 p.24, l.4–10 | **再加一个 proof roadmap 图/示意例**，把“event-driven process → embedded review process → boundary/threshold queues”画出来 | 建议新增一张 2-type/2-segment 小图，图注明确“one-interval lag”与“stage advancement”如何进入 coupling。 |
| **中** | §6 与 Appendix H.2，尤其 p.32, l.12–18；p.84, l.15–23 | **把真实 GPU 校准摘要前移到主文** | 在 §2.2 或 §6 首段末补一句：**“Appendix H.2 reports A100 calibration with \(R^2=0.9943\) and MAPE \(=1.93\%\) on the profiled grid.”** 这样能在首轮阅读时立即解除“全靠模拟”的疑虑。 |
| **中** | Table 2 前后，p.38, l.42–46；长输出讨论 p.35, l.55–63 | **把 \(M^*(\lambda)\) 与长输出实验的物理可行性联系得更明确** | 在 Table 2 后补一句：**“This crossing helps explain why the long-decode workload loses stability at much lower arrival rates and why admission control matters earlier in p512d1000 than in p512d20.”** |

## AE 决策检查清单

| 选项 | 建议 | 理由 |
|---|---|---|
| 接收 | **否** | 模型边界、主张强度、实验披露仍需收口。 |
| 小修 | **否** | 剩余问题不只是措辞；至少涉及 framing、限制说明与实验公平性。 |
| 大修 | **是，且最贴切** | 论文已具备可救性，核心反驳基本成立，但需要一次**定向中修**后再重投。 |
| 拒稿 | **否（当前不建议）** | 与原稿相比已有实质跃升；问题主要是“再收口”，不是“推倒重来”。 |

**推荐的审稿动作：** 若作者按上表完成高优先级修改，建议**回原审稿人**，尤其请最负面的原审稿人重点复核三件事：  
一是 stability-region / latency framing 现在是否已站住；二是模型边界（all-resident KV、无 swap-in latency）是否被充分诚实披露；三是 per-load calibration 是否已在摘要、主文和结论中被准确限定。若作者不愿显著弱化摘要/结论措辞，或不愿补固定参数鲁棒性说明，我会建议**不要按现稿重投**。