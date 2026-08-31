import pytest
from unittest.mock import MagicMock
import patent_agent.tools.bigquery_patents as bqp
from patent_agent.tools.bigquery_patents import BigQueryPatentsDataSource, get_patents_datasource
from patent_agent.tools.schemas import PatentRecord


@pytest.fixture(autouse=True)
def _reset_datasource_singleton():
    """get_patents_datasource() is memoized process-wide; isolate that global
    across tests so one test's monkeypatched env/client doesn't leak into the next."""
    bqp._datasource_singleton = None
    yield
    bqp._datasource_singleton = None


def test_bigquery_search_patents_fallback_on_error():
    ds = BigQueryPatentsDataSource(project="test-project")
    # Simulate client throwing an Exception (e.g., auth failure or quota error)
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery connection error")

    records = ds.search_patents("solid electrolyte", "batteries", max_results=5)
    assert len(records) > 0
    assert isinstance(records[0], PatentRecord)
    assert records[0].publication_number is not None


def test_bigquery_get_patent_by_number_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    patent = ds.get_patent_by_number("US-1234567-A")
    assert patent is not None
    assert patent.publication_number == "US-1234567-A"


def test_bigquery_get_citations_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    citations = ds.get_citations("US-1234567-A")
    assert isinstance(citations, list)
    assert len(citations) > 0


def test_bigquery_get_similar_patents_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    similar = ds.get_similar_patents("US-1234567-A", max_results=3)
    assert isinstance(similar, list)
    assert len(similar) > 0


def _fake_query_result(rows):
    """Mimics client.query(sql, job_config=...).result() -> iterable of row objects."""
    query_result = MagicMock()
    query_result.result.return_value = rows
    return query_result


def _fake_row(**fields):
    row = MagicMock()
    for key, value in fields.items():
        setattr(row, key, value)
    return row


def test_bigquery_search_patents_sets_maximum_bytes_billed(monkeypatch):
    monkeypatch.setenv("BIGQUERY_MAX_BYTES_BILLED", "123456")
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.return_value = _fake_query_result(
        [_fake_row(publication_number="US-1", title="t", abstract="a", cpc_codes=[], assignee=[],
                    filing_date="2025-01-01", publication_date="2025-06-01", country_code="US")]
    )

    ds.search_patents("solid electrolyte", "batteries", max_results=5)

    _, kwargs = ds._client.query.call_args
    assert kwargs["job_config"].maximum_bytes_billed == 123456


def test_bigquery_search_patents_caches_and_marks_source():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.return_value = _fake_query_result(
        [_fake_row(publication_number="US-1", title="t", abstract="a", cpc_codes=[], assignee=[],
                    filing_date="2025-01-01", publication_date="2025-06-01", country_code="US")]
    )

    first = ds.search_patents("solid electrolyte", "batteries", max_results=5)
    assert ds.last_result_source == "bigquery"
    assert ds._client.query.call_count == 1

    second = ds.search_patents("solid electrolyte", "batteries", max_results=5)
    assert ds.last_result_source == "bigquery_cached"
    assert ds._client.query.call_count == 1  # served from cache, no second query
    assert second == first


def test_bigquery_last_result_source_reflects_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    ds.search_patents("solid electrolyte", "batteries", max_results=5)
    assert ds.last_result_source == "mock_fallback"


def test_bigquery_get_status_reports_mock_only_methods():
    ds = BigQueryPatentsDataSource(project="test-project")
    status = ds.get_status()
    assert status["type"] == "bigquery"
    assert status["get_citations_backed_by"] == "bigquery"
    assert status["get_similar_patents_backed_by"] == "mock"  # not wired yet -- see get_similar_patents
    assert status["search_patents_backed_by"] == "bigquery"


def test_bigquery_get_citations_sets_maximum_bytes_billed_and_reads_domain_index(monkeypatch):
    monkeypatch.setenv("BIGQUERY_MAX_BYTES_BILLED", "654321")
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.return_value = _fake_query_result(
        [_fake_row(publication_number="US-2", title="cited t", abstract="cited a", cpc_codes=[], assignee=[],
                    filing_date="2020-01-01", publication_date="2020-06-01", country_code="US")]
    )

    citations = ds.get_citations("US-1234567-A")

    assert len(citations) == 1
    assert citations[0].publication_number == "US-2"
    assert ds.last_result_source == "bigquery"

    sql, kwargs = ds._client.query.call_args[0][0], ds._client.query.call_args[1]
    assert "UNNEST(src.citations)" in sql
    assert bqp.DOMAIN_INDEX_TABLE in sql
    assert kwargs["job_config"].maximum_bytes_billed == 654321


def test_bigquery_get_citations_caches():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.return_value = _fake_query_result(
        [_fake_row(publication_number="US-2", title="cited t", abstract="cited a", cpc_codes=[], assignee=[],
                    filing_date="2020-01-01", publication_date="2020-06-01", country_code="US")]
    )

    ds.get_citations("US-1234567-A")
    ds.get_citations("US-1234567-A")

    assert ds._client.query.call_count == 1
    assert ds.last_result_source == "bigquery_cached"


def test_mock_datasource_get_status():
    from patent_agent.tools.bigquery_patents import MockPatentsDataSource

    assert MockPatentsDataSource().get_status() == {"type": "mock", "last_query_source": "mock"}


def test_get_patents_datasource_memoizes_bigquery_instance(monkeypatch):
    monkeypatch.setenv("USE_MOCK_BIGQUERY", "false")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    construct_calls: list[str] = []

    class FakeBigQueryDataSource:
        def __init__(self, project):
            construct_calls.append(project)

    monkeypatch.setattr(bqp, "BigQueryPatentsDataSource", FakeBigQueryDataSource)

    first = get_patents_datasource()
    second = get_patents_datasource()

    assert first is second
    assert construct_calls == ["test-project"]


def test_get_patents_datasource_memoizes_mock_instance(monkeypatch):
    monkeypatch.setenv("USE_MOCK_BIGQUERY", "true")

    first = get_patents_datasource()
    second = get_patents_datasource()

    assert first is second
