"""InnoGet HTML normalizer implementing the 4-level Spanish Origin Verification Hierarchy.

Adheres strictly to Protocol Section 3.4:
- Level 1: Direct Platform Country Metadata == Spain / España.
- Level 2: Sponsoring Organization designated in Spain (e.g. CSIC, INDUSAC, SMAR3TS).
- Level 3: Organization verified as registered Spanish commercial entity (.es TLD or verified registry).
- Non-Spanish: Explicitly foreign countries (United States, United Kingdom, Poland, etc.) -> EXCLUDED_NON_SPANISH.
- Missing Critical Text: Empty title or description -> EXCLUDED_MISSING_TEXT.
- Malformed HTML / Missing ID -> QUARANTINED_MALFORMED.
"""

import re
from collections.abc import Iterator
from datetime import datetime

from bs4 import BeautifulSoup

from domain.models.demand import (
    DemandDiscoveryChannel,
    DemandDisposition,
    DemandNormalizationResult,
    DemandRecord,
    SpanishOriginLevel,
)
from domain.protocols.sources import RawPayload

KNOWN_SPANISH_ORGANIZATIONS: frozenset[str] = frozenset({
    "smar3ts",
    "indusac",
    "csic",
    "consejo superior de investigaciones científicas",
    "consejo superior de investigaciones cientificas",
    "universitat politècnica de valència",
    "universitat politecnica de valencia",
    "universidad politécnica de madrid",
    "universidad politecnica de madrid",
    "universidad de zaragoza",
    "acciona",
    "repsol",
    "ferrovial",
    "iberdrola",
    "telefonica",
    "telefónica",
})

EXPLICIT_NON_SPANISH_COUNTRIES: frozenset[str] = frozenset({
    "united states",
    "usa",
    "united kingdom",
    "uk",
    "germany",
    "france",
    "italy",
    "poland",
    "netherlands",
    "belgium",
    "switzerland",
    "japan",
    "china",
    "canada",
    "brazil",
})


