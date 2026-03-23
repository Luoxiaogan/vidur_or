# AI痕迹与Typo审查报告

本报告根据`claude.md`中的规范，对论文的各个部分进行了审查。审查重点是识别潜在的AI生成痕迹、不自然的语言、重复性短语以及拼写和格式错误（typo）。

---

## 总体性建议

- **重复的“关键洞见” (Key Insight)**: “The key insight is...” 或类似变体 (e.g., "The central insight is...", "This last point reflects a key insight:", "The proof relies on a key observation:") 在 `introduction.tex`, `known_type.tex`, `extension.tex` 和 `conclusion.tex` 中反复出现。这是非常典型的AI写作模式，建议替换为更多样化的表达，或直接陈述观点。
- **结论部分的陈词滥调**: `conclusion.tex` 中大量使用了学术八股文式的短语，如 "important avenue for future research", "promising direction for future research", "poses a significant challenge"。建议使用更具体、更真诚的语言来描述未来工作。

---

## 各文件具体问题

### `abstract.tex`

- **轻微AI痕迹**:
  - **原文**: "This work bridges operations research and machine learning, providing a theoretically grounded framework for LLM deployment under memory constraints."
  - **问题**: "bridges X and Y" 和 "theoretically grounded framework" 是常见的AI用语，虽然可接受，但略显俗套。
  - **建议**: 可以考虑更直接的陈述，例如 "This work applies operations research principles to establish a theoretical framework for..."

### `introduction.tex`

- **AI化词语**:
  - **原文**: "Large Language Models (LLMs) are **indispensable** in natural language processing (NLP)..."
  - **问题**: "Indispensable" (不可或缺的) 是一个很强的词，经常被AI滥用。
  - **建议**: 替换为 "fundamental to" 或 "have become essential in"。

- **模板化句子**:
  - **原文**: "However, these traditional approaches **fall short in addressing the unique dynamics** of LLM inference."
  - **问题**: "fall short in addressing" 和 "unique dynamics" 是非常典型的AI短语组合。
  - **建议**: 改为更具体的描述，例如 "However, these traditional approaches do not account for key features of LLM inference, such as..."

- **Typo / 格式问题**:
  - 在 `\subsection{Other Related Work}` 之后有一个多余的 `\subsection{Notations}` 标题。符号表和对应的标题在 `model.tex` 中。应删除此处的标题。

### `model.tex`

- **AI化词语**:
  - **原文**: "...our algorithms can **generalize naturally** to this setting as well."
  - **问题**: "generalize naturally" (自然地泛化) 有点含糊不清，是AI常用的说法。
  - **建议**: 改为 "can be directly extended to this setting"。

- **Typo**:
  - **原文**: "...using batches consisting of different number of tokens with **20 repeats**."
  - **问题**: "repeats" 用词不当。
  - **建议**: 改为 "with 20 repetitions" 或 "repeated 20 times"。

### `fluid.tex`

- **用词不当**:
  - **原文**: "...before **completely understanding** such asymptotic regime."
  - **问题**: "completely understanding" 在学术论文中略显口语化。
  - **建议**: 改为 "pending a complete characterization of such an asymptotic regime." 

- **引用标签不匹配**:
  - **原文**: "Detailed proofs of this result are provided in Appendix `\ref{appendix::proof of fluid lower bound}`."
  - **问题**: 在 `Appendix.tex` 中，对应的标签是 `\label{appendix:proof_large_rate}`。两个标签不一致，会导致引用错误。
  - **建议**: 将文中的引用改为 `\ref{appendix:proof_large_rate}`。

### `known_type.tex` (Section 4)

- **AI化词语**:
  - **原文**: "**Leveraging** the fluid dynamics established in Section \ref{sec:fluid}..."
  - **问题**: "Leveraging" 是AI最爱用的词之一。
  - **建议**: 改为 "Using the fluid dynamics..." 或 "Based on the fluid dynamics..."

- **禁用词**:
  - **原文**: "**Crucially**, KV caches for waiting prompts are preserved..."
  - **问题**: `claude.md` 中明确指出要避免使用 "Crucially"。
  - **建议**: 直接删除 "Crucially,"。

