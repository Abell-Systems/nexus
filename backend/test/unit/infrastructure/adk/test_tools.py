"""Unit tests for ADK agent FunctionTools."""

from infrastructure.adk.tools import exit_loop, get_citations, get_similar_patents, search_patents


def test_search_patents_tool():
    results = search_patents(query="electrolyte", domain="solid_state_battery")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "publication_number" in results[0]


def test_get_similar_patents_tool():
    results = get_similar_patents(publication_number="ES-2849102-B2")
    assert isinstance(results, list)
    assert len(results) > 0


def test_get_citations_tool():
    res = get_citations(publication_number="ES-2849102-B2")
    assert res["publication_number"] == "ES-2849102-B2"
    assert res["citation_count"] == 5


def test_exit_loop_tool():
    assert exit_loop() == "EXIT_LOOP"
