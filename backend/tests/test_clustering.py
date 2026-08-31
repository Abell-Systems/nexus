import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from patent_agent.tools.bigquery_patents import MockPatentsDataSource
from patent_agent.tools.clustering import cluster_patents, cluster_patents_tool
from patent_agent.tools.schemas import DemandSignal, PatentCluster, PatentRecord


def test_cluster_patents_groups_by_cpc_prefix():
    source = MockPatentsDataSource()
    records = source.search_patents("solid electrolyte", "solid-state battery electrolytes", max_results=30)

    clusters = cluster_patents(records, current_year=2026)

    assert len(clusters) > 0
    for cluster in clusters:
        assert isinstance(cluster, PatentCluster)
        assert cluster.patent_count > 0
        assert 0.0 <= cluster.white_space_score <= 1.0
        assert len(cluster.representative_patents) <= 3

    total_in_clusters = sum(c.patent_count for c in clusters)
    assert total_in_clusters == len(records)


def test_cluster_patents_sorted_by_white_space_score_desc():
    source = MockPatentsDataSource()
    records = source.search_patents("solid electrolyte", "solid-state battery electrolytes", max_results=30)

    clusters = cluster_patents(records, current_year=2026)
    scores = [c.white_space_score for c in clusters]

    assert scores == sorted(scores, reverse=True)


def test_cluster_patents_demand_signal_raises_matching_cluster_score():
    source = MockPatentsDataSource()
    records = source.search_patents("solid electrolyte", "solid-state battery electrolytes", max_results=30)

    baseline = {c.cluster_id: c.white_space_score for c in cluster_patents(records, current_year=2026)}

    target_prefix = next(c for c in baseline).removeprefix("cluster-")
    demand = [
        DemandSignal(
            source="sbir",
            id=f"sbir-{i}",
            title="t",
            description="d",
            cpc_prefix=target_prefix,
            posted_date="2025-01-01",
            url="https://example.invalid/x",
        )
        for i in range(5)
    ]

    boosted = {
        c.cluster_id: c.white_space_score
        for c in cluster_patents(records, demand_signals=demand, current_year=2026)
    }

    assert boosted[f"cluster-{target_prefix}"] > baseline[f"cluster-{target_prefix}"]


def test_cluster_patents_empty_input():
    assert cluster_patents([], current_year=2026) == []


def test_cluster_patents_tool_returns_dicts():
    result = cluster_patents_tool("solid electrolyte", "solid-state battery electrolytes", max_results=15)

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(c, dict) for c in result)
    assert all("white_space_score" in c for c in result)


def test_malformed_filing_date_does_not_crash():
    record = PatentRecord(
        publication_number="US-1",
        title="t",
        abstract="a",
        filing_date="not-a-date",
        publication_date="2025-06-01",
        country_code="US",
        cpc_codes=["H01M10/0562"],
    )
    clusters = cluster_patents([record], current_year=2026)
    assert len(clusters) == 1
