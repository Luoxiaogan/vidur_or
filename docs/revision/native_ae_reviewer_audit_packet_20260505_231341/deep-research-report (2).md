# 对修回稿的编辑与审稿综合意见

## 总体评估

这次修回**明显不是表面润色**。与首轮决定信、AE 报告和审稿意见相比，作者确实做了三类实质性修正：其一，把问题从“固定外生到达下的吞吐优化”改写为“在外生到达下维持更大的可持续负载/稳定区，并把重启损失计入有效吞吐”；其二，把 GPU 端 KV-cache 约束改写为**覆盖所有保留在 GPU 上的在系统请求**，并明确了 eviction 与 restart 语义；其三，去掉了误导性的 heavy-traffic 表述，补加了 A100/SGLang 补充验证，并把实验从“时间横轴”改成了“到达率横轴”。这些修正正面回应了首轮最核心的批评。fileciteturn0file2L4-L6 fileciteturn0file7L76-L120 fileciteturn0file4L13-L44

我目前的判断是：**首轮那些“会导致拒稿/重投风险”的大问题，大多已被压缩为少数几处仍然重要但可手术式修补的遗留问题**。尤其是表述、记号、policy space、Equation (1) 的适用范围、以及 GPU KV-cache/OOM 语义，已经达到“可以继续认真评估贡献”的程度，而不再是“因为写法和建模不清而无法判定”的状态。fileciteturn0file6L22-L35 fileciteturn0file6L62-L75 fileciteturn0file5L49-L62 fileciteturn0file0L394-L427 fileciteturn0file0L486-L500 fileciteturn0file0L532-L552

## 已基本解决的原始关切

从“是否回应了首轮核心质疑”的角度看，我认为以下方面已经**基本过关**。对 exposition 和 notation 的大修是可信的：Section 2 现在把目标函数、policy class、有效吞吐、Latency 与 TTFT 放在一起，叙述顺序也更符合 OR 读者的阅读逻辑。对 open system 的 framing 也已经纠正：文中明确承认，在稳定区内完成率受 offered load 上界约束，真正要比较的是谁能在更大到达率区间内维持可持续服务并减少 eviction/restart 浪费。对 GPU memory mechanism 的修正也到位：保留在 GPU 上但未入当前 batch 的请求，其 KV-cache 仍计入约束；若超出容量，采用 last-in-first-out eviction，并从 prefill 重启。Equation (1) 的线性时间模型，也不再被说成普适物理定律，而是被限定为 KV-cache-driven regime 的一阶近似，并补了 A100 标定。fileciteturn0file4L13-L23 fileciteturn0file4L31-L44 fileciteturn0file0L399-L427 fileciteturn0file0L493-L499 fileciteturn0file0L534-L550

理论定位方面，论文也比原稿诚实得多。作者在 response letter 中不再把工作包装成新的 heavy-traffic theorem，而是把新意放在**LLM inference 这个 memory-coupled、multi-stage、partial-information 调度问题的建模与阈值化降维**上；正文对应地把 fluid benchmark 与稳定域/内存需求联系起来，并把 WAIT/Nested WAIT 的证明思路写成 threshold queue / boundary queue 的降维机制。这至少解决了“理论到底新在哪里”的表述性误导。就“proof clarity 是否仍是决定性阻碍”而言，我现在的答案是：**不再是**。fileciteturn0file7L114-L120 fileciteturn0file4L45-L58 fileciteturn0file4L845-L852

## 仍会影响决定的事项

### TTFT 证据仍然缺位

**位置：** TTFT 在正文开头和目标函数中仍被列为三大核心服务指标之一，且作者明确声称后文会给出 throughput、latency、TTFT 的保证；但 Section 6 的主图与 Appendix H 的 GPU 图，展示的仍然只有 mean end-to-end latency 与 effective completion rate，没有任何 TTFT 曲线、表格或摘要统计。fileciteturn0file0L79-L81 fileciteturn0file0L545-L550 fileciteturn0file0L1347-L1354 fileciteturn0file0L1727-L1735 fileciteturn0file0L4190-L4195

**为什么重要：** 首轮决定信已经明确指出，“latency 被明显忽视，throughput 不是唯一目标”；而修回稿自己又把 TTFT 继续保留为 headline metric。现在的修订确实补上了 latency-vs-arrival-rate，但仍然没有把“首 token 延迟”这一最贴近交互式 LLM 体验的指标落到实证层面。对于一个同时把 latency 和 TTFT 写进模型、算法目标和理论结论的稿件，这个空缺仍足以影响决定。fileciteturn0file2L4-L6 fileciteturn0file0L545-L550

**最小修改：** 不需要重做整套实验。只要在**同一到达率网格**上，为单类型、两类型/真实数据 workload，各补一组 mean TTFT（最好再加 p95 TTFT）曲线；GPU appendix 至少补一个 TTFT 图或表即可。若篇幅紧张，可把 TTFT 放入 appendix，但正文必须至少给出一句总结性结论并指向图表。

### 实证优势仍带有按负载逐点调参的色彩，公平性与鲁棒性还未完全钉牢

**位置：** 文中明确说明：baseline 使用默认 Vidur 配置；而 WAIT/Nested WAIT 的主要控制量是 system-wide batch-size cap `tl`，真实数据实验中还同时在 `L ∈ {1,2,3,4,5,10,20}` 与 `tl ∈ {20,40,…,200}` 的网格上，**对每一个 offered arrival rate 选取最低延迟配置**。response letter 也把这点表述为“rate-aware calibration”。fileciteturn0file0L1364-L1375 fileciteturn0file0L1689-L1702 fileciteturn0file4L696-L701

