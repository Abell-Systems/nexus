"""Unit tests for OPS pagination + enumerability verification (ADR 0020 §3, §4 support)."""

from collections.abc import Iterator

import pytest

from domain.protocols.sources import RawPayload
from infrastructure.sources.patent.ops_pagination import (
    fetch_all_ops_batches,
    parse_total_result_count,
)

ONE_DOC_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org">
  <ops:biblio-search total-result-count="3">
    <exchange-documents><exchange-document country="US" doc-number="1" kind="B2"/></exchange-documents>
  </ops:biblio-search>
</ops:world-patent-data>"""

NO_COUNT_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org">
  <ops:biblio-search><exchange-documents/></ops:biblio-search>
</ops:world-patent-data>"""


def test_parse_total_result_count_reads_attribute():
    assert parse_total_result_count(ONE_DOC_PAGE) == 3


def test_parse_total_result_count_returns_none_when_absent():
    assert parse_total_result_count(NO_COUNT_PAGE) is None


class _FakeClient:
    """Test double: EpoOpsClient-shaped, returns one canned page per call, by range."""

    def __init__(self, pages_by_range: dict[tuple[int, int], bytes]) -> None:
        self._pages = pages_by_range
        self.calls: list[tuple[int, int]] = []

    def fetch_batches(
        self, cql_query: str = "", range_start: int = 1, range_end: int = 25
    ) -> Iterator[RawPayload]:
        self.calls.append((range_start, range_end))
        yield RawPayload(
            source_id="epo_ops",
            batch_id=f"batch_{range_start}_{range_end}",
            payload_bytes=self._pages[(range_start, range_end)],
            metadata={},
        )


def test_fetch_all_ops_batches_stops_at_total_result_count():
    page1 = b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="3"/></ops:world-patent-data>'
    page2 = b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="3"/></ops:world-patent-data>'
    client = _FakeClient({(1, 2): page1, (3, 4): page2})

    batches = list(fetch_all_ops_batches(client, cql_query="pn=US", page_size=2))

    assert len(batches) == 2
    assert client.calls == [(1, 2), (3, 4)]


def test_fetch_all_ops_batches_raises_on_missing_total_count():
    client = _FakeClient({(1, 100): NO_COUNT_PAGE})
    with pytest.raises(RuntimeError, match="total-result-count"):
        list(fetch_all_ops_batches(client, cql_query="pn=US"))


def test_fetch_all_ops_batches_raises_when_max_records_reached_before_total():
    huge_total = b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="1000"/></ops:world-patent-data>'
    client = _FakeClient({(1, 10): huge_total})
    with pytest.raises(RuntimeError, match="max_records"):
        list(fetch_all_ops_batches(client, cql_query="pn=US", page_size=10, max_records=10))
