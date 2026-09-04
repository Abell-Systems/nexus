"""Paired demand-level bootstrap confidence intervals under ADR 0010."""

from collections.abc import Sequence

import numpy as np

from .types import BootstrapCIResult


def paired_bootstrap_ci(
    baseline: Sequence[float],
    treatment: Sequence[float],
    n_bootstrap: int = 10_000,
    confidence_level: float = 0.95,
    seed: int | None = 42,
) -> BootstrapCIResult:
    """Computes a paired bootstrap confidence interval for the mean treatment effect.

    Invariants:
    - Statistical unit is the paired demand: draws identical row indices for baseline and treatment.
    - Point estimate is empirical mean(treatment - baseline).
    - Percentile bootstrap CI: [percentile(alpha_ci/2), percentile(1 - alpha_ci/2)].
    - Strictly deterministic when seed is provided.
    - Fails fast on length mismatch, empty sequences, non-finite values, or invalid confidence level.
    """
    n_b = len(baseline)
    n_t = len(treatment)
    if n_b != n_t:
        raise ValueError(f"Length mismatch: baseline has {n_b} items, treatment has {n_t}")
    if n_b < 2:
        raise ValueError(f"Need at least 2 paired observations for bootstrap CI, got {n_b}")
    if not (0.0 < confidence_level < 1.0):
        raise ValueError(f"confidence_level must be in (0.0, 1.0), got {confidence_level}")
    if n_bootstrap < 100:
        raise ValueError(f"n_bootstrap must be at least 100, got {n_bootstrap}")

    b_arr = np.asarray(baseline, dtype=float)
    t_arr = np.asarray(treatment, dtype=float)
    if not np.all(np.isfinite(b_arr)) or not np.all(np.isfinite(t_arr)):
        raise ValueError("Input sequences contain non-finite values (NaN or Inf)")

    deltas = t_arr - b_arr
    point_estimate = float(np.mean(deltas))

    rng = np.random.default_rng(seed)

    # Vectorized bootstrap resampling using a single shared index matrix
    indices = rng.integers(0, n_b, size=(n_bootstrap, n_b))
    bootstrap_deltas = deltas[indices]
    boot_means = np.mean(bootstrap_deltas, axis=1)

    alpha_ci = 1.0 - confidence_level
    lower_pct = 100.0 * (alpha_ci / 2.0)
    upper_pct = 100.0 * (1.0 - alpha_ci / 2.0)

    ci_lower = float(np.percentile(boot_means, lower_pct))
    ci_upper = float(np.percentile(boot_means, upper_pct))

    return BootstrapCIResult(
        estimate=round(point_estimate, 6),
        ci_lower=round(ci_lower, 6),
        ci_upper=round(ci_upper, 6),
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level,
        seed=seed,
    )
