"""OEPM (Oficina Española de Patentes y Marcas) BOPI Tomo II XML normalizer.

Adheres strictly to WIPO ST.16, WIPO ST.36, and the official OEPM Tomo2.xsd schema.
Extracts patent publications using semantic tag matching (order-independent), validates
dates, applies the normative kind code universe {A1, A2, B1, B2, U, T3}, supports claims/text
fallback for European translations (T3), and classifies records into INCLUDED, EXCLUDED,
or QUARANTINED without dropping invalid data.
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime

from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.ingestion import (
    ExcludedRecord,
    ExclusionReason,
    NormalizationResult,
    QuarantinedRecord,
    QuarantineReason,
    RecordDisposition,
)
from domain.models.patent import PatentDocument
from domain.protocols.sources import RawPayload

NORMATIVE_KIND_CODES: frozenset[str] = frozenset({"A1", "A2", "B1", "B2", "U", "T3"})
DATE_PATTERNS = [
    (re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"), "%d/%m/%Y"),  # Official Tomo2.xsd dd/MM/yyyy
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), "%Y-%m-%d"),  # ISO-8601 YYYY-MM-DD
    (re.compile(r"^(\d{4})(\d{2})(\d{2})$"), "%Y%m%d"),      # Compact EPO/WIPO YYYYMMDD
]


class OepmXmlNormalizer:
    """Production XML normalizer for OEPM BOPI Tomo II (Invenciones) publications."""

    def __init__(
        self,
        extraction_version: str = "2.0.0",
        target_country: str = "ES",
        min_publication_year: int = 2016,
        max_publication_year: int = 2024,
    ) -> None:
        self.extraction_version = extraction_version
        self.target_country = target_country
        self.min_publication_year = min_publication_year
        self.max_publication_year = max_publication_year

    def normalize_stream(
        self, raw_payload: RawPayload
    ) -> Iterator[tuple[PatentDocument, list[FieldObservation]]]:
        """Backward-compatible stream yielding only INCLUDED records for existing pipeline."""
        for result in self.normalize_results(raw_payload):
            if result.disposition == RecordDisposition.INCLUDED and result.document is not None:
                yield result.document, result.observations

    def normalize_results(self, raw_payload: RawPayload) -> Iterator[NormalizationResult]:
        """Comprehensive stream yielding all results (INCLUDED, EXCLUDED, QUARANTINED)."""
        source_uri = raw_payload.metadata.get("source_uri") or raw_payload.metadata.get(
            "official_catalog_url", "https://sede.oepm.gob.es/bopiweb"
        )
        source_authority = raw_payload.metadata.get(
            "source_authority", "Oficina Española de Patentes y Marcas (OEPM)"
        )

        # Defend against external entity expansion and malicious DTD injections
        raw_bytes = raw_payload.payload_bytes
        if b"<!ENTITY" in raw_bytes or b"SYSTEM" in raw_bytes and b"<!DOCTYPE" in raw_bytes:
            yield NormalizationResult(
                disposition=RecordDisposition.QUARANTINED,
                quarantined=QuarantinedRecord(
                    raw_identifier=raw_payload.batch_id,
                    reason=QuarantineReason.MALFORMED_XML_SYNTAX,
                    error_message="Security Violation: XML contains disallowed external entities or DTD declarations",
                    raw_snippet=raw_bytes[:300].decode("utf-8", errors="replace"),
                    detected_at=datetime.now(UTC),
                    source_uri=source_uri,
                ),
            )
            return

        try:
            root = ET.fromstring(raw_bytes)
        except ET.ParseError as e:
            raw_snippet = raw_payload.payload_bytes[:300].decode("utf-8", errors="replace")
            yield NormalizationResult(
                disposition=RecordDisposition.QUARANTINED,
                quarantined=QuarantinedRecord(
                    raw_identifier=raw_payload.batch_id,
                    reason=QuarantineReason.MALFORMED_XML_SYNTAX,
                    error_message=f"XML ParseError: {e}",
                    raw_snippet=raw_snippet,
                    detected_at=datetime.now(UTC),
                    source_uri=source_uri,
                ),
            )
            return

        # Discover all publication blocks semantically
        pub_elements = self._find_publication_elements(root)
        if not pub_elements:
            # Check if root itself is a single publication or document
            pub_elements = [root]

        for elem in pub_elements:
            yield self._normalize_single_element(elem, raw_payload, source_authority, source_uri)

    def _find_publication_elements(self, root: ET.Element) -> list[ET.Element]:
        """Locate individual publication elements strictly avoiding nested double-counting.
        
        Searches top-down and does not descend into matched publication elements.
        """
        matches: list[ET.Element] = []
        target_tags = {
            "publicacion",
            "publicacionconcesion",
            "patente",
            "modeloutilidad",
            "exchange-document",
        }
        
        def traverse(node: ET.Element) -> None:
            tag_local = self._clean_tag(node.tag).lower()
            if tag_local in target_tags:
                matches.append(node)
                # Do not recurse into child elements of an already identified publication unit
                return
            for child in node:
                traverse(child)

        traverse(root)
        return matches

    def _clean_tag(self, tag: str) -> str:
        """Strip XML namespace prefix from tag name."""
        return tag.split("}")[-1] if "}" in tag else tag

    def _get_element_text(self, parent: ET.Element, pattern_names: list[str]) -> str:
        """Find the first matching descendant tag matching any pattern in pattern_names."""
        lower_patterns = [p.lower() for p in pattern_names]
        for desc in parent.iter():
            clean = self._clean_tag(desc.tag).lower()
            if any(clean == p or clean.endswith(f"_{p}") or clean.startswith(f"{p}_") for p in lower_patterns) and desc.text and desc.text.strip():
                return desc.text.strip()
        return ""

    def _get_all_element_texts(self, parent: ET.Element, pattern_names: list[str]) -> list[str]:
        """Find all matching descendant tags matching any pattern in pattern_names."""
        lower_patterns = [p.lower() for p in pattern_names]
        results: list[str] = []
        for desc in parent.iter():
            clean = self._clean_tag(desc.tag).lower()
            if any(clean == p or clean.endswith(f"_{p}") or clean.startswith(f"{p}_") for p in lower_patterns) and desc.text and desc.text.strip():
                val = desc.text.strip()
                if val not in results:
                    results.append(val)
        return results

    def _normalize_date(self, raw_date: str) -> str | None:
        """Convert official OEPM date formats to ISO-8601 (YYYY-MM-DD)."""
        if not raw_date:
            return None
        cleaned = raw_date.strip()
        for regex, date_fmt in DATE_PATTERNS:
            if regex.match(cleaned):
                try:
                    dt = datetime.strptime(cleaned, date_fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    def _normalize_single_element(
        self,
        elem: ET.Element,
        raw_payload: RawPayload,
        source_authority: str,
        source_uri: str,
    ) -> NormalizationResult:
        """Normalize a single XML publication element into a typed NormalizationResult."""
        raw_snippet = ET.tostring(elem, encoding="utf-8")[:300].decode("utf-8", errors="replace")

        # 1. Identifier extraction (order-independent)
        pub_id_raw = self._get_element_text(
            elem,
            ["publicacionid", "p11_numpatenteccp", "doc-number", "doc_number", "id", "numero_publicacion"],
        )
        if not pub_id_raw and "doc-number" in elem.attrib:
            pub_id_raw = elem.attrib["doc-number"]

        if not pub_id_raw:
            return NormalizationResult(
                disposition=RecordDisposition.QUARANTINED,
                quarantined=QuarantinedRecord(
                    raw_identifier=None,
                    reason=QuarantineReason.MISSING_REQUIRED_IDENTIFIER,
                    error_message="Publication element is missing publication identifier tag (p11, PublicacionId, doc-number)",
                    raw_snippet=raw_snippet,
                    detected_at=datetime.now(UTC),
                    source_uri=source_uri,
                ),
            )

        # 2. Country code & Kind code parsing
        country_code = self._get_element_text(elem, ["pais", "country", "country_code"])
        if not country_code and "country" in elem.attrib:
            country_code = elem.attrib["country"]

        kind_code = self._get_element_text(elem, ["kind", "kind_code", "codigotipo", "letra_tipo"])
        if not kind_code and "kind" in elem.attrib:
            kind_code = elem.attrib["kind"]

        # If pub_id_raw contains prefix/suffix (e.g. ES2849102B2 or ES-2849102-B2)
        clean_num = pub_id_raw.replace("-", "").strip()
        m_pattern = re.match(r"^([A-Z]{2})?(\d+)([A-Z]\d?)?$", clean_num, re.IGNORECASE)
        if m_pattern:
            if not country_code and m_pattern.group(1):
                country_code = m_pattern.group(1).upper()
            doc_number = m_pattern.group(2)
            if not kind_code and m_pattern.group(3):
                kind_code = m_pattern.group(3).upper()
        else:
            doc_number = clean_num

        country_code = (country_code or self.target_country).upper()
        kind_code = (kind_code or "").upper()
        canonical_pub_id = f"{country_code}{doc_number}{kind_code}"

        # 3. Validation against Kind-Code Universe
        if kind_code not in NORMATIVE_KIND_CODES:
            return NormalizationResult(
                disposition=RecordDisposition.EXCLUDED,
                excluded=ExcludedRecord(
                    publication_id=canonical_pub_id,
                    country_code=country_code,
                    kind_code=kind_code,
                    reason=ExclusionReason.UNSUPPORTED_KIND_CODE,
                    detail=f"Kind code '{kind_code}' is outside normative universe {sorted(NORMATIVE_KIND_CODES)}",
                    source_uri=source_uri,
                ),
            )

        # 4. Dates extraction and validation
        pub_date_raw = self._get_element_text(
            elem,
            ["fechapublicacion", "p45_fechapublicaciondelaconcesion", "date", "publication_date"],
        )
        norm_pub_date = self._normalize_date(pub_date_raw)
        if pub_date_raw and not norm_pub_date:
            return NormalizationResult(
                disposition=RecordDisposition.QUARANTINED,
                quarantined=QuarantinedRecord(
                    raw_identifier=canonical_pub_id,
                    reason=QuarantineReason.INVALID_DATE_FORMAT,
                    error_message=f"Invalid publication date value '{pub_date_raw}' does not match expected patterns",
                    raw_snippet=raw_snippet,
                    detected_at=datetime.now(UTC),
                    source_uri=source_uri,
                ),
            )

        # Temporal boundary check
        if norm_pub_date:
            pub_year = int(norm_pub_date.split("-")[0])
            if pub_year < self.min_publication_year or pub_year > self.max_publication_year:
                return NormalizationResult(
                    disposition=RecordDisposition.EXCLUDED,
                    excluded=ExcludedRecord(
                        publication_id=canonical_pub_id,
                        country_code=country_code,
                        kind_code=kind_code,
                        reason=ExclusionReason.OUT_OF_SCOPE_TEMPORAL_WINDOW,
                        detail=f"Publication year {pub_year} outside target window [{self.min_publication_year}, {self.max_publication_year}]",
                        source_uri=source_uri,
                    ),
                )

        filing_date_raw = self._get_element_text(elem, ["fechasolicitud", "p22_fechasolicitud", "filing_date"])
        norm_filing_date = self._normalize_date(filing_date_raw)

        priority_date_raw = self._get_element_text(
            elem, ["p32_fechasolicitudprioritaria", "prioridad_fecha", "priority_date"]
        )
        norm_priority_date = self._normalize_date(priority_date_raw)

        # 5. Text fields extraction with explicit deterministic hierarchy (Abstract > Claims > Description)
        title = self._get_element_text(
            elem, ["p54_tituloinvencion", "titulo", "tituloinvencion", "invention-title", "title"]
        )
        
        # Primary: Look exclusively for formal abstract tags first
        abstract = self._get_element_text(
            elem, ["p57_resumenoreivindicacion", "resumen", "abstract"]
        )

        # Fallback hierarchy for T3 (European translations) when formal abstract is omitted
        if not abstract and kind_code == "T3":
            claims_text = self._get_element_text(
                elem, ["claims", "reivindicaciones", "p57_reivindicaciones", "reivindicacion"]
            )
            if claims_text:
                abstract = claims_text
            else:
                desc_text = self._get_element_text(
                    elem, ["description", "memoria_descriptiva", "p57_memoria"]
                )
                if desc_text:
                    abstract = desc_text

        # 6. Metadata: Assignees, Inventors, CPC, IPC
        assignees = self._get_all_element_texts(
            elem, ["p73_nombretitular", "p731_nombretitularotros", "titular", "applicant-name", "name"]
        )
        inventors = self._get_all_element_texts(
            elem, ["p72_nombreinventor", "inventor-name", "inventor"]
        )

        # Classifications
        classifications_cpc = self._get_all_element_texts(
            elem, ["classification-symbol", "cpc", "p51_clasificacioninternacionalpatentes", "clasificacion"]
        )
        # Filter standard format (A01B, C11D, etc.)
        valid_cpc = [c.replace(" ", "").upper() for c in classifications_cpc if len(c.strip()) >= 3]

        app_num = self._get_element_text(
            elem, ["p21_numsolicitud", "p21_numeroexpediente", "numsolicitud", "application_number"]
        )

        # Rule: Critical text completeness (must possess non-empty title and abstract/claims)
        if not title or not title.strip() or not abstract or not abstract.strip():
            return NormalizationResult(
                disposition=RecordDisposition.EXCLUDED,
                excluded=ExcludedRecord(
                    publication_id=canonical_pub_id,
                    country_code=country_code,
                    kind_code=kind_code,
                    reason=ExclusionReason.MISSING_CRITICAL_TEXT,
                    detail=f"Missing essential technical text: title='{bool(title and title.strip())}', abstract='{bool(abstract and abstract.strip())}'",
                    source_uri=source_uri,
                ),
            )

        doc = PatentDocument(
            publication_id=canonical_pub_id,
            country_code=country_code,
            doc_number=doc_number,
            kind_code=kind_code,
            application_number=app_num or None,
            title=title.strip(),
            abstract=abstract.strip(),
            assignees=assignees,
            inventors=inventors,
            filing_date=norm_filing_date,
            publication_date=norm_pub_date,
            priority_date=norm_priority_date,
            classifications_cpc=valid_cpc,
            classifications_ipc=valid_cpc,
        )

        # 7. Build Provenance Field Observations
        observations = self._build_observations(
            doc, raw_payload, source_authority, source_uri
        )

        return NormalizationResult(
            disposition=RecordDisposition.INCLUDED,
            document=doc,
            observations=observations,
        )

    def _build_observations(
        self,
        doc: PatentDocument,
        raw_payload: RawPayload,
        source_authority: str,
        source_uri: str,
    ) -> list[FieldObservation]:
        """Construct granular field observations for legal and empirical traceability."""
        ts = raw_payload.retrieval_timestamp
        sha = raw_payload.payload_sha256

        fields = [
            ("title", doc.title, "str"),
            ("abstract", doc.abstract, "str"),
            ("kind_code", doc.kind_code, "str"),
            ("publication_date", doc.publication_date or "", "str"),
            ("classifications_cpc", str(doc.classifications_cpc), "list[str]"),
        ]

        obs_list: list[FieldObservation] = []
        for name, val, v_type in fields:
            obs_list.append(
                FieldObservation(
                    entity_id=doc.publication_id,
                    field_name=name,
                    observed_value_json=f'"{val}"',
                    value_type=v_type,
                    source_authority=source_authority,
                    source_uri=source_uri,
                    retrieval_timestamp=ts,
                    raw_payload_sha256=sha,
                    extraction_version=self.extraction_version,
                    verification_status=VerificationStatus.SOURCE_REPORTED,
                )
            )
        return obs_list
