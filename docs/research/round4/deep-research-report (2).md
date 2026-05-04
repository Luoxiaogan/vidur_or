# 最终复投稿审计报告

## 执行结论

**Executive verdict：`needs targeted revision`。** 我的判断是：这版修回已经**实质性解决了**上一轮最危险的几类问题——开放系统下 throughput 的表述、latency-vs-arrival-rate 的实验框架、GPU-resident memory semantics、Section 2 的可读性、以及 proof roadmap / Appendix 组织——因此论文已经从“高风险 major revision”推进到了“只剩定点文字与定位修整”的阶段；但在正式重投前，我仍建议做一轮**小范围但必须到位**的 targeted revision，重点收口 **simulation-vs-real-GPU 的表述边界、经验稳定性语言、real-data 调参口径、以及少数仍偏系统化/宣传化的措辞**。这些问题都可以通过**文字、caption、response-letter scope control**解决；我**不建议要求新增实验**。这个结论也与决定信中“risky major revision”的提醒相一致：如果 exposition 和 scope 还留有刺，下一轮很容易被 AE/负面审稿人抓住不放。 （`04_decision_letter(5).md`, lines 4–10, 62–88；`06_revised_paper(5).pdf`, pp. 13–18, 30–39, 79–83；`07_response_letter(5).pdf`, pp. 1–4, 12–18）

我认为这次修回里**已经做对**的事情包括：把 throughput 重新锚定在 exogenous arrivals / stability-region 语境下，而不是错误地把开放系统 throughput 当作固定 arrival rate 下的优化目标；把 memory constraint 明确到**所有 GPU-resident KV caches**而不只是当前 batch；把 Eq. (1) 明确限定在 **decode-dominant / affine decode-centered** 范围，并补上 A100 校准与 supplemental GPU runs；把主要 formal results 的 proof coverage 与 theorem-interpretation 基本补齐。这几项是从“可能被拒”走到“接近可投”的核心原因。 （`04_decision_letter(5).md`, lines 75–88；`03_review_report_2(5).pdf`, pp. 1–2；`02_review_report_1(5).pdf`, pp. 2–6；`06_revised_paper(5).pdf`, pp. 12–18, 22–30, 30–38, 48–49, 79–83；`07_response_letter(5).pdf`, pp. 1–4, 10–18）

另外，我同意内部 checklist 对 **abstract scope** 与 **rate-aware calibration 标签** 的优先级判断，但我**不同意**把 “Theorem 4 proof packaging” 继续当作当前版本的阻塞项：内部清单把它列为 P0，是基于更早版本；而当前 PDF 的 Appendix A.2 已经在 Theorem 4 后给出显式 proof paragraph，我不会再把这一项当作 remaining blocker。换句话说，当前版本比内部清单所描述的状态**更好**，但 abstract / conclusion / captions 的 scope honesty 仍需最后一轮收边。 （`08_internal_followup_checklist(1).md`, lines 12–29；`06_revised_paper(5).pdf`, pp. 48–49）

## 最高剩余风险

- **摘要与结论对“Vidur 仿真 vs 真实 GPU 验证”的边界仍然偏强。** 最危险的位置是摘要最后两句，以及结论最后一段：摘要目前把 “Vidur simulations configured for Llama-2-7B on an A100 GPU, supported by supplemental real-A100 validation” 和 “enlarge the realized stability region”放在同一条主结论里，结论也写成“Vidur simulations ... show these effects ... and supplemental real-GPU validation supports the timing model and implementation behavior”。正文 Section 6/H.2 其实已经把边界说得更准确：主比较证据来自 Vidur，真实 A100/SGLang 主要支持 **timing model / implementation behavior**，并提供 supplemental end-to-end checks，而不是对所有 baseline league-table 结论做 fully physical replication。若不在摘要与结论收紧，AE 或负面审稿人很容易认为你们在“把模拟结果包装成 GPU 实证”。 （`06_revised_paper(5).pdf`, p. 1, pp. 38–39, pp. 79–83；`07_response_letter(5).pdf`, pp. 1–3, 13–14）

