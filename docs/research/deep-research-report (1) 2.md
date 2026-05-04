# 修回包最终审计报告

## 执行结论

**Executive verdict：`needs targeted revision`。**  
我的总体判断是：这版修订稿已经**实质性回应了**AE、两位审稿人和决定信中的绝大多数核心问题，尤其是在**开放系统吞吐量表述、驻留内存语义、Section 2重写、延迟—到达率实验、附录证明组织、以及将论文重新定位为流体近似引导的OR/MS调度论文**这几个方面，进步明显；但在正式重投前，仍有几处**高可避免、但足以刺激怀疑型审稿人**的残余风险，主要集中在**摘要/结论的claims边界、真实GPU验证表述、附录中个别正式定理的证明显式性、以及回应信若干措辞的对齐与收敛**。这些问题都属于**定点文字修订**，**不需要新增实验**。 （AE报告，pp. 1–3；决定信，p. 1；修订稿，pp. 1, 13–18, 30–39, 52–83；回应信，pp. 1–18；内部清单，pp. 1–2）

对用户提出的八个主问题，简答如下。  
修订稿**大体上直接回应了**AE/审稿/决定信关切；回应信**基本准确**描述了修改内容，但在少数地方**略有“写得比做得更满”**的倾向；理论部分与主文命题/定理的**主体覆盖是对齐的**，尤其主文中的 Proposition 1–5 与 Theorem 1–2 都能在附录 C–E 找到对应证明；数值实验的透明度已达到“可审可复核”的水平，尤其模拟/真实GPU范围、memory cap、replications、long-decode和real-data tuning 都说清楚了；论文现在**明显更像一篇OR/MS论文**而不是纯系统论文；但仍有一些**claim-scope与语言洁净度**问题应在重投前收口。 （AE报告，pp. 1–3；审稿意见1，pp. 1–6；审稿意见2，pp. 1–2；修订稿，pp. 13–14, 17–18, 22–30, 30–38, 52–70, 77–83；回应信，pp. 1–18）

## 最高剩余风险

| 严重性 | 位置 | 风险 | 为什么重要 | 具体修复 |
|---|---|---|---|---|
| 高 | 修订稿摘要 p. 1 | **真实GPU验证表述仍偏强**：现在的句子结构容易让人读成“主比较结论都被真实A100验证了”，但实际主比较仍是Vidur仿真配置A100，真实GPU更多是**timing model/implementation behavior 的补充验证**。 | 这是AE和负面审稿人都最敏感的“scope honesty”问题之一；一句摘要过满，足以让审稿人怀疑数值证据边界。 | 把摘要最后一句改成“**Vidur simulations configured for Llama-2-7B on an A100 GPU, supplemented by physical-A100 validation of the timing model and implementation behavior, indicate that...**”。（修订稿，p. 1；修订稿附录H.2，pp. 78–81） |
| 高 | Appendix A.2, Theorem 4，pp. 48–49 | **Theorem 4 是正式定理，但没有独立、可核验的证明段落，只写了“proof follows the structure of Theorem 2”**。 | 你们这轮最敏感的审稿痛点之一就是“proofs easier to verify”；主文核心命题都补齐了，但**正式 theorem without a real proof** 仍是可被挑刺点。 | 最好补一个**2–4段 proof sketch**：明确“如何由 Theorem 2 的 binomial thinning + segment aggregation 得到(17)式与 O(1) delay”。若不想展开，则可降成 **Corollary/Extension result**。 （AE报告，pp. 2–3；修订稿，pp. 48–49, 64–70；回应信，pp. 10–12） |
| 中高 | 摘要 p. 1；结论 pp. 38–39 | **Nested WAIT 的 safety buffer / overflow-prevention 用语仍可再条件化**。现在虽提到 finite-horizon/logarithmic buffer，但读起来仍接近“能防止overflow/eviction”的无条件口吻。 | 负面审稿人会盯“模型假设 + 保证范围”；这里最好明确是**在定理2的条件下、以 high probability 控制 overflow**。 | 改成“**with a finite-horizon logarithmic safety buffer that yields high-probability no-overflow feasibility under the stated conditions**”。结论同步缩口。 （修订稿，pp. 1, 29–30, 38–39） |
| 中 | 修订稿 Section 6.2, pp. 36–38；Figure 12 | **real-data Nested WAIT 是按到达率做 prespecified grid calibration 的 rate-aware implementation，但正文仍容易让人一眼读成“一个固定参数算法曲线”**。 | 这不是方法错误，而是**presentation risk**；若不显式提醒，审稿人会把它当作“per-rate oracle tuning”。 | 在 Figure 12 caption 或 section首段加一句：**“Each plotted Nested WAIT point uses the best configuration from a prespecified grid for that offered rate; this is a rate-aware calibrated implementation, not a single fixed parameterization.”** （修订稿，pp. 37–38；回应信，pp. 12–13） |
| 中 | 回应信通篇，尤其 pp. 1–4, 14–18 | **回应信整体专业，但仍略显模板化、铺陈过长**；少数地方写得比论文本身更“满”。 | 在 risky major revision 场景下，回应信最好的状态是**克制、精准、少抒情、多定位**。 | 压缩开头 bullets；减少 “This suggestion led us…”/“This point is central…” 类重复句式；把 proof-organization 与 GPU-validation 的 scope 说得更窄更准。 （决定信，p. 1；回应信，pp. 1–18） |

