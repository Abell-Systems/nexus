"""Typed statistical outcome models under ADR 0010."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WilcoxonResult:
    """Outcome of a paired Wilcoxon signed-rank test."""

    statistic: float
    p_value: float
    n_pairs: int
    n_nonzero: int
    alternative: str


@dataclass(frozen=True)
class BenjaminiHochbergResult:
    """Outcome of Benjamini-Hochberg False Discovery Rate adjustment."""

    p_values: list[float]
    adjusted_p_values: list[float]
    rejected: list[bool]
    alpha: float
    n_hypotheses: int
    n_rejected: int


@dataclass(frozen=True)
class BootstrapCIResult:
    """Outcome of a paired bootstrap confidence interval estimation."""

    estimate: float
    ci_lower: float
    ci_upper: float
    n_bootstrap: int
    confidence_level: float
    seed: int | None