- **经验结果仍借用了偏理论化的“稳定/不稳定/stability region”语言，尤其在 Figure 10 及其正文解释里。** 现在最容易被抓的句子是：正文写 “At λ = 23, both policies are unstable...”“consistent with Nested WAIT being stable at λ = 22 and unstable at λ = 23”，Figure 10 caption 也直接写 “both policies are unstable”。对有限 horizon 仿真而言，这种写法太硬；更稳妥的说法应是“continue to exhibit latency growth over the tested horizons”“consistent with the observed transition between these two rates”。同样，abstract / conclusion / Section 6 里 “realized stability region”“empirically realized stable region”与理论上的 fluid stability region 混用，也会刺激上一轮对 queueing semantics 很敏感的负面审稿人。 （`04_decision_letter(5).md`, lines 79–81；`06_revised_paper(5).pdf`, p. 1, pp. 31–38, p. 39）

- **real-data 曲线虽然正文已透明说明是 rate-aware calibration，但 Figure 12 附近仍缺少“一眼就懂”的标签。** Section 6.2 已经老实写明：对每个 offered arrival rate，从 prespecified \((tl, L)\) grid 中选 lowest-latency configuration，而且 online scheduler 不使用未来 arrivals 或 individual output-length prediction。这在方法上并不不当；问题在于如果读者只看 Figure 12 和邻近文字，很容易把它读成“一个固定参数版本的 Nested WAIT 曲线”。这不是实验缺失，而是呈现层面的**interpretation risk**。最稳的做法是在 Figure 12 caption 或紧邻正文加一句：**“Each Nested WAIT point uses the best configuration from the prespecified grid for that offered rate; the curve should be read as a rate-aware calibrated implementation, not as a single fixed-parameter configuration.”** （`06_revised_paper(5).pdf`, pp. 37–38；`07_response_letter(5).pdf`, p. 13）

- **Proposition 2 仍有重启上一轮“开放系统 throughput 是会计恒等式”争论的风险。** 你们这轮已经把 open-system framing 基本改正，特别是紧接着 Equation (10) 就强调 “the contribution ... is not this accounting identity alone, but the accompanying description of the composition needed to realize it”，这一步是对的；但把这个上界仍然保留为 **Proposition 2**，形式上还是容易给负面审稿人一个把柄：他会说“作者明知这是 open-system accounting upper bound，为什么还把它 theoremize 成 proposition？”我的建议不是删掉这个点，而是把它**降成 Benchmark Remark / Observation**，或者在题头里直接标记成 “offered-load upper bound”。这样能减少无谓摩擦。 （`04_decision_letter(5).md`, lines 77–80；`06_revised_paper(5).pdf`, pp. 17–18；`07_response_letter(5).pdf`, pp. 14–16）

- **少数句子仍然不够 OPRE/Management Science 风格，或者略有“系统论文/产品口吻”。** 最典型的包括：Introduction 里 “Users experience this as error messages (e.g., ‘Something went wrong’)”；Section 1.1/Conclusion 里“decouples interactions across prompt types”“expand the empirically realized stable region”；以及 response letter 开头若干 bullet 和 closing，仍有一点模板化、略满、略像“解释自己已经做了很多工作”的口气。单独看都不致命，但在一个决定信已经明确点名“serious, conscientious revision of exposition”的 risky major revision 里，我建议把这些边角也清干净。 （`04_decision_letter(5).md`, lines 6–10；`01_AE_report(5).pdf`, pp. 2–3；`06_revised_paper(5).pdf`, p. 4, p. 6, pp. 38–39；`07_response_letter(5).pdf`, pp. 1–4, 18）

## 评审关切覆盖矩阵

- **AE：complete expositional overhaul；不要只修 typo。**  
  **回应信：已覆盖。** 回应信一开头就把 exposition rewrite 列为主改动，并在 AE response 里具体写了：Section 2 重写、notation summary、算法前示例、theorem interpretation、proof appendix modularization。  
  **论文：已覆盖。** 当前稿的 Section 2–6 确实比原版更像一个完整的 OR/MS narrative：模型—目标—fluid equilibrium—policy—theorem interpretation—numerics 这一条线现在是通的。  
  **审计判断：实质性解决。** 我不会再把 exposition 视为 blocking issue。 （`01_AE_report(5).pdf`, pp. 2–3；`06_revised_paper(5).pdf`, pp. 8–14, 22–30；`07_response_letter(5).pdf`, pp. 2–4, 18）

