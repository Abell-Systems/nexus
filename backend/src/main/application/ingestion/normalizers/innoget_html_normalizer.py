"""InnoGet HTML normalizer separating pure factual extraction from origin resolution.

Adheres strictly to Protocol Section 3.4 and ADR 0001:
1. Extraction: Parses HTML safely (rejecting corrupted inputs) and extracts raw fields without inference.
2. Resolution: Delegates origin assessment to an explicit OriginResolver producing audit evidence.
3. Normalization: Constructs typed DemandRecord and DemandNormalizationResult with full provenance.
"""

import re
from collections.abc import Iterator
from datetime import UTC, datetime

from bs4 import BeautifulSoup

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
        origin_resolver: DefaultOriginResolver | None = None,
        extraction_version: str = "2.0.0",
    ) -> None:
        self.origin_resolver = origin_resolver or DefaultOriginResolver()
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

        # Reject payload if it cannot be decoded cleanly
        try:
            raw_html = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raw_snippet = raw_bytes[:300].decode("utf-8", errors="replace")
            assessment = self.origin_resolver.assess_origin(
                RawExtractedDemandFields(extraction_timestamp=datetime.now(UTC), source_uri=source_uri)
            )
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_snippet,
                error_detail=f"Unicode decoding failed: {e}",
            )
            return

        try:
            soup = BeautifulSoup(raw_html, "html.parser")
        except Exception as e:
            assessment = self.origin_resolver.assess_origin(
                RawExtractedDemandFields(extraction_timestamp=datetime.now(UTC), source_uri=source_uri)
            )
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_html[:300],
                error_detail=f"HTML Parse Error: {e}",
            )
            return

        # 1. Pure factual extraction
        fields = self._extract_raw_fields(soup, raw_payload, source_uri)

        # 2. Strict ID verification - must be authentic from page, URL, or metadata, never synthetic
        if not fields.demand_id:
            assessment = self.origin_resolver.assess_origin(fields)
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_assessment=assessment,
                raw_snippet=raw_html[:300],
                error_detail="Unable to extract authentic challenge identifier from HTML or canonical URL",
            )
            return

        # 3. Critical text completeness
        if not fields.title or not fields.description:
            assessment = self.origin_resolver.assess_origin(fields)
            yield DemandNormalizationResult(
                disposition=DemandDisposition.EXCLUDED_MISSING_TEXT,
                origin_assessment=assessment,
                raw_snippet=raw_html[:300],
                error_detail=f"Missing critical technical text: title='{bool(fields.title)}', description='{bool(fields.description)}'",
            )
            return

        # 4. Resolve origin against policy
        origin_assessment = self.origin_resolver.assess_origin(fields)

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
            requesting_organization=fields.organization_raw or "Unknown Organization",
            origin_country=fields.country_raw or ("Spain" if origin_assessment.is_target_origin else "Unverified"),
            spanish_origin_level=origin_assessment.level,
            is_spanish_demand=origin_assessment.is_target_origin,
            cpc_prefix=raw_payload.metadata.get("cpc_prefix"),
            posted_date=raw_payload.metadata.get("posted_date"),
            deadline_date=norm_deadline,
            url=fields.canonical_url or source_uri,
            discovery_channel=DemandDiscoveryChannel.DIRECTORY,
            budget_range=fields.budget_range_raw,
        )

        observations = self._build_observations(demand_rec, raw_payload, source_uri)

        yield DemandNormalizationResult(
            disposition=disposition,
            demand=demand_rec,
            origin_assessment=origin_assessment,
            raw_snippet=raw_html[:300],
            error_detail=origin_assessment.rationale,
            field_observations=observations,
        )

    def _extract_raw_fields(
        self, soup: BeautifulSoup, raw_payload: RawPayload, source_uri: str
    ) -> RawExtractedDemandFields:
        """Extract uninterpreted factual fields from HTML."""
        # A. Canonical URL & Challenge ID
        og_url_tag = soup.find("meta", property="og:url")
        canonical_url = str(og_url_tag.get("content", "")) if og_url_tag else str(source_uri)

        demand_id = raw_payload.metadata.get("demand_id")
        if not demand_id and canonical_url:
            m_id = re.search(r"/(?:technology-calls|challenges)/(\d+)", canonical_url)
            if m_id:
                demand_id = f"INNOGET-{m_id.group(1)}"

        # B. Title
        title = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = str(og_title.get("content", "")).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # C. Description
        description = None
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = str(og_desc.get("content", "")).strip()
        elif soup.find("meta", attrs={"name": "description"}):
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = str(meta_desc.get("content", "")).strip()

        if not description or len(description) < 30:
            main_block = soup.find(
                "div", class_=re.compile(r"challenge-content|description|content-text", re.I)
            )
            if main_block:
                text_val = main_block.get_text(separator=" ", strip=True)
                if len(text_val) >= 30:
                    description = text_val

        # D. Organization & Country from details or user metadata
        organization = raw_payload.metadata.get("requesting_organization")
        country = raw_payload.metadata.get("origin_country")
        budget_range = None
        deadline_raw = None

        details_ul = soup.find("ul", class_=re.compile(r"details|challenge-details", re.I))
        if details_ul:
            lis = details_ul.find_all("li")
            if lis and not organization:
                first_text = lis[0].get_text(separator=" ", strip=True)
                if not first_text.lower().startswith("from ") and "deadline" not in first_text.lower():
                    organization = first_text

            for li in lis:
                li_text = li.get_text(separator=" ", strip=True)
                if li_text.lower().startswith("from "):
                    country = li_text[5:].strip()
                elif any(sym in li_text for sym in ("€", "$", "Project Size")):
                    budget_range = li_text
                elif "deadline" in li_text.lower():
                    m_date = re.search(r"(\d{2}/\d{2}/\d{4})", li_text)
                    if m_date:
                        deadline_raw = m_date.group(1)

        user_meta = soup.find("div", class_=re.compile(r"user-meta|company-name|posted-by", re.I))
        if user_meta and not organization:
            raw_user = user_meta.get_text(separator=" ", strip=True)
            m_org = re.match(r"^(?:posted by\s+)?([^0-9]+?)(?:\s+\d+\s+followers)?$", raw_user, re.I)
            if m_org:
                organization = m_org.group(1).strip()

        return RawExtractedDemandFields(
            demand_id=demand_id,
            title=title,
            description=description,
            organization_raw=organization,
            country_raw=country,
            deadline_date_raw=deadline_raw,
            budget_range_raw=budget_range,
            canonical_url=canonical_url,
            extraction_timestamp=datetime.now(UTC),
            source_uri=source_uri,
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
