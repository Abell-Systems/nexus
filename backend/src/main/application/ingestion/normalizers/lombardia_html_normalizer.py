"""Open Innovation Lombardia HTML normalizer orchestrating LombardiaExtractor and DefaultOriginResolver.

Mirrors InnogetHtmlNormalizer's structure (extraction -> origin resolution -> canonical
DemandRecord / DemandNormalizationResult), applied to a different source's DOM shape.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

from application.ingestion.extractors.lombardia_extractor import LombardiaExtractor
from application.ingestion.origin_resolver import DefaultOriginResolver
from domain.models.demand import (
    DemandDiscoveryChannel,
    DemandDisposition,
    DemandNormalizationResult,
    DemandRecord,
    RawExtractedDemandFields,
    SpanishOriginLevel,
)
from domain.models.evidence import FieldObservation, VerificationStatus
from domain.protocols.sources import RawPayload


class LombardiaHtmlNormalizer:
    """Normalizes raw Open Innovation Lombardia HTML pages into canonical DemandRecords."""

    def __init__(
        self,
        origin_resolver: DefaultOriginResolver,
        extractor: LombardiaExtractor | None = None,
        extraction_version: str = "1.0.0",
    ) -> None:
        if origin_resolver is None:
            raise ValueError("origin_resolver must be provided to LombardiaHtmlNormalizer")
        self.origin_resolver = origin_resolver
        self.extractor = extractor or LombardiaExtractor()
        self.extraction_version = extraction_version

    def normalize_stream(self, raw_payload: RawPayload) -> Iterator[DemandRecord]:
        """Yield only validated INCLUDED Spanish demands for downstream pipelines."""
        for result in self.normalize_results(raw_payload):
            if result.disposition == DemandDisposition.INCLUDED and result.demand is not None:
                yield result.demand

    def normalize_results(self, raw_payload: RawPayload) -> Iterator[DemandNormalizationResult]:
        """Normalize and classify a raw Lombardia HTML payload with full provenance and disposition."""
        source_uri = raw_payload.metadata.get("source_uri") or raw_payload.metadata.get("url", "")
        raw_bytes = raw_payload.payload_bytes
        raw_sha256 = raw_payload.payload_sha256

        if not raw_bytes:
            assessment = self.origin_resolver.assess_origin(
                RawExtractedDemandFields(extraction_timestamp=datetime.now(UTC), source_uri=source_uri),
                raw_payload_sha256=raw_sha256,
            )
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet="",
                error_detail="Empty payload bytes received",
            )
            return

        try:
            raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            assessment = self.origin_resolver.assess_origin(
                RawExtractedDemandFields(extraction_timestamp=datetime.now(UTC), source_uri=source_uri),
                raw_payload_sha256=raw_sha256,
            )
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                error_detail=f"Unicode decoding failed: {e}",
            )
            return

        try:
            fields = self.extractor.extract(raw_payload, source_uri)
        except Exception as e:
            assessment = self.origin_resolver.assess_origin(
                RawExtractedDemandFields(extraction_timestamp=datetime.now(UTC), source_uri=source_uri),
                raw_payload_sha256=raw_sha256,
            )
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                error_detail=f"HTML Extraction failed: {e}",
            )
            return

        if not fields.demand_id:
            assessment = self.origin_resolver.assess_origin(fields, raw_payload_sha256=raw_sha256)
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                error_detail="Unable to extract authentic collaboration proposal identifier from URL",
            )
            return

        if not fields.title or not fields.description:
            assessment = self.origin_resolver.assess_origin(fields, raw_payload_sha256=raw_sha256)
            yield DemandNormalizationResult(
                disposition=DemandDisposition.EXCLUDED_MISSING_TEXT,
                origin_assessment=assessment,
                raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                error_detail=f"Missing critical technical text: title='{bool(fields.title)}', description='{bool(fields.description)}'",
            )
            return

        origin_assessment = self.origin_resolver.assess_origin(fields, raw_payload_sha256=raw_sha256)

        if origin_assessment.is_target_origin:
            disposition = DemandDisposition.INCLUDED
        elif origin_assessment.level == SpanishOriginLevel.NON_SPANISH:
            disposition = DemandDisposition.EXCLUDED_NON_SPANISH
        else:
            disposition = DemandDisposition.EXCLUDED_UNVERIFIED_ORIGIN

        metadata: dict[str, str] = {}
        if fields.external_reference_raw:
            metadata["pod_reference"] = fields.external_reference_raw

        demand_rec = DemandRecord(
            demand_id=fields.demand_id,
            title=fields.title,
            description=fields.description,
            origin_country=fields.country_raw,
            spanish_origin_level=origin_assessment.level,
            is_spanish_demand=origin_assessment.is_target_origin,
            url=source_uri,
            discovery_channel=DemandDiscoveryChannel.DIRECTORY,
            metadata=metadata,
        )

        observations = self._build_observations(demand_rec, raw_payload, source_uri)

        yield DemandNormalizationResult(
            disposition=disposition,
            demand=demand_rec,
            origin_assessment=origin_assessment,
            raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
            error_detail=origin_assessment.rationale,
            field_observations=observations,
        )

    def _build_observations(
        self, demand: DemandRecord, raw_payload: RawPayload, source_uri: str
    ) -> list[FieldObservation]:
        ts = raw_payload.retrieval_timestamp
        sha = raw_payload.payload_sha256
        return [
            FieldObservation(
                entity_id=demand.demand_id,
                field_name="title",
                observed_value_json=f'"{demand.title}"',
                value_type="str",
                source_authority="Open Innovation Lombardia",
                source_uri=source_uri,
                retrieval_timestamp=ts,
                raw_payload_sha256=sha,
                extraction_version=self.extraction_version,
                verification_status=VerificationStatus.SOURCE_REPORTED,
            ),
            FieldObservation(
                entity_id=demand.demand_id,
                field_name="description",
                observed_value_json=f'"{demand.description[:100]}..."',
                value_type="str",
                source_authority="Open Innovation Lombardia",
                source_uri=source_uri,
                retrieval_timestamp=ts,
                raw_payload_sha256=sha,
                extraction_version=self.extraction_version,
                verification_status=VerificationStatus.SOURCE_REPORTED,
            ),
        ]