- **AE：proof summaries 过空；appendix 像“deposit boxes”。**  
  **回应信：已覆盖。** 回应信现在不再泛泛说“proof employs coupling”，而是解释 WAIT / Nested WAIT 如何把 memory-coupled control 压成 threshold or boundary queues。  
  **论文：基本覆盖。** Theorem 1/2 主文后紧跟解释段；Appendix C–G 的组织也明显优于原版。  
  **审计判断：基本解决。** 我不再认为 proof packaging 是主风险；内部 checklist 的 Theorem 4 担忧在当前 PDF 中已基本解除。 （`01_AE_report(5).pdf`, pp. 2–3；`08_internal_followup_checklist(1).md`, lines 12–20；`06_revised_paper(5).pdf`, pp. 23, 30, 48–49, 56–79；`07_response_letter(5).pdf`, pp. 2–4, 10–12）

- **Referee 2：memory overflow / OOM safeguards、notation consistency、policy space。**  
  **回应信：已覆盖。** 回应信明确写了 GPU-resident KV accounting applies to all admitted in-system prompts，policy class \(\Pi\) 在 Section 2.4 明确化。  
  **论文：已覆盖。** Section 2.3 的 \(G_t\) 定义、Section 2.4 关于 preemption / eviction 的澄清、Algorithm 1/2 的 “already resident prompts ... retain KV caches” 都与回应信对齐。  
  **审计判断：解决得很实。** 这是本轮修回最扎实的一块，无明显 mismatch。 （`03_review_report_2(5).pdf`, pp. 1–2；`06_revised_paper(5).pdf`, pp. 12–14, 21, 27；`07_response_letter(5).pdf`, pp. 5–7, 17–18）

- **Referee 1：Eq. (1) 的 affine timing model scope、proof of Theorem 1、实际 GPU 校准。**  
  **回应信：已覆盖。** 回应信把模型 scope 明确到 decode-dominant regime，解释何时需要 richer calibrated curve，并给出 A100/SGLang validation。  
  **论文：已覆盖，但 abstract / conclusion 仍需对 scope 再收一格。** Section 2.2 和 Appendix H.2 现在是清楚的；摘要和结论则仍比正文略强半步。  
  **审计判断：大体解决，存在轻微 overstating。** 这是一个**非结构性**问题，文字收口即可。 （`02_review_report_1(5).pdf`, pp. 2–6；`06_revised_paper(5).pdf`, pp. 10–12, 30–31, 79–83；`07_response_letter(5).pdf`, pp. 3, 8–9, 13–14）

- **Decision letter / negative referee：heavy traffic misuse。**  
  **回应信：已覆盖。** 专门用 D.1 认错并改成 fixed-load / long-horizon asymptotic framing。  
  **论文：已覆盖。** 正文已去掉 heavy-traffic 表述。  
  **审计判断：已解决。** 这条不应再成为下一轮问题。 （`04_decision_letter(5).md`, lines 64–75；`06_revised_paper(5).pdf`, pp. 22–30；`07_response_letter(5).pdf`, pp. 14–15）

- **Decision letter / negative referee：open-system throughput 应转成 stability-region / latency framing。**  
  **回应信：已覆盖。** 回应信把这类批评当作主要修改来源之一。  
  **论文：已覆盖，但 Proposition 2 的 formal packaging 仍可更顺手。** Section 2.4/6 的 framing 是对的；剩余问题主要是 presentation tactic。  
  **审计判断：内容上解决，形式上最好再润一刀。** （`04_decision_letter(5).md`, lines 77–81；`06_revised_paper(5).pdf`, pp. 13–18, 30–38；`07_response_letter(5).pdf`, pp. 14–17）

- **Decision letter / negative referee：latency 不能只在看起来 unstable 的区间里比较。**  
  **回应信：已覆盖。** 明确说 Section 6 改成 long-enough latency vs arrival-rate 结构，并添加 repeated runs / long-horizon check。  
  **论文：基本覆盖。** Section 6 现在确实比原版稳得多；但 Figure 10 和相关正文对 “stable / unstable” 的经验表述仍然过硬。  
  **审计判断：核心问题解决，但仍有局部语言风险。** 这是我认为最值得最后修的 empirical-language 问题之一。 （`04_decision_letter(5).md`, lines 81–88；`06_revised_paper(5).pdf`, pp. 31–38, 83；`07_response_letter(5).pdf`, pp. 14–18）

