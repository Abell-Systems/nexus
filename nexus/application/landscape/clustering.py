"""Clustering and landscape generation logic."""

from typing import Any
from google.adk.tools import FunctionTool
from nexus.domain.models.runtime_schemas import PatentRecord, PatentCluster, DemandSignalItem
from .metrics import compute_white_space_metrics
from .cpc_taxonomy import map_concept_to_cpc


def cluster_patents(
    patents: list[PatentRecord],
    demand_signals: list[Any] | None = None,
    domain: str = "solid_state_battery",
) -> list[PatentCluster]:
    if not patents:
        return []

    demands = demand_signals or []
    cluster_groups: dict[str, list[PatentRecord]] = {}

    for p in patents:
        cpc_prefix = p.cpc_codes[0][:4] if p.cpc_codes else "H01M"
        cluster_groups.setdefault(cpc_prefix, []).append(p)

    demand_groups: dict[str, list[Any]] = {}
    for d in demands:
        prefix = getattr(d, "cpc_prefix", None) or "H01M"
        demand_groups.setdefault(prefix, []).append(d)

    max_patents = max(len(grp) for grp in cluster_groups.values()) if cluster_groups else 1
    max_demands = max(len(grp) for grp in demand_groups.values()) if demand_groups else 1

    clusters: list[PatentCluster] = []
    for c_id, grp in cluster_groups.items():
        metrics = compute_white_space_metrics(
            cluster_id=c_id,
            patents=grp,
            demand_signals=demand_groups.get(c_id, []),
            max_patents=max_patents,
            max_demands=max_demands,
        )
        clusters.append(
            PatentCluster(
                cluster_id=c_id,
                label=f"Technology Cluster {c_id}",
                representative_patents=[p.publication_number for p in grp[:3]],
                patent_count=len(grp),
                white_space_score=metrics["white_space_score"],
                is_white_space=metrics["is_white_space"],
            )
        )

    return clusters


def patents_for_demand_signal(
    signal: Any,
    domain: str,
    max_results: int = 20,
) -> list[PatentRecord]:
    from nexus.infrastructure.sources.bigquery_patents import get_patents_datasource
    datasource = get_patents_datasource()
    return datasource.search_patents(query=signal.title, domain=domain, limit=max_results)


cluster_patents_tool = FunctionTool(func=cluster_patents)
