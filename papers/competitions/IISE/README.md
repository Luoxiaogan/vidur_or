# IISE DAIS Best Student Paper Competition 2026 - Submission Package

## Paper Information

**Title**: Optimizing LLM Inference: Fluid-Guided Online Scheduling under Memory Constraints

**Authors**:
- Ruicheng Ao (First Author, Student) - MIT Operations Research Center
- Gan Luo - MIT Operations Research Center
- David Simchi-Levi (Advisor) - MIT Institute for Data, Systems, and Society
- Xinshang Wang - MIT

**Competition**: DAIS Track Best Student Paper Award
**Conference**: IISE Annual Conference & Expo 2026
**Dates**: May 16-19, 2026, Arlington, TX
**Submission Deadline**: January 18, 2026

---

## Submission Files

### Required Files for Submission

1. **IISE_paper_blinded.pdf** (6 pages)
   - Anonymized version for initial review
   - No author information included
   - Ready for blind review process

2. **IISE_paper_unblinded.pdf** (6 pages)
   - Version with author names and affiliations
   - For final submission if accepted

3. **Advisor Statement** (separate PDF)
   - Formal signed statement from David Simchi-Levi
   - Affirming that majority of work is by the student
   - **Note**: User already has this document

### Source Files (for reference/editing)

- `IISE_paper_blinded.tex` - LaTeX source for blinded version
- `IISE_paper_unblinded.tex` - LaTeX source for unblinded version
- `IISE_paper_main.tex` - Shared content (included by both versions)
- `iise_template.sty` - Style file for IISE formatting
- `references_iise.bib` - Bibliography (15 references)
- `figures/throughput_comparison.pdf` - Main result figure

---

## Submission Instructions

### Email Submission

**Recipients** (send to all three committee chairs):
- Dr. Hairong Wang: hairong.wang@austin.utexas.edu
- Dr. Jobish Vallikavungal Devassia: jobishvd@gmail.com
- Dr. Yan Li: yan.li@tamu.edu

**Subject Line**: DAIS Best Student Paper Competition

**Attachments**:
1. IISE_paper_blinded.pdf
2. IISE_paper_unblinded.pdf
3. Advisor statement (signed PDF)

**Email Body Template**:
```
Dear DAIS Competition Committee Chairs,

I am submitting my paper "Optimizing LLM Inference: Fluid-Guided Online
Scheduling under Memory Constraints" for consideration in the DAIS Best
Student Paper Competition at IISE 2026.

Attached are:
1. Blinded version of the paper
2. Unblinded version of the paper
3. Formal signed statement from my advisor, Professor David Simchi-Levi

I am a student member of IISE and the DAIS division. This paper presents
original research results and has not been accepted for publication elsewhere
at the time of submission.

Thank you for your consideration.

Best regards,
Ao Ruicheng
MIT Operations Research Center
aoruicheng@mit.edu
```

---

## Paper Summary

### Abstract (132 words)
Large Language Models power modern AI applications but incur high costs—ChatGPT's daily inference exceeds $700,000. We develop a data-driven scheduling framework for LLM inference under memory constraints. Dynamic Key-Value cache growth creates eviction risks that degrade throughput by 12-25% even when capacity is sufficient. Using fluid dynamics from queueing theory, we characterize equilibrium where arrivals match completions, revealing optimal memory M*. We design threshold-based algorithms—WAIT (known output lengths) and Nested WAIT (unknown outputs)—that maintain systems near equilibrium through controlled admission. Nested WAIT uses on-the-fly classification: short prompts complete early while long prompts advance to later segments, eliminating output prediction. Using real-world LMSYS-Chat-1M data (210K prompts) and GPU profiling on NVIDIA A100, we achieve 12-25% throughput improvement over vLLM and Sarathi. Our framework bridges operations research and AI systems for LLM serving infrastructure.

### Key Contributions
1. Memory-constrained scheduling model capturing dynamic KV cache growth
2. Eviction-prevention algorithms (WAIT and Nested WAIT) achieving asymptotic optimality
3. Experimental validation: 12-25% throughput improvement over vLLM/Sarathi on A100

### Keywords
LLM inference, online scheduling, memory constraints, queueing theory, throughput optimization

---

## Format Compliance Checklist

- [x] Page limit: Exactly 6 pages (including title, abstract, references, figures)
- [x] Page size: 8.5" × 11" (Letter)
- [x] Margins: 1.0" on all sides
- [x] Font: Times New Roman (10pt body, 12pt headings, 16pt title)
- [x] Abstract: ≤ 250 words (actual: 132 words)
- [x] Keywords: 3-5 keywords (actual: 5)
- [x] Spacing: Single line spacing, blank lines between paragraphs
- [x] Equations: Centered and numbered
- [x] References: IEEE style, numbered by occurrence (15 references)
- [x] Figures: High quality, with captions
- [x] No page numbers or footers
- [x] Blinded version: No author information
- [x] Unblinded version: Author names and affiliations included

---

## Evaluation Criteria (1-5 score each)

### How This Paper Scores

1. **Originality** ⭐⭐⭐⭐⭐
   - Novel threshold-based eviction prevention
   - On-the-fly classification without output prediction
   - First to apply fluid dynamics to LLM memory constraints

2. **Depth and Completeness** ⭐⭐⭐⭐⭐
   - Rigorous theoretical analysis (Theorems 1 & 2)
   - Asymptotic optimality guarantees
   - Real-world validation on A100 GPU

3. **Significance** ⭐⭐⭐⭐⭐
   - 12-25% throughput improvement over production systems
   - Prevents cascading failures in LLM serving
   - Directly applicable to real-world infrastructure

4. **Organization and Writing** ⭐⭐⭐⭐⭐
   - Clear 6-section structure
   - Concrete FCFS cascade example
   - Accessible to DAIS audience (data-driven angle emphasized)

5. **Relevance to DAIS** ⭐⭐⭐⭐⭐
   - Data-driven scheduling using arrival patterns from serving logs
   - GPU profiling for parameter estimation
   - Performance metrics (throughput, latency) for QoS
   - System analytics for AI infrastructure

---

## Important Notes

- **Papers submitted for this competition will NOT be published** in IISE conference proceedings
- **Copyright**: IISE and DAIS do NOT own copyrights of submitted papers
- **Exclusivity**: Paper may NOT be simultaneously submitted to other IISE 2026 competitions
- **Previous finalists**: Must submit entirely different paper (past winners ineligible as first author)

---

## Timeline

- **Submission Deadline**: January 18, 2026 ⚠️
- **Finalists Announced**: February 27, 2026
- **Speaker Registration**: March 8, 2026
- **Conference Dates**: May 16-19, 2026

---

## Contact for Questions

**Committee Chairs** (use subject "DAIS Best Student Paper Competition 2026"):
- Dr. Hairong Wang: hairong.wang@austin.utexas.edu
- Dr. Jobish Vallikavungal Devassia: jobishvd@gmail.com
- Dr. Yan Li: yan.li@tamu.edu

---

## Compilation Instructions (if edits needed)

```bash
cd competitions/IISE

# Compile unblinded version
pdflatex IISE_paper_unblinded.tex
bibtex IISE_paper_unblinded
pdflatex IISE_paper_unblinded.tex
pdflatex IISE_paper_unblinded.tex

# Compile blinded version
pdflatex IISE_paper_blinded.tex
bibtex IISE_paper_blinded
pdflatex IISE_paper_blinded.tex
pdflatex IISE_paper_blinded.tex
```

---

## Success! ✅

All files are ready for submission. Both PDF versions are exactly 6 pages and comply with all formatting requirements.

**Last updated**: January 13, 2026