- **AE / Referee 1：论文应更明确说明理论新意是 modeling / problem structuring，而不一定是新 stochastic-process theorem。**  
  **回应信：已覆盖。**  
  **论文：已覆盖。** Section 1.2、4.2、5.2 与结论现在都将贡献定位为：memory-coupled queueing-control problem 的结构化与 fluid-guided threshold design。  
  **审计判断：定位基本到位。** 剩余需要做的只是把若干“ extends naturally / decouples interactions / stable region”式说法再收紧，不是内容缺失。 （`01_AE_report(5).pdf`, p. 3；`04_decision_letter(5).md`, lines 86–88；`06_revised_paper(5).pdf`, pp. 6–8, 20–30, 38–39；`07_response_letter(5).pdf`, pp. 4, 15–17）

- **Response-letter 与论文是否存在实质 mismatch。**  
  **回应信：总体准确。**  
  **论文：总体支持。**  
  **审计判断：没有严重不一致；只有两处“写得比正文略满”的地方：其一是 real-GPU validation 的 opening bullet；其二是 real-data calibrated curve 的可见性在 response letter 里比正文图附近更清楚。** 这两处都属于收口，不是实质性失配。 （`07_response_letter(5).pdf`, pp. 1–3, 13–14, 18；`06_revised_paper(5).pdf`, pp. 37–38, 79–83）

## 表达与语言审计

- **位置：摘要，第 1 页最后三句。**  
  **问题：** scope 太满，且 simulation / physical-GPU / safety buffer 三件事被压在一起，读起来像“真实 A100 支撑了全部主比较”。  
  **建议替换：**  
  *“Under the stated scaling and memory conditions, WAIT attains the fluid effective-throughput benchmark, and Nested WAIT achieves the analogous guarantee with a finite-horizon logarithmic safety buffer that yields high-probability no-overflow feasibility for unknown output lengths. In Vidur simulations configured for Llama-2-7B on an A100 GPU, complemented by supplemental physical-A100 validation of the timing model and implementation behavior, the policies expand the empirically observed stable operating range relative to the tested baselines and reduce latency most visibly in near-overloaded and overloaded regimes.”*  
  这版更像 OPRE 摘要：把 theorem scope、empirical scope、GPU scope 分开，不把“补充验证”写成“主证据”。 （`06_revised_paper(5).pdf`, p. 1）

- **位置：Introduction，第 4 页 “Something went wrong” 那句。**  
  **问题：** 这句偏系统博客/产品体验口吻，不像 OR/MS 正文。  
  **建议替换：**  
  *“Operationally, this appears as failed or aborted generations under heavy load.”*  
  这样既保留 operational meaning，又去掉 consumer-facing 语气。 （`06_revised_paper(5).pdf`, p. 4）

- **位置：Section 6.1，Figure 10 及其前置段落，第 35–36 页。**  
  **问题：** “both policies are unstable”“Nested WAIT being stable at 22 and unstable at 23” 对有限 horizon 仿真过强。  
  **建议替换正文：**  
  *“At λ = 22, Nested WAIT’s latency appears to plateau over the tested horizons, whereas Sarathi’s continues to grow. At λ = 23, both policies exhibit continued latency growth over the tested horizons, with Nested WAIT remaining 30%–50% below Sarathi. Taken together, these patterns are consistent with the observed transition lying between the two rates.”*  
  **建议替换 Figure 10 caption：**  
  *“At λ = 22, Nested WAIT approaches a finite plateau over the tested horizons while Sarathi continues to grow; at λ = 23, both policies show continued growth, but Nested WAIT remains lower-latency.”*  
  这一改动很值，因为它会直接降低 reviewer 对 empirical-overstatement 的警觉。 （`06_revised_paper(5).pdf`, pp. 35–36）

- **位置：Section 6.2 与 Figure 12，第 37–38 页。**  
  **问题：** 已经透明说明 per-rate 选 grid 上最佳配置，但图和紧邻文字还不够“一眼看懂”。  
  **建议补一句：**  
  *“Each Nested WAIT point uses the lowest-latency configuration from the prespecified \((tl, L)\) grid for that offered arrival rate; the curve should therefore be read as a rate-aware calibrated implementation rather than as a single fixed-parameter configuration.”*  
  这句话最好放在 Figure 12 caption 或其前一段末尾。 （`06_revised_paper(5).pdf`, pp. 37–38）

