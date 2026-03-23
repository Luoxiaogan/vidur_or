# Proof Corrections Summary

**Date**: 2025-01-28
**Reviewer**: Claude Code automated verification

---

## Issues Identified and Fixed

### 1. θ_k Lower Bound Denominator Mismatch (FIXED)

**File**: `unknown_type.tex` line 134

**Problem**: Main text had `n_k` in denominator, but derivation in `pf_lemmas.tex` (line 101) correctly shows `n_{k-1}`.

**Original**:
```latex
where $\theta_k \geq 8(n_k - n_{k-1}p_k)/n_k.$ Then:
```

**Fixed**:
```latex
where $\theta_k \geq 8(n_k - n_{k-1}p_{k-1})/n_{k-1}$ (with $p_0 = 1$). Then:
```

**Reasoning**: The lower bound derivation in Lemma (pf_lemmas.tex) uses Taylor expansion of the MGF condition, yielding denominator `n_{k-1}`, not `n_k`.

---

### 2. p_k Index Convention in Main Text (FIXED)

**File**: `unknown_type.tex` line 134

**Problem**: Used `n_{k-1}p_k` which mixes proof convention with main text convention.

**Main text definition** (line 111): `p_k = (Σ_{j=k+1}^m λ_j)/(Σ_{j=k}^m λ_j)` - continuation probability from segment k to k+1

**Original**: `n_{k-1}p_k`

**Fixed**: `n_{k-1}p_{k-1}` (with note that `p_0 = 1`)

**Reasoning**: Under main text convention, prompts entering segment k come from `n_{k-1} × p_{k-1}`, where p_{k-1} is the continuation probability from segment k-1.

---

### 3. Undefined LaTeX Reference (FIXED)

**File**: `pf_thm_wait.tex` line 74

**Problem**: Referenced `\ref{lemma::throughput gap}` but lemma is defined as `\ref{lemma::throughput gap, single}`.

**Original**:
```latex
By Lemma~\ref{lemma::throughput gap}:
```

**Fixed**:
```latex
By Lemma~\ref{lemma::throughput gap, single}:
```

---

## Issues Verified as Correct (No Change Needed)

### 4. p_k Definition in Proof Files

**Files**: `pf_thm_nested.tex`, `pf_thm_timevarying.tex`

**Observation**: Proof files use `p_k = (Σ_{j=k}^m λ_j)/(Σ_{j=k-1}^m λ_j)` which differs from main text.

**Conclusion**: This is **internally consistent** within the proofs. The proof convention represents "probability of arriving into segment k" while main text represents "probability of continuing from segment k". These are equivalent with shifted index: main_text_p_k = proof_p_{k+1}.

The mathematical derivations in the proofs are correct under their own convention.

---

### 5. FCFS Overflow Probability Calculation

**File**: `Appendix.tex` / `appendix_props_compressed.tex` (Proposition prop:lower_bound_FCFS)

**Observation**: Overflow probability calculation p ≈ 0.391 appears to be a rough approximation.

**Verification**:
- Non-overflow combinations: (0,0), (1,0), (0,1), (1,1), (2,0)
- Sum of probabilities: 1/e² + 1/e² + 1/e² + 1/e² + 1/(2e²) = 4.5/e² ≈ 0.609
- Overflow probability: 1 - 4.5/e² ≈ 0.391

**Conclusion**: The calculation is correct. The approximation serves the purpose of showing constant overflow probability.

---

### 6. λ_j vs n_j in pf_thm_wait.tex

**File**: `pf_thm_wait.tex` lines 74-75, 83-84

**Observation**: Uses `λ_j + √(λ_j B)` in zero drift case.

**Verification**: In zero drift case, `λ_j·ΔT = n_j`, so numerically these are consistent. The expression `λ_j + √(λ_j B)` follows from the single-type analysis where arrivals per batch are `Poisson(λ)` with `λ = n`.

**Conclusion**: No change needed. The expressions are correct under the zero-drift assumption.

---

## Files Modified

| File | Line | Change |
|------|------|--------|
| `unknown_type.tex` | 134 | θ_k denominator: n_k → n_{k-1}; p_k → p_{k-1} with note |
| `pf_thm_wait.tex` | 74 | Reference: throughput gap → throughput gap, single |
| `numerical.tex` | 13 | Converted \gan{...} comment to formal text |

---

## Recommendations for Future

1. **Consistent p_k notation**: Consider adding a remark in the proof appendix clarifying the index convention difference from main text.

2. **Cross-reference checks**: Run LaTeX with `-interaction=nonstopmode` to catch undefined references.

3. **Symbol verification**: Verify all θ_k bounds against their derivations in lemmas.
