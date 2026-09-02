from datetime import datetime, timezone
from pathlib import Path
import pytest

from nexus.domain.models.evidence import FieldObservation, VerificationStatus
from nexus.domain.models.patent import PatentDocument
from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore


def _sample_doc(
    pub_id: str,
    cpc: list[str] | None = None,
    fwd_cit: int | None = None,
    bwd_cit: int | None = None,
    title: str = "Test Title",
) -> PatentDocument:
    return PatentDocument(
        publication_id=pub_id,
        country_code="ES",
        doc_number=pub_id.split("-")[1] if "-" in pub_id else "1234567",
        kind_code="B2",
        application_number="P202030001",
        title=title,
        abstract="Abstract description.",
        assignees=["UNIVERSIDAD DE SEVILLA"],
        inventors=["GARCIA, Juan"],
        filing_date="2020-05-15",
        publication_date="2021-11-25",
        priority_date="2020-05-15",
        classifications_cpc=cpc or ["C11D1/00"],
        classifications_ipc=["C11D1/00"],
        forward_citation_count=fwd_cit,
        backward_citation_count=bwd_cit,
        family_id="FAM-100",
    )


def _sample_obs(entity_id: str, field_name: str = "title") -> FieldObservation:
    return FieldObservation(
        entity_id=entity_id,
        field_name=field_name,
        observed_value_json='"Test Title"',
        value_type="str",
        source_authority="OEPM BOPI",
        source_uri="https://consultas2.oepm.es/InvenesWeb/",
        retrieval_timestamp=datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc),
        raw_payload_sha256="a" * 64,
        extraction_version="1.0.0",
        verification_status=VerificationStatus.SOURCE_REPORTED,
    )


def test_duckdb_engine_zero_copy_view_registration(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "ds_zero_copy"

    docs = [
        _sample_doc("ES-1", ["C11D1/00"], fwd_cit=5),
        _sample_doc("ES-2", ["C11D3/00"], fwd_cit=15),
    ]
    obs = [_sample_obs("ES-1"), _sample_obs("ES-2")]
    store.write_batch(dataset_id, docs, obs)
    store.seal_dataset(dataset_id)

    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / dataset_id)

    # Verify query engine executes against views without duplicating into memory
    patents_res = engine.search_by_cpc_prefix("C11D")
    assert len(patents_res) == 2
    pub_ids = {r["publication_id"] for r in patents_res}
    assert pub_ids == {"ES-1", "ES-2"}


def test_duckdb_engine_search_by_cpc_prefix(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "ds_search"

    docs = [
        _sample_doc("ES-1", ["C11D1/00", "C11D3/382"], title="Doc 1"),
        _sample_doc("ES-2", ["C11D1/02"], title="Doc 2"),
        _sample_doc("ES-3", ["A61K8/00"], title="Doc 3"),
    ]
    obs = [_sample_obs(d.publication_id) for d in docs]
    store.write_batch(dataset_id, docs, obs)
    store.seal_dataset(dataset_id)

    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / dataset_id)

    # Prefix match
    c11d_results = engine.search_by_cpc_prefix("C11D")
    assert len(c11d_results) == 2
    assert {r["publication_id"] for r in c11d_results} == {"ES-1", "ES-2"}

    # Sub-prefix match
    c11d3_results = engine.search_by_cpc_prefix("C11D3")
    assert len(c11d3_results) == 1
    assert c11d3_results[0]["publication_id"] == "ES-1"

    # Other branch match
    a61k_results = engine.search_by_cpc_prefix("A61K")
    assert len(a61k_results) == 1
    assert a61k_results[0]["publication_id"] == "ES-3"

    # Non-existent branch match
    empty_results = engine.search_by_cpc_prefix("H01M")
    assert empty_results == []