- **位置：结论，第 38–39 页。**  
  **问题：** “decouples interactions across prompt types”“expand the empirically realized stable region” 仍稍显大而化之。  
  **建议替换：**  
  *“The threshold construction induces lower-dimensional threshold and boundary queues that summarize the memory-coupled state for analysis. Under the affine decode-centered model and the stated memory conditions, the resulting policies attain the fluid effective-throughput benchmark and the accompanying delay guarantees. In the tested Vidur settings, they also expand the empirically observed stable operating range and reduce latency most clearly near the observed transition to overload.”*  
  这样既保留了理论贡献，也把 empirical claim 收到了 “tested Vidur settings”。 （`06_revised_paper(5).pdf`, pp. 38–39）

- **位置：回应信开头第 1–2 页，以及 closing 第 18 页。**  
  **问题：** 整体专业，但略长、略模板化、略像“解释自己做了很多工作”。  
  **建议改法：** 开头 bullets 从 6 个压成 4 个，且把 GPU 那一条改成：  
  *“We added supplemental physical-A100 validation of the iteration-time model and implementation behavior. The main policy comparisons remain Vidur simulations configured for A100 hardware.”*  
  Closing 则建议改成：  
  *“The revised manuscript reframes the problem around stability-region expansion, eviction prevention, and latency under exogenous arrivals; clarifies the model assumptions and proof logic; and strengthens the empirical evidence. The main comparative results remain simulation-based, with supplemental physical-A100 validation of the timing model and implementation behavior.”*  
  这会更克制，也更像给 AE 的专业复函。 （`07_response_letter(5).pdf`, pp. 1–3, 13–14, 18）

## 技术一致性审计

**Notation 与 policy-space consistency：通过。** 原来最明显的冲突——stage index、prompt length、decode progress、policy class \(\Pi\) 的混乱——在当前稿里基本已经清掉。Section 2.1–2.4 现在是连贯的：\(s=0\) 表示 prefill，\(s\ge 1\) 表示 decode stage；\(\Pi\) 在 2.4 中给出；Algorithm 1/2 与正文符号对齐。我没有再看到会让 reviewer 一眼皱眉的主符号冲突。 （`03_review_report_2(5).pdf`, pp. 1–2；`06_revised_paper(5).pdf`, pp. 8–14；`07_response_letter(5).pdf`, pp. 6–7, 18）

**Memory semantics：通过，而且现在是这篇稿子的强项之一。** 论文已明确区分 waiting outside GPU before prefill 的 jobs、admitted but not selected resident prompts、scheduler-side pausing 与 eviction/restart；memory constraint 适用于所有 GPU-resident KV caches，而不是仅当前 batch。这个点与审稿意见、回应信和算法伪码是一致的。 （`03_review_report_2(5).pdf`, pp. 1–2；`04_decision_letter(5).md`, lines 86–88；`06_revised_paper(5).pdf`, pp. 12–14, 21, 27, 29–30；`07_response_letter(5).pdf`, pp. 5–7, 17–18）

**Throughput / latency / effective completion rate 的层次区分：基本通过，但 Proposition 2 的 packaging 仍可更稳。** 现在理论里 token-level effective throughput，实验里 request-level effective completion rate，Section 6 开头也把“stable policy completes at offered load”点讲清楚了；这已经满足开放系统 queueing 语义。唯一还可能被挑的是 Proposition 2 的标题化 formalization，会让 reviewer 重新把注意力放回“this is just accounting”。如果将其降级为 benchmark remark，整篇 paper 的 queueing positioning 会更顺。 （`04_decision_letter(5).md`, lines 77–81；`06_revised_paper(5).pdf`, pp. 13–18, 31–32；`07_response_letter(5).pdf`, pp. 14–17）

**Stability-region language：理论与经验的切分还差最后一刀。** 理论里 “fluid stability region / fluid stability boundary / \(M^*\le C\)” 是对的；经验部分最好统一写成 “empirically observed stable operating range”“observed transition point”，而不是不加限定地写 “stable / unstable / realized stability region”。这不是数学错误，而是**semantic hygiene**。在当前决定信背景下，这一刀值得做。 （`04_decision_letter(5).md`, lines 75–88；`06_revised_paper(5).pdf`, p. 1, pp. 31–38, p. 39）

