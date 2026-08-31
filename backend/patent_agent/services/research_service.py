"""Unified Research Service for IP-Matchmaker.

Provides a single, authoritative research layer that:
1. Concurrently fetches prior art patents and enterprise demand signals.
2. Clusters patents to detect white spaces.
3. Selects the target opportunity cluster and generates rich technical context.
4. Returns a strongly typed ResearchResult consumable by both API endpoints and ADK agent graphs.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from ..shared.telemetry import PipelineProfiler
from ..tools.bigquery_patents import get_patents_datasource
from ..tools.clustering import cluster_patents
from ..tools.context import build_cluster_context
from ..tools.demand_sources import get_demand_datasource
from ..tools.schemas import DemandSignal, PatentCluster, PatentRecord


@dataclass
class ResearchResult:
    """Strongly typed output of the unified research phase."""

    query: str
    domain: str
    patents: list[PatentRecord] = field(default_factory=list)
    demand_signals: list[DemandSignal] = field(default_factory=list)
    clusters: list[PatentCluster] = field(default_factory=list)
    selected_cluster: Optional[PatentCluster] = None
    cluster_id: str = "unknown"
    cluster_context: str = ""


class ResearchService:
    """Unified service for patent retrieval, demand matching, and clustering."""

    def __init__(self, patents_datasource=None, demand_datasource=None):
        self._patents_datasource = patents_datasource
        self._demand_datasource = demand_datasource

    def _get_patents_ds(self):
        if self._patents_datasource:
            return self._patents_datasource
        import sys
        if "main" in sys.modules and hasattr(sys.modules["main"], "get_patents_datasource"):
            return sys.modules["main"].get_patents_datasource()
        return get_patents_datasource()

    def _get_demand_ds(self):
        if self._demand_datasource:
            return self._demand_datasource
        import sys
        if "main" in sys.modules and hasattr(sys.modules["main"], "get_demand_datasource"):
            return sys.modules["main"].get_demand_datasource()
        return get_demand_datasource()


    async def conduct_research(
        self,
        query: str,
        domain: str,
        cluster_id: Optional[str] = None,
        max_patents: int = 20,
        profiler: Optional[PipelineProfiler] = None,
    ) -> ResearchResult:
        """Executes concurrent retrieval and clustering, returning a unified ResearchResult."""
        patents_ds = self._get_patents_ds()
        demand_ds = self._get_demand_ds()

        if profiler:
            with profiler.span("retrieval_concurrent_io", category="retrieval_io"):
                records_task = asyncio.to_thread(patents_ds.search_patents, query, domain, max_patents)
                demand_task = asyncio.to_thread(demand_ds.search_demand, query, domain)
                records, demand_signals = await asyncio.gather(records_task, demand_task)
        else:
            records_task = asyncio.to_thread(patents_ds.search_patents, query, domain, max_patents)
            demand_task = asyncio.to_thread(demand_ds.search_demand, query, domain)
            records, demand_signals = await asyncio.gather(records_task, demand_task)

        if profiler:
            with profiler.span("clustering", category="clustering"):
                clusters = cluster_patents(records, demand_signals)
        else:
            clusters = cluster_patents(records, demand_signals)

        selected_id = cluster_id or (clusters[0].cluster_id if clusters else "unknown")
        selected_cluster = next((c for c in clusters if c.cluster_id == selected_id), None)
        if selected_cluster is None and clusters:
            selected_cluster = clusters[0]
            selected_id = selected_cluster.cluster_id

        cluster_context = (
            build_cluster_context(selected_cluster, records, demand_signals)
            if selected_cluster
            else ""
        )

        return ResearchResult(
            query=query,
            domain=domain,
            patents=records,
            demand_signals=demand_signals,
            clusters=clusters,
            selected_cluster=selected_cluster,
            cluster_id=selected_id,
            cluster_context=cluster_context,
        )


_default_research_service: Optional[ResearchService] = None


def get_research_service() -> ResearchService:
    """Singleton getter for the default ResearchService."""
    global _default_research_service
    if _default_research_service is None:
        _default_research_service = ResearchService()
    return _default_research_service
