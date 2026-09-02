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

    def fetch_batches(self) -> Iterator[RawPayload]:
        """Read and yield unmodified raw JSON bytes from OEPM open data snapshot file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"OEPM raw data file not found at: {self.file_path}")

        raw_bytes = self.file_path.read_bytes()

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
                if "dataset_title" in ds_meta:
                    metadata["source_authority"] = ds_meta["dataset_title"]
                if "official_catalog_url" in ds_meta:
                    metadata["official_catalog_url"] = ds_meta["official_catalog_url"]
                if "dataset_id" in ds_meta:
                    metadata["dataset_id"] = ds_meta["dataset_id"]
                if "extraction_timestamp" in ds_meta:
                    try:
                        ts_str = ds_meta["extraction_timestamp"]
                        if ts_str.endswith("Z"):
                            ts_str = ts_str[:-1] + "+00:00"
                        retrieval_timestamp = datetime.fromisoformat(ts_str)
                    except Exception:
                        pass
        except Exception:
            pass

        yield RawPayload(
            source_id=self.source_id,
            batch_id=self.batch_id,
            payload_bytes=raw_bytes,
            metadata=metadata,
            retrieval_timestamp=retrieval_timestamp,
        )