**Simulation vs real-GPU consistency：正文基本通过，摘要/结论/回应信开头仍有小幅 scope slippage。** 正文 Section 6 与 Appendix H.2 其实写得很干净：Vidur 是 calibrated simulator；A100/SGLang 提供 timing calibration 和 supplemental end-to-end runs；Table 3 甚至把 real-data GPU 的参数公开了。这说明实证部分的**底层逻辑是清楚的**。剩下的只是把 abstract / conclusion / response-letter opening 里的话也对齐到正文这种克制程度。 （`06_revised_paper(5).pdf`, pp. 30–38, 79–83；`07_response_letter(5).pdf`, pp. 1–3, 13–14）

**Affine timing model scope：通过。** 我认为这一点已经足以应对 Referee 1。Section 2.2 明确表示 Equation (1) 适用于 decode-dominant setting；H.2 给出 A100 校准指标 \(R^2=0.9943\)、MAPE 1.93%、\(B=256\) extrapolation error 4.93%；正文也说明 richer calibrated service-time curves 需要 model-specific analysis。这个 scope 是诚实的。 （`02_review_report_1(5).pdf`, pp. 2–3；`06_revised_paper(5).pdf`, pp. 10–12, 80–81；`07_response_letter(5).pdf`, pp. 3, 8–9, 13–14）

**Proof statement coverage：通过。** 目前 Proposition 1–5、Theorem 1–4 都有对应 proof section / proof paragraph；内部清单曾把 Theorem 4 proof packaging 列为 P0，但当前 PDF 已补上短证明。我不再建议为“proof coverage”新增结构性工作。 （`08_internal_followup_checklist(1).md`, lines 12–20；`06_revised_paper(5).pdf`, pp. 48–49, 52–79）

**Experiment parameter transparency：通过。** 硬件、KV-cap、baseline memory margin、Sarathi chunk size、replications、arrival-rate grids、real-data \(tl\)/\(L\)/\(\eta\)、GPU appendix 参数表，都已经清楚。这轮不需要再补实验细节，只需要在 Figure 12 附近把 “rate-aware calibrated implementation” 提醒更前置。 （`02_review_report_1(5).pdf`, pp. 5–6；`06_revised_paper(5).pdf`, pp. 31–38, 80–83；`07_response_letter(5).pdf`, pp. 12–14）

## Claim-scope 审计

- **摘要：** “Nested WAIT uses an additional safety buffer of moderate scale to handle unknown output lengths and prevent memory overflow and evictions.”  
  **问题：** 太像 unconditional prevention。  
  **更安全的写法：** *“Nested WAIT uses a finite-horizon logarithmic safety buffer that yields high-probability no-overflow feasibility under the stated conditions.”* （`06_revised_paper(5).pdf`, p. 1, pp. 29–30）

- **摘要 / 结论：** “supported by supplemental real-A100 validation ... enlarge the realized stability region” / “show these effects”  
  **问题：** 容易被读成 “physical-GPU confirms the main comparative claim”。  
  **更安全的写法：** *“In Vidur simulations configured for Llama-2-7B on an A100 GPU, complemented by supplemental physical-A100 validation of the timing model and implementation behavior, ...”* （`06_revised_paper(5).pdf`, p. 1, pp. 38–39）

- **Section 6.1 / Figure 10：** “both policies are unstable”  
  **问题：** 有限 horizon empirical claim 过硬。  
  **更安全的写法：** *“both policies exhibit continued latency growth over the tested horizons”* 或 *“the results are consistent with the observed transition lying between the two rates”*。 （`06_revised_paper(5).pdf`, pp. 35–36）

- **Section 6.2 / Figure 12：** “Nested WAIT has lower latency than the baselines”  
  **问题：** 容易被读成一般性 superiority claim。  
  **更安全的写法：** *“Nested WAIT is lower-latency than the tested baselines on the plotted arrival-rate grid, with a larger gap near overload.”* （`06_revised_paper(5).pdf`, p. 38）

- **PD extension sentence，第 6 页：** “Our batching theory also extends naturally ... The same threshold construction applies on the decode side...”  
  **问题：** 这句话的强度略高于正文给出的证据类型；你们有 numerics，但没有在本文内给 formal extension theorem。  
  **更安全的写法：** *“The same queueing perspective suggests a natural extension to prefill-decode-disaggregated systems; after calibration, an analogous decode-side threshold construction can be implemented, and Appendix H.4 reports representative numerical illustrations.”* （`06_revised_paper(5).pdf`, p. 6）

