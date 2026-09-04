# ADR 0010: Inferential Statistical Testing Framework for Comparative Benchmark Validation

**Status:** Proposed  
**Date:** 2026-09-04  
**Scope:** `application/evaluation/statistics/` (`wilcoxon.py`, `multiple_testing.py`, `bootstrap.py`, `resampling.py`, `types.py`), `backend/test/unit/application/evaluation/`  

---

## Context

Under ADR 0006 (Scientific Validation Dataset, Schema, and Evaluation Provenance) and ADR 0007 (Scientific Evaluation Protocol and Metrics for Matching Validation), Nexus establishes a sealed, reproducible benchmark environment that computes deterministic descriptive ranking metrics (such as MRR, nDCG@K, Judged@K, and UncertaintyRate) across target demands.

However, descriptive metrics alone cannot answer the core scientific question of Phase 2 validation:
> **Are observed differences between comparative system configurations (e.g., hybrid vs. single-signal baselines, ablation variants M0–M6) statistically defensible, and with what magnitude and uncertainty?**

To answer this question without introducing architectural coupling or statistical debt, the following invariants must be satisfied:

1. **Pure Decoupled Mathematics:** Inferential statistics must receive pre-computed numerical arrays and produce explicit, typed statistical outcome models. The statistical machinery must have zero knowledge of how those scores were generated: no dependencies on `matching`, `policies`, `datasets`, or external provider SDKs.
2. **Paired Demand-Level Testing:** The statistical unit is the **demand**, not individual patent observations. Performance metric differences across runs are paired:
   $$\Delta_i = M_{\text{treatment}}(d_i) - M_{\text{baseline}}(d_i)$$
   Tests and resampling procedures must strictly preserve the covariance between paired evaluations on the same demand.
3. **Exact Zero-Difference Handling in Non-Parametric Tests:** As specified in `docs/empirical-study-protocol.md §3.2`, paired differences are analyzed via the non-parametric Wilcoxon signed-rank test. In information retrieval benchmarks, identical performance on specific queries produces zero-differences ($\Delta_i = 0.0$). The standard treatment (`zero_method="wilcox"`) discards zero pairs from rank sums while tracking the total number of evaluated pairs $N_{\text{pairs}}$ versus non-zero pairs $N_{\text{nonzero}}$. When all differences are zero ($N_{\text{nonzero}} = 0$), the test must deterministically yield $p = 1.0$ rather than raising an uncaught exception.
4. **Multiple Comparisons Control:** When evaluating multiple ablation variants or metrics, family-wise error rate or False Discovery Rate (FDR) must be controlled. The Benjamini–Hochberg (BH) step-up procedure guarantees FDR control while distinguishing between adjusted $p$-values ($q$-values) and the binary hypothesis rejection decision ($q_i \le \alpha$).
5. **Reproducible Confidence Intervals:** Effect sizes must be accompanied by paired non-parametric bootstrap confidence intervals. Resampling must use a single shared index vector per bootstrap replication, ensuring that treatment and baseline are drawn from the exact same demand realizations.
6. **No Speculative Abstractions:** No `StatisticsEngine`, `StatisticsService`, factory, registry, or strategy abstraction. Only pure, auditable functions.

---

## Decision

We establish a dedicated, pure statistical testing module in `backend/src/main/application/evaluation/statistics/`.

### 1. Architectural Layout & Dependency Boundary

```text
application/evaluation/statistics/
├── __init__.py          # Clean explicit exports
├── types.py             # Typed dataclasses for statistical results
├── resampling.py        # Paired demand-level index resampling primitive
├── wilcoxon.py          # Paired Wilcoxon signed-rank test
├── multiple_testing.py  # Benjamini–Hochberg step-up FDR adjustment
└── bootstrap.py         # Paired bootstrap confidence interval estimation
```

**Dependency Graph Invariant:**
```text
types.py
   ↑
wilcoxon.py
multiple_testing.py
bootstrap.py
   ↑
resampling.py
```
* Dependencies are strictly internal to `application.evaluation.statistics` and standard numerical libraries (`numpy`, `scipy.stats`).
* ZERO imports from `matching`, `infrastructure`, `policies`, or provider SDKs.
* Protected by Import Linter contracts in `.importlinter`.

---

### 2. Mathematical Contracts & Behavioral Specifications

#### 2.1 Paired Wilcoxon Signed-Rank Test (`wilcoxon.py`)

* **Signature:**
  ```python
  def paired_wilcoxon_test(
      baseline: Sequence[float],
      treatment: Sequence[float],
      alternative: str = "two-sided",
      zero_method: str = "wilcox",
  ) -> WilcoxonResult:
  ```
* **Output Model (`WilcoxonResult`):**
  * `statistic: float`: The Wilcoxon test statistic ($W$).
  * `p_value: float`: The asymptotic or exact $p$-value.
  * `n_pairs: int`: Total number of valid paired observations ($N$).
  * `n_nonzero: int`: Total number of pairs with non-zero difference ($\Delta_i \neq 0$).
  * `alternative: str`: The hypothesis tested (`"two-sided"`, `"greater"`, `"less"`).
