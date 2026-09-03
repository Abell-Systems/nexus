"""Unit tests for white-space metrics and citation traction calculations."""

from application.landscape.metrics import compute_citation_traction, compute_white_space_metrics
from domain.models.runtime_schemas import DemandSignalItem, PatentRecord


def test_compute_citation_traction_handles_null_citations():
    """Scientific Gate 1: Unobserved citations (None) must not drag down the average."""
    patents = [
        PatentRecord(
            publication_number="ES-2849102-B2",
            title="Detergent composition",
            abstract="Abstract 1",
            filing_date="2020-01-01",
            citation_count=10,
        ),
        PatentRecord(
            publication_number="ES-2715482-B2",
            title="Cleaning formulation",
            abstract="Abstract 2",
            filing_date="2020-01-01",
            citation_count=None,  # Unobserved
        ),
    ]
    traction, coverage = compute_citation_traction(patents, ref_year=2026)
    assert coverage == 0.50
    assert traction > 0.0


def test_compute_white_space_metrics():
    patents = [
        PatentRecord(
            publication_number="ES-2849102-B2",
            title="Detergent composition",
            abstract="Abstract 1",
            filing_date="2020-01-01",
            cpc_codes=["C11D1/00"],
            citation_count=5,
        )
    ]
    demands = [
        DemandSignalItem(
            source="innoget",
            id="INNOGET-2292",
            title="Industrial detergent",
            description="Seeking surfactants",
            cpc_prefix="C11D",
        )
    ]
    metrics = compute_white_space_metrics(
        cluster_id="C11D",
        patents=patents,
        demand_signals=demands,
        max_patents=10,
        max_demands=5,
    )
    assert metrics["cluster_id"] == "C11D"
    assert metrics["patent_count"] == 1
    assert metrics["demand_count"] == 1
    assert 0.0 <= metrics["white_space_score"] <= 1.0