- **Appendix H.2：** “This agreement supports the use of Vidur for the latency and stability comparisons in Section 6.”  
  **问题：** “stability comparisons” 听起来过满。  
  **更安全的写法：** *“This agreement supports the use of Vidur as a calibrated simulator for the latency and operating-range comparisons in Section 6.”* （`06_revised_paper(5).pdf`, p. 80）

- **Conclusion：** “The threshold mechanism performs a dimensionality reduction: it decouples interactions across prompt types...”  
  **问题：** 容易显得太抽象、太 sweeping。  
  **更安全的写法：** *“The threshold construction induces lower-dimensional threshold and boundary queues that summarize the memory-coupled state for analysis.”* （`06_revised_paper(5).pdf`, pp. 38–39）

## 最终修改清单

**P0**

- **收紧 abstract 与 conclusion 的 scope**：把 “Vidur vs physical A100” 的边界、以及 Nested WAIT safety buffer 的 theorem scope 明确写成 *supplemental physical validation* 与 *high-probability no-overflow feasibility under stated conditions*；同时把 “realized stability region / empirically realized stable region” 统一替换成 *empirically observed stable operating range*。位置：摘要 p. 1；结论 pp. 38–39。 （`06_revised_paper(5).pdf`, p. 1, pp. 38–39）
- **修 Figure 10 及对应段落中的 empirical stability 语言**：把 “stable / unstable” 改成 “appears to plateau / continues to grow over the tested horizons / consistent with the observed transition...”。位置：pp. 35–36。 （`06_revised_paper(5).pdf`, pp. 35–36）
- **给 Figure 12 或其前段加上 rate-aware calibration 标签**，并在 response letter 对应位置镜像说明。位置：论文 pp. 37–38；回应信 p. 13。 （`06_revised_paper(5).pdf`, pp. 37–38；`07_response_letter(5).pdf`, p. 13）

**P1**

- **弱化 Proposition 2 的 theorem-like force**：最好改成 “offered-load upper bound” 的 remark / observation；若不改编号，至少在题头或导语里明确这是 accounting benchmark，而非技术贡献。位置：pp. 17–18。 （`06_revised_paper(5).pdf`, pp. 17–18）
- **软化 PD extension 与 H.2 simulator-support 的 claim scope**：把 “extends naturally / same threshold construction applies / supports stability comparisons” 改成 “suggests a natural extension / can be adapted after calibration / supports operating-range comparisons”。位置：p. 6；p. 80。 （`06_revised_paper(5).pdf`, p. 6, p. 80）
- **做一次 OR/MS 风格清洗**：删掉 “Something went wrong” 这种产品口吻；把结论里 “decouples interactions...” 改成 boundary-queue language。位置：p. 4；pp. 38–39。 （`06_revised_paper(5).pdf`, p. 4, pp. 38–39）

**P2**

- **压缩 response letter 开头与 closing**：从“说明自己做了很多”改为“精确说明改了什么、边界是什么”；尤其要在 opening bullet 里加一句“main policy comparisons remain Vidur simulations”。位置：回应信 pp. 1–3, 18。 （`07_response_letter(5).pdf`, pp. 1–3, 18）
- **统一经验术语**：正文/图注尽量统一用 *observed transition point*, *near-overloaded / overloaded*, *operating range*；理论部分保留 *fluid stability region / boundary*。位置：论文 pp. 31–39, 83。 （`06_revised_paper(5).pdf`, pp. 31–39, 83）
- **做一次轻量 caption/typo cleanup**：例如 appendix GPU setting 里 `prefill max requests= 8` 这类技术说明可以排版得更 journal-like；`tl` 若继续保留，建议首次出现时再加一句其与理论 threshold 的关系。位置：p. 80；pp. 31–32。 （`06_revised_paper(5).pdf`, pp. 31–32, 80）

总体上，我的建议不是“再做更多”，而是“把已经做对的大修，最后收成一版不会因为 scope 和口径问题被挑掉的稿子”。如果把上面这些 P0/P1 项目补完，我会把判断从 **`needs targeted revision`** 提升到 **`ready after minor edits`**。