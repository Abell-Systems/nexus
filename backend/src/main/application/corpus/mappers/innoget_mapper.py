"""InnoGet Candidate Mapper for Phase-2 demand corpus expansion (ADR 0032)."""

import re
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from application.corpus.mappers.errors import MappingError
from domain.models.corpus_expansion import (
    DemandCandidateContractRecord,
    PublicationDateEvidence,
    PublicationDateEvidenceType,
)

_ID_PATH_RE = re.compile(r"/(?:technology-calls|challenges)/(\d+)")
_DEADLINE_TEXT_RE = re.compile(
    r"deadline\s*(?:at|:)?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})")
_CONFIDENTIALITY_RE = re.compile(r"\[(?:confidential|redacted)\]", re.IGNORECASE)
_SPANISH_INDICATORS = frozenset({"spain", "es", "españa", "espana"})


def _parse_date_string(val: str) -> date | None:
    """Parse date from ISO or standard DD/MM/YYYY string."""
    clean = val.strip()
    if "T" in clean:
        clean = clean.split("T")[0]
    try:
        return date.fromisoformat(clean)
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


class InnogetCandidateMapper:
    """Offline factual mapper for InnoGet challenge/technology-call HTML payloads."""

    @classmethod
    def map_payload(
        cls,
        raw_bytes: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> DemandCandidateContractRecord:
        """Map raw InnoGet HTML payload into a canonical DemandCandidateContractRecord."""
        meta = metadata or {}
        if not raw_bytes or not raw_bytes.strip():
            raise MappingError("InnoGet raw payload is empty")

        try:
            html_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                html_text = raw_bytes.decode("latin-1")
            except Exception as exc:
                raise MappingError(f"Failed to decode InnoGet payload: {exc}") from exc

        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Demand ID
        demand_id = cls._extract_demand_id(soup, meta)
        if not demand_id:
            raise MappingError("Demand ID could not be determined from InnoGet payload")

        # 2. Title
        title = cls._extract_title(soup, meta)
        if not title:
            raise MappingError("Title could not be extracted from InnoGet payload")

        # 3. Technical problem evidence
        has_tech_prob, tech_prob_text = cls._extract_technical_problem(soup, meta)

        # 4. Description
        description = cls._extract_description(soup, meta)
        if not description:
            raise MappingError("Description could not be extracted from InnoGet payload")

        # 5. Temporal evidence (Hierarchy: Explicit metadata -> Historical feed -> Deadline/Unverifiable)
        date_evidence = cls._extract_date_evidence(soup, html_text, meta)

        # 6. Organization and origin country
        org_name, country_name = cls._extract_org_and_country(soup, meta)

        # 7. Geographic stratum
        if country_name and country_name.strip().lower() in _SPANISH_INDICATORS:
            geographic_stratum = "spain"
        else:
            geographic_stratum = "international_european"

        # 8. Language code
        lang = meta.get("language_code")
        if not lang:
            html_tag = soup.find("html")
            if isinstance(html_tag, Tag) and html_tag.get("lang"):
                lang_attr = html_tag.get("lang")
                lang = str(lang_attr).strip() if lang_attr else "en"
            else:
                lang = "en"
        language_code = lang[:5].lower()
        if len(language_code) < 2:
            language_code = "en"

        # 9. Confidentiality and accessibility
        has_confidentiality = bool(_CONFIDENTIALITY_RE.search(html_text))
        is_public = meta.get("is_publicly_accessible", True)

        return DemandCandidateContractRecord(
            demand_id=demand_id,
            source_id="innoget",
            source_construct="Technology call",
            publication_date_evidence=date_evidence,
            geographic_stratum=geographic_stratum,
            title=title,
            description_text=description,
            language_code=language_code,
            organization_raw=org_name,
            is_publicly_accessible=is_public,
            has_confidentiality_redaction=has_confidentiality,
            has_articulated_technical_problem=has_tech_prob,
            technical_problem_evidence_text=tech_prob_text,
        )

    @classmethod
    def _extract_demand_id(cls, soup: BeautifulSoup, meta: dict[str, Any]) -> str | None:
        if meta.get("demand_id"):
            return str(meta["demand_id"]).strip()

        og_url = soup.find("meta", property="og:url")
        if og_url and isinstance(og_url, Tag):
            content = og_url.get("content")
            if content:
                m = _ID_PATH_RE.search(str(content))
                if m:
                    return f"INNOGET-{m.group(1)}"

        canonical = soup.find("link", rel="canonical")
        if canonical and isinstance(canonical, Tag):
            href = canonical.get("href")
            if href:
                m = _ID_PATH_RE.search(str(href))
                if m:
                    return f"INNOGET-{m.group(1)}"

        source_uri = meta.get("source_uri")
        if source_uri:
            m = _ID_PATH_RE.search(source_uri)
            if m:
                return f"INNOGET-{m.group(1)}"

        return None

    @classmethod
    def _extract_title(cls, soup: BeautifulSoup, meta: dict[str, Any]) -> str | None:
        if meta.get("title"):
            return str(meta["title"]).strip()

        og_title = soup.find("meta", property="og:title")
        if og_title and isinstance(og_title, Tag):
            content = og_title.get("content")
            if content and str(content).strip():
                return str(content).strip()

        h1 = soup.find("h1")
        if h1 and isinstance(h1, Tag):
            text = h1.get_text(separator=" ", strip=True)
            if text:
                return text

        if soup.title and soup.title.string:
            text = soup.title.string.strip()
            if text:
                return text

        return None

    @classmethod
    def _extract_date_evidence(
        cls,
        soup: BeautifulSoup,
        html_text: str,
        meta: dict[str, Any],
    ) -> PublicationDateEvidence:
        """Resolve publication date evidence via strict 3-tier hierarchy."""
        # Tier 1: Explicit metadata tag in DOM
        meta_candidates = [
            ("meta:article:published_time", soup.find("meta", property="article:published_time")),
            ("meta:datePublished", soup.find("meta", attrs={"name": "datePublished"})),
            ("meta:datePublished", soup.find("meta", attrs={"itemprop": "datePublished"})),
            ("meta:pubdate", soup.find("meta", attrs={"name": "pubdate"})),
            ("meta:publication_date", soup.find("meta", attrs={"name": "publication_date"})),
        ]
        for field_name, tag in meta_candidates:
            if tag and isinstance(tag, Tag):
                content = tag.get("content")
                if content:
                    parsed = _parse_date_string(str(content))
                    if parsed is not None:
                        return PublicationDateEvidence(
                            publication_date=parsed,
                            evidence_type=PublicationDateEvidenceType.EXPLICIT_METADATA,
                            evidence_field=field_name,
                            evidence_value=str(content).strip(),
                        )

        # Look for <time datetime="..."> or element with itemprop="datePublished"
        time_tag = soup.find("time")
        if time_tag and isinstance(time_tag, Tag) and time_tag.get("datetime"):
            dt_val = str(time_tag.get("datetime")).strip()
            parsed = _parse_date_string(dt_val)
            if parsed is not None:
                return PublicationDateEvidence(
                    publication_date=parsed,
                    evidence_type=PublicationDateEvidenceType.EXPLICIT_METADATA,
                    evidence_field="time:datetime",
                    evidence_value=dt_val,
                )

        # Tier 2: Historical feed entry if provided in metadata
        feed_date_str = meta.get("historical_feed_date") or meta.get("historical_feed")
        if feed_date_str:
            parsed = _parse_date_string(str(feed_date_str))
            if parsed is not None:
                return PublicationDateEvidence(
                    publication_date=parsed,
                    evidence_type=PublicationDateEvidenceType.HISTORICAL_FEED,
                    evidence_field="historical_feed",
                    evidence_value=str(feed_date_str).strip(),
                )

        # Tier 3: Deadline observation or UNVERIFIABLE
        deadline_raw = meta.get("deadline_date_raw") or meta.get("deadline")
        if not deadline_raw:
            # Check ul.details li items for deadline
            details_ul = soup.find("ul", class_=re.compile(r"details", re.I))
            if details_ul and isinstance(details_ul, Tag):
                for li in details_ul.find_all("li"):
                    li_text = li.get_text(separator=" ", strip=True)
                    if "deadline" in li_text.lower():
                        m = _DATE_ONLY_RE.search(li_text)
                        if m:
                            deadline_raw = m.group(1)
                            break

        if not deadline_raw:
            m = _DEADLINE_TEXT_RE.search(html_text)
            if m:
                deadline_raw = m.group(1)

        if deadline_raw:
            return PublicationDateEvidence(
                publication_date=None,
                evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
                evidence_field="deadline_date_raw",
                evidence_value=str(deadline_raw).strip(),
            )

        return PublicationDateEvidence(
            publication_date=None,
            evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
            evidence_field="no_date_field_observed",
            evidence_value="no_date_field_observed",
        )

    @classmethod
    def _extract_technical_problem(
        cls,
        soup: BeautifulSoup,
        meta: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if meta.get("technical_problem_evidence_text"):
            return True, str(meta["technical_problem_evidence_text"]).strip()

        # Look for "Details of the Innovation Need" heading
        for heading in soup.find_all(re.compile(r"h[1-6]")):
            h_text = heading.get_text(separator=" ", strip=True)
            if "details of the innovation need" in h_text.lower():
                container = heading.find_next_sibling(
                    ["div", "p"], class_=re.compile(r"post-section-container|body", re.I)
                )
                if not container:
                    container = heading.find_next_sibling(["div", "p"])
                if container and isinstance(container, Tag):
                    text = container.get_text(separator=" ", strip=True)
                    if text:
                        return True, text

        # Alternative: look for class matching challenge-content or problem
        for heading in soup.find_all(re.compile(r"h[1-6]")):
            h_text = heading.get_text(separator=" ", strip=True)
            if any(k in h_text.lower() for k in ("technical problem", "problem", "challenge description")):
                sibling = heading.find_next_sibling(["div", "p"])
                if sibling and isinstance(sibling, Tag):
                    text = sibling.get_text(separator=" ", strip=True)
                    if text:
                        return True, text

        return False, None

    @classmethod
    def _extract_description(cls, soup: BeautifulSoup, meta: dict[str, Any]) -> str | None:
        if meta.get("description"):
            return str(meta["description"]).strip()

        sections: list[str] = []

        # Check for Desired outcome heading and content
        for heading in soup.find_all(re.compile(r"h[1-6]")):
            h_text = heading.get_text(separator=" ", strip=True)
            if "desired outcome" in h_text.lower():
                sibling = heading.find_next_sibling(["p", "div"])
                if sibling and isinstance(sibling, Tag):
                    s_text = sibling.get_text(separator=" ", strip=True)
                    if s_text:
                        sections.append(f"Desired outcome: {s_text}")

        # Check for Details of the Innovation Need
        for heading in soup.find_all(re.compile(r"h[1-6]")):
            h_text = heading.get_text(separator=" ", strip=True)
            if "details of the innovation need" in h_text.lower():
                container = heading.find_next_sibling(
                    ["div", "p"], class_=re.compile(r"post-section-container|body", re.I)
                )
                if not container:
                    container = heading.find_next_sibling(["div", "p"])
                if container and isinstance(container, Tag):
                    text = container.get_text(separator=" ", strip=True)
                    if text:
                        sections.append(text)

        if sections:
            return "\n\n".join(sections)

        # Fallback to div.body.post or div.challenge-content
        body_elem = soup.find("div", class_=re.compile(r"body\s+post|challenge-content", re.I))
        if body_elem and isinstance(body_elem, Tag):
            text = body_elem.get_text(separator=" ", strip=True)
            if len(text) >= 30:
                return text

        og_desc = soup.find("meta", property="og:description")
        if og_desc and isinstance(og_desc, Tag):
            content = og_desc.get("content")
            if content and len(str(content).strip()) >= 20:
                return str(content).strip()

        # Fallback to paragraph accumulation
        paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
        non_empty = [p for p in paragraphs if len(p) > 20]
        if non_empty:
            return "\n\n".join(non_empty)

        return None

    @classmethod
    def _extract_org_and_country(
        cls,
        soup: BeautifulSoup,
        meta: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        organization: str | None = meta.get("requesting_organization") or meta.get("organization")
        country: str | None = meta.get("origin_country") or meta.get("country")

        # Check poster / user meta for organization
        if not organization:
            poster_li = soup.find("ul", class_=re.compile(r"poster", re.I))
            if poster_li and isinstance(poster_li, Tag):
                blue_li = poster_li.find("li", class_=re.compile(r"blue", re.I))
                if blue_li and isinstance(blue_li, Tag):
                    organization = blue_li.get_text(separator=" ", strip=True)

        if not organization:
            user_meta = soup.find("div", class_=re.compile(r"user-meta", re.I))
            if user_meta and isinstance(user_meta, Tag):
                name_link = user_meta.find("a", class_=re.compile(r"dark|bold", re.I))
                if name_link and isinstance(name_link, Tag):
                    organization = name_link.get_text(separator=" ", strip=True)
                else:
                    h3 = user_meta.find("h3")
                    if h3 and isinstance(h3, Tag):
                        raw_h3 = h3.get_text(separator=" ", strip=True)
                        m_posted = re.search(r"posted\s+by\s+(.+)$", raw_h3, re.I)
                        if m_posted:
                            organization = m_posted.group(1).strip()

        if not organization:
            tech_owner = soup.find("div", class_=re.compile(r"tech-owner", re.I))
            if tech_owner and isinstance(tech_owner, Tag):
                blue_p = tech_owner.find("p", class_=re.compile(r"blue", re.I))
                if blue_p and isinstance(blue_p, Tag):
                    organization = blue_p.get_text(separator=" ", strip=True)

        # Check details list for organization and country
        details_ul = soup.find("ul", class_=re.compile(r"details", re.I))
        if details_ul and isinstance(details_ul, Tag):
            lis = details_ul.find_all("li")
            if lis and not organization:
                first_text = lis[0].get_text(separator=" ", strip=True)
                if not first_text.lower().startswith("from ") and "deadline" not in first_text.lower():
                    organization = first_text

            for li in lis:
                li_text = li.get_text(separator=" ", strip=True)
                if li_text.lower().startswith("from "):
                    country = li_text[5:].strip()

        if not country:
            # Check tech-owner paragraph for from <em>Country</em>
            tech_owner = soup.find("div", class_=re.compile(r"tech-owner", re.I))
            if tech_owner and isinstance(tech_owner, Tag):
                t_text = tech_owner.get_text(separator=" ", strip=True)
                m_from = re.search(r"from\s+([A-Za-z\s]+?)(?:\.|$)", t_text, re.I)
                if m_from:
                    country = m_from.group(1).strip()

        return organization, country
