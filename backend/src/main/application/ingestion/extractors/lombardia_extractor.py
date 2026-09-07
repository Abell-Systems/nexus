"""Clean Architecture factual extractor for Open Innovation Lombardia HTML pages.

Lombardia republishes Enterprise Europe Network Partnering Opportunities Database
listings (identical POD reference scheme). Its pages carry no explicit country field,
so country_raw is deterministically decoded from the POD reference's embedded
2-letter jurisdiction code (e.g. "TRES20250806011" -> "ES") -- a factual parse of a
raw identifier, not a heuristic or interpretation.
"""

import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup

from domain.models.demand import ExtractionSourceKind, RawExtractedDemandFields
from domain.protocols.sources import RawPayload

_POD_REFERENCE_RE = re.compile(r"^[A-Z]{2}([A-Z]{2})\d+$")


class LombardiaExtractor:
    """Extracts raw, uninterpreted demand fields from Open Innovation Lombardia HTML payloads."""

    def extract(self, raw_payload: RawPayload, source_uri: str) -> RawExtractedDemandFields:
        raw_html = raw_payload.payload_bytes.decode("utf-8")
        soup = BeautifulSoup(raw_html, "html.parser")

        # 1. Demand ID from the collaboration-proposals URL path
        demand_id: str | None = None
        id_source = ExtractionSourceKind.PAYLOAD_METADATA
        m_id = re.search(r"/collaboration-proposals/(\d+)", source_uri)
        if m_id:
            demand_id = f"LOMBARDIA-{m_id.group(1)}"
            id_source = ExtractionSourceKind.SOURCE_URI

        # 2. Title
        title: str | None = None
        title_el = soup.find(class_=re.compile(r"collaborations-detail-title"))
        if title_el:
            title = title_el.get_text(strip=True)

        # 3. Description (Abstract)
        description: str | None = None
        abstract_el = soup.find(class_=re.compile(r"collaborations-abstract-text"))
        if abstract_el:
            text_val = abstract_el.get_text(separator=" ", strip=True)
            if text_val:
                description = text_val

        # 4. POD reference and derived country code
        pod_reference: str | None = None
        country: str | None = None
        info_value_el = soup.find(class_=re.compile(r"collaborations-info-value lead"))
        if info_value_el:
            candidate = info_value_el.get_text(strip=True)
            m_pod = _POD_REFERENCE_RE.match(candidate)
            if m_pod:
                pod_reference = candidate
                country = m_pod.group(1)

        return RawExtractedDemandFields(
            demand_id=demand_id,
            demand_id_source=id_source,
            title=title,
            description=description,
            country_raw=country,
            external_reference_raw=pod_reference,
            extraction_timestamp=datetime.now(UTC),
            source_uri=source_uri,
        )
