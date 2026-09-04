# PR #22: Statistical Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a pure, isolated inferential statistics package (`application/evaluation/statistics/`) providing paired Wilcoxon signed-rank testing, Benjamini–Hochberg FDR multiple testing adjustment, and paired bootstrap confidence intervals, verified against the frozen empirical power analysis.

**Architecture:** Pure decoupled mathematical functions in `application/evaluation/statistics/` that receive pre-computed numerical arrays and produce explicit, typed statistical outcome models. The package has zero dependencies on `matching`, `policies`, `infrastructure`, or provider SDKs.

**Tech Stack:** Python 3.12 / NumPy / SciPy / Pydantic v2 / pytest.

## Global Constraints
- Zero dependencies on `domain.models.matching`, `application.matching`, `infrastructure`, or external provider SDKs.
- Clean Architecture layer isolation: all code resides in `application/evaluation/statistics/` with pure domain/application contracts.
- Deterministic seeding on all stochastic procedures (RNG explicitly injected or seeded).
- Fail-fast validation on all inputs (length mismatch, NaNs, non-finite numbers, invalid alpha).
- Do not modify existing power analysis parameters or rerun simulation grids; validate coherence against the frozen artifact `data/experiments/power_analysis_wilcoxon.json`.
- Keep test surface lean: ~15-20 high-value tests covering core mathematical properties, invalid inputs, edge cases, and numerical correctness.

---

### Task 1: Record ADR 0010 (Inferential Statistical Testing Framework)

**Files:**
- Create: `docs/adr/0010-inferential-statistical-testing-framework.md`

**Interfaces:**
- Documents the architectural and mathematical contract for inferential statistics in Nexus evaluation:
  - Paired Wilcoxon Signed-Rank (`zero_method="wilcox"`, two-sided/one-sided).
  - Benjamini–Hochberg FDR controlling procedure with step-up monotonicity.
  - Paired demand-level bootstrap CI preserving covariance between comparative runs.
  - Zero coupling between statistical primitives and ranking/matching mechanisms.

- [ ] **Step 1: Draft ADR 0010 document**
- [ ] **Step 2: Verify ADR formatting and cross-references with ADR 0006 and ADR 0007**
- [ ] **Step 3: Commit ADR 0010**

---

### Task 2: Define Typed Statistical Outcome Models & Resampling Primitive

**Files:**
- Create: `backend/src/main/application/evaluation/statistics/__init__.py`
- Create: `backend/src/main/application/evaluation/statistics/types.py`
- Create: `backend/src/main/application/evaluation/statistics/resampling.py`
- Test: `backend/test/unit/application/evaluation/test_statistical_testing.py`

**Interfaces:**
- Produces:
  - `WilcoxonResult`: `statistic: float`, `p_value: float`, `n_pairs: int`, `n_nonzero: int`, `alternative: str`
  - `BenjaminiHochbergResult`: `p_values: list[float]`, `adjusted_p_values: list[float]`, `rejected: list[bool]`, `alpha: float`, `n_hypotheses: int`, `n_rejected: int`
  - `BootstrapCIResult`: `estimate: float`, `ci_lower: float`, `ci_upper: float`, `n_bootstrap: int`, `confidence_level: float`, `seed: int | None`
  - `paired_resample(values_a, values_b, rng)`: draws synchronized bootstrap index pairs

