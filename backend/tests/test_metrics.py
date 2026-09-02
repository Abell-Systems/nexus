import pytest
from backend.patent_agent.tools.metrics import compute_citation_traction, compute_white_space_metrics
from backend.patent_agent.tools.schemas import PatentRecord, DemandSignal


def test_citation_traction_formula():
    # Patent 1: 2021 (age=5), forward_citations=10 -> tau = 10/5 = 2.0
    p1 = PatentRecord(
        publication_number="ES-001",
        title="T1",
        abstract="A1",
        assignee="X",
        filing_date="2021-01-01",
        cpc_codes=["C11D"],
        citation_count=10,
    )
    setattr(p1, "publication_date", "2021-01-01")
    setattr(p1, "backward_citation_count", 5)

    # Patent 2: 2025 (age=1, young <= 3), forward=1, backward=5 -> tilde_tau = (1 + 0.2*min(5,5))/3 = 2.0 / 3 = 0.667
    p2 = PatentRecord(
        publication_number="ES-002",
        title="T2",
        abstract="A2",
        assignee="Y",
        filing_date="2025-01-01",
        cpc_codes=["C11D"],
        citation_count=1,
    )
    setattr(p2, "publication_date", "2025-01-01")
    setattr(p2, "backward_citation_count", 5)

    # Mean tau = (2.0 + 0.6667)/2 = 1.3333. Traction T = clip(1.3333 / 5.0, 0, 1) = 0.2667
    traction, coverage = compute_citation_traction([p1, p2], ref_year=2026, tau_max=5.0)
    assert 0.25 <= traction <= 0.28
    assert coverage == 1.0


def test_citation_traction_empty():
    traction, coverage = compute_citation_traction([])
    assert traction == 0.0
    assert coverage == 0.0


def test_citation_traction_handles_null_unobserved():
    p_null = PatentRecord(
        publication_number="ES-003",
        title="T3",
        abstract="A3",
        assignee="Z",
        filing_date="2020-01-01",
        cpc_codes=["C11D"],
        citation_count=None,
    )
    traction, coverage = compute_citation_traction([p_null])
    assert traction == 0.0
    assert coverage == 0.0


def test_composite_white_space_score():
    p1 = PatentRecord(
        publication_number="ES-001",
        title="T1",
        abstract="A1",
        assignee="X",
        filing_date="2022-01-01",
        cpc_codes=["C11D"],
        citation_count=4,
    )
    setattr(p1, "publication_date", "2022-01-01")
    setattr(p1, "backward_citation_count", 3)

    demand = DemandSignal(
        source="innoget",
        id="d1",
        title="Detergent Need",
        description="desc",
        cpc_prefix="C11D",
        posted_date="2026-01-01",
        url="http://example.com",
    )

    metrics = compute_white_space_metrics(
        cluster_id="C11D",
        patents=[p1],
        demand_signals=[demand],
        max_patents=10,  # n_max = 10, so d_i = 1/10 = 0.1
        max_demands=2,  # m_max = 2, so q_i = 1/2 = 0.5
        ref_year=2026,
    )

    assert metrics["cluster_id"] == "C11D"
    assert metrics["density"] == 0.1
    assert metrics["demand_intensity"] == 0.5
    assert metrics["citation_coverage"] == 1.0
    assert 0.0 <= metrics["recency"] <= 1.0
    assert 0.0 <= metrics["citation_traction"] <= 1.0
    # W_i = 0.40*(1 - 0.1) + 0.20*r + 0.15*T + 0.25*0.5
    assert metrics["white_space_score"] >= 0.50
    assert metrics["is_white_space"] is True
    assert metrics["quadrant"] == "Quadrant I (Unmet Opportunity)"


def test_quadrants():
    p = PatentRecord(
        publication_number="ES-001",
        title="T1",
        abstract="A1",
        assignee="X",
        filing_date="2022-01-01",
        cpc_codes=["C11D"],
        citation_count=4,
    )
    demand = DemandSignal(
        source="innoget",
        id="d1",
        title="Detergent Need",
        description="desc",
        cpc_prefix="C11D",
        posted_date="2026-01-01",
        url="http://example.com",
    )

    # Quadrant I: demand >= 0.5, density < 0.4
    m1 = compute_white_space_metrics("C1", [p], [demand], max_patents=10, max_demands=2)
    assert m1["quadrant"] == "Quadrant I (Unmet Opportunity)"

    # Quadrant II: demand >= 0.5, density >= 0.4
    m2 = compute_white_space_metrics("C2", [p, p], [demand], max_patents=2, max_demands=2)
    assert m2["quadrant"] == "Quadrant II (Co-developed / Saturated)"

    # Quadrant III: demand < 0.5, density >= 0.4
    m3 = compute_white_space_metrics("C3", [p, p], [], max_patents=2, max_demands=2)
    assert m3["quadrant"] == "Quadrant III (Dormant / Established IP)"

    # Quadrant IV: demand < 0.5, density < 0.4
    m4 = compute_white_space_metrics("C4", [p], [], max_patents=10, max_demands=2)
    assert m4["quadrant"] == "Quadrant IV (Niche / Emerging)"
