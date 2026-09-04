"""Paired Wilcoxon signed-rank test under ADR 0010 and Protocol §3.2."""

from collections.abc import Sequence

import numpy as np
from scipy.stats import wilcoxon

from .types import WilcoxonResult

VALID_ALTERNATIVES = {"two-sided", "greater", "less"}
VALID_ZERO_METHODS = {"wilcox", "pratt", "zsplit"}


def paired_wilcoxon_test(
    baseline: Sequence[float],
    treatment: Sequence[float],
    alternative: str = "two-sided",
    zero_method: str = "wilcox",
) -> WilcoxonResult:
    """Computes the paired Wilcoxon signed-rank test between treatment and baseline.

    Under Protocol §3.2, test evaluates paired differences Delta = treatment - baseline.

    Invariants:
    - Fails fast on length mismatch or empty sequences.
    - Fails fast on non-finite values (NaN or Inf).
    - Tracks both total valid pairs (n_pairs) and non-zero differences (n_nonzero).
    - If all pairs are tied (n_nonzero == 0), returns statistic=0.0, p_value=1.0 deterministically.
    - Uses zero_method='wilcox' (discards exact ties from rank sums).
    """
    if alternative not in VALID_ALTERNATIVES:
        raise ValueError(
            f"Invalid alternative '{alternative}'. Must be one of {sorted(VALID_ALTERNATIVES)}"
        )
    if zero_method not in VALID_ZERO_METHODS:
        raise ValueError(
            f"Invalid zero_method '{zero_method}'. Must be one of {sorted(VALID_ZERO_METHODS)}"
        )

    n_b = len(baseline)
    n_t = len(treatment)
    if n_b != n_t:
        raise ValueError(f"Length mismatch: baseline has {n_b} items, treatment has {n_t}")
    if n_b < 1:
        raise ValueError("Cannot perform Wilcoxon test on empty sequences")

    b_arr = np.asarray(baseline, dtype=float)
    t_arr = np.asarray(treatment, dtype=float)

    if not np.all(np.isfinite(b_arr)) or not np.all(np.isfinite(t_arr)):
        raise ValueError("Input sequences contain non-finite values (NaN or Inf)")

    deltas = t_arr - b_arr
    n_nonzero = int(np.count_nonzero(deltas))

    if n_nonzero == 0:
        return WilcoxonResult(
            statistic=0.0,
            p_value=1.0,
            n_pairs=n_b,
            n_nonzero=0,
            alternative=alternative,
        )

    res = wilcoxon(t_arr, b_arr, alternative=alternative, zero_method=zero_method)
    return WilcoxonResult(
        statistic=float(res.statistic),
        p_value=float(res.pvalue),
        n_pairs=n_b,
        n_nonzero=n_nonzero,
        alternative=alternative,
    )
