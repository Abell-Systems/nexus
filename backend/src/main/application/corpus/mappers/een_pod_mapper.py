"""EEN/POD Candidate Mapper for Phase-2 demand corpus expansion (ADR 0032)."""

import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup, Tag

from application.corpus.mappers.errors import MappingError
from domain.models.corpus_expansion import (
    DemandCandidateContractRecord,
    PublicationDateEvidence,
    PublicationDateEvidenceType,
)

_POD_DATE_RE = re.compile(r"TR([A-Z]{2})(\d{4})(\d{2})(\d{2})\d+")
_POD_LABEL_RE = re.compile(
    r"(?:(?:POD\s+Reference|POD\s+Ref)\s*[:\s]\s*|Reference\s*(?:Number|Code|Record)?\s*:\s*)([A-Z0-9_-]+)",
    re.IGNORECASE,
)
_CONFIDENTIALITY_RE = re.compile(r"\[(?:confidential|redacted)\]", re.IGNORECASE)
_TECH_PROBLEM_HEADING_RE = re.compile(
    r"technical\s+problem|technical\s+specification|challenge|problem\s+solved",
    re.IGNORECASE,
)


class EenPodCandidateMapper:
    """Offline factual mapper for Enterprise Europe Network POD HTML payloads."""

    @classmethod
    def map_payload(
        cls,
        raw_bytes: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> DemandCandidateContractRecord:
        """Map raw EEN/POD HTML payload into a canonical DemandCandidateContractRecord."""
        meta = metadata or {}
        if not raw_bytes or not raw_bytes.strip():
            raise MappingError("EEN/POD raw payload is empty")

        try:
            html_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                html_text = raw_bytes.decode("latin-1")
            except Exception as exc:
                raise MappingError(f"Failed to decode EEN/POD payload: {exc}") from exc

        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Reference and temporal evidence
        pod_ref, country_code, date_evidence = cls._extract_date_evidence(soup, html_text, meta)

        # 2. Demand ID
        demand_id = meta.get("demand_id")
        if not demand_id:
            if pod_ref and pod_ref != "missing":
                demand_id = pod_ref
            else:
                raise MappingError("Demand ID could not be determined from EEN/POD payload")

        # 3. Title
        title = cls._extract_title(soup, meta)
        if not title:
            raise MappingError("Title could not be extracted from EEN/POD payload")

        # 4. Technical problem evidence
        has_tech_prob, tech_prob_text = cls._extract_technical_problem(soup, meta)

        # 5. Abstract / description
        description = cls._extract_description(soup, meta)
        if not description:
            raise MappingError("Description could not be extracted from EEN/POD payload")

        # 6. Geographic stratum
        orig_country = meta.get("origin_country") or country_code
        geographic_stratum = "spain" if orig_country.upper() == "ES" else "international_european"

        # 7. Language code
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

        # 8. Confidentiality and accessibility
        has_confidentiality = bool(_CONFIDENTIALITY_RE.search(html_text))
        is_public = meta.get("is_publicly_accessible", True)
        organization_raw = meta.get("organization_raw") or meta.get("organization")

        return DemandCandidateContractRecord(
            demand_id=demand_id,
            source_id="een_pod",
            source_construct="Technology request",
            publication_date_evidence=date_evidence,
            geographic_stratum=geographic_stratum,
            title=title,
            description_text=description,
            language_code=language_code,
            organization_raw=organization_raw,
            is_publicly_accessible=is_public,
            has_confidentiality_redaction=has_confidentiality,
            has_articulated_technical_problem=has_tech_prob,
            technical_problem_evidence_text=tech_prob_text,
        )

    @classmethod
    def _extract_date_evidence(
        cls,
        soup: BeautifulSoup,
        html_text: str,
        meta: dict[str, Any],
    ) -> tuple[str | None, str, PublicationDateEvidence]:
        """Extract POD reference code, country, and structured PublicationDateEvidence."""
        ref_candidate: str | None = meta.get("pod_reference")

        if not ref_candidate:
            ref_elem = soup.find(
                attrs={"class": re.compile(r"pod-ref|reference-info|reference", re.I)}
            )
            if ref_elem and isinstance(ref_elem, Tag):
                ref_text = ref_elem.get_text(separator=" ", strip=True)
                m_label = _POD_LABEL_RE.search(ref_text)
                if m_label:
                    ref_candidate = m_label.group(1).strip()
                else:
                    m_date = _POD_DATE_RE.search(ref_text)
                    if m_date:
                        ref_candidate = m_date.group(0).strip()

        if not ref_candidate:
            m_label = _POD_LABEL_RE.search(html_text)
            if m_label:
                ref_candidate = m_label.group(1).strip()
            else:
                m_date = _POD_DATE_RE.search(html_text)
                if m_date:
                    ref_candidate = m_date.group(0).strip()

        if not ref_candidate:
            evidence = PublicationDateEvidence(
                publication_date=None,
                evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
                evidence_field="pod_reference",
                evidence_value="missing",
            )
            return None, "", evidence

        m_date = _POD_DATE_RE.search(ref_candidate)
        if m_date:
            country_code = m_date.group(1)
            year = int(m_date.group(2))
            month = int(m_date.group(3))
            day = int(m_date.group(4))
            try:
                pub_date = date(year, month, day)
                evidence = PublicationDateEvidence(
                    publication_date=pub_date,
                    evidence_type=PublicationDateEvidenceType.POD_REFERENCE,
                    evidence_field="pod_reference",
                    evidence_value=ref_candidate,
                )
                return ref_candidate, country_code, evidence
            except ValueError:
                pass

        # Reference exists but does not conform to valid YYYYMMDD date
        country_match = re.search(r"^TR([A-Z]{2})", ref_candidate)
        country_code = country_match.group(1) if country_match else ""
        evidence = PublicationDateEvidence(
            publication_date=None,
            evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
            evidence_field="pod_reference",
            evidence_value=ref_candidate,
        )
        return ref_candidate, country_code, evidence

    @classmethod
    def _extract_title(cls, soup: BeautifulSoup, meta: dict[str, Any]) -> str | None:
        if meta.get("title"):
            return str(meta["title"]).strip()

        h1 = soup.find("h1")
        if h1 and isinstance(h1, Tag):
            text = h1.get_text(separator=" ", strip=True)
            if text:
                return text

        og_title = soup.find("meta", property="og:title")
        if og_title and isinstance(og_title, Tag):
            content = og_title.get("content")
            if content and str(content).strip():
                return str(content).strip()

        if soup.title and soup.title.string:
            text = soup.title.string.strip()
            if text:
                return text

        return None

    @classmethod
    def _extract_technical_problem(
        cls,
        soup: BeautifulSoup,
        meta: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if meta.get("technical_problem_evidence_text"):
            val = str(meta["technical_problem_evidence_text"]).strip()
            return True, val

        # Look for section with class matching technical problem/specification
        tp_elem = soup.find(
            attrs={"class": re.compile(r"technical-problem|technical-specification|problem", re.I)}
        )
        if tp_elem and isinstance(tp_elem, Tag):
            text = tp_elem.get_text(separator=" ", strip=True)
            # Strip heading if present
            heading = tp_elem.find(re.compile(r"h[1-6]|dt"))
            if heading and isinstance(heading, Tag):
                heading_text = heading.get_text(separator=" ", strip=True)
                if text.startswith(heading_text):
                    text = text[len(heading_text) :].strip()
            if text:
                return True, text

        # Look for headings in DOM
        for heading in soup.find_all(re.compile(r"h[1-6]|dt")):
            h_text = heading.get_text(separator=" ", strip=True)
            if _TECH_PROBLEM_HEADING_RE.search(h_text):
                # find next sibling or container
                sibling = heading.find_next_sibling(["p", "dd", "div"])
                if sibling and isinstance(sibling, Tag):
                    s_text = sibling.get_text(separator=" ", strip=True)
                    if s_text:
                        return True, s_text

        return False, None

    @classmethod
    def _extract_description(cls, soup: BeautifulSoup, meta: dict[str, Any]) -> str | None:
        if meta.get("description"):
            return str(meta["description"]).strip()

        desc_elem = soup.find(
            attrs={"class": re.compile(r"summary|abstract|description|pod-summary", re.I)}
        )
        if desc_elem and isinstance(desc_elem, Tag):
            text = desc_elem.get_text(separator=" ", strip=True)
            if text:
                return text

        og_desc = soup.find("meta", property="og:description")
        if og_desc and isinstance(og_desc, Tag):
            content = og_desc.get("content")
            if content and str(content).strip():
                return str(content).strip()

        # Fallback: collect paragraphs
        paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
        non_empty = [p for p in paragraphs if len(p) > 20]
        if non_empty:
            return "\n\n".join(non_empty)

        return None
