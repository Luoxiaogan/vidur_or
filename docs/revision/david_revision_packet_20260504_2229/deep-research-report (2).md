# 修回包再投稿准备度评估

## 简短结论

我的短评是：**这版已经接近可重投状态，但我不建议原样提交；做一轮小修后再投更稳妥。** 作为一位偏 OPRE/MS 风格的 AE 或 referee 来看，作者已经明显且实质性地回应了上一轮最危险的批评：写作与结构重写、开放系统下 throughput/stability 的重新表述、latency 证据的补强、以及 WAIT / Nested WAIT 证明叙事的“可检查性”都比上一轮强很多。现在最可能继续引起审稿人犹豫的，不再是“这篇文章是否 fundamentally 没想清楚”，而是少数 **claim scope** 句子是否比正式定理更强，以及附录是否还能再降低一点核查成本。上一轮决定信明确把这次修回定为“risky major revision”，AE 也把 exposition/proof-checkability 列为首要问题；按这个标准看，这次修回已经跨过了大部分门槛。fileciteturn0file1 fileciteturn0file4 fileciteturn0file0 fileciteturn0file5

## 为什么我认为它已经基本具备可重投性

回复信的质量是够格的，而且**确实是在回应前一轮意见，不是在“绕开问题”**。回复信开头先总括六类大改动，然后分别按 AE、Reviewer 1、Reviewer 2，以及“Queueing, Stability, and Latency Concerns”来逐块回应。更重要的是，它对最敏感的几类批评——例如 heavy-traffic terminology 用错、开放系统里 throughput 的解释、unstable/overloaded regime 下 latency 图该怎么读、Equation (1) 的适用范围、以及 OOM / eviction / preemption 的建模边界——都不是泛泛致谢，而是明确承认原稿问题、说明改写方向，并把改动落到具体章节与附录。这个语气和结构，对 OPRE/MS 的 resubmission letter 来说是专业且可信的。fileciteturn0file0

从论文本体看，**OR/MS framing 现在已经清楚得多**。Section 2 不再把问题直接抛成抽象算法，而是先讲 prefill / decode、KV-cache 增长、policy space、calendar-time latency/TTFT，再进入目标函数与 admissible policies；Section 3 把 fluid equilibrium、memory requirement \(M^*(\lambda)\) 和 fluid stability region 连起来；Section 4–5 把 WAIT 和 Nested WAIT 解释成“用 threshold / boundary queue 控制 GPU-resident population”的 queueing-control 机制；Section 6 则把 latency 与 effective completion rate 配对，显式覆盖 underloaded、near-overloaded 与 overloaded 区间。换句话说，这版已经不只是“拿一个 LLM 系统 heuristic 来讲故事”，而是相当明确地把它写成了一个**开放随机服务系统中、带内生内存增长约束的调度控制问题**。这正是上轮决定信和负面评审最想看到的方向。fileciteturn0file1 fileciteturn0file5

WAIT 的证明叙事现在**基本是可核查的**。主文第 23–24 页不再只说“用了 coupling”，而是明确说明了：先用 full-threshold review interval 定义一个 auxiliary embedded process，再把实际 event-driven WAIT 按 type-by-type 的 service opportunities 去耦合；关键句“each type’s threshold batch receives a corresponding service opportunity within one full-threshold review interval”直接把 proof burden 说出来。Appendix D 第 64–69 页又把这件事真正落到了 Lemma 7 上：给出 deterministic review epochs、定义 \(R_j^\pi\) 与 \(\bar R_j^\pi\)，并明确证明 one-interval lag dominance。对一个 referee 来说，这已经从“看不出 proof 在干什么”提升到了“虽然仍需仔细读，但可以沿着清晰路线检查”。这正面回应了 AE 关于“proof summaries too high level”以及 Reviewer 2 关于 decode-stage dynamics 没讲清的批评。fileciteturn0file4 fileciteturn0file3 fileciteturn0file5

Nested WAIT 的证明叙事也到了**可核查、但仍建议再降一点心智负担**的水平。主文第 29–31 页已经把核心对象从“unknown output lengths”收束成了 downstream boundary queues，并明确写出 binomial thinning、negative drift condition、base memory \(M_\pi\) 与额外 safety buffer 的分工。Appendix E 第 71–74 页进一步定义了 post-review residual boundary queue \(V_r^{(k)}\)，说明 fresh survivors 记入 \(M_\pi\)，只有 carryover residual 才进入附加内存项，再用 reflected random walk 和 exponential-martingale / Doob inequality 给出 bounded expectation 与 high-probability memory bound。这个结构比原稿强很多，也和回复信里的解释一致。对 OPRE/MS 审稿人来说，这已经不是“不可核查”的稿子了。fileciteturn0file0 fileciteturn0file5