- [ ] **Step 1: Write tests for types and `paired_resample`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `types.py` and `resampling.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 3: Implement Paired Wilcoxon Signed-Rank Test

**Files:**
- Create: `backend/src/main/application/evaluation/statistics/wilcoxon.py`
- Modify: `backend/test/unit/application/evaluation/test_statistical_testing.py`

**Interfaces:**
- Produces:
  - `paired_wilcoxon_test(baseline: Sequence[float], treatment: Sequence[float], alternative: str = "two-sided", zero_method: str = "wilcox") -> WilcoxonResult`
- Invariants:
  - Validates `len(baseline) == len(treatment)` (raises `ValueError` if mismatch).
  - Validates all values are finite (`np.isfinite`, raises `ValueError` on NaN / Inf).
  - Validates `len(baseline) >= 1` (raises `ValueError` on empty input).
  - Validates `alternative` in `("two-sided", "greater", "less")`.
  - Exact ties handling: when all deltas are zero (`n_nonzero == 0`), returns deterministic `statistic=0.0, p_value=1.0`.
  - Non-zero deltas: uses `scipy.stats.wilcoxon` with `zero_method=zero_method`.

- [ ] **Step 1: Write failing unit tests for `paired_wilcoxon_test`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `paired_wilcoxon_test`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 4: Implement Benjamini–Hochberg FDR Adjustment

**Files:**
- Create: `backend/src/main/application/evaluation/statistics/multiple_testing.py`
- Modify: `backend/test/unit/application/evaluation/test_statistical_testing.py`

**Interfaces:**
- Produces:
  - `adjust_benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> BenjaminiHochbergResult`
- Invariants:
  - Validates `0.0 < alpha < 1.0` and all `p_values` in `[0.0, 1.0]` (raises `ValueError` otherwise).
  - Output q-values bounded in `[0.0, 1.0]`.
  - Monotonicity: enforced via cumulative minimum from right to left on sorted p-values.
  - Input-order preserving: the returned `adjusted_p_values` and `rejected` match the original input array indexing.
  - Boundary cases: empty input returns empty result; single p-value returns `q = p`.

- [ ] **Step 1: Write failing unit tests for `adjust_benjamini_hochberg`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `adjust_benjamini_hochberg`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 5: Implement Paired Bootstrap Confidence Intervals

**Files:**
- Create: `backend/src/main/application/evaluation/statistics/bootstrap.py`
- Modify: `backend/test/unit/application/evaluation/test_statistical_testing.py`

**Interfaces:**
- Produces:
  - `paired_bootstrap_ci(baseline: Sequence[float], treatment: Sequence[float], n_bootstrap: int = 10_000, confidence_level: float = 0.95, seed: int | None = 42) -> BootstrapCIResult`
- Invariants:
  - Statistical unit is the paired demand: draws identical row indices for baseline and treatment.
  - Point estimate: `np.mean(treatment) - np.mean(baseline)`.
  - Percentile bootstrap CI: `[percentile(alpha/2), percentile(1 - alpha/2)]`.
  - Validates `len(baseline) == len(treatment) >= 2`.
  - Validates `0.0 < confidence_level < 1.0`, `n_bootstrap >= 100`.
  - Strictly deterministic when `seed` is provided.

- [ ] **Step 1: Write failing unit tests for `paired_bootstrap_ci`**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `paired_bootstrap_ci`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 6: Add Power Analysis Coherence & Invariant Tests

**Files:**
- Create: `backend/test/unit/application/evaluation/test_power_analysis_coherence.py`

**Interfaces:**
- Verifies:
  - Coherence with frozen `data/experiments/power_analysis_wilcoxon.json`.
  - For target standardized effect $\theta = 0.20$, pre-registered minimum sample size $N_{\min} = 60$.
  - For target standardized effect $\theta \ge 0.50$, pre-registered minimum sample size is at floor $N_{\min} = 15$.
  - Power curve monotonicity across candidate sample sizes for each effect size.
  - Architecture isolation: `application/evaluation/statistics` has zero imports from `matching`, `infrastructure`, or `policies`.

- [ ] **Step 1: Write power analysis coherence and architecture boundary tests**
- [ ] **Step 2: Run tests to verify they pass against frozen artifact**
- [ ] **Step 3: Commit**

---

### Task 7: Verification & Quality Gate Check

- [ ] **Step 1: Run Architecture Quality Gate**
- [ ] **Step 2: Run Static Code Analysis & Type Checking**
- [ ] **Step 3: Run Full Test Suite with Coverage**
- [ ] **Step 4: Push branch and create PR #22**
- [ ] **Step 5: Monitor CI until 100% green**
