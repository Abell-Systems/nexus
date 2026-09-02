"""OEPM (Oficina Española de Patentes y Marcas) patent normalizer."""

import json
from collections.abc import Iterator
from typing import Any

from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.patent import PatentDocument
from domain.protocols.sources import RawPayload


class OepmNormalizer:
    """Normalizer for Spanish Patent and Trademark Office (OEPM) open data publications."""

    def __init__(self, extraction_version: str = "1.0.0") -> None:
        self.extraction_version = extraction_version

    def normalize_stream(
        self, raw_payload: RawPayload
    ) -> Iterator[tuple[PatentDocument, list[FieldObservation]]]:
        """Normalize raw JSON payload into stream of PatentDocuments and FieldObservations."""
        payload_data = json.loads(raw_payload.payload_bytes.decode("utf-8"))

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

        source_authority = (
            dataset_metadata.get("dataset_title")
            or raw_payload.metadata.get("source_authority")
            or "Spanish Patent and Trademark Office (OEPM)"
        )

        for item in publications:
            pub_id = (
                item.get("publication_id")
                or item.get("publication_number")
                or item.get("id")
                or ""
            )

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

            # Assignees parsing
            assignees: list[str] = []
            if "assignees" in item and isinstance(item["assignees"], list):
                assignees = [str(a).strip() for a in item["assignees"] if str(a).strip()]
            elif "assignees" in item and isinstance(item["assignees"], str):
                assignees = self._split_names(item["assignees"])
            elif "assignee" in item and isinstance(item["assignee"], str):
                assignees = self._split_names(item["assignee"])

            # Inventors parsing
            inventors: list[str] = []
            if "inventors" in item and isinstance(item["inventors"], list):
                inventors = [str(i).strip() for i in item["inventors"] if str(i).strip()]
            elif "inventors" in item and isinstance(item["inventors"], str):
                inventors = self._split_names(item["inventors"])
            elif "inventor" in item and isinstance(item["inventor"], str):
                inventors = self._split_names(item["inventor"])

            # CPC / IPC Classifications
            cpc_raw = item.get("cpc_codes") or item.get("classifications_cpc") or []
            if isinstance(cpc_raw, str):
                cpc_raw = [cpc_raw]
            classifications_cpc = [str(c).strip() for c in cpc_raw if str(c).strip()]

            ipc_raw = item.get("ipc_codes") or item.get("classifications_ipc") or []
            if isinstance(ipc_raw, str):
                ipc_raw = [ipc_raw]
            classifications_ipc = [str(i).strip() for i in ipc_raw if str(i).strip()]

            # Citations (strict null preservation)
            forward_citation_count: int | None = None
            if item.get("forward_citation_count") is not None:
                forward_citation_count = int(item["forward_citation_count"])
            elif item.get("citation_count") is not None:
                forward_citation_count = int(item["citation_count"])

            backward_citation_count: int | None = None
            if item.get("backward_citation_count") is not None:
                backward_citation_count = int(item["backward_citation_count"])

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

            # Verification status
            raw_v_status = str(item.get("verification_status", "")).lower()
            if "verified" in raw_v_status or raw_v_status == "independently_verified":
                verification_status = VerificationStatus.INDEPENDENTLY_VERIFIED
            elif raw_v_status == "derived":
                verification_status = VerificationStatus.DERIVED
            elif raw_v_status == "unavailable":
                verification_status = VerificationStatus.UNAVAILABLE
            else:
                verification_status = VerificationStatus.SOURCE_REPORTED

            source_uri = (
                item.get("invenes_url")
                or raw_payload.metadata.get("source_uri")
                or dataset_metadata.get("official_catalog_url")
                or ""
            )

            observations: list[FieldObservation] = []

            def _add_obs(
                field_name: str,
                value: Any,
                val_type: str,
                p_id: str = pub_id,
                auth: str = source_authority,
                uri: str = source_uri,
                v_stat: VerificationStatus = verification_status,
                obs_list: list[FieldObservation] = observations,
            ) -> None:
                obs_list.append(
                    FieldObservation(
                        entity_id=p_id,
                        field_name=field_name,
                        observed_value_json=json.dumps(value, ensure_ascii=False),
                        value_type=val_type,
                        source_authority=auth,
                        source_uri=uri,
                        retrieval_timestamp=raw_payload.retrieval_timestamp,
                        raw_payload_sha256=raw_payload.payload_sha256,
                        extraction_version=self.extraction_version,
                        verification_status=v_stat,
                    )
                )

            if doc.title:
                _add_obs("title", doc.title, "str")
            if doc.abstract:
                _add_obs("abstract", doc.abstract, "str")
            if doc.publication_date is not None:
                _add_obs("publication_date", doc.publication_date, "str")
            if doc.filing_date is not None:
                _add_obs("filing_date", doc.filing_date, "str")
            if doc.priority_date is not None:
                _add_obs("priority_date", doc.priority_date, "str")
            if doc.assignees:
                _add_obs("assignees", doc.assignees, "list[str]")
            if doc.inventors:
                _add_obs("inventors", doc.inventors, "list[str]")
            if doc.classifications_cpc:
                _add_obs("classifications_cpc", doc.classifications_cpc, "list[str]")
            if doc.classifications_ipc:
                _add_obs("classifications_ipc", doc.classifications_ipc, "list[str]")
            if doc.forward_citation_count is not None:
                _add_obs("forward_citation_count", doc.forward_citation_count, "int")
            if doc.backward_citation_count is not None:
                _add_obs("backward_citation_count", doc.backward_citation_count, "int")

            yield doc, observations

    def _split_names(self, raw_str: str) -> list[str]:
        """Split a string containing one or more entity names."""
        raw_str = raw_str.strip()
        if not raw_str:
            return []
        if " / " in raw_str:
            return [part.strip() for part in raw_str.split(" / ") if part.strip()]
        if "/" in raw_str and not (raw_str.startswith("http://") or raw_str.startswith("https://")):
            return [part.strip() for part in raw_str.split("/") if part.strip()]
        if ";" in raw_str:
            return [part.strip() for part in raw_str.split(";") if part.strip()]
        return [raw_str]