- **格式Typo**:
  - **原文**: `\subsection{Asymptotic Analysis}`
  - **问题**: 该小节标题没有像同级别的其他标题（如 `\subsection{The WAIT Algorithm}`）一样使用首字母大写 (Title Case)。应统一为 `\subsection{Asymptotic Analysis}`。

- **数学格式Typo**:
  - **原文**: `\ex{}{\Latency^{(\zeta,\pi)}},\,\ex{}{\TTFT^{(\zeta,\pi)}}`
  - **问题**: `\Latency` 和 `\ex` 之间的逗号 `,\` 产生了一个不必要的额外间距，格式上不美观。
  - **建议**: 将逗号放在第一个数学环境之外，或者直接用普通逗号: `$\ex{}{\Latency^{(\zeta,\pi)}}$, $\ex{}{\TTFT^{(\zeta,\pi)}}$`。

### `unknown_type.tex` (Section 5)

- **严重文件问题**:
  - **原文**: "...achieving high utilization while respecting decode-stage he... **[truncated]**"
  - **问题**: 文件内容在句子中间被截断，并包含了 "[truncated]" 字符串。这是一个严重的文件损坏或复制粘贴错误，必须修复。

- **AI化表达**:
  - **原文**: "This dilemma---optimism leads to eviction, pessimism wastes capacity---**motivates our algorithm design principles**"
  - **问题**: "motivates our..." 是 `claude.md` 中建议警惕的短语。
  - **建议**: 改为 "This dilemma leads to our design principles:"。

  - **原文**: "There are **three notable observations** :"
  - **问题**: 这是AI组织列表时非常常见的引出方式。
  - **建议**: 可以直接开始陈述，或使用 "We make three main observations:"。

### `numerical.tex` (Section 6)

- **AI化表达**:
  - **原文**: "We present a **comprehensive evaluation** of our (Nested) WAIT algorithm..."
  - **问题**: "comprehensive evaluation" 是实验章节典型的AI式开场白。
  - **建议**: 改为 "We evaluate our (Nested) WAIT algorithm..."

  - **原文**: "This improvement **stems from** WAIT's ability to..."
  - **问题**: "stems from" 是AI解释原因时常用的短语。
  - **建议**: 改为 "This improvement is due to..."。

  - **原文**: "...remains within acceptable limits, **highlighting** WAIT's balance between efficiency and responsiveness."
  - **问题**: 用 "highlighting" 来引出结论是非常典型的AI风格。
  - **建议**: 直接陈述结果，例如 "...and latency remains within acceptable limits. This indicates a good balance..."。

- **引用错误**:
  - **原文**: "More discussions on this segment design are left in **Appendix \ref{sec:extension}**."
  - **问题**: `extension.tex` 对应的是 Section 7，而不是一个附录 (Appendix)。这是一个错误的交叉引用。
  - **建议**: 改为 "in Section \ref{sec:extension}"。

- **表达不清**:
  - **原文**: "The designed thresholds are on time-varying arrival rate but with static threshold, which leads to a little bit more latency."
  - **问题**: 句子结构混乱，"on... but with..." 难以理解。
  - **建议**: 重新组织句子，例如 "The thresholds, designed for static arrival rates, were applied to a time-varying scenario, which resulted in slightly higher latency." 

### `extension.tex` (Section 7)

- **AI化表达**:
  - **原文**: "...the performance of Nested WAIT is **guaranteed by**:"
  - **问题**: "guaranteed by" (被...保证) 语气过强。
  - **建议**: 改为 "is given by" 或 "satisfies"。

- **用词不当**:
  - **原文**: "...moderate segment number can reduce **waste of memory usage**."
  - **问题**: "waste of memory usage" 表达有点奇怪。
  - **建议**: 改为 "reduce memory waste" 或 "improve memory utilization"。

### `conclusion.tex` (Section 8)

- **AI化陈词滥调**:
  - **原文**: "...is an **important avenue for future research**."
  - **问题**: 非常老套的学术八股文。
  - **建议**: 描述更具体的研究问题。

  - **原文**: "...presents a **promising direction for future research**."
  - **问题**: 同上。
  - **建议**: 同上。

  - **原文**: "...**poses a significant challenge**, which we plan to investigate further."
  - **问题**: 同上。
  - **建议**: 同上。