**为什么重要：** 这当然不是不允许的，但它改变了读者应如何理解 Figure 12/19 这类结果。按现在写法，读者很容易把曲线理解成“同一个 Nested WAIT policy across λ 的优越性”；实际上，更准确的描述是“**每个 λ 上经离线搜索后得到的、load-aware tuned Nested WAIT** 相对于默认配置 baseline 的优越性”。这会影响经验性结论的强弱，也会影响对算法本身与调参贡献各占多少的判断。首轮审稿人已经特别关心参数、capacity、baseline 配置与可复现性；这一点若不再说清，会继续削弱实验说服力。fileciteturn0file5L300-L315 fileciteturn0file4L705-L708

**最小修改：** 只需两步。第一，把正文与 response letter 中相关表述明确改成“**rate-aware offline-tuned**”或“**ex ante load-aware calibrated**”。第二，补一张**固定参数**或**held-out tuning** 的鲁棒性图：例如在真实数据上固定一个 `tl, L` 组合跑完整个 λ-grid，或先用部分 λ 调参，再在剩余 λ 上报告结果。这样就足以把“算法效果”与“逐点调参效果”分开。

### 补充的真实 GPU 验证有价值，但覆盖面仍不足以支撑最强的经验性论断

**位置：** response letter 把新增 appendix 描述为对 WAIT 和 Nested WAIT scheduling logic 的 real-GPU implementation evidence；正文也说 Appendix H 提供 A100 实测校准并报告 real-GPU runs。不过，真实数据的主实验把 λ 从 10 到 150 扫描，并把 Nested WAIT 的优势主要放在 near-overloaded / overloaded 区间来解释；而 real-data GPU appendix 只在 `λ ∈ {0.1,0.2,…,0.7}` 上报告 absolute mean latency，且没有 completion-rate / restart 证据。fileciteturn0file4L31-L37 fileciteturn0file0L1334-L1337 fileciteturn0file0L1727-L1735 fileciteturn0file0L4149-L4152 fileciteturn0file0L4190-L4195

**为什么重要：** 这意味着 Appendix H 目前更像是**implementation sanity check**，而不是对“真实数据、近容量区、稳定域边界附近”主结论的直接实机验证。A100 timing calibration 本身做得不错，我认为它已经足以支持 Equation (1) 的局部近似；但仍不足以支持“真实 GPU 上也能在关键负载区间体现同样稳定域/延迟优势”的更强陈述。这里还牵涉到 response-letter accuracy：现在的写法略有“说得比证据宽”的问题。fileciteturn0file5L305-L310 fileciteturn0file0L4132-L4148

**最小修改：** 二选一即可。要么**收敛表述**：在正文和 response letter 中把 GPU appendix 明确改写成“timing calibration + implementation sanity check”，不要把它表述成对主实证结论的全面实机验证；要么**补一个更靠近边界的 GPU stress case**，哪怕只是单一 workload 下的一张 completion-rate / restart table，也足以把这块补齐。

### 稳定域 framing 已经改正，但“理论边界—实验边界”的对应只在真实数据上完成了一半

**位置：** response letter 把本轮修回的核心之一描述为“use the fluid model to identify the stability region and the memory required to sustain it”；正文 Section 6 也定义了经验性的 `λ*`，把它解释为从 near-overloaded 到 overloaded 的转折点。论文随后为真实数据增加了 `M*(λ)` 与 `C` 的对照表，并据此把 fluid crossing 点放在约 74.1 qps；但这种“理论边界—实验边界”的并置，目前只出现在 real-data 一节，Section 6.1 的三组 synthetic workloads 并没有给出相应的 `M*(λ)/C` 或 fluid boundary 标记。fileciteturn0file4L20-L23 fileciteturn0file0L1350-L1354 fileciteturn0file0L1704-L1716 fileciteturn0file0L1404-L1405

**为什么重要：** 这不是纯展示问题，而是与首轮最关键的 conceptual correction 直接相关。既然论文现在的核心论点已经从“固定到达率下的吞吐提升”转成“在外生到达下谁能维持更大的可持续负载区间”，那么 synthetic 实验也应该像 real-data 实验那样，把经验性的拐点与 fluid/memory 条件并排给出来。否则读者仍然难以判断这些 synthetic 边界反映的是理论机制、调参机制，还是 simulator-specific artifact。fileciteturn0file2L6-L6 fileciteturn0file4L13-L23

**最小修改：** 在 Section 6.1 增加一个**很短的汇总表**即可：对 p512d20、两类型 workload 和 p512d1000，列出一两个代表性 λ、对应的 `M*(λ)/C`（或 fluid-predicted boundary），并在正文一句话说明与图中观测到的 `λ*` 是否一致。无需新增理论，只需把现有 framing 做完整。

## 最终裁量

我的最终判断是：**这篇修回稿已经明显越过了“写作/建模不清，因而无法可靠评估”的门槛，但还没有完全到“可直接接收”的状态**。从 AE 视角，我不会再把它看成首轮那种高风险的 reject-and-resubmit 案件；从审稿人视角，我认为它现在更像是一次**聚焦型、可完成的再修**。若作者把上面四点补齐，尤其是：

- 补出 TTFT 的实证证据；
- 明确并约束“按负载逐点调参”的解释；
- 让真实 GPU 验证的表述与证据范围严格一致；
- 把 synthetic 实验也与 fluid/stability boundary 对齐；

那么我会倾向于给出**接收或接收前最后一轮轻度修订**。反之，若现稿保持不变，我仍会犹豫，因为目前的经验性主张——尤其是关于 TTFT、真实 GPU 外推、以及真实数据上的稳态/稳定域优势——仍然比现有证据略强了一步。fileciteturn0file2L4-L6 fileciteturn0file7L76-L120 fileciteturn0file4L13-L44