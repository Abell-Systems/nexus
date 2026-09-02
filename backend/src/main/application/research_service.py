"""Research service orchestrating landscape generation and patent retrieval."""

from typing import Any
from pydantic import BaseModel, Field
from domain.models.runtime_schemas import PatentRecord, PatentCluster
from .landscape.clustering import cluster_patents


class ResearchOutput(BaseModel):
    query: str
    domain: str
    patents: list[PatentRecord] = Field(default_factory=list)
    clusters: list[PatentCluster] = Field(default_factory=list)


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
    ) -> ResearchOutput:
        patents = self.patents_datasource.search_patents(query=query, domain=domain, limit=max_patents)
        demands = self.demand_datasource.search_demand(query=query, domain=domain)
        clusters = cluster_patents(patents=patents, demand_signals=demands, domain=domain)

        return ResearchOutput(
            query=query,
            domain=domain,
            patents=patents,
            clusters=clusters,
        )
