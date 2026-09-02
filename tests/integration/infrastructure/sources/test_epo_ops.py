import hashlib
from pathlib import Path
import httpx
import pytest

from nexus.domain.protocols.sources import PatentSourceProtocol, RawPayload
from nexus.infrastructure.sources.patent.epo_ops_client import EpoOpsClient


def test_epo_ops_client_implements_patent_source_protocol():
    client = EpoOpsClient.from_fixture_file("tests/fixtures/epo_ops_sample.xml")
    assert isinstance(client, PatentSourceProtocol)


def test_epo_ops_client_fetch_from_fixture_file():
    fixture_path = Path("tests/fixtures/epo_ops_sample.xml")
    assert fixture_path.exists(), f"Fixture file {fixture_path} must exist"

    expected_bytes = fixture_path.read_bytes()
    expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()

    client = EpoOpsClient.from_fixture_file(fixture_path)
    batches = list(client.fetch_batches(cql_query="pn=ES and pd within '2016 2024'"))

    assert len(batches) == 1
    batch = batches[0]
    assert isinstance(batch, RawPayload)
    assert batch.source_id == "epo_ops"
    assert batch.payload_bytes == expected_bytes
    assert batch.payload_sha256 == expected_sha256
    assert len(batch.payload_sha256) == 64
    assert batch.metadata["source_authority"] == "European Patent Office (EPO OPS 3.2)"
    assert batch.metadata["official_catalog_url"] == "https://ops.epo.org"
    assert batch.metadata["cql_query"] == "pn=ES and pd within '2016 2024'"
    assert batch.metadata["content_type"] == "application/xml"
    assert batch.retrieval_timestamp is not None


def test_epo_ops_client_fixture_missing_file_raises():
    client = EpoOpsClient.from_fixture_file("tests/fixtures/non_existent_epo.xml")
    with pytest.raises(FileNotFoundError, match="not found"):
        list(client.fetch_batches())


def test_epo_ops_client_missing_credentials_raises():
    client = EpoOpsClient(consumer_key=None, consumer_secret=None)
    with pytest.raises(RuntimeError, match="credentials"):
        list(client.fetch_batches())


def test_epo_ops_client_live_http_mocked_flow():
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org">
  <ops:biblio-search total-result-count="1">
    <exchange-documents>
      <exchange-document country="ES" doc-number="2999999" kind="A1">
        <invention-title lang="es">Dispositivo mock</invention-title>
      </exchange-document>
    </exchange-documents>
  </ops:biblio-search>
</ops:world-patent-data>"""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/auth/accesstoken" in url_str:
            assert request.method == "POST"
            # Verify Basic Auth and body
            auth_header = request.headers.get("authorization", "")
            assert auth_header.startswith("Basic ")
            return httpx.Response(200, json={"access_token": "mock_access_token_123", "token_type": "Bearer", "expires_in": "3600"})
        elif "/published-data/search/biblio" in url_str:
            assert request.method == "GET"
            assert request.headers.get("authorization") == "Bearer mock_access_token_123"
            assert request.headers.get("accept") == "application/xml"
            assert "pn%3DES" in url_str or "pn=ES" in url_str
            return httpx.Response(200, content=xml_content, headers={"Content-Type": "application/xml"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = EpoOpsClient(
        consumer_key="test_key",
        consumer_secret="test_secret",
        transport=transport,
    )

    batches = list(client.fetch_batches(cql_query="pn=ES", range_start=1, range_end=10))
    assert len(batches) == 1
    batch = batches[0]
    assert batch.source_id == "epo_ops"
    assert batch.payload_bytes == xml_content
    assert batch.payload_sha256 == hashlib.sha256(xml_content).hexdigest()
    assert batch.metadata["source_authority"] == "European Patent Office (EPO OPS 3.2)"
    assert batch.metadata["cql_query"] == "pn=ES"


def test_epo_ops_client_auth_failure_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    transport = httpx.MockTransport(handler)
    client = EpoOpsClient(
        consumer_key="bad_key",
        consumer_secret="bad_secret",
        transport=transport,
    )

    with pytest.raises(RuntimeError, match="Authentication failed"):
        list(client.fetch_batches(cql_query="pn=ES"))


def test_epo_ops_client_search_endpoint_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/auth/accesstoken" in url_str:
            return httpx.Response(200, json={"access_token": "tok_xyz"})
        return httpx.Response(500, content=b"Internal Server Error")

    transport = httpx.MockTransport(handler)
    client = EpoOpsClient(
        consumer_key="key",
        consumer_secret="sec",
        transport=transport,
    )

    with pytest.raises(RuntimeError, match="Search/Fetch failed"):
        list(client.fetch_batches(cql_query="pn=ES"))
