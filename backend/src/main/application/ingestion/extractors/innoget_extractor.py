"""Dedicated InnoGet HTML extractor separating DOM/metadata parsing from origin policy.

Produces typed RawExtractedDemandFields with clear provenance tracking for every field locator.
"""

import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup

from domain.models.demand import ExtractionSourceKind, RawExtractedDemandFields
from domain.protocols.sources import RawPayload


class InnoGetExtractor:
    """Extracts raw, uninterpreted demand fields from HTML payloads."""

    def extract(self, raw_payload: RawPayload, source_uri: str) -> RawExtractedDemandFields:
        """Parse raw HTML and extract facts, logging exact extraction source kind."""
        raw_html = raw_payload.payload_bytes.decode("utf-8")
        soup = BeautifulSoup(raw_html, "html.parser")

        # 1. Canonical URL & Challenge ID Extraction
        og_url_tag = soup.find("meta", property="og:url")
        canonical_uri_observed = str(og_url_tag.get("content", "")) if og_url_tag else None

        demand_id: str | None = None
        id_source = ExtractionSourceKind.PAYLOAD_METADATA

        if raw_payload.metadata.get("demand_id"):
            demand_id = str(raw_payload.metadata["demand_id"])
            id_source = ExtractionSourceKind.PAYLOAD_METADATA
        elif canonical_uri_observed:
            m_id = re.search(r"/(?:technology-calls|challenges)/(\d+)", canonical_uri_observed)
            if m_id:
                demand_id = f"INNOGET-{m_id.group(1)}"
                id_source = ExtractionSourceKind.META_TAG
        elif source_uri:
            m_id = re.search(r"/(?:technology-calls|challenges)/(\d+)", source_uri)
            if m_id:
                demand_id = f"INNOGET-{m_id.group(1)}"
                id_source = ExtractionSourceKind.SOURCE_URI

        # 2. Title Extraction
        title: str | None = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = str(og_title.get("content", "")).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # 3. Description Extraction
        description: str | None = None
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

        # 4. Organization, Country, Location, and Details list
        organization = raw_payload.metadata.get("requesting_organization")
        org_location = raw_payload.metadata.get("organization_location")
        country = raw_payload.metadata.get("origin_country")
        budget_range: str | None = None
        deadline_raw: str | None = None

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
            demand_id_source=id_source,
            title=title,
            description=description,
            organization_raw=organization,
            organization_location_raw=org_location,
            country_raw=country,
            deadline_date_raw=deadline_raw,
            budget_range_raw=budget_range,
            canonical_uri_observed=canonical_uri_observed,
            extraction_timestamp=datetime.now(UTC),
            source_uri=source_uri,
        )
