"""Streaming ingestion pipeline orchestrating raw storage, normalization, validation, and canonical sealing."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from application.ingestion.normalizers.base import PatentNormalizerProtocol
from application.ingestion.validator import PatentValidator
from domain.models.evidence import FieldObservation
from domain.models.patent import PatentDocument
from domain.models.snapshot import DatasetPart, DatasetSnapshot, RawBatch
from domain.protocols.sources import PatentSourceProtocol
from domain.protocols.storage import CanonicalStoreProtocol, RawStoreProtocol


class IngestionSummary(BaseModel):
    """Summary metrics and manifest reference produced upon completing an ingestion run."""

    snapshot: DatasetSnapshot
    processed_records: int
    error_count: int


class IngestionPipeline:
    """End-to-end streaming ingestion pipeline for patent data sources."""

    def __init__(
        self,
        raw_store: RawStoreProtocol,
        canonical_store: CanonicalStoreProtocol,
        validator: PatentValidator | None = None,
    ) -> None:
        self.raw_store = raw_store
        self.canonical_store = canonical_store
        self.validator = validator or PatentValidator()

    def ingest_patent_source(
        self,
        source: PatentSourceProtocol,
        normalizer: PatentNormalizerProtocol,
        dataset_id: str,
        manifest_output_dir: Path | str,
        transformation_version: str = "1.0.0",
        created_at: datetime | None = None,
    ) -> IngestionSummary:
        """Stream raw batches from source, store payloads, normalize, validate, and seal dataset."""
        manifest_dir = Path(manifest_output_dir)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        source_batches: list[RawBatch] = []
        total_records = 0

        for raw_payload in source.fetch_batches():
            # 1. Immutable raw payload storage
            self.raw_store.store_payload(
                source_id=raw_payload.source_id,
                payload_bytes=raw_payload.payload_bytes,
                metadata=raw_payload.metadata,
                file_ext="json",
            )

            # 2. Track raw batch identity
            source_batches.append(
                RawBatch(
                    batch_id=raw_payload.batch_id,
                    source_id=raw_payload.source_id,
                    retrieval_timestamp=raw_payload.retrieval_timestamp,
                    payload_sha256=raw_payload.payload_sha256,
                )
            )

            # 3. Stream normalization
            batch_docs: list[PatentDocument] = []
            batch_obs: list[FieldObservation] = []
            for doc, obs_list in normalizer.normalize_stream(raw_payload):
                batch_docs.append(doc)
                batch_obs.extend(obs_list)

            # 4. Validation
            self.validator.validate_batch(batch_docs)

            # 5. Canonical storage append
            self.canonical_store.write_batch(
                dataset_id=dataset_id,
                documents=batch_docs,
                observations=batch_obs,
            )
            total_records += len(batch_docs)

        # 6. Seal canonical dataset
        parts_data, dataset_content_sha256 = self.canonical_store.seal_dataset(dataset_id)
        parts: list[DatasetPart] = []
        for p in parts_data:
            if isinstance(p, DatasetPart):
                parts.append(p)
            elif isinstance(p, (tuple, list)) and len(p) == 3:
                parts.append(DatasetPart(part_name=p[0], row_count=p[1], file_sha256=p[2]))
            elif isinstance(p, dict):
                parts.append(DatasetPart(**p))

        if created_at is None:
            created_at = max(b.retrieval_timestamp for b in source_batches) if source_batches else datetime.now(UTC)

        # Compute deterministic manifest SHA256
        snapshot_dict = {
            "dataset_id": dataset_id,
            "schema_version": "1.0.0",
            "source_batches": [b.model_dump(mode="json") for b in source_batches],
            "record_count": total_records,
            "parts": [p.model_dump(mode="json") for p in parts],
            "dataset_content_sha256": dataset_content_sha256,
            "created_at": created_at.isoformat(),
            "transformation_version": transformation_version,
        }
        manifest_sha256 = hashlib.sha256(
            json.dumps(snapshot_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()

        snapshot = DatasetSnapshot(
            dataset_id=dataset_id,
            schema_version="1.0.0",
            source_batches=source_batches,
            record_count=total_records,
            parts=parts,
            dataset_content_sha256=dataset_content_sha256,
            manifest_sha256=manifest_sha256,
            created_at=created_at,
            transformation_version=transformation_version,
        )

        # Persist manifest to disk
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (manifest_dir / "manifest.json").write_text(snapshot.model_dump_json(indent=2))
        (manifest_dir / f"{dataset_id}_manifest.json").write_text(snapshot.model_dump_json(indent=2))

        return IngestionSummary(
            snapshot=snapshot,
            processed_records=total_records,
            error_count=0,
        )
