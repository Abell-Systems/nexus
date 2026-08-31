import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from patent_agent.tools.bigquery_patents import MockPatentsDataSource
from patent_agent.tools.schemas import PatentRecord


def test_search_patents_returns_valid_records():
    source = MockPatentsDataSource()
    records = source.search_patents("battery electrolyte", "energy storage", max_results=5)

    assert len(records) == 5
    for record in records:
        assert isinstance(record, PatentRecord)
        assert record.publication_number
        assert record.title
        assert record.cpc_codes


def test_search_patents_is_deterministic():
    source = MockPatentsDataSource()
    first = source.search_patents("battery electrolyte", "energy storage", max_results=3)
    second = source.search_patents("battery electrolyte", "energy storage", max_results=3)

    assert [r.publication_number for r in first] == [r.publication_number for r in second]


def test_get_similar_patents_sets_similarity_score():
    source = MockPatentsDataSource()
    similar = source.get_similar_patents("US-11234567-B2", max_results=3)

    assert len(similar) == 3
    assert all(r.similarity_score is not None for r in similar)
    scores = [r.similarity_score for r in similar]
    assert scores == sorted(scores, reverse=True)


def test_get_patent_by_number_echoes_requested_number():
    source = MockPatentsDataSource()
    record = source.get_patent_by_number("US-99999999-B2")

    assert record is not None
    assert record.publication_number == "US-99999999-B2"
