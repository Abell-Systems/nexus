"""TED (Tenders Electronic Daily) Candidate Mapper for Phase-2 demand corpus expansion
(ADR 0034)."""

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

_OJ_S_DATE_RE = re.compile(r"OJ\s+S\s+\d+/\d+\s+(\d{2})/(\d{2})/(\d{4})")
_CONFIDENTIALITY_RE = re.compile(r"\[(?:confidential|redacted)\]", re.IGNORECASE)
_NUTS_CODE_RE = re.compile(r"code\|name\|nuts\.([A-Z]{2})")
_LANGUAGE_CODE_RE = re.compile(r"code\|name\|language\.([A-Z]{3})")
_CHANGE_NOTICE_RE = re.compile(r"Change notice|Corrigendum", re.IGNORECASE)

# TED's 3-letter (EU-administrative) language codes -> ISO 639-1.
_LANGUAGE_3_TO_2 = {
    "BUL": "bg", "CES": "cs", "DAN": "da", "DEU": "de", "ELL": "el", "ENG": "en",
    "EST": "et", "FIN": "fi", "FRA": "fr", "GLE": "ga", "HRV": "hr", "HUN": "hu",
    "ITA": "it", "LAV": "lv", "LIT": "lt", "MLT": "mt", "NLD": "nl", "POL": "pl",
    "POR": "pt", "RON": "ro", "SLK": "sk", "SLV": "sl", "SPA": "es", "SWE": "sv",
}


class TedCandidateMapper:
    """Offline factual mapper for TED (Tenders Electronic Daily) server-rendered
    notice HTML payloads (`htmlDirect`, ADR 0034 SS2), keyed off stable eForms
    Business Term (BT) `data-labels-key` labels rather than free-text heuristics."""

    @classmethod
    def map_payload(
        cls,
        raw_bytes: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> DemandCandidateContractRecord:
        """Map a raw TED notice HTML payload into a canonical DemandCandidateContractRecord."""
        meta = metadata or {}
        if not raw_bytes or not raw_bytes.strip():
            raise MappingError("TED raw payload is empty")

        try:
            html_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                html_text = raw_bytes.decode("latin-1")
            except Exception as exc:
                raise MappingError(f"Failed to decode TED payload: {exc}") from exc

        # Amended/corrected notices are excluded outright (ADR 0034 SS3.3): their own
        # publication date is not the original solicitation's t_demand, and chasing
        # the amendment chain to its origin is deliberately out of scope.
        if _CHANGE_NOTICE_RE.search(html_text):
            raise MappingError("TED notice is a Change notice/Corrigendum; excluded per ADR 0034 SS3.3")

        soup = BeautifulSoup(html_text, "html.parser")

        demand_id = meta.get("demand_id") or cls._extract_bt_value(soup, "OPP-010")
        if not demand_id:
            raise MappingError("Demand ID (publication number) could not be determined from TED payload")

        title = cls._extract_bt_value(soup, "BT-21-Procedure")
        if not title:
            raise MappingError("Title could not be extracted from TED payload")

        description = cls._extract_bt_value(soup, "BT-24-Procedure")
        if not description:
            raise MappingError("Description could not be extracted from TED payload")

        organization_raw = cls._extract_bt_value(soup, "BT-500-Organization-Company")

        date_evidence = cls._extract_date_evidence(html_text)

        country_code = cls._extract_buyer_country(html_text)
        if country_code is None:
            # Fail closed: no buyer NUTS code found at all is an undetermined
            # stratum, not a known non-Spain one. "unknown" is not in any policy's
            # geographic_strata, so this rejects via UNAUTHORIZED_GEOGRAPHIC_STRATUM
            # rather than silently being authorized as "international_european".
            geographic_stratum = "unknown"
        else:
            geographic_stratum = "spain" if country_code == "ES" else "international_european"

        language_code = cls._extract_language_code(html_text)

        has_confidentiality = bool(_CONFIDENTIALITY_RE.search(html_text))
        is_public = meta.get("is_publicly_accessible", True)

        # No dedicated "technical specification" field distinct from the procedure
        # Description exists on this source either (same shape as EEN/POD's
        # Technology request / R&D request Abstract-fallback rule) -- the one
        # substantive narrative field serves both roles; the existing generic
        # min_word_count / NO_TECHNICAL_PROBLEM policy criteria (unmodified) do the
        # actual eligibility filtering downstream.
        has_articulated_technical_problem = bool(description.strip())
        technical_problem_evidence_text = description if has_articulated_technical_problem else None

        return DemandCandidateContractRecord(
            demand_id=str(demand_id),
            source_id="ted",
            source_construct="Innovation partnership",
            publication_date_evidence=date_evidence,
            geographic_stratum=geographic_stratum,
            title=title,
            description_text=description,
            language_code=language_code,
            organization_raw=organization_raw,
            is_publicly_accessible=is_public,
            has_confidentiality_redaction=has_confidentiality,
            has_articulated_technical_problem=has_articulated_technical_problem,
            technical_problem_evidence_text=technical_problem_evidence_text,
        )

    @classmethod
    def _extract_bt_value(cls, soup: BeautifulSoup, bt_code: str) -> str | None:
        """Find a `span.label` whose `data-labels-key` ends with `|<bt_code>` and
        return the text of the following `.data` value span."""
        label = soup.find("span", attrs={"data-labels-key": re.compile(rf"\|{re.escape(bt_code)}$")})
        if not label or not isinstance(label, Tag):
            return None
        data_span = label.find_next_sibling("span", class_="data")
        if not data_span or not isinstance(data_span, Tag):
            return None
        text = data_span.get_text(separator=" ", strip=True)
        return text or None

    @classmethod
    def _extract_date_evidence(cls, html_text: str) -> PublicationDateEvidence:
        m = _OJ_S_DATE_RE.search(html_text)
        if not m:
            return PublicationDateEvidence(
                publication_date=None,
                evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
                evidence_field="oj_s_publication_date",
                evidence_value="missing",
            )
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            pub_date = date(year, month, day)
        except ValueError:
            return PublicationDateEvidence(
                publication_date=None,
                evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
                evidence_field="oj_s_publication_date",
                evidence_value=m.group(0),
            )
        return PublicationDateEvidence(
            publication_date=pub_date,
            evidence_type=PublicationDateEvidenceType.EXPLICIT_METADATA,
            evidence_field="oj_s_publication_date",
            evidence_value=m.group(0),
        )

    @classmethod
    def _extract_buyer_country(cls, html_text: str) -> str | None:
        """First NUTS code in document order belongs to the buyer's own address
        block (section 1.1, Buyer), which precedes any Place-of-performance
        section (section 2/5) -- a document-order rule, not a semantic guess."""
        m = _NUTS_CODE_RE.search(html_text)
        return m.group(1) if m else None

    @classmethod
    def _extract_language_code(cls, html_text: str) -> str:
        m = _LANGUAGE_CODE_RE.search(html_text)
        if m:
            return _LANGUAGE_3_TO_2.get(m.group(1), "en")
        return "en"
