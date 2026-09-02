"""Research service orchestrating landscape generation and patent retrieval."""

from typing import Any
from pydantic import BaseModel, Field
from domain.models.runtime_schemas import PatentRecord, PatentCluster
from infrastructure.sources.bigquery_patents import get_patents_datasource
from infrastructure.sources.demand_sources import get_demand_datasource
from .landscape.clustering import cluster_patents


class ResearchOutput(BaseModel):
    query: str
    domain: str
    patents: list[PatentRecord] = Field(default_factory=list)
    clusters: list[PatentCluster] = Field(default_factory=list)


ResearchResult = ResearchOutput


class ResearchService:
    def __init__(self):
        self.patents_datasource = get_patents_datasource()
        self.demand_datasource = get_demand_datasource()

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


_RESEARCH_SERVICE_INSTANCE = ResearchService()


def get_research_service() -> ResearchService:
    return _RESEARCH_SERVICE_INSTANCE
