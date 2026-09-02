"""Formal White-Space and Citation Traction Metrics for Patent Analysis."""

from enum import Enum
from typing import Any
from domain.models.runtime_schemas import PatentRecord, DemandSignalItem


class ExecutionMode(str, Enum):
    FIXTURE = "fixture"
    PILOT = "pilot"
    EMPIRICAL = "empirical"


def compute_citation_traction(
    patents: list[PatentRecord],
    ref_year: int = 2026,
    tau_max: float = 5.0,
) -> tuple[float, float]:
    """Calculate normalized Cluster Citation Traction (T_i) and Citation Coverage.
    Distinguishes observed citations from unobserved (None).
    """
    if not patents:
        return 0.0, 0.0

    observed_patents = [p for p in patents if getattr(p, "citation_count", None) is not None]
    coverage = len(observed_patents) / len(patents)

    if not observed_patents:
        return 0.0, round(coverage, 4)

    annualized_rates: list[float] = []
    for p in observed_patents:
        pub_str = getattr(p, "publication_date", None) or p.filing_date
        pub_year = int(pub_str.split("-")[0]) if pub_str else ref_year
        age = max(1, ref_year - pub_year)

        f_p = float(p.citation_count) if p.citation_count is not None else 0.0
        raw_b = getattr(p, "backward_citation_count", None)
        b_p = float(raw_b) if raw_b is not None else 0.0

        if age > 3:
            tau_p = f_p / age
        else:
            tau_p = (f_p + 0.2 * min(b_p, 5.0)) / 3.0

        annualized_rates.append(tau_p)

    mean_tau = sum(annualized_rates) / len(annualized_rates)
    traction = min(1.0, max(0.0, mean_tau / tau_max))
    return round(traction, 4), round(coverage, 4)


def compute_white_space_metrics(
    cluster_id: str,
    patents: list[PatentRecord],
    demand_signals: list[Any],
    max_patents: int,
    max_demands: int,
    ref_year: int = 2026,
    horizon_years: int = 20,
) -> dict[str, Any]:
    """Compute formal composite white-space metrics for a given cluster."""
    n_i = len(patents)
    m_i = len(demand_signals)

    n_max = max(1, max_patents)
    density = round(n_i / n_max, 4)

    if n_i > 0:
        ages = [
            max(1, ref_year - (int(p.filing_date.split("-")[0]) if p.filing_date else ref_year))
            for p in patents
        ]
        mean_age = sum(ages) / n_i
        recency = round(max(0.0, min(1.0, 1.0 - (mean_age / horizon_years))), 4)
    else:
        mean_age = 0.0
        recency = 0.0

    traction, citation_coverage = compute_citation_traction(patents, ref_year=ref_year)

    m_max = max(1, max_demands)
    demand_intensity = round(m_i / m_max, 4) if m_i > 0 else 0.0

    w_d = 0.40
    w_r = 0.20
    w_T = 0.15
    w_q = 0.25

    white_space_score = round(
        w_d * (1.0 - density)
        + w_r * recency
        + w_T * traction
        + w_q * demand_intensity,
        4,
    )

    is_white_space = bool(white_space_score >= 0.50)

    if demand_intensity >= 0.50 and density < 0.40:
        quadrant = "Quadrant I (Unmet Opportunity)"
    elif demand_intensity >= 0.50 and density >= 0.40:
        quadrant = "Quadrant II (Co-developed / Saturated)"
    elif demand_intensity < 0.50 and density < 0.40:
        quadrant = "Quadrant III (Dormant / Speculative)"
    else:
        quadrant = "Quadrant IV (Over-patented / Low Market Pull)"

    return {
        "cluster_id": cluster_id,
        "patent_count": n_i,
        "demand_count": m_i,
        "density": density,
        "recency": recency,
        "mean_age_years": round(mean_age, 2),
        "citation_traction": traction,
        "citation_coverage": citation_coverage,
        "demand_intensity": demand_intensity,
        "white_space_score": white_space_score,
        "is_white_space": is_white_space,
        "quadrant": quadrant,
    }
