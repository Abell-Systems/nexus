"""OEPM (Oficina Española de Patentes y Marcas) patent normalizer."""

import json
from collections.abc import Iterator
from typing import Any

from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.patent import PatentDocument
from domain.protocols.sources import RawPayload

LIST_STR_TYPE = "list[str]"


class OepmNormalizer:
    """Normalizer for Spanish Patent and Trademark Office (OEPM) open data publications."""

    def __init__(self, extraction_version: str = "1.0.0") -> None:
        self.extraction_version = extraction_version

    def normalize_stream(
        self, raw_payload: RawPayload
    ) -> Iterator[tuple[PatentDocument, list[FieldObservation]]]:
        """Normalize raw JSON payload into stream of PatentDocuments and FieldObservations."""
        payload_data = json.loads(raw_payload.payload_bytes.decode("utf-8"))
        dataset_metadata, publications = self._extract_payload_meta_and_items(payload_data)

        source_authority = (
            dataset_metadata.get("dataset_title")
            or raw_payload.metadata.get("source_authority")
            or "Spanish Patent and Trademark Office (OEPM)"
        )

        for item in publications:
            doc, source_uri, verification_status = self._normalize_single_publication(
                item, raw_payload, dataset_metadata
            )
            observations = self._create_field_observations(
                doc, raw_payload, source_authority, source_uri, verification_status
            )
            yield doc, observations

    def _extract_payload_meta_and_items(
        self, payload_data: Any
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        dataset_metadata: dict[str, Any] = {}
        publications: list[dict[str, Any]] = []

        if isinstance(payload_data, dict):
            dataset_metadata = payload_data.get("dataset_metadata", {})
            if "publications" in payload_data:
                publications = payload_data["publications"]
            elif "items" in payload_data:
                publications = payload_data["items"]
            else:
                publications = [payload_data]
        elif isinstance(payload_data, list):
            publications = payload_data

        return dataset_metadata, publications

    def _normalize_single_publication(
        self,
        item: dict[str, Any],
        raw_payload: RawPayload,
        dataset_metadata: dict[str, Any],
    ) -> tuple[PatentDocument, str, VerificationStatus]:
        pub_id = item.get("publication_id") or item.get("publication_number") or item.get("id") or ""
        country_code, doc_number, kind_code = self._parse_biblio_codes(item, pub_id)

        assignees = self._extract_names(item, "assignee", "assignees")
        inventors = self._extract_names(item, "inventor", "inventors")
        classifications_cpc = self._extract_classifications(item, "cpc_codes", "classifications_cpc")
        classifications_ipc = self._extract_classifications(item, "ipc_codes", "classifications_ipc")

        forward_citation_count = self._parse_int_field(item, "forward_citation_count", "citation_count")
        backward_citation_count = self._parse_int_field(item, "backward_citation_count")

        doc = PatentDocument(
            publication_id=pub_id,
            country_code=country_code,
            doc_number=doc_number,
            kind_code=kind_code,
            application_number=item.get("application_number"),
            title=item.get("title", ""),
            abstract=item.get("abstract", ""),
            assignees=assignees,
            inventors=inventors,
            filing_date=item.get("filing_date"),
            publication_date=item.get("publication_date"),
            priority_date=item.get("priority_date"),
            classifications_cpc=classifications_cpc,
            classifications_ipc=classifications_ipc,
            forward_citation_count=forward_citation_count,
            backward_citation_count=backward_citation_count,
            family_id=item.get("family_id"),
        )

        source_uri = (
            item.get("invenes_url")
            or raw_payload.metadata.get("source_uri")
            or dataset_metadata.get("official_catalog_url")
            or ""
        )
        verification_status = self._parse_verification_status(item.get("verification_status"))
        return doc, source_uri, verification_status

    def _parse_biblio_codes(self, item: dict[str, Any], pub_id: str) -> tuple[str, str, str]:
        country_code = item.get("country_code")
        doc_number = item.get("doc_number")
        kind_code = item.get("kind_code")

        if pub_id and ("-" in pub_id):
            parts = pub_id.split("-")
            if country_code is None and len(parts) >= 1:
                country_code = parts[0]
            if doc_number is None and len(parts) >= 2:
                doc_number = parts[1]
            if kind_code is None and len(parts) >= 3:
                kind_code = parts[2]

        country_code = country_code or ("ES" if pub_id else "")
        doc_number = doc_number or pub_id
        kind_code = kind_code or ""
        return country_code, doc_number, kind_code

    def _extract_names(self, item: dict[str, Any], singular: str, plural: str) -> list[str]:
        if plural in item and isinstance(item[plural], list):
            return [str(a).strip() for a in item[plural] if str(a).strip()]
        if plural in item and isinstance(item[plural], str):
            return self._split_names(item[plural])
        if singular in item and isinstance(item[singular], str):
            return self._split_names(item[singular])
        return []

    def _extract_classifications(self, item: dict[str, Any], raw_key1: str, raw_key2: str) -> list[str]:
        raw = item.get(raw_key1) or item.get(raw_key2) or []
        if isinstance(raw, str):
            raw = [raw]
        return [str(c).strip() for c in raw if str(c).strip()]

    def _parse_int_field(self, item: dict[str, Any], *keys: str) -> int | None:
        for k in keys:
            if item.get(k) is not None:
                return int(item[k])
        return None

    def _parse_verification_status(self, raw_status: Any) -> VerificationStatus:
        raw_v = str(raw_status or "").lower()
        if "verified" in raw_v or raw_v == "independently_verified":
            return VerificationStatus.INDEPENDENTLY_VERIFIED
        if raw_v == "derived":
            return VerificationStatus.DERIVED
        if raw_v == "unavailable":
            return VerificationStatus.UNAVAILABLE
        return VerificationStatus.SOURCE_REPORTED

    def _create_field_observations(
        self,
        doc: PatentDocument,
        raw_payload: RawPayload,
        source_authority: str,
        source_uri: str,
        verification_status: VerificationStatus,
    ) -> list[FieldObservation]:
        observations: list[FieldObservation] = []

        def _add(field_name: str, value: Any, val_type: str) -> None:
            observations.append(
                FieldObservation(
                    entity_id=doc.publication_id,
                    field_name=field_name,
                    observed_value_json=json.dumps(value, ensure_ascii=False),
                    value_type=val_type,
                    source_authority=source_authority,
                    source_uri=source_uri,
                    retrieval_timestamp=raw_payload.retrieval_timestamp,
                    raw_payload_sha256=raw_payload.payload_sha256,
                    extraction_version=self.extraction_version,
                    verification_status=verification_status,
                )
            )

        if doc.title:
            _add("title", doc.title, "str")
        if doc.abstract:
            _add("abstract", doc.abstract, "str")
        if doc.publication_date is not None:
            _add("publication_date", doc.publication_date, "str")
        if doc.filing_date is not None:
            _add("filing_date", doc.filing_date, "str")
        if doc.priority_date is not None:
            _add("priority_date", doc.priority_date, "str")
        if doc.assignees:
            _add("assignees", doc.assignees, LIST_STR_TYPE)
        if doc.inventors:
            _add("inventors", doc.inventors, LIST_STR_TYPE)
        if doc.classifications_cpc:
            _add("classifications_cpc", doc.classifications_cpc, LIST_STR_TYPE)
        if doc.classifications_ipc:
            _add("classifications_ipc", doc.classifications_ipc, LIST_STR_TYPE)
        if doc.forward_citation_count is not None:
            _add("forward_citation_count", doc.forward_citation_count, "int")
        if doc.backward_citation_count is not None:
            _add("backward_citation_count", doc.backward_citation_count, "int")

        return observations

    def _split_names(self, raw_str: str) -> list[str]:
        """Split a string containing one or more entity names."""
        raw_str = raw_str.strip()
        if not raw_str:
            return []
        if " / " in raw_str:
            return [part.strip() for part in raw_str.split(" / ") if part.strip()]
        if "/" in raw_str and not raw_str.startswith(("http://", "https://")):
            return [part.strip() for part in raw_str.split("/") if part.strip()]
        if ";" in raw_str:
            return [part.strip() for part in raw_str.split(";") if part.strip()]
        return [raw_str]
