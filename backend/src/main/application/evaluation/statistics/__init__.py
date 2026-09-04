"""Inferential statistical testing primitives under ADR 0010.

Pure mathematical functions for paired hypothesis testing, multiple comparison
correction, and non-parametric bootstrap confidence intervals.
"""

from .bootstrap import paired_bootstrap_ci
from .multiple_testing import adjust_benjamini_hochberg
from .types import BenjaminiHochbergResult, BootstrapCIResult, WilcoxonResult
from .wilcoxon import paired_wilcoxon_test

__all__ = [
    "BenjaminiHochbergResult",
    "BootstrapCIResult",
    "WilcoxonResult",
    "adjust_benjamini_hochberg",
    "paired_bootstrap_ci",
    "paired_wilcoxon_test",
]