## 审稿意见映射表

| 来源 | 核心关切 | 回应信覆盖 | 论文覆盖 | 审计判断 |
|---|---|---|---|---|
| AE | **需要 complete expositional overhaul；Section 2/附录难核验** | 回应信专门有 Area Editor 段，逐项写了重写 Section 2、加入算法前示例、重组附录证明。 （回应信，pp. 2–4） | Section 2 现在完整定义 prompt/prefill/decode/batching/memory/objective/policy space；附录 C–F 按命题/定理组织，主文 theorem 后也有解释段。 （修订稿，pp. 8–14, 22–30, 52–71） | **基本解决。** 这是这次修回做得最成功的部分。 |
| AE | **证明主文解释过于空泛，附录像“deposit boxes”** | 回应信说明加入 proof-roadmap，并显式转向 Lindley/Kingman/Doob 等标准工具。 （回应信，pp. 2–4, 10–12） | Appendix D/E/F 开头都先给 proof architecture；Theorem 1/2 主文紧跟解释段。 （修订稿，pp. 22–30, 56–70） | **大体解决。** 但 Appendix A 的 Theorem 4 仍偏“只给结论”。 |
| AE + 审稿1/2 | **Equation (1) 的 affine timing model 需要更明确 scope/justification** | 回应信明确说模型是 decode-dominant，并补了 A100 profiling + simulator-vs-GPU validation + PD discussion。 （回应信，pp. 2–3, 8–9） | 主文 p. 10–12 明确把 Eq. (1) 置于 decode-centered regime；Figure 3 给 A100验证；附录 H.2 给 Vidur vs A100 calibration；H.4 讨论 PD deployment。 （修订稿，pp. 10–12, 30–31, 78–83） | **基本解决。** 但摘要仍应更谨慎地区分 simulation 和 physical-GPU support。 |
| 审稿2 + 审稿3 | **memory model 是否只约束当前batch；preempted/waiting jobs 的 KV 是否算GPU resident** | 回应信 D.6 和 R1.1 说清楚 memory applies to all retained GPU-resident KV caches。 （回应信，pp. 5, 17） | Section 2.3 与 2.4 明确定义 \(G_t\) 包括 current batch 之外的 resident prompts；算法1/2也明确“outside the batch waiting with KV caches retained”。 （修订稿，pp. 12–14, 21, 27, 29–30） | **明确解决。** 这是审稿中最关键的模型歧义之一。 |
| 决定信 + 审稿3 | **open-system throughput issue：稳定系统的 useful work 不会超过 offered load；应看 stability region 与 latency divergence** | 回应信 D.2/D.4 直接重构了目标函数和数值章节。 （回应信，pp. 14–16） | Section 2.4 把 effective throughput 定义为 completed decode-token service net of evictions；Section 3 把 \(M^*\) 定位为 fluid equilibrium memory requirement；Section 6 改成 latency-vs-arrival-rate + effective completion rate。 （修订稿，pp. 13–18, 30–38） | **解决得很好。** 这是本轮修回的核心成功点。 |
| 审稿3 | **heavy traffic 用词错误；其实是 fixed-load / long-horizon scaling** | 回应信 D.1 直接承认并改口。 （回应信，pp. 14–15） | 修订稿正文已不再把结果称作 heavy-traffic；只在参考文献中出现。 （修订稿，pp. 22–30；全文检索） | **已解决。** |
| 审稿3 + AE | **理论新意不能只是“positive recurrence”/routine batching；要说明真正困难在哪里** | 回应信 D.3/D.5 强调高维 memory-coupled control、boundary queues、dimensionality reduction。 （回应信，pp. 15–17） | Section 4.2、5.2 和 Appendix D/E 现在明确说 WAIT/Nested WAIT 先制造 tractable threshold/boundary queues，再谈稳定性。 （修订稿，pp. 20–23, 28–30, 56–70） | **大体解决。** 理论定位已明显更像 OR/MS。 |
| 审稿2 | **proof coverage / proof clarity，尤其 lower-bound propositions** | 回应信说已重组附录并修 proof details。 （回应信，pp. 10–12） | Proposition 1–5 的证明都在 Appendix C；Theorem 1 在 D；Theorem 2 在 E；Theorem 3 在 F。 （修订稿，pp. 52–70） | **主文 formal results 基本对齐。** 唯一剩余点是 Appendix A 的 Theorem 4 只有一句“proof follows…”。 |
| 审稿2 | **threshold without waiting 要单独比较** | 回应信 R2.5 说已加 targeted comparison。 （回应信，p. 11） | 附录 H.1 给 WAIT vs WAIT-no-wait。 （修订稿，pp. 77–78） | **已解决。** |
| 审稿2 | **实验参数/可复核性：memory cap、Sarathi config、replications、GPU validation** | 回应信 R2.8/R2.9 逐项对答。 （回应信，pp. 12–14） | Section 6 现在写清 A100 80GB、1.37×10^5 token cap、baseline memory margin、10 replications、Sarathi chunked prefill、rate grids；H.2 写 SGLang/A100 details。 （修订稿，pp. 30–38, 78–82） | **大体解决。** 数值透明度已达标。 |
| 审稿2 | **real-data tuning 不能像用 future arrivals/oracle** | 回应信明确说只用 workload distribution + offered rate 的 prespecified grid。 （回应信，pp. 12–13） | Section 6.2 已明确“no realized future arrivals or individual output-length predictions”。 （修订稿，pp. 37–38） | **已解决，但建议再显式标注为 rate-aware calibrated implementation。** |
| AE + 审稿3 | **相关工作与贡献定位要更公平，说明你们不是在宣称超越所有 concurrent work** | 回应信写了 timing/information model 的对比轴。 （回应信，p. 4） | Introduction 的 related work 现在并列讨论 Jaillet/Wang/Chen/Bari/Li 等，并强调“complementary queueing mechanism”。 （修订稿，pp. 6–8） | **基本公平。** 可再轻微柔化 “frameworks remain scarce” 一句。 |

