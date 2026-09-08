"""Clean Architecture factual extractor for InnoGet HTML challenge pages.

Parses DOM/meta tags without applying business logic, policies, or heuristics.
"""

import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag

from domain.models.demand import ExtractionSourceKind, RawExtractedDemandFields
from domain.protocols.sources import RawPayload

_ID_PATH_RE = re.compile(r"/(?:technology-calls|challenges)/(\d+)")
_DATE_IN_TEXT_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
_ORG_FROM_USER_META_RE = re.compile(
    r"^(?:posted\s+by\s+)?([^0-9]+?)(?:\s+\d+\s+followers)?$", re.IGNORECASE
)
_DESCRIPTION_BLOCK_RE = re.compile(r"challenge-content|description|content-text", re.I)
_DETAILS_UL_RE = re.compile(r"details|challenge-details", re.I)
_USER_META_RE = re.compile(r"user-meta|company-name|posted-by", re.I)


class InnoGetExtractor:
    """Extracts raw, uninterpreted demand fields from HTML payloads."""

    def extract(self, raw_payload: RawPayload, source_uri: str) -> RawExtractedDemandFields:
        """Parse raw HTML and extract facts, logging exact extraction source kind."""
        soup = BeautifulSoup(raw_payload.payload_bytes.decode("utf-8"), "html.parser")

        canonical_uri_observed = self._extract_canonical_uri(soup)
        demand_id, id_source = self._extract_demand_id(
            raw_payload, canonical_uri_observed, source_uri
        )
        title = self._extract_title(soup)
        description = self._extract_description(soup)
        organization, org_location, country, budget_range, deadline_raw = (
            self._extract_organization_and_details(raw_payload, soup)
        )

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

    # ------------------------------------------------------------------ #
    # Private extraction helpers                                         #
    # ------------------------------------------------------------------ #

    def _extract_canonical_uri(self, soup: BeautifulSoup) -> str | None:
        og_url_tag = soup.find("meta", property="og:url")
        if og_url_tag:
            return self._get_attr_str(og_url_tag.attrs, "content")
        return None

    def _extract_demand_id(
        self,
        raw_payload: RawPayload,
        canonical_uri: str | None,
        source_uri: str,
    ) -> tuple[str | None, ExtractionSourceKind]:
        """Resolve demand ID with strict metadata -> canonical -> source precedence.

        Preserves exact elif semantics: if canonical_uri is present but contains no
        parseable numeric ID, source_uri is NOT consulted.
        """
        if raw_payload.metadata.get("demand_id"):
            return str(raw_payload.metadata["demand_id"]), ExtractionSourceKind.PAYLOAD_METADATA

        if canonical_uri:
            extracted = self._id_from_uri(canonical_uri)
            if extracted:
                return extracted, ExtractionSourceKind.META_TAG
            # canonical_uri is present but contains no ID: stop cascade, do not consult source_uri
            return None, ExtractionSourceKind.PAYLOAD_METADATA

        if source_uri:
            extracted = self._id_from_uri(source_uri)
            if extracted:
                return extracted, ExtractionSourceKind.SOURCE_URI

        return None, ExtractionSourceKind.PAYLOAD_METADATA

    def _id_from_uri(self, uri: str) -> str | None:
        """Extract numeric InnoGet ID from URI path, or None."""
        m = _ID_PATH_RE.search(uri)
        return f"INNOGET-{m.group(1)}" if m else None

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            val = self._get_attr_str(og_title.attrs, "content")
            if val:
                return val

        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        description: str | None = None
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            description = self._get_attr_str(og_desc.attrs, "content")

        if not description:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = self._get_attr_str(meta_desc.attrs, "content")

        if not description or len(description) < 30:
            main_block = soup.find("div", class_=_DESCRIPTION_BLOCK_RE)
            if main_block and isinstance(main_block, Tag):
                text_val = main_block.get_text(separator=" ", strip=True)
                if len(text_val) >= 30:
                    description = text_val

        return description

    def _extract_organization_and_details(
        self,
        raw_payload: RawPayload,
        soup: BeautifulSoup,
    ) -> tuple[str | None, str | None, str | None, str | None, str | None]:
        organization: str | None = raw_payload.metadata.get("requesting_organization")
        org_location: str | None = raw_payload.metadata.get("organization_location")
        country: str | None = raw_payload.metadata.get("origin_country")
        budget_range: str | None = None
        deadline_raw: str | None = None

        details_ul = soup.find("ul", class_=_DETAILS_UL_RE)
        if details_ul and isinstance(details_ul, Tag):
            organization, country, budget_range, deadline_raw = self._parse_details_list(
                details_ul, organization, country
            )

        if not organization:
            organization = self._extract_org_from_user_meta(soup)

        return organization, org_location, country, budget_range, deadline_raw

    def _parse_details_list(
        self,
        details_ul: Tag,
        organization: str | None,
        country: str | None,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        budget_range: str | None = None
        deadline_raw: str | None = None
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
                m_date = _DATE_IN_TEXT_RE.search(li_text)
                if m_date:
                    deadline_raw = m_date.group(1)

        return organization, country, budget_range, deadline_raw

    def _extract_org_from_user_meta(self, soup: BeautifulSoup) -> str | None:
        user_meta = soup.find("div", class_=_USER_META_RE)
        if user_meta and isinstance(user_meta, Tag):
            raw_user = user_meta.get_text(separator=" ", strip=True)
            m_org = _ORG_FROM_USER_META_RE.match(raw_user)
            if m_org:
                return m_org.group(1).strip()
        return None

    def _get_attr_str(self, attrs: dict, key: str) -> str | None:
        val = attrs.get(key)
        if isinstance(val, list):
            val = " ".join(val)
        return str(val).strip() if val is not None and str(val).strip() else None