def test_duckdb_engine_scientific_invariant_none_not_zero(tmp_path: Path):
    """Scientific Gate 1: None != 0 in aggregate calculations.

    1 patent with 10 citations and 1 patent with None citations MUST yield
    avg_forward_citations == 10.0, not 5.0.
    """
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "ds_invariant_gate1"

    docs = [
        _sample_doc("ES-1", ["C11D1/00"], fwd_cit=10),
        _sample_doc("ES-2", ["C11D1/02"], fwd_cit=None),  # Unobserved citation count
    ]
    obs = [_sample_obs("ES-1"), _sample_obs("ES-2")]
    store.write_batch(dataset_id, docs, obs)
    store.seal_dataset(dataset_id)

    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / dataset_id)
    aggs = engine.get_cluster_aggregates("C11D")

    assert aggs["patent_count"] == 2
    assert aggs["observed_citations_count"] == 1
    assert aggs["avg_forward_citations"] == 10.0


def test_duckdb_engine_aggregates_all_null_citations(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "ds_all_null"

    docs = [
        _sample_doc("ES-1", ["C11D1/00"], fwd_cit=None),
        _sample_doc("ES-2", ["C11D1/02"], fwd_cit=None),
    ]
    obs = [_sample_obs("ES-1"), _sample_obs("ES-2")]
    store.write_batch(dataset_id, docs, obs)
    store.seal_dataset(dataset_id)

    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / dataset_id)
    aggs = engine.get_cluster_aggregates("C11D")

    assert aggs["patent_count"] == 2
    assert aggs["observed_citations_count"] == 0
    assert aggs["avg_forward_citations"] is None


def test_duckdb_engine_aggregates_empty_match(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "ds_empty"

    docs = [_sample_doc("ES-1", ["C11D1/00"], fwd_cit=5)]
    obs = [_sample_obs("ES-1")]
    store.write_batch(dataset_id, docs, obs)
    store.seal_dataset(dataset_id)

    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / dataset_id)
    aggs = engine.get_cluster_aggregates("NON_EXISTENT")

    assert aggs["patent_count"] == 0
    assert aggs["observed_citations_count"] == 0
    assert aggs["avg_forward_citations"] is None


def test_end_to_end_ingestion_and_duckdb_query(tmp_path: Path):
    from typing import Iterator
    import json
    from nexus.application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
    from nexus.application.ingestion.pipeline import IngestionPipeline
    from nexus.domain.protocols.sources import RawPayload
    from nexus.infrastructure.storage.raw_store import FilesystemRawStore

    raw_store = FilesystemRawStore(tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(tmp_path / "canonical")
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store)

    sample_oepm_json = json.dumps([
        {
            "publication_number": "ES-2849101-B2",
            "title": "Bio surfactant compound",
            "abstract": "Biodegradable composition.",
            "cpc_codes": ["C11D1/00", "C11D3/382"],
            "ipc_codes": ["C11D1/00"],
            "filing_date": "2020-05-15",
            "publication_date": "2021-11-25",
            "forward_citation_count": 8,
        },
        {
            "publication_number": "ES-2849102-B2",
            "title": "Unobserved citations compound",
            "abstract": "Another composition.",
            "cpc_codes": ["C11D1/02"],
            "ipc_codes": ["C11D1/02"],
            "filing_date": "2020-06-01",
            "publication_date": "2021-12-10",
        },
    ]).encode("utf-8")

    class MockSource:
        def fetch_batches(self) -> Iterator[RawPayload]:
            yield RawPayload(
                batch_id="batch_001",
                source_id="oepm_bopi",
                retrieval_timestamp=datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc),
                payload_bytes=sample_oepm_json,
                metadata={"source": "OEPM", "year": 2026},
            )

    summary = pipeline.ingest_patent_source(
        source=MockSource(),
        normalizer=OepmNormalizer(),
        dataset_id="oepm_2026",
        manifest_output_dir=tmp_path / "manifests",
    )

    assert summary.processed_records == 2
    assert summary.error_count == 0

    # Query with DuckDbQueryEngine
    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / "canonical" / "oepm_2026")
    results = engine.search_by_cpc_prefix("C11D")
    assert len(results) == 2

    aggs = engine.get_cluster_aggregates("C11D")
    assert aggs["patent_count"] == 2
    assert aggs["observed_citations_count"] == 1
    assert aggs["avg_forward_citations"] == 8.0