## 回应信需要修改之处

### GPU验证范围需要再收紧

**严重性：高**  
**位置：回应信开头摘要 bullets；R2.9；Closing。**  
**为什么重要：** 现在回应信虽然多数地方区分了 Vidur 与 physical A100，但开头和结尾仍容易给人一种“整套比较都在真实GPU上被验证”的印象，而正文附录 H.2 其实是**timing calibration + WAIT vs SGLang supplemental runs**，不是 Fig. 7–12 所有基线在真实GPU上的完全复现。 （回应信，pp. 1–2, 13–14, 18；修订稿，pp. 30–38, 78–82）

**建议替换语言：**  
把开头 bullet 中的  
> “We added direct A100 validation ... and reported end-to-end real-GPU experiments.”  

改成  
> “We added supplemental physical-A100 validation of the iteration-time model and implementation behavior. The main league-table comparisons remain Vidur simulations configured for Llama-2-7B on an A100 GPU.”  

把 Closing 中的  
> “the experiments now directly address the queueing diagnostics requested by the review team”  

改成  
> “the experiments now directly address the queueing diagnostics requested by the review team, with the main comparative evidence coming from Vidur simulations and the physical-A100 runs serving as supplemental validation.”  

### proof-organization claim 需与论文完全对齐

**严重性：中高**  
**位置：Area Editor response；开头表格写作质量行。**  
**为什么重要：** 回应信说附录已按 theorem/proposition logic 重组，这对主文 Proposition 1–5 / Theorem 1–3 基本成立，但 Appendix A 的 Theorem 4 仍没有真正独立 proof section；若维持当前论文写法，回应信最好别写得太满。 （回应信，pp. 2–3, 10–12；修订稿，pp. 48–49, 52–70）

