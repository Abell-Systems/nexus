import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from patent_agent.tools.bigquery_patents import MockPatentsDataSource
from patent_agent.tools.clustering import cluster_patents
from patent_agent.tools.context import build_cluster_context


def test_build_cluster_context_is_compact_and_grounded():
    source = MockPatentsDataSource()
    records = source.search_patents("solid electrolyte", "solid-state battery electrolytes", max_results=30)
    clusters = cluster_patents(records, current_year=2026)
    cluster = clusters[0]

    context = build_cluster_context(cluster, records, demand_signals=[])

    assert cluster.cluster_id in context
    # rough token proxy: chars/4. Must stay well under the 8K-token Groq
    # free-tier ceiling that motivated this function.
    assert len(context) / 4 < 1500
    for pub_number in cluster.representative_patents:
        assert pub_number in context
