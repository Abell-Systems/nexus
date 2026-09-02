"""Unit tests for ResearchService use case."""

import pytest

from application.research_service import ResearchService
from domain.models.runtime_schemas import DemandSignalItem, PatentRecord


class MockPatentsDataSource:
    def search_patents(self, query: str, domain: str, limit: int = 20):
        return [
            PatentRecord(
                publication_number="ES-2849102-B2",
                title=f"Sample patent for {query}",
                abstract="Technical abstract",
                assignee=["Bilper"],
                filing_date="2020-01-01",
                country_code="ES",
                cpc_codes=["H01M10/052"],
            )
        ]


class MockDemandDataSource:
    def search_demand(self, query: str, domain: str):
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
    assert len(result.patents) == 1
    assert len(result.clusters) == 1
    assert result.cluster_id == "H01M"
    assert result.cluster_context["cluster_id"] == "H01M"
