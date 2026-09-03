"""InnoGet HTML normalizer orchestrating InnoGetExtractor and DefaultOriginResolver.

Clean Architecture boundary:
1. InnoGetExtractor: Factual HTML/DOM parsing into RawExtractedDemandFields.
2. DefaultOriginResolver: Policy-driven evaluation against versioned OriginPolicyConfig into OriginAssessment.
3. InnogetHtmlNormalizer: Composition, validation, and canonical DemandRecord / DemandNormalizationResult creation.
"""

import re
from collections.abc import Iterator
from datetime import UTC, datetime

from application.ingestion.extractors.innoget_extractor import InnoGetExtractor
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


class InnogetHtmlNormalizer:
    """Normalizes raw InnoGet HTML challenge pages into canonical DemandRecords."""

    def __init__(
        self,
        origin_resolver: DefaultOriginResolver,
        extractor: InnoGetExtractor | None = None,
        extraction_version: str = "2.0.0",
    ) -> None:
        if origin_resolver is None:
            raise ValueError("origin_resolver must be provided to InnogetHtmlNormalizer")
        self.origin_resolver = origin_resolver
        self.extractor = extractor or InnoGetExtractor()
        self.extraction_version = extraction_version

    def normalize_stream(self, raw_payload: RawPayload) -> Iterator[DemandRecord]:
        """Yield only validated INCLUDED Spanish demands for downstream pipelines."""
        for result in self.normalize_results(raw_payload):
            if result.disposition == DemandDisposition.INCLUDED and result.demand is not None:
                yield result.demand

    def normalize_results(self, raw_payload: RawPayload) -> Iterator[DemandNormalizationResult]:
        """Normalize and classify raw InnoGet HTML payload with full provenance and disposition."""
        source_uri = raw_payload.metadata.get("source_uri") or raw_payload.metadata.get("url", "")
        raw_bytes = raw_payload.payload_bytes
        raw_sha256 = raw_payload.payload_sha256

        # Strict input validation: non-empty and valid UTF-8
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

        # 1. Delegate factual extraction to InnoGetExtractor
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

        # 2. Strict ID verification - must be authentic from page, URL, or metadata
        if not fields.demand_id:
            assessment = self.origin_resolver.assess_origin(fields, raw_payload_sha256=raw_sha256)
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                error_detail="Unable to extract authentic challenge identifier from HTML or canonical URL",
            )
            return

        # 3. Critical text completeness
        if not fields.title or not fields.description:
            assessment = self.origin_resolver.assess_origin(fields, raw_payload_sha256=raw_sha256)
            yield DemandNormalizationResult(
                disposition=DemandDisposition.EXCLUDED_MISSING_TEXT,
                origin_assessment=assessment,
                raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                error_detail=f"Missing critical technical text: title='{bool(fields.title)}', description='{bool(fields.description)}'",
            )
            return

        # 4. Resolve origin against versioned policy
        origin_assessment = self.origin_resolver.assess_origin(fields, raw_payload_sha256=raw_sha256)

        # 5. Determine disposition from assessment
        if origin_assessment.is_target_origin:
            disposition = DemandDisposition.INCLUDED
        elif origin_assessment.level == SpanishOriginLevel.NON_SPANISH:
            disposition = DemandDisposition.EXCLUDED_NON_SPANISH
        else:
            disposition = DemandDisposition.EXCLUDED_UNVERIFIED_ORIGIN

        # 6. Normalize dates
        norm_deadline = self._normalize_date(fields.deadline_date_raw)

        demand_rec = DemandRecord(
            demand_id=fields.demand_id,
            title=fields.title,
            description=fields.description,
            requesting_organization=fields.organization_raw,
            origin_country=fields.country_raw,
            spanish_origin_level=origin_assessment.level,
            is_spanish_demand=origin_assessment.is_target_origin,
            cpc_prefix=raw_payload.metadata.get("cpc_prefix"),
            posted_date=raw_payload.metadata.get("posted_date"),
            deadline_date=norm_deadline,
            url=fields.canonical_uri_observed or source_uri,
            discovery_channel=DemandDiscoveryChannel.DIRECTORY,
            budget_range=fields.budget_range_raw,
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

    def _normalize_date(self, raw_date: str | None) -> str | None:
        if not raw_date:
            return None
        m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw_date.strip())
        if m:
            try:
                dt = datetime.strptime(raw_date.strip(), "%d/%m/%Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None

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
                source_authority="InnoGet Marketplace",
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
                source_authority="InnoGet Marketplace",
                source_uri=source_uri,
                retrieval_timestamp=ts,
                raw_payload_sha256=sha,
                extraction_version=self.extraction_version,
                verification_status=VerificationStatus.SOURCE_REPORTED,
            ),
        ]