**建议替换语言：**  
把  
> “reorganized the appendices around theorem-specific proof logic”  

改成  
> “reorganized the appendix so that the main-text propositions and the principal theorems are easier to verify, with explicit proof roadmaps for the main proof sections.”  

如果你们补了 Theorem 4 的 proof sketch，则可保留更强说法。

### real-data tuning 应明确是 rate-aware calibration，而非固定参数版本

**严重性：中**  
**位置：R2.8, Closing。**  
**为什么重要：** 回应信说了 prespecified grid，但没把“**each rate can pick a different config**”翻译成一个 reviewer 一眼能懂的标签。 （回应信，pp. 12–13；修订稿，pp. 37–38）

**建议补一小句：**  
> “The real-data curve should be read as a rate-aware calibrated implementation selected from a prespecified grid, not as a single fixed-parameter Nested WAIT configuration.”  

### 口吻可以再压缩、再去模板化

**严重性：中**  
**位置：回应信通篇，尤其开头与 D.1–D.7。**  
**为什么重要：** 现在口吻总体专业、不防御，但仍偏长、偏教程式，存在较多重复句型，如 “This suggestion led us...”“This point is central...” 等；在 OPRE risky revision 场景下，**更短、更准、更少抒情**会更稳。 （决定信，p. 1；回应信，pp. 1–18）

**具体修复：**  
把开头 6 个 bullets 压成 4 个；每段保留一处感谢即可；把“感谢—解释—再感谢”的三拍子改成“感谢一句 + 直接陈述修改 + 具体页码/section”。

## 论文需要修改之处

### 摘要中 simulation vs real-GPU 的逻辑关系要重写

**严重性：高**  
**位置：摘要，p. 1。**  
**为什么重要：** 这是全包中最容易被误读的一句话。当前写法会让审稿人感觉“真实A100验证支持了稳定域扩大和整体baseline比较”，而附录 H.2 的真实GPU证据并不承担这么大的外延。 （修订稿，pp. 1, 78–82）

**建议替换语言：**  
> “In Vidur simulations configured for Llama-2-7B on an A100 GPU, and with supplemental physical-A100 validation of the timing model and implementation behavior, the policies enlarge the empirically realized stable operating range relative to the tested baselines and reduce latency especially in near-overloaded and overloaded regimes.”

我建议把 **realized stability region** 改成 **empirically realized stable operating range**，更稳。

### Theorem 4 需要显式 proof sketch，或降级为 corollary/extension result

