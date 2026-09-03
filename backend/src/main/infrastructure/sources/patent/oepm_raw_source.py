"""OEPM (Oficina Española de Patentes y Marcas) raw data source adapter."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from domain.protocols.sources import RawPayload


class OepmRawSource:
    """Source adapter for reading raw open data publications directly from OEPM / BOPI."""

    def __init__(
        self,
        file_path: Path | str = "data/raw/oepm_open_data_es.json",
        source_id: str = "oepm_open_data",
        batch_id: str = "oepm_batch_0001",
    ) -> None:
        self.file_path = Path(file_path)
        self.source_id = source_id
        self.batch_id = batch_id

    def _parse_extraction_timestamp(self, ts_str: Any) -> datetime | None:
        if not isinstance(ts_str, str):
            return None
        try:
            clean_str = ts_str[:-1] + "+00:00" if ts_str.endswith("Z") else ts_str
            return datetime.fromisoformat(clean_str)
        except Exception:
            return None

    def _build_metadata(self, raw_bytes: bytes) -> tuple[dict[str, Any], datetime]:
        metadata: dict[str, Any] = {
            "source_authority": "Oficina Española de Patentes y Marcas (OEPM / BOPI)",
            "official_catalog_url": "https://datos.gob.es/es/catalogo/e05024401-patentes-solicitadas-y-concedidas-bopi",
            "source_file": str(self.file_path),
            "source_type": "filesystem_raw",
            "content_type": "application/json",
        }
        retrieval_timestamp = datetime.now(UTC)

        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
            if isinstance(parsed, dict):
                ds_meta = parsed.get("dataset_metadata", {})
                for key, meta_key in [
                    ("dataset_title", "source_authority"),
                    ("official_catalog_url", "official_catalog_url"),
                    ("dataset_id", "dataset_id"),
                ]:
                    if key in ds_meta:
                        metadata[meta_key] = ds_meta[key]

                parsed_ts = self._parse_extraction_timestamp(ds_meta.get("extraction_timestamp"))
                if parsed_ts:
                    retrieval_timestamp = parsed_ts
        except Exception:
            pass

        return metadata, retrieval_timestamp

    def fetch_batches(self) -> Iterator[RawPayload]:
        """Read and yield unmodified raw JSON bytes from OEPM open data snapshot file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"OEPM raw data file not found at: {self.file_path}")

        raw_bytes = self.file_path.read_bytes()
        metadata, retrieval_timestamp = self._build_metadata(raw_bytes)

        yield RawPayload(
            source_id=self.source_id,
            batch_id=self.batch_id,
            payload_bytes=raw_bytes,
            metadata=metadata,
            retrieval_timestamp=retrieval_timestamp,
        )
