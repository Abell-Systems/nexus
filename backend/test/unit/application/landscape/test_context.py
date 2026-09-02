"""Unit tests for domain context and cluster context builder."""

from application.landscape.context import (
    build_cluster_context,
    get_domain_keywords,
    is_supported_domain,
)
from domain.models.runtime_schemas import DemandSignalItem, PatentCluster, PatentRecord


def test_is_supported_domain():
    assert is_supported_domain("solid_state_battery") is True
    assert is_supported_domain("spanish_patents") is True
    assert is_supported_domain("oepm") is True
    assert is_supported_domain("") is False
    assert is_supported_domain("   ") is False
    assert is_supported_domain("unsupported_domain_xyz") is False


def test_get_domain_keywords():
    kws = get_domain_keywords("solid_state_battery")
    assert "solid electrolyte" in kws

    pilot_kws = get_domain_keywords("spanish_patents_pilot")
    assert "detergent" in pilot_kws

    fallback_kws = get_domain_keywords("other")
    assert len(fallback_kws) > 0


def test_build_cluster_context():
    cluster = PatentCluster(
        cluster_id="H01M",
        label="Solid State Battery - H01M",
        representative_patents=["ES-1"],
        patent_count=1,
        white_space_score=0.85,
        is_white_space=True,
    )
    patents = [
        PatentRecord(
            publication_number="ES-1",
            title="Battery Electrolyte",
            abstract="Solid electrolyte",
            filing_date="2020-01-01",
        )
    ]
    demands = [
        DemandSignalItem(
            id="d1",
            title="Challenge 1",
            description="Desc",
            source="innoget",
        )
    ]

    ctx = build_cluster_context(cluster, patents, demands)
    assert ctx["cluster_id"] == "H01M"
    assert ctx["white_space_score"] == 0.85
    assert ctx["patent_count"] == 1
    assert len(ctx["patents"]) == 1
    assert len(ctx["demands"]) == 1
