"""Research service orchestrating landscape generation and patent retrieval."""

from typing import Any

from pydantic import BaseModel, Field

from domain.models.runtime_schemas import PatentCluster, PatentRecord

from .landscape.clustering import cluster_patents


class ResearchOutput(BaseModel):
    query: str
    domain: str
    patents: list[PatentRecord] = Field(default_factory=list)
    clusters: list[PatentCluster] = Field(default_factory=list)
    cluster_id: str | None = None
    cluster_context: dict[str, Any] = Field(default_factory=dict)


ResearchResult = ResearchOutput


class ResearchService:
    def __init__(
        self,
        patents_datasource: Any,
        demand_datasource: Any,
    ) -> None:
        self.patents_datasource = patents_datasource
        self.demand_datasource = demand_datasource

    async def conduct_research(
        self,
        query: str,
        domain: str,
        max_patents: int = 20,
        cluster_id: str | None = None,
        profiler: Any = None,
    ) -> ResearchOutput:
        if profiler:
            profiler.start_stage("search_patents")
        patents = self.patents_datasource.search_patents(query=query, domain=domain, limit=max_patents)

        if profiler:
            profiler.start_stage("search_demand")
        demands = self.demand_datasource.search_demand(query=query, domain=domain)

        if profiler:
            profiler.start_stage("cluster_patents")
        clusters = cluster_patents(patents=patents, demand_signals=demands, domain=domain)

        selected_cid = cluster_id or (clusters[0].cluster_id if clusters else "H01M")
        selected_cluster = next((c for c in clusters if c.cluster_id == selected_cid), None)

        cluster_context: dict[str, Any] = {
            "cluster_id": selected_cid,
            "domain": domain,
            "representative_patents": selected_cluster.representative_patents if selected_cluster else [],
            "patent_count": selected_cluster.patent_count if selected_cluster else len(patents),
        }

        return ResearchOutput(
            query=query,
            domain=domain,
            patents=patents,
            clusters=clusters,
            cluster_id=selected_cid,
            cluster_context=cluster_context,
        )