数值部分也明显更符合上轮意见。决定信特别提醒“throughput is one goal, but not the only one”，而最负面的评审明确要求不要只在 unstable regime 里画 throughput/latency。修订稿现在在 Section 6 用 arrival-rate curves 同时报告 mean end-to-end latency 与 effective completion rate，并明确用 \(\lambda^*\) 标出从 near-overloaded 到 overloaded 的 observed transition；Appendix H 又补了 threshold-without-waiting、A100 实机验证、重复实验波动、以及 prefill-decode disaggregated deployment。也就是说，实验已经从“只像系统论文的 benchmark 图”转成了“更像 queueing / OR 读者能解释的 operational evidence”。fileciteturn0file1 fileciteturn0file0 fileciteturn0file5

## 按严重性排序的剩余修改清单

- **最高优先级：统一 Nested WAIT 的 claim scope，避免任何比 Theorem 2 更强的口径。** 这是我认为唯一一个真正值得在投稿前一定修掉的点。回复信在 R1.1、D.6 等处对 Nested WAIT 的安全性是谨慎表述的：它依赖 segment-level thresholds 与 safety buffers，并在有限时域内给出 high-probability feasibility。可论文摘要第 1 页与贡献小节第 6 页还有偏强的表述，比如把两类算法一起写成 “prevent eviction under the stated memory conditions” 之类，这会让严谨型审稿人立刻抓住“正文口径 > 正式定理口径”。建议把这些地方统一改成：**WAIT 在已知输出长度下给 deterministic no-eviction / feasibility guarantee；Nested WAIT 在附加 buffer 下给 finite-horizon, high-probability no-overflow guarantee。** 这样就能和 Theorem 2（第 30–31 页）以及 Appendix E.4（第 73–74 页）完全对齐。fileciteturn0file0 fileciteturn0file5

- **较高优先级：在导言或贡献段再加一句，把“非平凡处在哪里”说得更硬一些。** 负面评审上轮最核心的理论质疑，不是说结果错，而是担心“开放系统里 stable throughput 本来就等于 arrival rate，剩下的可能只是 positive recurrence 的 routine consequence”。修订稿已经在主文第 23–24 页和第 29–31 页作了很大改善，但我仍建议在导言贡献段再补一刀：明确写出**非平凡对象不是 throughput identity 本身，而是 fluid equilibrium composition、memory requirement \(M^*(\lambda)\)、以及 how threshold control prevents endogenous memory growth from shrinking the stability region through eviction/restart**。一句话写透后，会进一步封住上轮这条攻击线。fileciteturn0file1 fileciteturn0file4 fileciteturn0file5

- **中等优先级：给 Appendix D 和 E 各加一个 proof roadmap / notation mini-table。** 虽然现在证明已经能查，但 Appendix D–E 仍然有不少符号需要在脑中来回切换，例如 \(R_j^\pi\)、\(\bar R_j^\pi\)、\(\bar W_b^{(j)}\)、\(V_r^{(k)}\)、\(I_k(T)\)、\(c_k\) 等。建议在 D 和 E 开头各放一个 6–8 行的小导览：每个符号是什么、是在 event-driven system 还是 comparison process 里、索引是 batch/review/segment/stage 中哪个。这样会显著降低 referee 的 proof-audit 成本。就当前版本而言，我认为“可检查”已经成立；这条修改属于让审稿人**更愿意检查**。fileciteturn0file5

- **中等优先级：把 main-text experiments 的关键设置再汇成一张总表。** 现在参数其实基本都有：Section 6 说明了 KV-cache cap、arrival-rate grid、replications、measurement window、\(t_l\) grid、segment design；Appendix H 又给了 GPU run 的具体设置。但这些信息分散在第 33–39 页和第 83–87 页，对想核对 reproducibility 的审稿人来说还是要来回翻。建议补一个总表，至少列出：workload、capacity/KV cap、baseline config、\(t_l\) 或 \(L\) 的搜索网格、最终选用规则、replication 数、measurement window。这样能进一步兑现回复信里“参数与可复现性已补全”的说法。fileciteturn0file3 fileciteturn0file0 fileciteturn0file5

