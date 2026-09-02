import re
from datetime import datetime, timezone
from pathlib import Path
import pyarrow.parquet as pq
import pytest

from nexus.domain.models.evidence import FieldObservation, VerificationStatus
from nexus.domain.models.patent import PatentDocument
from nexus.domain.models.snapshot import DatasetPart
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore


def _sample_doc(
    pub_id: str,
    cpc: list[str] | None = None,
    fwd_cit: int | None = None,
    bwd_cit: int | None = None,
) -> PatentDocument:
    return PatentDocument(
        publication_id=pub_id,
        country_code="ES",
        doc_number=pub_id.split("-")[1] if "-" in pub_id else "1234567",
        kind_code="B2",
        application_number="P202030001",
        title="Eco Formulation",
        abstract="A novel formulation.",
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
        observed_value_json='"Eco Formulation"',
        value_type="str",
        source_authority="OEPM BOPI",
        source_uri="https://consultas2.oepm.es/InvenesWeb/",
        retrieval_timestamp=datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc),
        raw_payload_sha256="a" * 64,
        extraction_version="1.0.0",
        verification_status=VerificationStatus.SOURCE_REPORTED,
    )


def test_parquet_store_write_batch_and_seal(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "test_ds_1"

    docs = [
        _sample_doc("ES-2849101-B2", ["C11D1/00"], fwd_cit=10),
        _sample_doc("ES-2849102-B2", ["C11D3/00"], fwd_cit=None),
    ]
    obs = [
        _sample_obs("ES-2849101-B2"),
        _sample_obs("ES-2849102-B2"),
    ]

    store.write_batch(dataset_id, docs, obs)
    parts, dataset_sha = store.seal_dataset(dataset_id)

    assert len(parts) >= 2
    assert all(isinstance(p, DatasetPart) for p in parts)
    assert re.match(r"^[0-9a-f]{64}$", dataset_sha)

    # Check that parts contain patents and observations
    part_names = [p.part_name for p in parts]
    assert any("patents" in name for name in part_names)
    assert any("observations" in name for name in part_names)

    # Verify rows in parts
    patents_part = next(p for p in parts if "patents" in p.part_name)
    assert patents_part.row_count == 2
    assert re.match(r"^[0-9a-f]{64}$", patents_part.file_sha256)


def test_parquet_store_null_citation_preservation(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "test_null_preservation"

    doc = _sample_doc("ES-2849103-B2", fwd_cit=None, bwd_cit=None)
    store.write_batch(dataset_id, [doc], [])

    # Read back the parquet file using PyArrow
    dataset_dir = tmp_path / dataset_id
    patents_files = list((dataset_dir / "patents").glob("*.parquet"))
    assert len(patents_files) == 1

    table = pq.read_table(patents_files[0])
    fwd_col = table.column("forward_citation_count")
    bwd_col = table.column("backward_citation_count")

    # Invariant Gate 1 & 6: NULL preserved, NOT 0
    assert fwd_col[0].as_py() is None
    assert bwd_col[0].as_py() is None


def test_parquet_store_multi_batch_partitioning(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "test_multi_batch"

    # Batch 1
    docs_1 = [_sample_doc("ES-1"), _sample_doc("ES-2")]
    obs_1 = [_sample_obs("ES-1"), _sample_obs("ES-2")]
    store.write_batch(dataset_id, docs_1, obs_1)

    # Batch 2
    docs_2 = [_sample_doc("ES-3"), _sample_doc("ES-4"), _sample_doc("ES-5")]
    obs_2 = [_sample_obs("ES-3"), _sample_obs("ES-4"), _sample_obs("ES-5")]
    store.write_batch(dataset_id, docs_2, obs_2)

    parts, _ = store.seal_dataset(dataset_id)
    patents_parts = [p for p in parts if "patents" in p.part_name]
    obs_parts = [p for p in parts if "observations" in p.part_name]

    assert len(patents_parts) == 2
    assert len(obs_parts) == 2
    assert sum(p.row_count for p in patents_parts) == 5
    assert sum(p.row_count for p in obs_parts) == 5


def test_parquet_store_deterministic_sealing(tmp_path: Path):
    store = ParquetCanonicalStore(tmp_path)
    dataset_id = "test_deterministic"

    docs = [_sample_doc("ES-1", fwd_cit=5)]
    obs = [_sample_obs("ES-1")]
    store.write_batch(dataset_id, docs, obs)

    parts1, sha1 = store.seal_dataset(dataset_id)
    parts2, sha2 = store.seal_dataset(dataset_id)

    assert sha1 == sha2
    assert len(parts1) == len(parts2)
    for p1, p2 in zip(parts1, parts2):
        assert p1.part_name == p2.part_name
        assert p1.row_count == p2.row_count
        assert p1.file_sha256 == p2.file_sha256
