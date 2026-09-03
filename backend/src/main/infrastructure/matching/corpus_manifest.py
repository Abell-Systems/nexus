import hashlib
import json
from pathlib import Path


def compute_file_sha256(file_path: Path | str) -> str:
    """Computes SHA-256 hash of a file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_corpus_manifest(corpus_path: Path | str, manifest_path: Path | str) -> tuple[bool, str]:
    """Verifies that the corpus snapshot matches the expected SHA-256 in its manifest."""
    m_path = Path(manifest_path)
    if not m_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {m_path}")

    with m_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Check if manifest has a file-specific hash in provenance or root
    c_path = Path(corpus_path)
    file_name = c_path.name
    expected_sha256 = None

    if "files" in manifest and isinstance(manifest["files"], dict):
        expected_sha256 = manifest["files"].get(file_name)

    if not expected_sha256:
        expected_sha256 = (
            manifest.get("sha256")
            or manifest.get("sha256_hash")
            or manifest.get("dataset_content_sha256")
        )

    if not expected_sha256:
        raise ValueError(f"Manifest at {m_path} does not contain valid sha256 information")

    actual_sha256 = compute_file_sha256(corpus_path)
    if actual_sha256.lower() != expected_sha256.lower():
        return False, f"Corpus SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"

    return True, actual_sha256
