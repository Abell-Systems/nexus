"""Unit tests for pure inferential statistical primitives under ADR 0010."""

import numpy as np
import pytest
from scipy.stats import wilcoxon

from application.evaluation.statistics import (
    BenjaminiHochbergResult,
    BootstrapCIResult,
    WilcoxonResult,
    adjust_benjamini_hochberg,
    paired_bootstrap_ci,
    paired_resample,
    paired_wilcoxon_test,
)

# ---------------------------------------------------------------------------
# Resampling Primitives
# ---------------------------------------------------------------------------


def test_paired_resample_preserves_pairing_and_covariance():
    """Verify that paired_resample samples baseline and treatment with identical row indices."""
    baseline = [10.0, 20.0, 30.0, 40.0, 50.0]
    treatment = [11.0, 21.0, 31.0, 41.0, 51.0]  # perfect delta = 1.0 for every pair
    rng = np.random.default_rng(123)

    sample_b, sample_t = paired_resample(baseline, treatment, rng)

    assert len(sample_b) == len(baseline)
    assert len(sample_t) == len(treatment)
    # Every resampled pair must maintain treatment - baseline == 1.0
    deltas = sample_t - sample_b
    np.testing.assert_allclose(deltas, 1.0)


def test_paired_resample_validations():
    """Verify fail-fast on length mismatch and empty sequences."""
    rng = np.random.default_rng(42)
    with pytest.raises(ValueError, match="Length mismatch"):
        paired_resample([1.0, 2.0], [1.0], rng)

    with pytest.raises(ValueError, match="empty sequences"):
        paired_resample([], [], rng)


def test_paired_resample_determinism():
    """Verify byte-exact reproducibility with identical seed."""
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    t = [1.5, 2.5, 3.2, 4.8, 5.1, 6.9]

    b1, t1 = paired_resample(b, t, np.random.default_rng(999))
    b2, t2 = paired_resample(b, t, np.random.default_rng(999))

    np.testing.assert_array_equal(b1, b2)
    np.testing.assert_array_equal(t1, t2)


# ---------------------------------------------------------------------------
# Paired Wilcoxon Signed-Rank Test
# ---------------------------------------------------------------------------


def test_paired_wilcoxon_standard_conformance_with_scipy():
    """Verify numerical equivalence with direct scipy.stats.wilcoxon call."""
    baseline = [0.45, 0.52, 0.61, 0.70, 0.33, 0.82, 0.59, 0.65]
    treatment = [0.55, 0.60, 0.63, 0.81, 0.39, 0.88, 0.62, 0.72]

    expected = wilcoxon(treatment, baseline, alternative="two-sided", zero_method="wilcox")
    res = paired_wilcoxon_test(baseline, treatment, alternative="two-sided")

    assert isinstance(res, WilcoxonResult)
    assert res.statistic == pytest.approx(float(expected.statistic))
    assert res.p_value == pytest.approx(float(expected.pvalue))
    assert res.n_pairs == 8
    assert res.n_nonzero == 8
    assert res.alternative == "two-sided"


def test_paired_wilcoxon_symmetry():
    """Verify directional symmetry between 'greater' and 'less' alternatives."""
    baseline = [0.20, 0.30, 0.40, 0.50, 0.60]
    treatment = [0.35, 0.45, 0.38, 0.65, 0.72]

    res_greater = paired_wilcoxon_test(baseline, treatment, alternative="greater")
    res_less = paired_wilcoxon_test(treatment, baseline, alternative="less")

    assert res_greater.p_value == pytest.approx(res_less.p_value)
    assert res_greater.n_pairs == res_less.n_pairs


def test_paired_wilcoxon_exact_ties_all_zero():
    """When all paired differences are 0.0, returns statistic=0.0, p_value=1.0 deterministically."""
    baseline = [0.50, 0.60, 0.70, 0.80]
    treatment = [0.50, 0.60, 0.70, 0.80]

    res = paired_wilcoxon_test(baseline, treatment)
    assert res.statistic == 0.0
    assert res.p_value == 1.0
    assert res.n_pairs == 4
    assert res.n_nonzero == 0


