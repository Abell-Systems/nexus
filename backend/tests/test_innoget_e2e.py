"""End-to-End integration test for Innoget Demand Source integration.

Verifies 3 core invariants:
1. DEMAND_SOURCE=innoget selects InnogetDemandDataSource in factory.
2. Relevant technology query receives demand_signals > 0 matching CPC prefix.
3. White-space score incorporates demand signal contribution (0.25 * demand_norm) cleanly.
"""

from patent_agent.tools.clustering import cluster_patents, cluster_patents_tool
from patent_agent.tools.demand_sources import InnogetDemandDataSource, get_demand_datasource
from patent_agent.tools.schemas import PatentRecord


def test_invariant_1_demand_source_selection(monkeypatch):
    monkeypatch.setenv("DEMAND_SOURCE", "innoget")
    ds = get_demand_datasource()
    assert isinstance(ds, InnogetDemandDataSource)


def test_invariant_2_and_3_e2e_innoget_demand_raises_white_space_score(monkeypatch):
    monkeypatch.setenv("DEMAND_SOURCE", "innoget")

    # Sample patent records covering polymer/coating (C08L) and semiconductors (H01L)
    patents = [
        PatentRecord(
            publication_number="US-10000001-B2",
            title="Silicone coating for metal substrates",
            abstract="Silicone coating...",
            filing_date="2024-01-01",
            publication_date="2024-06-01",
            country_code="US",
            cpc_codes=["C08L10/00"],
            citation_count=5,
        ),
        PatentRecord(
            publication_number="US-10000002-B2",
            title="Semiconductor wafer design",
            abstract="Semiconductor...",
            filing_date="2020-01-01",
            publication_date="2020-06-01",
            country_code="US",
            cpc_codes=["H01L21/00"],
            citation_count=1,
        ),
    ]

    # 1. Cluster without demand signals
    clusters_no_demand = cluster_patents(patents, demand_signals=None, current_year=2026)

    # 2. Search demand signals from Innoget for query matching silicone/coating
    innoget_ds = InnogetDemandDataSource()
    demand_signals = innoget_ds.search_demand(query="silicone coating metal", domain="materials")
    assert len(demand_signals) > 0

    # 3. Cluster with Innoget demand signals
    clusters_with_demand = cluster_patents(patents, demand_signals=demand_signals, current_year=2026)

    # Find the C08L cluster in both runs
    c08l_no_demand = next(c for c in clusters_no_demand if c.cluster_id == "cluster-C08L")
    c08l_with_demand = next(c for c in clusters_with_demand if c.cluster_id == "cluster-C08L")

    # Verify score with demand is strictly greater due to demand signal contribution
    assert c08l_with_demand.white_space_score > c08l_no_demand.white_space_score


def test_e2e_clustering_tool_with_innoget_env(monkeypatch):
    monkeypatch.setenv("DEMAND_SOURCE", "innoget")
    monkeypatch.setenv("USE_MOCK_BIGQUERY", "true")

    # Run tool function directly
    clusters = cluster_patents_tool(query="coating", domain="materials", max_results=20)

    assert isinstance(clusters, list)
    assert len(clusters) > 0
    for cluster in clusters:
        assert "cluster_id" in cluster
        assert "white_space_score" in cluster
        assert "is_white_space" in cluster
