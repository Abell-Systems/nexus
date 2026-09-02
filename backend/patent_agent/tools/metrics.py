"""Formal White-Space and Citation Traction Metrics for Patent Analysis."""

from enum import Enum
from typing import Any
from .schemas import PatentRecord, DemandSignal


class ExecutionMode(str, Enum):
    """Execution mode distinguishing scientific evidence tiers."""
    FIXTURE = "fixture"      # Mock data for fast unit testing
    PILOT = "pilot"          # Local sample smoke tests
    EMPIRICAL = "empirical"  # Validated empirical dataset with cryptographic provenance


def compute_citation_traction(
    patents: list[PatentRecord],
    ref_year: int = 2026,
    tau_max: float = 5.0,
) -> float:
    """Calculate normalized Cluster Citation Traction (T_i).

    Note: Citation Traction (T_i) is an experimental composite heuristic metric
    defined specifically for this exploratory study. It differentiates forward citations
    (f_p) and patent age (a_p), applying an experimental dampening baseline for recent
    patents (a_p <= 3 years) using backward citation foundation (b_p).

    Null Handling: If citation counts are None (unobserved from raw biblio data),
    they are handled as neutral observations rather than penalizing confirmed zeros.
    """
    if not patents:
        return 0.0

    annualized_rates: list[float] = []
    for p in patents:
        pub_str = getattr(p, "publication_date", None) or p.filing_date
        pub_year = int(pub_str.split("-")[0]) if pub_str else ref_year
        age = max(1, ref_year - pub_year)

        # Handle None vs confirmed int
        raw_f = getattr(p, "citation_count", None)
        raw_b = getattr(p, "backward_citation_count", None)

        if raw_f is None:
            # Unobserved citation data from basic biblio feed: treat as baseline rate
            f_p = 0.0
            b_p = 0.0
        else:
            f_p = float(raw_f)
            b_p = float(raw_b or 0.0)

        if age > 3:
            tau_p = f_p / age
        else:
            # Dampened annualized rate for recent patents
            tau_p = (f_p + 0.2 * min(b_p, 5.0)) / 3.0

        annualized_rates.append(tau_p)

    mean_tau = sum(annualized_rates) / len(annualized_rates)
    traction = min(1.0, max(0.0, mean_tau / tau_max))
    return round(traction, 4)


def compute_white_space_metrics(
    cluster_id: str,
    patents: list[PatentRecord],
    demand_signals: list[DemandSignal],
    max_patents: int,
    max_demands: int,
    ref_year: int = 2026,
    horizon_years: int = 20,
) -> dict[str, Any]:
    """Compute formal composite white-space metrics for a given cluster."""
    n_i = len(patents)
    m_i = len(demand_signals)

    # 1. Density d_i
    n_max = max(1, max_patents)
    density = round(n_i / n_max, 4)

    # 2. Recency r_i
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

    # 3. Citation Traction T_i (Experimental Metric)
    traction = compute_citation_traction(patents, ref_year=ref_year)

    # 4. Demand Intensity q_i
    m_max = max(1, max_demands)
    demand_intensity = round(m_i / m_max, 4) if m_i > 0 else 0.0

    # 5. Composite White-Space Score W_i
    # W_i = 0.40*(1 - d_i) + 0.20*r_i + 0.15*T_i + 0.25*q_i
    white_space_score = (
        0.40 * (1.0 - density)
        + 0.20 * recency
        + 0.15 * traction
        + 0.25 * demand_intensity
    )
    white_space_score = round(min(1.0, max(0.0, white_space_score)), 4)

    # Quadrant determination
    if demand_intensity >= 0.5 and density < 0.4:
        quadrant = "Quadrant I (Unmet Opportunity)"
    elif demand_intensity >= 0.5 and density >= 0.4:
        quadrant = "Quadrant II (Co-developed / Saturated)"
    elif demand_intensity < 0.5 and density >= 0.4:
        quadrant = "Quadrant III (Dormant / Established IP)"
    else:
        quadrant = "Quadrant IV (Niche / Emerging)"

    return {
        "cluster_id": cluster_id,
        "patent_count": n_i,
        "demand_count": m_i,
        "density": density,
        "mean_age_years": round(mean_age, 2),
        "recency": recency,
        "citation_traction": traction,
        "demand_intensity": demand_intensity,
        "white_space_score": white_space_score,
        "is_white_space": white_space_score >= 0.50,
        "quadrant": quadrant,
    }