def test_paired_wilcoxon_partial_ties_tracking():
    """Verify n_pairs and n_nonzero distinguish total versus non-tied pairs."""
    baseline = [0.50, 0.60, 0.70, 0.80, 0.90]
    treatment = [0.55, 0.60, 0.75, 0.80, 0.95]  # indices 1 and 3 are exact ties

    res = paired_wilcoxon_test(baseline, treatment)
    assert res.n_pairs == 5
    assert res.n_nonzero == 3
    assert res.p_value > 0.0


def test_paired_wilcoxon_validations():
    """Verify fail-fast on mismatched length, non-finite values, and invalid alternative."""
    with pytest.raises(ValueError, match="Length mismatch"):
        paired_wilcoxon_test([1.0, 2.0], [1.0])

    with pytest.raises(ValueError, match="empty sequences"):
        paired_wilcoxon_test([], [])

    with pytest.raises(ValueError, match="non-finite"):
        paired_wilcoxon_test([1.0, np.nan], [2.0, 3.0])

    with pytest.raises(ValueError, match="non-finite"):
        paired_wilcoxon_test([1.0, 2.0], [np.inf, 3.0])

    with pytest.raises(ValueError, match="Invalid alternative"):
        paired_wilcoxon_test([1.0, 2.0], [2.0, 3.0], alternative="invalid")


# ---------------------------------------------------------------------------
# Benjamini-Hochberg FDR Adjustment
# ---------------------------------------------------------------------------


def test_benjamini_hochberg_standard_benchmark_values():
    """Verify against standard textbook Benjamini-Hochberg calculations.

    P-values: [0.01, 0.04, 0.03, 0.20], m=4, alpha=0.05
    Sorted:   [0.01, 0.03, 0.04, 0.20]
    Ranks:    1,     2,     3,     4
    Raw q:    0.04,  0.06,  0.0533, 0.20
    Cummin q: 0.04,  0.0533, 0.0533, 0.20
    Re-ordered to original indices: [0.04, 0.0533, 0.0533, 0.20]
    """
    p_vals = [0.01, 0.04, 0.03, 0.20]
    res = adjust_benjamini_hochberg(p_vals, alpha=0.05)

    assert isinstance(res, BenjaminiHochbergResult)
    assert res.n_hypotheses == 4
    assert res.alpha == 0.05

    expected_q = [0.04, 0.04 * (4.0 / 3.0), 0.04 * (4.0 / 3.0), 0.20]
    np.testing.assert_allclose(res.adjusted_p_values, expected_q, rtol=1e-4)
    assert res.rejected == [True, False, False, False]
    assert res.n_rejected == 1


def test_benjamini_hochberg_step_up_monotonicity():
    """Verify step-up monotonicity: when sorted by p-value, q-values never decrease."""
    p_vals = [0.005, 0.045, 0.02, 0.035, 0.08, 0.06]
    res = adjust_benjamini_hochberg(p_vals, alpha=0.05)

    sorted_indices = np.argsort(p_vals)
    sorted_q = [res.adjusted_p_values[i] for i in sorted_indices]

    for i in range(len(sorted_q) - 1):
        assert sorted_q[i] <= sorted_q[i + 1] + 1e-9


def test_benjamini_hochberg_preserves_input_order():
    """Verify that the original ordering of hypotheses is strictly preserved."""
    p_vals = [0.90, 0.0005, 0.40, 0.002]
    res = adjust_benjamini_hochberg(p_vals, alpha=0.05)

    # Lowest p-value was at index 1 -> must have lowest q-value at index 1
    assert res.adjusted_p_values[1] < res.adjusted_p_values[3]
    assert res.adjusted_p_values[3] < res.adjusted_p_values[2]
    assert res.adjusted_p_values[2] < res.adjusted_p_values[0]
    assert res.rejected[1] is True
    assert res.rejected[3] is True
    assert res.rejected[0] is False