- **较低优先级：回复信最好给出更精确的页码，而不仅是 section 指向。** 现在回复信整体已经专业，但若能在关键回答里把“改在 Section X”进一步改成“改在 Section X, pp. Y–Z；核心 lemma / theorem 在 Appendix D/E 的哪一页”，会更像成熟的 OR resubmission practice。尤其是 Theorem 1/2 proof rewrite、Section 6 图形重构、Appendix H A100 validation 这几处，给页码几乎是零成本增益。fileciteturn0file0

- **较低优先级：做一次最后的 copy edit。** 按我读到的 PDF 抽取文本，相关工作和附录里仍有少量 spacing / punctuation / citation-level 小瑕疵；如果这些不是抽取伪影而是源文件里真实存在，建议在提交前再通读一次。它们不会改变结论，但这轮修回最不该再让审稿人有“careless writing” 的观感。fileciteturn0file4 fileciteturn0file5

## 论文与回复信的一致性检查

我**没有发现除一个 claim-scope 问题之外的实质性 paper/letter 不一致**。回复信承诺的几项关键修改，在论文里都能找到对应落点：去掉误导性的 heavy-traffic narrative；把开放系统下的 throughput 故事改写成 stability region / effective throughput / latency / TTFT 的平衡；把 Section 6 改成 arrival-rate latency + completion-rate 的成对呈现；增加 A100 真实硬件校准与 end-to-end GPU validation；把附录重写成 theorem-specific proof modules。这些承诺和论文正文是对得上的。fileciteturn0file0 fileciteturn0file5

我看到的**唯一值得明确指出的不一致**是：回复信在 memory-safety 问题上对 Nested WAIT 说得相当谨慎，明确强调 unknown-output-length 情形依赖 safety buffer，并是 high-probability / finite-horizon 的保证；但论文摘要第 1 页和贡献段第 6 页个别句子仍把两类算法并列写成似乎都能“prevent eviction / overflow under the stated memory conditions”。而正式 theorem 只在 Theorem 2 里给出“no-overflow dynamics are feasible … with probability at least \(1-\delta\) over horizon \([0,T]\)”的口径，并在 Appendix E.4 用有限时域的 boundary-buffer 分析来支持它。这个张力不大，但确实足够让细致审稿人挑出来。fileciteturn0file0 fileciteturn0file5

## 会影响重投观感的语言与行文问题

主文的语言与结构，**已经达到了“可送审”的水平**。AE 上轮最看重的是 exposition overhaul，而修订稿现在确实做到了：Section 2 先机制后模型，Section 4–5 先 example / intuition 再 algorithm / theorem，Figure captions 也不再只是图名，而是能告诉读者每幅图要怎么看。尤其是 Section 6 的图文关系，比原稿更符合 OR/MS 读者阅读习惯。fileciteturn0file4 fileciteturn0file5

但从“已经能投”到“更像一篇会让审稿人先入为主给 benefit of the doubt 的稿子”，还差最后一点**语义压缩与术语显性化**。我会建议在导言某处更直接地写出：这篇论文研究的是一个 **open stochastic service system with endogenous KV-cache memory growth**；这样会比现在主要通过上下文让读者自己归纳，更利于 OPRE/MS 审稿人迅速定位文章。另一个可改善点是，附录中凡是从 comparison process 切回 actual policy 的地方，尽量用一句非常短的“this is what the reviewer needs to verify”式提示句，这会进一步增强 proof narrative 的可读性。fileciteturn0file5

回复信本身的语言也总体合格：语气克制，不防御，不偷换概念；对“heavy traffic 用错”“open system throughput interpreted wrongly”“unstable latency comparisons need rework”这类会让作者尴尬的意见，也都选择了正面承认并实质修改，而不是只做措辞辩护。这个态度会给 AE 和审稿人留下好印象。唯一还能再提升的，是把 section-only references 改成 page-aware references。fileciteturn0file0

## 最终建议

**最终建议：submit after minor edits。** 我不会建议“submit as-is”，因为摘要/贡献段对 Nested WAIT 内存安全性的表述还有必要与 Theorem 2 统一，且附录 proof roadmap 与实验参数总表会明显降低下一轮的审稿摩擦；但我也**不认为还需要再做一轮实质性大修或重构**。如果作者按上面的高优先级与中优先级项目再打磨一次，这份修回包已经足以作为一份有竞争力的 OPRE/MS 风格 resubmission 进入下一轮评审。fileciteturn0file1 fileciteturn0file4 fileciteturn0file0 fileciteturn0file5