"""Descriptive sensitivity of the base-rate counts to perturbations of the corpus (ADR 0036, section 8.10, O5.2).

The scenarios were fixed in the ADR before any result: S-A the observed corpus; S-B1 one history year removed at a
time; S-B2 a history shortened to the last three years; S-C random deletion at the known absence rate of each
year and kind group. Every other rule is the one of the base rates (activity rule of O4, horizon 3, pairs from
single records). S-B1 and S-B2 change which pairs are unseen, so they change the problem as well as the coverage;
S-C removes observed publications at a known rate and recovers nothing, and cannot represent a kind that is wholly
absent. None of this measures the effect of the omitted publications.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import base_rates
from application.whitespace.corpus_exposure import exposure_group

QUANTITIES = ("active_subclasses", "candidate_pairs", "positives", "positive_rate_percent")
AbsencePercent = Mapping[tuple[int, str], float]  # (publication year, kind group) -> share of the inventory absent


def _counts(
    records: Sequence[AnalysisRecord], origin: int, horizon: int, min_documents: int, **extra: Any
) -> dict[str, Any]:
    figures = base_rates(
        records,
        [origin],
        min_documents=min_documents,
        horizon=horizon,
        filing_diagnostic=False,
        copy_policy="union",
        **extra,
    )
    return figures[str(origin)] if figures else dict.fromkeys(QUANTITIES, 0)


def _observed(figures: Mapping[str, Any]) -> dict[str, Any]:
    return {q: figures[q] for q in QUANTITIES}


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))]


def omission_sensitivity(
    records: Sequence[AnalysisRecord],
    origins: Sequence[int],
    absence_percent: AbsencePercent,
    *,
    replications: int = 200,
    seed_base: int = 0,
    horizon: int = 3,
    window: int = 3,
    min_documents: int = 20,
) -> dict[str, Any]:
    """The four scenarios at each origin; S-C uses the seeds ``seed_base + 1`` … ``seed_base + replications``."""
    first_year = min(r.published.year for r in records)
    result: dict[str, Any] = {}
    for origin in origins:
        observed = _counts(records, origin, horizon, min_documents)
        hidden = _counts(
            records,
            origin,
            horizon,
            min_documents,
            hidden_year_origins=[origin],
            hidden_years=list(range(first_year, origin + 1)),
        )["hidden_year"]["by_hidden_year"]
        b1 = {}
        for year in range(first_year, origin + 1):
            figures = _observed(
                _counts([r for r in records if r.published.year != year], origin, horizon, min_documents)
            )
            reclassified = hidden[str(year)]
            figures["positives_whose_pair_was_seen_only_in_the_removed_year"] = reclassified
            figures["positives_change_not_explained_by_that"] = (
                figures["positives"] - observed["positives"] - reclassified
            )
            b1[str(year)] = figures
        b2 = _observed(
            _counts([r for r in records if r.published.year >= origin - window + 1], origin, horizon, min_documents)
        )

        in_scope = [r for r in records if r.published.year <= origin + horizon]
        keep_probability = np.array(
            [1 - absence_percent.get((r.published.year, exposure_group(r.kind)), 0.0) / 100 for r in in_scope]
        )
        draws: dict[str, list[float]] = defaultdict(list)
        for replication in range(1, replications + 1):
            rng = np.random.default_rng(seed_base + replication)  # a reproducible simulation, not a security use
            kept = [r for r, keep in zip(in_scope, rng.random(len(in_scope)) < keep_probability, strict=True) if keep]
            for quantity, value in _observed(_counts(kept, origin, horizon, min_documents)).items():
                draws[quantity].append(value)
        result[str(origin)] = {
            "S-A": _observed(observed),
            "S-B1": b1,
            "S-B2": b2,
            "S-C": {
                "replications": replications,
                "seeds": [seed_base + 1, seed_base + replications],
                **{
                    q: {
                        "mean": round(sum(v) / len(v), 2),
                        "p2.5": _percentile(v, 0.025),
                        "p97.5": _percentile(v, 0.975),
                    }
                    for q, v in draws.items()
                },
            },
        }
    return result