def test_benjamini_hochberg_boundary_cases():
    """Verify behavior for empty lists, single p-value, p=0, and p=1."""
    # Empty
    res_empty = adjust_benjamini_hochberg([], alpha=0.05)
    assert res_empty.n_hypotheses == 0
    assert res_empty.adjusted_p_values == []
    assert res_empty.rejected == []

    # Single p-value
    res_single = adjust_benjamini_hochberg([0.03], alpha=0.05)
    assert res_single.adjusted_p_values == [0.03]
    assert res_single.rejected == [True]

    # Extreme p-values
    res_extremes = adjust_benjamini_hochberg([0.0, 1.0], alpha=0.05)
    assert res_extremes.adjusted_p_values == [0.0, 1.0]
    assert res_extremes.rejected == [True, False]


def test_benjamini_hochberg_validations():
    """Verify fail-fast on invalid alpha, out-of-bound p-values, or non-finite values."""
    with pytest.raises(ValueError, match="alpha"):
        adjust_benjamini_hochberg([0.05], alpha=0.0)

    with pytest.raises(ValueError, match="alpha"):
        adjust_benjamini_hochberg([0.05], alpha=1.0)

    with pytest.raises(ValueError, match="bounded in"):
        adjust_benjamini_hochberg([-0.1, 0.5])

    with pytest.raises(ValueError, match="bounded in"):
        adjust_benjamini_hochberg([0.5, 1.1])

    with pytest.raises(ValueError, match="non-finite"):
        adjust_benjamini_hochberg([0.05, np.nan])


# ---------------------------------------------------------------------------
# Paired Bootstrap Confidence Intervals
# ---------------------------------------------------------------------------


def test_paired_bootstrap_ci_deterministic_reproducibility():
    """Verify that a fixed seed produces byte-identical bootstrap intervals."""
    b = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    t = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    res1 = paired_bootstrap_ci(b, t, n_bootstrap=1000, seed=42)
    res2 = paired_bootstrap_ci(b, t, n_bootstrap=1000, seed=42)

    assert isinstance(res1, BootstrapCIResult)
    assert res1.estimate == res2.estimate == 0.1
    assert res1.ci_lower == res2.ci_lower
    assert res1.ci_upper == res2.ci_upper


def test_paired_bootstrap_ci_contains_point_estimate():
    """Verify confidence interval bounds surround the empirical point estimate."""
    rng = np.random.default_rng(101)
    baseline = rng.uniform(0.3, 0.7, size=50)
    treatment = baseline + rng.normal(0.08, 0.03, size=50)

    res = paired_bootstrap_ci(baseline, treatment, n_bootstrap=2000, confidence_level=0.95, seed=42)

    assert res.ci_lower <= res.estimate <= res.ci_upper
    assert res.ci_lower > 0.0  # Significant positive effect


def test_paired_bootstrap_ci_validations():
    """Verify fail-fast on length mismatch, N < 2, invalid confidence level, and non-finite values."""
    with pytest.raises(ValueError, match="Length mismatch"):
        paired_bootstrap_ci([1.0, 2.0], [1.0])

    with pytest.raises(ValueError, match="at least 2"):
        paired_bootstrap_ci([1.0], [2.0])

    with pytest.raises(ValueError, match="confidence_level"):
        paired_bootstrap_ci([1.0, 2.0], [2.0, 3.0], confidence_level=1.0)

    with pytest.raises(ValueError, match="n_bootstrap"):
        paired_bootstrap_ci([1.0, 2.0], [2.0, 3.0], n_bootstrap=50)

    with pytest.raises(ValueError, match="non-finite"):
        paired_bootstrap_ci([1.0, np.nan], [2.0, 3.0])