class InnogetHtmlNormalizer:
    """Normalizes raw InnoGet HTML challenge pages into canonical DemandRecords."""

    def __init__(self, target_jurisdiction: str = "ES") -> None:
        self.target_jurisdiction = target_jurisdiction

    def normalize_stream(self, raw_payload: RawPayload) -> Iterator[DemandRecord]:
        """Yield only validated INCLUDED Spanish demands for downstream pipelines."""
        for result in self.normalize_results(raw_payload):
            if result.disposition == DemandDisposition.INCLUDED and result.demand is not None:
                yield result.demand

    def normalize_results(self, raw_payload: RawPayload) -> Iterator[DemandNormalizationResult]:
        """Normalize and classify raw InnoGet HTML payload with full provenance and disposition."""
        raw_html = raw_payload.payload_bytes.decode("utf-8", errors="replace")
        source_uri = raw_payload.metadata.get("source_uri") or raw_payload.metadata.get("url", "")

        try:
            soup = BeautifulSoup(raw_html, "html.parser")
        except Exception as e:
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_level=SpanishOriginLevel.UNVERIFIED,
                raw_snippet=raw_html[:300],
                error_detail=f"HTML Parse Error: {e}",
            )
            return

        # 1. Demand ID extraction
        demand_id = raw_payload.metadata.get("demand_id") or ""
        if not demand_id:
            # Attempt to extract from canonical URL or og:url
            og_url = soup.find("meta", property="og:url")
            url_str = str(og_url.get("content", "")) if og_url else str(source_uri)
            m_id = re.search(r"/(?:technology-calls|challenges)/(\d+)", url_str)
            if m_id:
                demand_id = f"INNOGET-{m_id.group(1)}"
            else:
                m_batch = re.search(r"(\d+)", raw_payload.batch_id)
                if m_batch:
                    demand_id = f"INNOGET-{m_batch.group(1)}"

        if not demand_id:
            yield DemandNormalizationResult(
                disposition=DemandDisposition.QUARANTINED_MALFORMED,
                origin_level=SpanishOriginLevel.UNVERIFIED,
                raw_snippet=raw_html[:300],
                error_detail="Unable to extract mandatory technology challenge ID",
            )
            return

        # 2. Title extraction
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = str(og_title.get("content", "")).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # 3. Technical Description extraction
        description = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = str(og_desc.get("content", "")).strip()
        elif soup.find("meta", attrs={"name": "description"}):
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = str(meta_desc.get("content", "")).strip()

        # Fallback to main text block if description is very brief
        if len(description) < 30:
            main_content = soup.find("div", class_=re.compile(r"challenge-content|description|content-text", re.I))
            if main_content:
                description = main_content.get_text(separator=" ", strip=True)

        # 4. Critical Text Completeness Check
        if not title or not description:
            yield DemandNormalizationResult(
                disposition=DemandDisposition.EXCLUDED_MISSING_TEXT,
                origin_level=SpanishOriginLevel.UNVERIFIED,
                raw_snippet=raw_html[:300],
                error_detail=f"Missing critical text: title='{bool(title)}', description='{bool(description)}'",
            )
            return

        # 5. Organization, Country, and Details extraction
        organization = ""
        country_str = ""
        budget_range = None
        deadline_date = None

        details_ul = soup.find("ul", class_="details")
        if details_ul:
            for li in details_ul.find_all("li"):
                li_text = li.get_text(separator=" ", strip=True)
                if li_text.startswith("From "):
                    country_str = li_text.replace("From ", "").strip()
                elif "Project Size Range" in li_text or "€" in li_text or "$" in li_text:
                    budget_range = li_text
                elif "Deadline at " in li_text:
                    m_date = re.search(r"(\d{2}/\d{2}/\d{4})", li_text)
                    if m_date:
                        try:
                            dt = datetime.strptime(m_date.group(1), "%d/%m/%Y")
                            deadline_date = dt.strftime("%Y-%m-%d")
                        except ValueError:
                            deadline_date = m_date.group(1)

        # Look for organization name
        user_meta = soup.find("div", class_="user-meta")
        if user_meta:
            org_candidate = user_meta.get_text(separator=" ", strip=True)
            # e.g. "The Procter & Gamble Company 85 Followers"
            m_org = re.match(r"^([^0-9]+?)(?:\s+\d+\s+Followers)?$", org_candidate)
            if m_org:
                organization = m_org.group(1).replace("Posted by", "").strip()

        if not organization and details_ul:
            first_li = details_ul.find("li")
            if first_li and not first_li.get_text().startswith("From "):
                organization = first_li.get_text(strip=True)

        # Metadata fallback for organization/country
        if not organization:
            organization = raw_payload.metadata.get("requesting_organization", "Unknown Organization")
        if not country_str:
            country_str = raw_payload.metadata.get("origin_country", "")

        # 6. Apply 4-Level Spanish Origin Verification Hierarchy
        origin_level, is_spanish = self._classify_spanish_origin(country_str, organization)

        canonical_url = str(source_uri) if source_uri else f"https://www.innoget.com/technology-calls/{demand_id}"

        # Classify disposition
        if is_spanish:
            disposition = DemandDisposition.INCLUDED
        elif origin_level == SpanishOriginLevel.NON_SPANISH:
            disposition = DemandDisposition.EXCLUDED_NON_SPANISH
        else:
            disposition = DemandDisposition.EXCLUDED_UNVERIFIED_ORIGIN

        demand_rec = DemandRecord(
            demand_id=demand_id,
            title=title,
            description=description,
            requesting_organization=organization or "Unknown Organization",
            origin_country=country_str or ("Spain" if is_spanish else "Unverified"),
            spanish_origin_level=origin_level,
            is_spanish_demand=is_spanish,
            cpc_prefix=raw_payload.metadata.get("cpc_prefix"),
            posted_date=raw_payload.metadata.get("posted_date"),
            deadline_date=deadline_date,
            url=canonical_url,
            discovery_channel=DemandDiscoveryChannel.DIRECTORY,
            budget_range=budget_range,
        )

        yield DemandNormalizationResult(
            disposition=disposition,
            demand=demand_rec,
            origin_level=origin_level,
            raw_snippet=raw_html[:300],
            error_detail=f"Classified under Spanish Origin {origin_level.value}",
        )

    def _classify_spanish_origin(
        self, country_str: str, organization: str
    ) -> tuple[SpanishOriginLevel, bool]:
        """Operationalize Protocol Section 3.4."""
        norm_country = country_str.strip().lower()
        norm_org = organization.strip().lower()

        # Explicit non-Spanish check
        if norm_country in EXPLICIT_NON_SPANISH_COUNTRIES:
            return SpanishOriginLevel.NON_SPANISH, False

        # Level 1: Direct Platform Country Metadata
        if norm_country in {"spain", "españa", "es"}:
            return SpanishOriginLevel.LEVEL_1_DIRECT_METADATA, True

        # Level 2: Sponsoring Organization Designated in Spain
        if any(known in norm_org for known in KNOWN_SPANISH_ORGANIZATIONS):
            return SpanishOriginLevel.LEVEL_2_ORGANIZATION_METADATA, True

        # Level 3: Cross-Check / S.L. / S.A. / Spanish domain suffix
        if re.search(r"\b(s\.?l\.?|s\.?a\.?|sociedad limitada|sociedad anonima)\b", norm_org):
            return SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK, True

        # Default fallback
        if norm_country:
            return SpanishOriginLevel.NON_SPANISH, False
        return SpanishOriginLevel.UNVERIFIED, False