* **Invariants & Boundary Conditions:**
  * **Input Validation:** Fails fast (`ValueError`) if `len(baseline) != len(treatment)`, if `len(baseline) < 1`, if any element is non-finite (`NaN` or `Inf`), or if `alternative` is invalid.
  * **All-Ties Case:** If all differences are zero ($N_{\text{nonzero}} = 0$), returns `statistic = 0.0, p_value = 1.0, n_pairs = len(baseline), n_nonzero = 0`.
  * **Symmetry:** Testing `(treatment, baseline, alternative="greater")` produces the exact same $p$-value as `(baseline, treatment, alternative="less")`.

#### 2.2 Benjamini–Hochberg FDR Adjustment (`multiple_testing.py`)

* **Signature:**
  ```python
  def adjust_benjamini_hochberg(
      p_values: Sequence[float],
      alpha: float = 0.05,
  ) -> BenjaminiHochbergResult:
  ```
* **Output Model (`BenjaminiHochbergResult`):**
  * `p_values: list[float]`: Original unadjusted $p$-values.
  * `adjusted_p_values: list[float]`: Adjusted $q$-values.
  * `rejected: list[bool]`: Hypothesis rejection indicator ($q_i \le \alpha$).
  * `alpha: float`: Pre-specified FDR threshold ($0 < \alpha < 1$).
  * `n_hypotheses: int`: Number of tested hypotheses ($m$).
  * `n_rejected: int`: Number of rejected hypotheses.
* **Mathematical Invariants:**
  * **Step-up Monotonicity:** Let $p_{(1)} \le p_{(2)} \le \dots \le p_{(m)}$ be the sorted $p$-values. The raw step-up values are $q_{(i)}^{\text{raw}} = \frac{m}{i} p_{(i)}$. Monotonicity is strictly enforced from right to left:
    $$q_{(i)} = \min\left(1.0, \min_{j \ge i} q_{(j)}^{\text{raw}}\right)$$
  * **Input Order Alignment:** The returned `adjusted_p_values` and `rejected` lists map 1-to-1 to the order of the original input `p_values`.
  * **Boundary Cases:** For empty inputs, returns empty result lists ($m=0, n_{\text{rejected}}=0$). For a single hypothesis, $q_1 = p_1$.
  * **Domain:** Every $q_i \in [0.0, 1.0]$. $p_i = 0.0 \implies q_i = 0.0$; $p_i = 1.0 \implies q_i = 1.0$.

#### 2.3 Paired Bootstrap Confidence Interval (`bootstrap.py` & `resampling.py`)

* **Signature:**
  ```python
  def paired_bootstrap_ci(
      baseline: Sequence[float],
      treatment: Sequence[float],
      n_bootstrap: int = 10_000,
      confidence_level: float = 0.95,
      seed: int | None = 42,
  ) -> BootstrapCIResult:
  ```
* **Output Model (`BootstrapCIResult`):**
  * `estimate: float`: Point estimate on the empirical sample:
    $$\widehat{\theta} = \frac{1}{N} \sum_{i=1}^N (y_i - x_i)$$
  * `ci_lower: float`: Lower bound at percentile $\alpha_{\text{ci}} / 2$.
  * `ci_upper: float`: Upper bound at percentile $1 - \alpha_{\text{ci}} / 2$.
  * `n_bootstrap: int`: Replications performed ($B$).
  * `confidence_level: float`: Target confidence ($1 - \alpha_{\text{ci}}$).
  * `seed: int | None`: RNG seed used.
* **Resampling Invariant:**
  * In `resampling.py`, `paired_resample` draws **a single index vector**:
    ```python
    indices = rng.integers(0, n, size=n)
    sample_a = baseline[indices]
    sample_b = treatment[indices]
    ```
    This guarantees that paired demand correlation is strictly preserved across bootstrap draws.
  * Determinism: When `seed` is provided, output is strictly reproducible.

---

### 3. Coherence with Pre-Registered Power Analysis

PR #22 does not modify, recalibrate, or re-run the *a priori* power analysis simulation grid in `data/experiments/power_analysis_wilcoxon.json`. Instead, deterministic tests verify:
1. **Sample Size Consistency:** For medium effect $\theta = 0.20$, the minimum required sample size is $N_{\min} = 60$; for large effects $\theta \ge 0.50$, $N_{\min} = 15$ (the protocol floor).
2. **Empirical Monotonicity:** Macro statistical power increases from $N = 15$ to $N = 100$ under non-null effect sizes.

---

## Consequences

### Positive
* Enables rigorous inferential claims for Phase 2 validation and ablation comparisons.
* Independent mathematical primitives that can be audited and tested without setting up database stores or LLM endpoints.
* Zero architectural weight: no unnecessary classes, services, or factories.

### Negative
* Additional dependency on SciPy's Wilcoxon implementation within the evaluation subsystem.

---

## Enforcement & Verification

A PR is non-compliant and MUST NOT be merged if:
1. Statistical primitives import from `domain.models.matching`, `application.matching`, `infrastructure`, or provider SDKs.
2. `paired_resample` uses separate index vectors for baseline and treatment.
3. Wilcoxon does not report both `n_pairs` and `n_nonzero`.
4. Benjamini–Hochberg adjusted $p$-values violate monotonicity or fail to preserve the original input sequence alignment.
5. All tests in `backend/test/unit/application/evaluation/` fail to pass cleanly.
