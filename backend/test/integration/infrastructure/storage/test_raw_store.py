import hashlib
import json
from pathlib import Path

import pytest

from infrastructure.storage.raw_store import FilesystemRawStore


def test_raw_store_store_and_get_payload(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)
    sample_data = b'{"publication_id": "ES-2849102-B2", "title": "Test Patent"}'
    metadata = {"source_authority": "OEPM", "version": "1.0.0"}

    path, sha256_digest = store.store_payload(
        source_id="oepm_bopi",
        payload_bytes=sample_data,
        metadata=metadata,
        file_ext="json",
    )

    expected_sha = hashlib.sha256(sample_data).hexdigest()
    assert sha256_digest == expected_sha
    assert len(sha256_digest) == 64
    assert path.exists()
    assert path.is_file()

    # Verify metadata sidecar
    meta_path = path.parent / f"{sha256_digest}.meta.json"
    assert meta_path.exists()
    loaded_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert loaded_meta["source_authority"] == "OEPM"
    assert loaded_meta["version"] == "1.0.0"

    # Verify retrieval
    retrieved = store.get_payload(sha256_digest)
    assert retrieved == sample_data


def test_raw_store_idempotent_writes(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)
    sample_data = b'{"key": "value"}'
    metadata = {"meta": "data"}

    path1, sha1 = store.store_payload("src1", sample_data, metadata)
    path2, sha2 = store.store_payload("src1", sample_data, metadata)

    assert path1 == path2
    assert sha1 == sha2
    assert store.get_payload(sha1) == sample_data


def test_raw_store_integrity_verification_success(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)
    sample_data = b"immutable raw content"
    _, sha = store.store_payload("src", sample_data, {"batch": 1})

    assert store.verify_payload_integrity(sha) is True


def test_raw_store_integrity_verification_corruption_raises(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)
    sample_data = b"original uncorrupted content"
    payload_path, sha = store.store_payload("src", sample_data, {"batch": 1})

    # Corrupt the payload on disk
    payload_path.write_bytes(b"corrupted tampered content")

    with pytest.raises(ValueError, match="Integrity verification failed"):
        store.verify_payload_integrity(sha)


def test_raw_store_strict_sha256_validation(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)

    # Short hash
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        store.get_payload("short123")

    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        store.verify_payload_integrity("short123")

    # Non-hex characters
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        store.get_payload("g" * 64)

    # Uppercase hex (strict lowercase required)
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        store.get_payload("A" * 64)


def test_raw_store_file_not_found(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)
    missing_sha = "f" * 64

    with pytest.raises(FileNotFoundError):
        store.get_payload(missing_sha)

    with pytest.raises(FileNotFoundError):
        store.verify_payload_integrity(missing_sha)


def test_raw_store_path_traversal_prevention(tmp_path: Path):
    store = FilesystemRawStore(tmp_path)
    malicious_source = "../../../etc"
    sample_data = b'{"malicious": "payload"}'
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        store.store_payload(malicious_source, sample_data, {"source": "evil"})

