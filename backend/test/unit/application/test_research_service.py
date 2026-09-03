"""Unit tests for ResearchService use case."""

import pytest

from application.research_service import ResearchService
from domain.models.runtime_schemas import DemandSignalItem, PatentRecord
from infrastructure.telemetry import PipelineProfiler


class MockPatentsDataSource:
    def __init__(self, patents=None):
        self._patents = patents

    def search_patents(self, query: str, domain: str, limit: int = 20):
        if self._patents is not None:
            return self._patents[:limit]
        return [
            PatentRecord(
                publication_number="ES-2849102-B2",
                title=f"Sample patent for {query}",
                abstract="Technical abstract",
                assignee=["Bilper"],
                filing_date="2020-01-01",
                country_code="ES",
                cpc_codes=["H01M10/052"],
            ),
            PatentRecord(
                publication_number="ES-2849103-B2",
                title=f"Second patent for {query}",
                abstract="Technical abstract 2",
                assignee=["Repsol"],
                filing_date="2021-01-01",
                country_code="ES",
                cpc_codes=["C11D1/00"],
            ),
        ]


class MockDemandDataSource:
    def __init__(self, demands=None):
        self._demands = demands

    def search_demand(self, query: str, domain: str):
        if self._demands is not None:
            return self._demands
        return [
            DemandSignalItem(
                id="dem-1",
                title=f"Industrial challenge {query}",
                description="Challenge description",
                source="Innoget",
                cpc_prefix="H01M",
            )
        ]


@pytest.mark.asyncio
async def test_research_service_conducts_research():
    service = ResearchService(
        patents_datasource=MockPatentsDataSource(),
        demand_datasource=MockDemandDataSource(),
    )
    result = await service.conduct_research(
        query="solid electrolyte",
        domain="solid_state_battery",
        max_patents=10,
    )
    assert result.query == "solid electrolyte"
    assert result.domain == "solid_state_battery"
    assert len(result.patents) == 2
    assert len(result.clusters) == 2
    assert result.cluster_id == "H01M"
    assert result.cluster_context["cluster_id"] == "H01M"


@pytest.mark.asyncio
async def test_research_service_empty_datasources():
    service = ResearchService(
        patents_datasource=MockPatentsDataSource(patents=[]),
        demand_datasource=MockDemandDataSource(demands=[]),
    )
    result = await service.conduct_research(
        query="empty query",
        domain="solid_state_battery",
    )
    assert len(result.patents) == 0
    assert len(result.clusters) == 0
    assert result.cluster_id == "H01M"
    assert result.cluster_context["representative_patents"] == []
    assert result.cluster_context["patent_count"] == 0


@pytest.mark.asyncio
async def test_research_service_explicit_cluster_id():
    service = ResearchService(
        patents_datasource=MockPatentsDataSource(),
        demand_datasource=MockDemandDataSource(),
    )
    result = await service.conduct_research(
        query="cleaning",
        domain="detergent",
        cluster_id="C11D",
    )
    assert result.cluster_id == "C11D"
    assert result.cluster_context["cluster_id"] == "C11D"
    assert "ES-2849103-B2" in result.cluster_context["representative_patents"]


@pytest.mark.asyncio
async def test_research_service_with_profiler():
    profiler = PipelineProfiler()
    service = ResearchService(
        patents_datasource=MockPatentsDataSource(),
        demand_datasource=MockDemandDataSource(),
    )
    result = await service.conduct_research(
        query="solid electrolyte",
        domain="solid_state_battery",
        profiler=profiler,
    )
    summary = profiler.get_summary()
    assert "search_patents" in summary["stages"]
    assert "search_demand" in summary["stages"]
    assert "cluster_patents" in summary["stages"]
    assert len(result.clusters) >= 1
