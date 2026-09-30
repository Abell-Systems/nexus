"""Frozen embedding index: a float32 .npy matrix, its row ids, and a manifest with content hashes.

Binary rather than the ADR 0014 JSON layout: 54,997 x 768 values as JSON is roughly 850 MB.
Writing and reading need only numpy and pydantic, so the isolated generation environment can use it.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

_UNIT_NORM_TOLERANCE = 1e-4


class EmbeddingIndexManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    index_name: str
    n_rows: int
    embedding_dimension: int
    dtype: str = "float32"
    normalization: str = "l2"
    matrix_sha256: str
    ids_sha256: str
    model_name: str
    model_revision: str
    generation_device: str
    batch_size: int
    library_versions: dict[str, str]
    source_sha256: dict[str, str]
    generation_script_path: str
    generation_script_commit: str
    truncated_fraction: float
    generated_at: str
    batch_deviation: dict[str, Any] | None = None


@dataclass(frozen=True)
class FrozenEmbeddingIndex:
    ids: tuple[str, ...]
    matrix: np.ndarray
    manifest: EmbeddingIndexManifest


def _paths(directory: Path, name: str) -> tuple[Path, Path, Path]:
    return directory / f"{name}.npy", directory / f"{name}.ids.json", directory / f"{name}.manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate(ids: Sequence[str], matrix: np.ndarray) -> None:
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2-dimensional, got {matrix.ndim}")
    if matrix.dtype != np.float32:
        raise ValueError(f"matrix must be float32, got {matrix.dtype}")
    if matrix.shape[0] != len(ids):
        raise ValueError(f"ids ({len(ids)}) and matrix rows ({matrix.shape[0]}) differ in count")
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        raise ValueError("ids must be unique non-empty strings")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("matrix must contain only finite values")
    norms = np.linalg.norm(matrix, axis=1)
    if not np.allclose(norms, 1.0, atol=_UNIT_NORM_TOLERANCE):
        raise ValueError("every row must have unit norm (L2-normalized embeddings)")


def save_index(
    directory: Path,
    name: str,
    ids: Sequence[str],
    matrix: np.ndarray,
    **manifest_fields: Any,
) -> EmbeddingIndexManifest:
    _validate(ids, matrix)
    directory.mkdir(parents=True, exist_ok=True)
    npy_path, ids_path, manifest_path = _paths(directory, name)

    np.save(npy_path, matrix, allow_pickle=False)
    ids_path.write_text(json.dumps(list(ids), ensure_ascii=False), encoding="utf-8")

    manifest = EmbeddingIndexManifest(
        index_name=name,
        n_rows=matrix.shape[0],
        embedding_dimension=matrix.shape[1],
        matrix_sha256=_sha256(npy_path),
        ids_sha256=_sha256(ids_path),
        generated_at=datetime.now(UTC).isoformat(),
        **manifest_fields,
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest


def load_index(directory: Path, name: str) -> FrozenEmbeddingIndex:
    npy_path, ids_path, manifest_path = _paths(directory, name)
    manifest = EmbeddingIndexManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    if _sha256(npy_path) != manifest.matrix_sha256:
        raise ValueError(f"{npy_path.name}: matrix sha256 does not match the manifest")
    if _sha256(ids_path) != manifest.ids_sha256:
        raise ValueError(f"{ids_path.name}: ids sha256 does not match the manifest")

    matrix = np.load(npy_path, allow_pickle=False)
    ids = tuple(json.loads(ids_path.read_text(encoding="utf-8")))
    _validate(ids, matrix)
    if matrix.shape != (manifest.n_rows, manifest.embedding_dimension):
        raise ValueError(f"{npy_path.name}: shape {matrix.shape} does not match the manifest")
    return FrozenEmbeddingIndex(ids=ids, matrix=matrix, manifest=manifest)
