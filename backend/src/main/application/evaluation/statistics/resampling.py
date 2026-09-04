"""Paired demand-level resampling primitive under ADR 0010."""

from collections.abc import Sequence

import numpy as np


def paired_resample(
    baseline: Sequence[float],
    treatment: Sequence[float],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Draws a paired bootstrap sample of baseline and treatment using a single shared index vector.

    Invariants:
    - baseline and treatment must have equal length >= 1.
    - Preserves paired covariance across comparative runs by sampling the exact same indices.
    """
    n_b = len(baseline)
    n_t = len(treatment)
    if n_b != n_t:
        raise ValueError(f"Length mismatch: baseline has {n_b} elements, treatment has {n_t}")
    if n_b < 1:
        raise ValueError("Cannot resample from empty sequences")

    indices = rng.integers(0, n_b, size=n_b)
    arr_b = np.asarray(baseline, dtype=float)
    arr_t = np.asarray(treatment, dtype=float)
    return arr_b[indices], arr_t[indices]
