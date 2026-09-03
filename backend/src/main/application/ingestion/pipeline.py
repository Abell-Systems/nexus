"""Streaming ingestion pipeline orchestrating raw storage, normalization, validation, and canonical sealing."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from application.ingestion.manifest_builder import EnhancedManifestBuilder
from application.ingestion.normalizers.base import PatentNormalizerProtocol
from application.ingestion.validator import PatentValidator
from domain.models.evidence import FieldObservation
from domain.models.ingestion import EnhancedManifest, RecordDisposition
from domain.models.patent import PatentDocument
from domain.models.snapshot import DatasetPart, DatasetSnapshot, RawBatch
from domain.protocols.sources import PatentSourceProtocol
from domain.protocols.storage import CanonicalStoreProtocol, RawStoreProtocol


class IngestionSummary(BaseModel):
    """Summary metrics and manifest reference produced upon completing an ingestion run."""

    snapshot: DatasetSnapshot
    processed_records: int
    error_count: int
    enhanced_manifest: EnhancedManifest | None = None


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
        file_ext: str = "json",
    ) -> IngestionSummary:
        """Stream raw batches from source, store payloads, normalize, validate, and seal dataset."""
        manifest_dir = Path(manifest_output_dir)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        source_batches: list[RawBatch] = []
        total_records = 0

        manifest_builder = EnhancedManifestBuilder(
            dataset_id=dataset_id,
            normalizer_version=transformation_version,
        )
        self.validator.reset_deduplication()

        for raw_payload in source.fetch_batches():
            manifest_builder.record_raw_payload()

            # 1. Immutable raw payload storage
            ext = file_ext or raw_payload.metadata.get("file_ext", "json")
            self.raw_store.store_payload(
                source_id=raw_payload.source_id,
                payload_bytes=raw_payload.payload_bytes,
                metadata=raw_payload.metadata,
                file_ext=ext,
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

            # 3. Stream normalization and validation
            batch_docs: list[PatentDocument] = []
            batch_obs: list[FieldObservation] = []

            # Check if normalizer provides full normalize_results
            if hasattr(normalizer, "normalize_results"):
                for raw_res in normalizer.normalize_results(raw_payload):
                    val_res = self.validator.validate_normalization_result(raw_res)
                    manifest_builder.record_normalization_result(val_res)
                    if val_res.disposition == RecordDisposition.INCLUDED and val_res.document is not None:
                        batch_docs.append(val_res.document)
                        batch_obs.extend(val_res.observations)
            else:
                for doc, obs_list in normalizer.normalize_stream(raw_payload):
                    self.validator.validate_document(doc)
                    batch_docs.append(doc)
                    batch_obs.extend(obs_list)

            # 4. Canonical storage append
            if batch_docs or batch_obs:
                self.canonical_store.write_batch(
                    dataset_id=dataset_id,
                    documents=batch_docs,
                    observations=batch_obs,
                )
            total_records += len(batch_docs)

        # 5. Seal canonical dataset
        parts_data, dataset_content_sha256 = self.canonical_store.seal_dataset(dataset_id)
        parts: list[DatasetPart] = []
        files_and_hashes: dict[str, str] = {}
        for p in parts_data:
            if isinstance(p, DatasetPart):
                parts.append(p)
                files_and_hashes[p.part_name] = p.file_sha256
            elif isinstance(p, (tuple, list)) and len(p) == 3:
                parts.append(DatasetPart(part_name=p[0], row_count=p[1], file_sha256=p[2]))
                files_and_hashes[p[0]] = p[2]
            elif isinstance(p, dict):
                dp = DatasetPart(**p)
                parts.append(dp)
                files_and_hashes[dp.part_name] = dp.file_sha256

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

        # Persist manifests to disk
        resolved_manifest_dir = manifest_dir.resolve()
        resolved_manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = (resolved_manifest_dir / "manifest.json").resolve()
        named_manifest_file = (resolved_manifest_dir / f"{dataset_id}_manifest.json").resolve()
        if not named_manifest_file.is_relative_to(resolved_manifest_dir):
            raise ValueError(f"Invalid dataset_id in manifest output: {dataset_id}")

        manifest_json = snapshot.model_dump_json(indent=2)
        manifest_file.write_text(manifest_json, encoding="utf-8")
        named_manifest_file.write_text(manifest_json, encoding="utf-8")

        # Build and persist EnhancedManifest
        enhanced_manifest, _ = manifest_builder.persist_manifest(
            output_dir=resolved_manifest_dir,
            files_and_hashes=files_and_hashes,
            canonical_sha256=dataset_content_sha256,
        )

        return IngestionSummary(
            snapshot=snapshot,
            processed_records=total_records,
            error_count=0,
            enhanced_manifest=enhanced_manifest,
        )
