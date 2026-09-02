"""Filesystem-based immutable raw payload store with SHA-256 integrity verification."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from nexus.domain.protocols.storage import RawStoreProtocol


class FilesystemRawStore(RawStoreProtocol):
    """Immutable raw payload storage organized on the local filesystem."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_sha256(self, sha256_digest: str) -> str:
        if not isinstance(sha256_digest, str) or not re.match(r"^[0-9a-f]{64}$", sha256_digest):
            raise ValueError(f"Invalid SHA-256 digest format: {sha256_digest}")
        return sha256_digest

    def store_payload(
        self,
        source_id: str,
        payload_bytes: bytes,
        metadata: dict[str, Any],
        file_ext: str = "json",
    ) -> tuple[Path, str]:
        """Store raw payload bytes along with a metadata sidecar file."""
        sha256_digest = hashlib.sha256(payload_bytes).hexdigest()
        self._validate_sha256(sha256_digest)

        ext = file_ext.lstrip(".")
        target_dir = self.base_dir / source_id if source_id else self.base_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        payload_path = target_dir / f"{sha256_digest}.{ext}"
        meta_path = target_dir / f"{sha256_digest}.meta.json"

        # Write payload
        payload_path.write_bytes(payload_bytes)

        # Write sidecar metadata
        meta_content = json.dumps(metadata, indent=2, sort_keys=True, default=str)
        meta_path.write_text(meta_content, encoding="utf-8")

        return payload_path, sha256_digest

    def _find_payload_file(self, sha256_digest: str) -> Path:
        self._validate_sha256(sha256_digest)
        candidates = [
            p
            for p in self.base_dir.rglob(f"{sha256_digest}.*")
            if not p.name.endswith(".meta.json") and p.is_file()
        ]
        if not candidates:
            raise FileNotFoundError(
                f"Payload with SHA-256 digest {sha256_digest} not found in {self.base_dir}"
            )
        return candidates[0]

    def get_payload(self, sha256_digest: str) -> bytes:
        """Retrieve raw payload bytes by SHA-256 digest."""
        file_path = self._find_payload_file(sha256_digest)
        return file_path.read_bytes()

    def verify_payload_integrity(self, sha256_digest: str) -> bool:
        """Verify the integrity of a stored payload against its expected SHA-256 digest."""
        file_path = self._find_payload_file(sha256_digest)
        content = file_path.read_bytes()
        actual_sha = hashlib.sha256(content).hexdigest()
        if actual_sha != sha256_digest:
            raise ValueError("Integrity verification failed")
        return True