**严重性：高**  
**位置：Appendix A.2, pp. 48–49。**  
**为什么重要：** 这轮审稿最忌讳“formal statement without verifiable proof”。主文 formal results 你们已经修得很好，但 Theorem 4 仍然是明显的薄弱点。 （AE报告，pp. 2–3；修订稿，pp. 48–49, 64–70）

**具体修复：**  
至少补三步：  
- aggregate rates \(\lambda'_k\) 如何替代 type-level \(\lambda_j\)；  
- 为什么 boundary queue 仍满足与 Theorem 2 同型的 binomial thinning domination；  
- 为什么式(17) 的 memory accounting 直接继承式(14) 的结构。  

如果不想展开，请把它改成：  
> “Corollary 1 (segment aggregation extension). The claim follows from the proof skeleton of Theorem 2 under aggregated segment rates.”  

### 对 Nested WAIT 的 overflow-prevention 表述再条件化

**严重性：中高**  
**位置：摘要 p. 1；结论 pp. 38–39。**  
**为什么重要：** 定理2明明是“在 stated conditions 下，由 logarithmic safety buffer 给出 high-probability no-overflow feasibility”；正文主 theorem 写得很清楚，但摘要和结论仍有读者可能读成“算法本身防止overflow”。 （修订稿，pp. 29–30, 38–39）

**建议改法：**  
把  
> “with a finite-horizon logarithmic safety buffer preventing memory overflow and evictions for Nested WAIT”  

改成  
> “with a finite-horizon logarithmic safety buffer that yields high-probability no-overflow feasibility for Nested WAIT under the stated conditions.”  

### Figure 12/Section 6.2 应更明显标注为“rate-aware calibrated”

**严重性：中**  
**位置：Section 6.2，pp. 36–38；Figure 12 caption。**  
**为什么重要：** 读者如果不仔细读正文，会误把曲线当作一个固定参数实现。你们正文其实已经讲清楚，但图附近最好再提醒一次。 （修订稿，pp. 37–38）

**建议补一句：**  
> “Each Nested WAIT point uses the best configuration from the prespecified \((tl, L)\) grid for that offered arrival rate.”  

### 个别口语化/系统味过重的句子应收掉

**严重性：中**  
**位置：Introduction p. 4；Conclusion pp. 38–39。**  
**为什么重要：** 现在论文整体已经是 OR/MS 风格，但仍有少量“系统文章/博客口气”的残留。 （修订稿，pp. 4, 38–39）

**建议具体改动：**  
- p. 4 把  
  > “Users experience this as error messages (e.g., ‘Something went wrong’) …”  
  改成  
  > “Operationally, this appears as failed or aborted generations under heavy load …”  
- 结论把  
  > “decouples interactions across prompt types”  
  改成  
  > “induces lower-dimensional threshold or boundary queues that summarize the memory-coupled state for analysis.”  

### 相关工作里“frameworks remain scarce”可再柔化

**严重性：低到中**  
**位置：Introduction related work，pp. 7–8。**  
**为什么重要：** 你们已经列了 2025 年多篇 concurrent work，再说 “frameworks remain scarce” 容易显得把别人的存在压低。 （修订稿，pp. 7–8）

**建议改法：**  
> “Analytical frameworks remain relatively limited compared with the scale of deployment.”  

这会更公允，也更像 AE 想要的 positioning。

## 论证、证明与实验一致性审计

### 理论陈述与附录证明的对齐情况

**结论：主文 formal results 基本对齐，尤其 reviewer 最担心的 lower-bound propositions 现在是补齐的。**  
主文里的 Proposition 1–5 与 Theorem 1–2 都能在附录中找到相应证明：Prop. 1–5 在 Appendix C，Theorem 1 在 Appendix D，Theorem 2 在 Appendix E，Theorem 3 在 Appendix F；其中 Proposition 4 的 latency/TTFT lower bound 这次确实已经明确写出并给了 Appendix C.3，而不是继续缺位。这个点对负面审稿人的“proof coverage”疑虑是直接减压的。 （修订稿，pp. 23, 28–30, 52–56, 56–70；内部清单，p. 1）

**但有一个尾部弱点：Appendix A 的 Theorem 4 仍没有同等强度的 proof packaging。**  
严格说，如果你把 Theorem 4 保持为正式 theorem，那么目前“proof follows the structure of Theorem 2 in Appendix E”还不够 reviewer-friendly；它不像主文 formal results 那样可核验。若你不想展开完整证明，最好把位阶降低，或者给出更明确 proof sketch。 （修订稿，pp. 48–49, 64–70）

### 开放系统吞吐量与稳定性解释

**结论：这部分现在处理得对。**  
Section 2.4 明确说 fixed external arrivals 下，effective throughput 上界是 offered decode-token load；Section 6 进一步说明 stable policies 在稳定区内 completion rate 都应跟着 offered load 走，差异主要在靠近边界或超载时通过 latency growth、completion-rate saturation、eviction/restart waste 显现。这正是负面审稿人要求的 open-system framing。 （决定信，p. 1；审稿意见1，pp. 1–4；修订稿，pp. 13–14, 17–18, 30–38；回应信，pp. 14–16）

### 内存模型与 WAIT / Nested WAIT 的定位

**结论：memory semantics 已经清楚，WAIT/Nested WAIT 也不再像“普通 batching”。**  
Section 2.3–2.4 和 Algorithms 1–2 现在都明确：GPU-resident KV cache 包括当前不在 batch 里的 admitted requests；preemption 是“pause while keeping KV on GPU”，不是无成本 swap 到 CPU/SSD；exceeding memory leads to eviction/restart。与此同时，Section 4.2 和 5.2 把 WAIT / Nested WAIT 定位为**控制内生内存增长与 downstream buildup 的 threshold policies**，而不是一般的 queue batching。 （修订稿，pp. 12–14, 20–23, 24–30；回应信，pp. 5, 9, 15–17）

### 数值实验透明度

**结论：总体达到“透明且足以审稿核验”的标准。**  
Section 6 说明了 simulator、硬件、A100 80GB、Llama-2-7B、KV-cache token size、1.37×10^5 token cap、baseline 1% memory margin、eviction-and-restart semantics、Sarathi 的 chunked prefill、10 replications、arrival-rate grids、以及 real-data 的 \(tl\)/\(L\)/\(\eta\) calibration；附录 H.2 进一步说明了 simulator-vs-GPU calibration 细节、SGLang 版本、single-type/real-data GPU runs；H.3 给 repeated-run variability；H.4 解释 PD deployment。 （修订稿，pp. 30–38, 78–83；回应信，pp. 12–14, 16）

**仍需改善的不是“实验内容不够”，而是“结果边界标注还可更诚实一眼可见”。**  
最典型就是 real-data Figure 12 应更明显标成 rate-aware calibrated implementation；真实GPU runs 应更明显标成 supplemental validation，而不是 baseline league-table replication。 （修订稿，pp. 37–38, 78–82）

### 现在是否像 OR/MS 论文

**结论：是，且比原审稿轮次要求的“系统论文转成OR论文”目标更接近了。**  
原因不在于删掉了系统细节，而在于现在的核心叙事是：**多阶段开放系统、流体平衡、稳定域、阈值控制、队列嵌入、Lindley/Kingman/Doob、完成率与延迟的队列化解释**。这已经是 OR/MS 的主语言。系统实验如今扮演的是 supporting evidence，而不是文章主体。 （AE报告，pp. 1–3；修订稿，pp. 15–30, 52–70, 77–83）

## 表述与语言审计

### 回应信开头仍略 AI-like / 模板化

**严重性：中**  
**位置：回应信 pp. 1–2。**  
**问题：** 开头信息很多，但略有“总结发言稿”感，尤其六个 bullets 过长、句型相似。  
**为什么会刺激审稿人：** risky revision 的理想回应信是“短、准、对齐”；过长反而像在做 framing。  
**建议：** 压到四条：  
- objective reframing；  
- resident-memory semantics + timing model scope；  
- theory positioning + proof organization；  
- experiments + validation scope。 （回应信，pp. 1–2）

### “This suggestion led us… / This point is central…” 重复偏多

**严重性：中**  
**位置：回应信多处，特别是 pp. 8–18。**  
**问题：** 虽不失礼，但容易显得模板化。  
**建议：** 一半改成直接式：  
> “We revised Section 6 to …”  
> “The revised Appendix now …”  
> “The main text now makes explicit that …”  
而不是总先铺一个评价句。 （回应信，pp. 8–18）

### 论文中仍有少量口语化句子

**严重性：中**  
**位置：修订稿 p. 4。**  
**问题：** “Users experience this as error messages (e.g., ‘Something went wrong’)” 偏口语。  
**建议：** 改成更操作学/系统运作语言。 （修订稿，p. 4）

### 个别句子仍有“讲机制”时过于口号化的倾向

**严重性：低到中**  
**位置：修订稿 p. 5–6, p. 38。**  
**问题：** 如 “memory is a resource to exploit rather than merely a constraint” 这种句子，思路是对的，但 reviewer 可能更喜欢朴素表达。  
**建议：** 改成“larger batches amortize fixed overhead subject to memory feasibility”。 （修订稿，pp. 5–6）

### 相关工作段最后一句略带“我们把理论说圆了”的味道

**严重性：低**  
**位置：修订稿 p. 8。**  
**问题：** “moves the realized stability region closer to that fluid prediction” 读起来略像在把经验现象写成理论 consequence。  
**建议：** 改成  
> “helps explain why threshold-based admission can bring the empirically observed operating range closer to the fluid prediction in the tested settings.” （修订稿，p. 8）

## Claim-scope 审计与最终建议

### 需要软化的 claims

**摘要：**  
“validated by real-A100 experiments” 与 “policies enlarge the realized stability region” 放在同一句里，建议拆开并显式加 **empirically / tested baselines / supplemental validation**。 （修订稿，p. 1）

**结论：**  
“algorithms attain the fluid effective-throughput benchmark … even when output lengths are unknown at arrival” 建议加上**under the affine decode-centered model and the stated memory conditions / safety-buffer conditions**，避免读成无条件 generality。 （修订稿，pp. 38–39）

**PD appendix：**  
“especially appropriate” 可以保留，但若你们想极稳，可改成 “more natural / more closely aligned”。 （修订稿，pp. 82–83）

### 需要 sharpen 的 claims

**real-data implementation：**  
应主动 sharpen 成“**rate-aware calibrated implementation from a prespecified grid**”。这不是弱化，反而是把实验设计说清楚。 （修订稿，pp. 37–38；回应信，pp. 12–13）

**proof coverage：**  
如果你们补 Theorem 4 proof sketch，那么回应信可更明确写一句：  
> “All formal propositions in the main text now have explicit appendix proofs; the segment-aggregation extension is also linked to the Theorem 2 proof skeleton.”  
这能直接打掉 reviewer 对“proofs obscured in appendix”的旧印象。 （修订稿，pp. 48–49, 52–70；回应信，pp. 10–12）

### 最终 resubmission recommendation

**建议：先做一轮很小但很精准的终修，再提交。不要再加实验。**  
如果按上面列出的点做一次 1–2 天内可完成的定点修补——尤其是**摘要 scope、Theorem 4 proof packaging、Figure 12 的 rate-aware标注、回应信收口**——我会把结论从 `needs targeted revision` 上调到 **`ready after minor edits`**。以当前版本直接投也不是不行，但在 OPRE 这个“risky major revision”语境下，我不建议把这些**明知会被抓的小口子**留给审稿人。最优策略是：**不再扩张内容，只做形式诚实性和可核验性的最后收边**。 （决定信，p. 1；AE报告，pp. 2–3；修订稿，pp. 1, 37–39, 48–49, 78–82；回应信，pp. 1–18）