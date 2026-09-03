"""Builder for EnhancedManifest recording exact attrition, provenance, and environment."""

import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from domain.models.ingestion import (
    AttritionCounts,
    DatasetContentIdentity,
    EnhancedManifest,
    ExecutionEnvironment,
    ExecutionProvenance,
    NormalizationResult,
    RecordDisposition,
    TemporalWindow,
)


class EnhancedManifestBuilder:
    """Orchestrates attrition counting, hash calculation, and cryptographic manifest generation."""

    def __init__(
        self,
        dataset_id: str = "OEPM-ES-CORPUS-2016-2024-CANONICAL",
        dataset_version: str = "1.0.0",
        source_authority: str = "Oficina Española de Patentes y Marcas (OEPM)",
        source_release_id: str = "OEPM-BOPI-BULK-2016-2024",
        source_uri: str = "https://datos.gob.es/es/catalogo/e05024401-patentes-solicitadas-y-concedidas-bopi",
        normalizer_version: str = "2.0.0",
        temporal_start_date: str = "2016-01-01",
        temporal_end_date: str = "2024-12-31",
    ) -> None:
        self.dataset_id = dataset_id
        self.dataset_version = dataset_version
        self.source_authority = source_authority
        self.source_release_id = source_release_id
        self.source_uri = source_uri
        self.normalizer_version = normalizer_version
        self.temporal_start_date = temporal_start_date
        self.temporal_end_date = temporal_end_date

        self.acquisition_started_at: datetime = datetime.now(UTC)
        self.raw_payload_count: int = 0
        self.disposition_counts: Counter[RecordDisposition] = Counter()
        self.exclusion_reasons: Counter[str] = Counter()
        self.quarantine_reasons: Counter[str] = Counter()
        self.kind_code_distribution: Counter[str] = Counter()

    def record_raw_payload(self) -> None:
        """Increment the raw payload counter."""
        self.raw_payload_count += 1

    def record_normalization_result(self, result: NormalizationResult) -> None:
        """Accumulate attrition metrics and classifications from a NormalizationResult."""
        self.disposition_counts[result.disposition] += 1

        if result.disposition == RecordDisposition.INCLUDED and result.document is not None:
            if result.document.kind_code:
                self.kind_code_distribution[result.document.kind_code] += 1

        elif result.disposition == RecordDisposition.EXCLUDED and result.excluded is not None:
            reason_key = f"EXCLUDED_{result.excluded.reason.value.upper()}"
            self.exclusion_reasons[reason_key] += 1

        elif result.disposition == RecordDisposition.QUARANTINED and result.quarantined is not None:
            q_key = f"QUARANTINED_{result.quarantined.reason.value.upper()}"
            self.quarantine_reasons[q_key] += 1

    def _get_git_commit(self) -> str:
        """Obtain current git commit hash safely."""
        try:
            out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            return out.decode("utf-8").strip()
        except Exception:
            return "unknown_commit"

    def compute_content_identity_hash(self, content_identity: DatasetContentIdentity) -> str:
        """Compute bit-exact deterministic hash over the content identity (independent of execution timestamps)."""
        content_dict = content_identity.model_dump(mode="json")
        canonical_bytes = json.dumps(content_dict, sort_keys=True).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def build_manifest(
        self,
        files_and_hashes: dict[str, str],
        canonical_sha256: str = "",
        acquisition_started_at: datetime | None = None,
        acquisition_finished_at: datetime | None = None,
        git_commit: str | None = None,
    ) -> EnhancedManifest:
        """Construct the EnhancedManifest model with decoupled content identity and execution provenance."""
        started_at = acquisition_started_at or self.acquisition_started_at
        finished_at = acquisition_finished_at or datetime.now(UTC)

        total_normalized = sum(self.disposition_counts.values())
        counts = AttritionCounts(
            raw_payload_count=self.raw_payload_count,
            normalized_record_count=total_normalized,
            included_record_count=self.disposition_counts[RecordDisposition.INCLUDED],
            quarantined_record_count=self.disposition_counts[RecordDisposition.QUARANTINED],
            excluded_record_count=self.disposition_counts[RecordDisposition.EXCLUDED],
            duplicate_count=self.disposition_counts[RecordDisposition.DUPLICATE],
        )

        temporal_window = TemporalWindow(
            start_date=self.temporal_start_date,
            end_date=self.temporal_end_date,
        )

        # If canonical_sha256 not provided, derive from files
        if not canonical_sha256 and files_and_hashes:
            combined = "".join(f"{k}:{v}" for k, v in sorted(files_and_hashes.items()))
            canonical_sha256 = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        # 1. Scientific Content Identity (Reproducible across runs and environments)
        content_identity = DatasetContentIdentity(
            dataset_id=self.dataset_id,
            dataset_version=self.dataset_version,
            source_authority=self.source_authority,
            source_release_id=self.source_release_id,
            source_uri=self.source_uri,
            jurisdiction="ES",
            temporal_window=temporal_window,
            canonical_sha256=canonical_sha256,
            counts=counts,
            exclusion_reasons=dict(self.exclusion_reasons),
            quarantine_reasons=dict(self.quarantine_reasons),
            kind_code_distribution=dict(self.kind_code_distribution),
            files=files_and_hashes,
        )

        content_identity_sha256 = self.compute_content_identity_hash(content_identity)

        # 2. Execution Provenance (Runtime audit trail)
        environment = ExecutionEnvironment(
            git_commit=git_commit or self._get_git_commit(),
            normalizer_version=self.normalizer_version,
            python_version=platform.python_version(),
            platform=sys.platform,
        )

        execution_provenance = ExecutionProvenance(
            created_at=finished_at,
            acquisition_started_at=started_at,
            acquisition_finished_at=finished_at,
            environment=environment,
        )

        manifest = EnhancedManifest(
            content_identity=content_identity,
            content_identity_sha256=content_identity_sha256,
            execution_provenance=execution_provenance,
            manifest_sha256="",
        )

        # Compute full manifest digest
        manifest_dict = manifest.model_dump(by_alias=True, mode="json")
        manifest_dict["manifest_sha256"] = ""
        manifest_bytes = json.dumps(manifest_dict, sort_keys=True).encode("utf-8")
        manifest.manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

        return manifest

    def persist_manifest(
        self,
        output_dir: Path | str,
        files_and_hashes: dict[str, str],
        canonical_sha256: str = "",
    ) -> tuple[EnhancedManifest, Path]:
        """Build and atomically write enhanced_manifest.json via temporary file rename."""
        manifest = self.build_manifest(files_and_hashes, canonical_sha256)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        manifest_file = out_path / "enhanced_manifest.json"
        temp_file = out_path / f".enhanced_manifest.json.tmp_{os.getpid()}"

        manifest_json = manifest.model_dump_json(by_alias=True, indent=2)
        temp_file.write_text(manifest_json, encoding="utf-8")
        temp_file.replace(manifest_file)  # Atomic rename on POSIX filesystems
        return manifest, manifest_file
