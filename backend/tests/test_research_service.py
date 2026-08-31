import pytest
import os
from patent_agent.services.research_service import ResearchService, ResearchResult, get_research_service
from patent_agent.tools.schemas import PatentRecord, DemandSignal

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")


@pytest.mark.anyio
async def test_research_service_conduct_research():
    service = get_research_service()
    res = await service.conduct_research(
        query="solid electrolyte interphase",
        domain="solid-state battery electrolytes",
        max_patents=10,
    )
    assert isinstance(res, ResearchResult)
    assert res.query == "solid electrolyte interphase"
    assert res.domain == "solid-state battery electrolytes"
    assert len(res.patents) > 0
    assert len(res.clusters) > 0
    assert res.selected_cluster is not None
    assert res.cluster_id != "unknown"
    assert len(res.cluster_context) > 0
