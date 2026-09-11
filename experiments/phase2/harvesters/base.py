"""Base Harvester and Operational Raw Storage Foundations (ADR 0032)."""

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DEFAULT_HARVESTER_VERSION = "phase2_harvester_v1"


class PayloadCollisionError(Exception):
    """Raised when an incoming raw payload has differing SHA-256 hash from an existing file on disk."""


class BaseHarvester:
    """Base class for polite demand harvesters with immutable raw staging."""

    def __init__(
        self,
        delay_seconds: float = 1.0,
        user_agent: str | None = None,
        timeout_seconds: float = 30.0,
        harvester_version: str = DEFAULT_HARVESTER_VERSION,
    ) -> None:
        self.delay_seconds = delay_seconds
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.timeout_seconds = timeout_seconds
        self.harvester_version = harvester_version
        self.acquisition_errors: list[dict[str, Any]] = []
        self._last_request_time: float = 0.0

    def _pace(self) -> None:
        """Enforce polite delay between consecutive network requests."""
        if self.delay_seconds > 0.0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay_seconds:
                time.sleep(self.delay_seconds - elapsed)
        self._last_request_time = time.time()

    def fetch_url(self, url: str) -> tuple[bytes, int]:
        """Fetch content from URL using standard urllib with custom user-agent and timeout."""
        self._pace()
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            payload = resp.read()
            raw_status = getattr(resp, "status", None)
            if raw_status is None:
                raw_status = getattr(resp, "code", 200)
            status = int(raw_status) if raw_status is not None else 200
            return payload, status


    def record_error(
        self,
        source_id: str,
        uri: str,
        error_type: str,
        message: str,
        demand_id: str | None = None,
        http_status: int | None = None,
    ) -> dict[str, Any]:
        """Record an operational acquisition error."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "source_id": source_id,
            "uri": uri,
            "demand_id": demand_id,
            "error_type": error_type,
            "message": message,
            "http_status": http_status,
        }
        self.acquisition_errors.append(entry)
        return entry

    def dump_errors(self, path: Path) -> None:
        """Persist accumulated acquisition errors into a formatted JSON artifact."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.acquisition_errors, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def save_raw_payload(
        self,
        demand_id: str,
        source_id: str,
        source_uri: str,
        payload_bytes: bytes,
        out_dir: Path,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Immutably stage raw payload bytes with cryptographic SHA-256 sidecar.

        If <demand_id>.<ext> already exists:
          - If existing content matches incoming hash: idempotent no-op (skips write).
          - If existing content differs: raises PayloadCollisionError.
        """
        meta = dict(metadata or {})
        target_dir = out_dir if out_dir.name == source_id else (out_dir / source_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        ext = meta.get("file_extension")
        if not ext:
            stripped = payload_bytes.strip()
            ext = ".json" if (stripped.startswith(b"{") or stripped.startswith(b"[")) else ".html"
        if not ext.startswith("."):
            ext = f".{ext}"

        target_file = target_dir / f"{demand_id}{ext}"
        meta_file = target_dir / f"{demand_id}.meta.json"

        incoming_hash = hashlib.sha256(payload_bytes).hexdigest()

        if target_file.exists():
            existing_bytes = target_file.read_bytes()
            existing_hash = hashlib.sha256(existing_bytes).hexdigest()
            if existing_hash == incoming_hash:
                return target_file
            raise PayloadCollisionError(
                f"Payload collision for {demand_id}: existing hash {existing_hash} differs from incoming hash {incoming_hash}"
            )

        target_file.write_bytes(payload_bytes)

        meta_record: dict[str, Any] = {
            "demand_id": demand_id,
            "source_id": source_id,
            "source_uri": source_uri,
            "acquisition_timestamp": datetime.now(UTC).isoformat(),
            "raw_payload_sha256": incoming_hash,
            "harvester_version": meta.get("harvester_version", self.harvester_version),
            "http_status": meta.get("http_status", 200),
        }
        for k, v in meta.items():
            if k not in meta_record and k != "file_extension":
                meta_record[k] = v

        meta_file.write_text(json.dumps(meta_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target_file

    @staticmethod
    def get_known_source_uris(out_dir: Path, source_id: str) -> dict[str, Path]:
        """Scan out_dir / source_id for existing raw payloads by source_uri."""
        target_dir = out_dir if out_dir.name == source_id else (out_dir / source_id)
        if not target_dir.exists():
            return {}
        known: dict[str, Path] = {}
        for meta_path in target_dir.glob("*.meta.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                uri = data.get("source_uri")
                demand_id = data.get("demand_id")
                if uri and demand_id:
                    for payload_file in target_dir.glob(f"{demand_id}.*"):
                        if not payload_file.name.endswith(".meta.json"):
                            known[uri] = payload_file
                            break
            except Exception:
                continue
        return known
