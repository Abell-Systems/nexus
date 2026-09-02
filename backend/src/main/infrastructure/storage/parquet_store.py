"""Relational Parquet canonical store implementation."""

import hashlib
import json
from datetime import UTC
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.patent import PatentDocument
from domain.models.snapshot import DatasetPart
from domain.protocols.storage import CanonicalStoreProtocol

PATENTS_SCHEMA = pa.schema([
    pa.field("publication_id", pa.string(), nullable=False),
    pa.field("country_code", pa.string(), nullable=False),
    pa.field("doc_number", pa.string(), nullable=False),
    pa.field("kind_code", pa.string(), nullable=False),
    pa.field("application_number", pa.string(), nullable=True),
    pa.field("title", pa.string(), nullable=False),
    pa.field("abstract", pa.string(), nullable=False),
    pa.field("assignees", pa.list_(pa.string()), nullable=False),
    pa.field("inventors", pa.list_(pa.string()), nullable=False),
    pa.field("filing_date", pa.string(), nullable=True),
    pa.field("publication_date", pa.string(), nullable=True),
    pa.field("priority_date", pa.string(), nullable=True),
    pa.field("classifications_cpc", pa.list_(pa.string()), nullable=False),
    pa.field("classifications_ipc", pa.list_(pa.string()), nullable=False),
    pa.field("forward_citation_count", pa.int64(), nullable=True),
    pa.field("backward_citation_count", pa.int64(), nullable=True),
    pa.field("family_id", pa.string(), nullable=True),
])

OBSERVATIONS_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string(), nullable=False),
    pa.field("field_name", pa.string(), nullable=False),
    pa.field("observed_value_json", pa.string(), nullable=False),
    pa.field("value_type", pa.string(), nullable=False),
    pa.field("source_authority", pa.string(), nullable=False),
    pa.field("source_uri", pa.string(), nullable=False),
    pa.field("retrieval_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("raw_payload_sha256", pa.string(), nullable=False),
    pa.field("extraction_version", pa.string(), nullable=False),
    pa.field("verification_status", pa.string(), nullable=False),
])


def _documents_to_table(documents: list[PatentDocument]) -> pa.Table:
    data: dict[str, list[Any]] = {
        "publication_id": [],
        "country_code": [],
        "doc_number": [],
        "kind_code": [],
        "application_number": [],
        "title": [],
        "abstract": [],
        "assignees": [],
        "inventors": [],
        "filing_date": [],
        "publication_date": [],
        "priority_date": [],
        "classifications_cpc": [],
        "classifications_ipc": [],
        "forward_citation_count": [],
        "backward_citation_count": [],
        "family_id": [],
    }
    for doc in documents:
        data["publication_id"].append(doc.publication_id)
        data["country_code"].append(doc.country_code)
        data["doc_number"].append(doc.doc_number)
        data["kind_code"].append(doc.kind_code)
        data["application_number"].append(doc.application_number)
        data["title"].append(doc.title)
        data["abstract"].append(doc.abstract)
        data["assignees"].append(doc.assignees if doc.assignees is not None else [])
        data["inventors"].append(doc.inventors if doc.inventors is not None else [])
        data["filing_date"].append(doc.filing_date)
        data["publication_date"].append(doc.publication_date)
        data["priority_date"].append(doc.priority_date)
        data["classifications_cpc"].append(
            doc.classifications_cpc if doc.classifications_cpc is not None else []
        )
        data["classifications_ipc"].append(
            doc.classifications_ipc if doc.classifications_ipc is not None else []
        )
        data["forward_citation_count"].append(doc.forward_citation_count)
        data["backward_citation_count"].append(doc.backward_citation_count)
        data["family_id"].append(doc.family_id)

    return pa.Table.from_pydict(data, schema=PATENTS_SCHEMA)


