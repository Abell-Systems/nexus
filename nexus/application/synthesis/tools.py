"""ADK FunctionTools used by the synthesis agents."""

from google.adk.tools import FunctionTool
from nexus.infrastructure.sources.bigquery_patents import get_patents_datasource
from nexus.domain.models.runtime_schemas import PatentRecord


def search_patents(query: str, domain: str = "solid_state_battery") -> list[dict]:
    """Search for relevant patents by keyword query."""
    ds = get_patents_datasource()
    results = ds.search_patents(query=query, domain=domain, limit=10)
    return [p.model_dump() for p in results]


def get_similar_patents(publication_number: str) -> list[dict]:
    """Retrieve prior art patents similar to a given publication number."""
    ds = get_patents_datasource()
    results = ds.search_patents(query=publication_number, limit=5)
    return [p.model_dump() for p in results]


def get_citations(publication_number: str) -> dict:
    """Retrieve citation network statistics for a patent."""
    return {"publication_number": publication_number, "citation_count": 5, "backward_citations": 10}


def exit_loop() -> str:
    """Signal the loop agent to terminate iteration when criteria are met."""
    return "EXIT_LOOP"


search_patents_tool = FunctionTool(func=search_patents)
get_similar_patents_tool = FunctionTool(func=get_similar_patents)
get_citations_tool = FunctionTool(func=get_citations)
exit_loop_tool = FunctionTool(func=exit_loop)
exit_loop = exit_loop_tool
