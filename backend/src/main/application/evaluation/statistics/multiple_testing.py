"""Benjamini-Hochberg False Discovery Rate (FDR) adjustment under ADR 0010."""

from collections.abc import Sequence

import numpy as np

from .types import BenjaminiHochbergResult


def adjust_benjamini_hochberg(
    p_values: Sequence[float],
    alpha: float = 0.05,
) -> BenjaminiHochbergResult:
    """Adjusts p-values for multiple comparisons using the Benjamini-Hochberg (BH) step-up FDR procedure.

    Invariants:
    - Guaranteed q-values in [0.0, 1.0].
    - Guaranteed step-up monotonicity: q_(i) <= q_(i+1).
    - Preserves the original input order in returned adjusted_p_values and rejected.
    - Explicit distinction between adjusted p-values and binary decision:
      rejected[i] = adjusted_p_values[i] <= alpha.
    - Validates 0.0 < alpha < 1.0.
    - Validates all p-values are bounded in [0.0, 1.0] and finite.
    - Deterministic across calls.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0.0, 1.0), got {alpha}")

    m = len(p_values)
    if m == 0:
        return BenjaminiHochbergResult(
            p_values=[],
            adjusted_p_values=[],
            rejected=[],
            alpha=alpha,
            n_hypotheses=0,
            n_rejected=0,
        )

    arr = np.asarray(p_values, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError("p-values contain non-finite values (NaN or Inf)")
    if np.any((arr < 0.0) | (arr > 1.0)):
        raise ValueError("All p-values must be bounded in [0.0, 1.0]")

    # Sort p-values ascending and keep track of original positions
    order = np.argsort(arr)
    sorted_p = arr[order]

    # Compute raw Benjamini-Hochberg quotients: q_i = p_(i) * m / i (1-indexed)
    ranks = np.arange(1, m + 1, dtype=float)
    raw_q = sorted_p * (m / ranks)

    # Enforce step-up monotonicity via cumulative minimum from right to left:
    # q_(i) = min(1.0, min_{j >= i} raw_q_(j))
    cummin_q = np.minimum.accumulate(raw_q[::-1])[::-1]
    adjusted_sorted = np.clip(cummin_q, 0.0, 1.0)

    # Restore original input order
    adjusted_p = np.empty_like(adjusted_sorted)
    adjusted_p[order] = adjusted_sorted

    adj_list = [float(q) for q in adjusted_p]
    rejected_list = [bool(q <= alpha) for q in adj_list]

    return BenjaminiHochbergResult(
        p_values=[float(p) for p in p_values],
        adjusted_p_values=adj_list,
        rejected=rejected_list,
        alpha=alpha,
        n_hypotheses=m,
        n_rejected=sum(rejected_list),
    )