def _observations_to_table(observations: list[FieldObservation]) -> pa.Table:
    data: dict[str, list[Any]] = {
        "entity_id": [],
        "field_name": [],
        "observed_value_json": [],
        "value_type": [],
        "source_authority": [],
        "source_uri": [],
        "retrieval_timestamp": [],
        "raw_payload_sha256": [],
        "extraction_version": [],
        "verification_status": [],
    }
    for obs in observations:
        data["entity_id"].append(obs.entity_id)
        data["field_name"].append(obs.field_name)
        data["observed_value_json"].append(obs.observed_value_json)
        data["value_type"].append(obs.value_type)
        data["source_authority"].append(obs.source_authority)
        data["source_uri"].append(obs.source_uri)

        ts = obs.retrieval_timestamp
        ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)
        data["retrieval_timestamp"].append(ts)

        data["raw_payload_sha256"].append(obs.raw_payload_sha256)
        data["extraction_version"].append(obs.extraction_version)
        status_val = (
            obs.verification_status.value
            if isinstance(obs.verification_status, VerificationStatus)
            else str(obs.verification_status)
        )
        data["verification_status"].append(status_val)

    return pa.Table.from_pydict(data, schema=OBSERVATIONS_SCHEMA)


PARQUET_GLOB = "*.parquet"


class ParquetCanonicalStore(CanonicalStoreProtocol):
    """Relational canonical storage organizing patent entities into columnar Parquet files."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_batch(
        self,
        dataset_id: str,
        documents: list[PatentDocument],
        observations: list[FieldObservation],
    ) -> None:
        """Write a batch of patent documents and field observations as Parquet partition parts."""
        base_resolved = self.base_dir.resolve()
        dataset_dir = (self.base_dir / dataset_id).resolve()
        if not dataset_dir.is_relative_to(base_resolved):
            raise ValueError(f"Path traversal detected: {dataset_id}")

        patents_dir = dataset_dir / "patents"
        observations_dir = dataset_dir / "observations"
        patents_dir.mkdir(parents=True, exist_ok=True)
        observations_dir.mkdir(parents=True, exist_ok=True)

        existing_patents = len(list(patents_dir.glob(PARQUET_GLOB)))
        existing_obs = len(list(observations_dir.glob(PARQUET_GLOB)))
        next_idx = max(existing_patents, existing_obs)
        part_filename = f"part_{next_idx:04d}.parquet"

        if documents or not list(patents_dir.glob(PARQUET_GLOB)):
            patents_table = _documents_to_table(documents)
            pq.write_table(patents_table, patents_dir / part_filename)

        if observations or not list(observations_dir.glob(PARQUET_GLOB)):
            obs_table = _observations_to_table(observations)
            pq.write_table(obs_table, observations_dir / part_filename)

    def seal_dataset(self, dataset_id: str) -> tuple[list[DatasetPart], str]:
        """Seal dataset, compute partition hashes and canonical Merkle dataset content hash."""
        base_resolved = self.base_dir.resolve()
        dataset_dir = (self.base_dir / dataset_id).resolve()
        if not dataset_dir.is_relative_to(base_resolved):
            raise ValueError(f"Path traversal detected: {dataset_id}")

        if not dataset_dir.exists():
            return [], hashlib.sha256(b"[]").hexdigest()

        parts: list[DatasetPart] = []
        for parquet_file in sorted(dataset_dir.rglob(PARQUET_GLOB)):
            rel_name = parquet_file.relative_to(dataset_dir).as_posix()
            file_bytes = parquet_file.read_bytes()
            file_sha256 = hashlib.sha256(file_bytes).hexdigest()
            row_count = pq.read_metadata(parquet_file).num_rows
            parts.append(
                DatasetPart(
                    part_name=rel_name,
                    row_count=row_count,
                    file_sha256=file_sha256,
                )
            )

        sorted_parts = sorted(parts, key=lambda p: p.part_name)

        manifest_entries = [
            {
                "file_sha256": p.file_sha256,
                "part_name": p.part_name,
                "row_count": p.row_count,
            }
            for p in sorted_parts
        ]
        dataset_content_sha256 = hashlib.sha256(
            json.dumps(manifest_entries, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return sorted_parts, dataset_content_sha256
