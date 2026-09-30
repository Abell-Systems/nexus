# Operational Dense Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate frozen multilingual embeddings for the operational corpus, retrieve over them without torch at runtime, and build the pre-registered blind probe (BM25 vs dense) that decides whether dense retrieval removes the cross-language bottleneck.

**Architecture:** Shared torch-free embedding code lives in a new package `infrastructure/embeddings/` (no DuckDB import, so the isolated generation venv can use it). The runtime `NumpyDenseRetriever` sits in `infrastructure/matching/` and reads a frozen `.npy` matrix through a `PrecomputedEmbedder`. The probe harness under `experiments/operational-dense-probe/` holds pure scoring functions plus two thin CLIs (build blinded sheets, score judgments) and never gets imported by backend code.

**Tech Stack:** Python 3.12, numpy, pydantic 2.13.4, pyarrow, DuckDB (BM25 only), pytest, sentence-transformers 3.4.1 in `.venv-embedding-generation` (generation only).

**Spec:** `docs/superpowers/specs/2026-09-30-operational-dense-retrieval-design.md`

## Global Constraints

- Model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, revision `4328cf26390c98c5e3c738b4460a05b95f4911f5`, CPU, `normalize_embeddings=True`, 768 dimensions. Not configurable beyond `--batch-size`.
- Patent text is `title + ' ' + abstract`; demand text is `title + ' ' + description`. No other text.
- `batch_size=1` by default. If the projected full run exceeds 4 hours on the 500-text throughput gate, a larger batch size is allowed and the deviation plus a bit-difference check on a 500-text overlap against `batch_size=1` go in the manifest. The decision is recorded before the full run.
- Runtime (`domain`, `application`, `infrastructure`) never imports `torch`, `transformers`, or `sentence_transformers` (Import Linter contract `embedding-generation-stack-isolation`).
- `backend/src/main` never imports from `experiments/` (ADR 0026 boundary guard).
- `infrastructure/embeddings/` must not import `duckdb`, `pyarrow`, or anything from `infrastructure.matching` (the generation venv has none of them and `infrastructure/matching/__init__.py` imports DuckDB).
- Eligibility: `DefaultPatentEligibilityPolicy(target_jurisdiction="ES")`, unchanged, same type for both methods.
- Probe seeds are 42 everywhere (blind shuffle, common sample, bootstrap).
- P@5 counts a grade of 2 or more as relevant; empty slots stay in the denominator of 5; excluded pairs leave numerator and denominator; unjudged pairs raise.
- Outcomes: `RESOLVED-YES` if `κ_w >= 0.70` and `P@5(dense) >= 0.40` and `P@5(dense) - P@5(BM25) >= 0.15`; `RESOLVED-NO` if `κ_w >= 0.70` and either threshold fails; `UNRESOLVED` if `κ_w < 0.70`. Bootstrap is informative only and never changes an outcome.
- Test names are `test_should_<behavior>_when_<condition>`, grouped in `*Test` classes as in the existing suite. Mock only at architectural boundaries.
- Every commit in this repo credits Lydia Bares. Commit steps below already carry the required trailers. The user's approval of this plan authorizes the commits it lists.
- Do not commit `data/snapshots/operational_corpus_v1/*.npy`, the embedding sources JSON, or the untracked `experiments/thesis/` and `experiments/article/minesoft_origin_2000_2025/enriched/` directories. Only add the exact paths named in each commit step.

## Review Focus

- A demand text that differs from the stored one by a single character (extra space, trailing newline) must raise, never return an empty or wrong vector. Pinned in Task 1.
- A matrix whose row count or id order does not match the patent list, or an `.npy` file whose bytes changed, must fail at load time, not produce silently shifted results. Pinned in Tasks 2 and 3.
- A demand whose eligible set is empty or smaller than `limit` (every patent published after its `posted_date`, or only EP-coded records) returns `[]` or a short list, not an error. Pinned in Task 3.
- A pair in a top-5 list with no judgment must raise at scoring time, never count as 0. Pinned in Task 5.
- A demand whose five pairs are all excluded is dropped with a count, not turned into NaN; the `0.15` threshold must survive float fuzz (`0.41 - 0.26 == 0.14999999999999997`). Pinned in Task 5.

---

### Task 1: Embedding texts and `PrecomputedEmbedder`

**Files:**
- Create: `backend/src/main/infrastructure/embeddings/__init__.py`
- Create: `backend/src/main/infrastructure/embeddings/embedding_texts.py`
- Create: `backend/src/main/infrastructure/embeddings/precomputed_embedder.py`
- Create: `backend/test/unit/infrastructure/embeddings/__init__.py`
- Test: `backend/test/unit/infrastructure/embeddings/test_precomputed_embedder.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `demand_embedding_text(title: str, description: str) -> str` (returns `f"{title} {description}".strip()`)
  - `patent_embedding_text(title: str, abstract: str) -> str` (returns `f"{title} {abstract}".strip()`)
  - `class UnknownEmbeddingTextError(KeyError)`
  - `class PrecomputedEmbedder` with `__init__(self, vectors_by_text: Mapping[str, Sequence[float]])` and `embed(self, text: str) -> list[float]`

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/infrastructure/embeddings/test_precomputed_embedder.py
import pytest

from infrastructure.embeddings.embedding_texts import demand_embedding_text, patent_embedding_text
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder, UnknownEmbeddingTextError


class EmbeddingTextsTest:
    def test_should_join_title_and_description_with_single_space_when_both_present(self):
        assert demand_embedding_text("Lighter vehicles", "Seeking new materials") == "Lighter vehicles Seeking new materials"

    def test_should_strip_outer_whitespace_when_description_is_empty(self):
        assert demand_embedding_text("Lighter vehicles", "") == "Lighter vehicles"

    def test_should_return_empty_string_when_title_and_description_are_blank(self):
        assert demand_embedding_text("  ", "") == ""

    def test_should_join_title_and_abstract_when_both_present(self):
        assert patent_embedding_text("Smart sink", "Sensor and thermal control") == "Smart sink Sensor and thermal control"


class PrecomputedEmbedderTest:
    def test_should_return_stored_vector_when_text_is_known(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0], "beta text": [0.0, 1.0]})
        assert embedder.embed("alpha text") == [1.0, 0.0]

    def test_should_return_copy_when_caller_mutates_result(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0]})
        embedder.embed("alpha text").append(9.9)
        assert embedder.embed("alpha text") == [1.0, 0.0]

    def test_should_raise_unknown_text_when_text_differs_by_one_trailing_space(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0]})
        with pytest.raises(UnknownEmbeddingTextError):
            embedder.embed("alpha text ")

    def test_should_raise_unknown_text_when_text_was_never_stored(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0]})
        with pytest.raises(UnknownEmbeddingTextError):
            embedder.embed("free text typed by a user")

    def test_should_reject_construction_when_no_vectors_given(self):
        with pytest.raises(ValueError):
            PrecomputedEmbedder({})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/embeddings/test_precomputed_embedder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.embeddings'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/main/infrastructure/embeddings/__init__.py
"""Offline embedding artifacts shared by the generation scripts and the runtime retriever.

Must not import duckdb, pyarrow, torch, or anything from infrastructure.matching: the isolated
generation environment (requirements/evaluation-generation.txt) has none of them.
"""
```

```python
# backend/src/main/infrastructure/embeddings/embedding_texts.py
"""The exact texts that are embedded. One definition shared by generation and retrieval, so the
string a retriever looks up is byte-identical to the string the generator encoded."""


def demand_embedding_text(title: str, description: str) -> str:
    return f"{title} {description}".strip()


def patent_embedding_text(title: str, abstract: str) -> str:
    return f"{title} {abstract}".strip()
```

```python
# backend/src/main/infrastructure/embeddings/precomputed_embedder.py
from collections.abc import Mapping, Sequence


class UnknownEmbeddingTextError(KeyError):
    """No frozen vector exists for this text. The runtime never falls back to a live model."""


class PrecomputedEmbedder:
    """Looks up frozen demand vectors by their exact text. Structurally satisfies TextEmbedder."""

    def __init__(self, vectors_by_text: Mapping[str, Sequence[float]]) -> None:
        if not vectors_by_text:
            raise ValueError("PrecomputedEmbedder requires at least one vector")
        self._vectors = {text: [float(x) for x in vector] for text, vector in vectors_by_text.items()}

    def embed(self, text: str) -> list[float]:
        try:
            return list(self._vectors[text])
        except KeyError as err:
            raise UnknownEmbeddingTextError(f"No frozen embedding for text starting {text[:60]!r}") from err
```

```python
# backend/test/unit/infrastructure/embeddings/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/embeddings/test_precomputed_embedder.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/embeddings/__init__.py backend/src/main/infrastructure/embeddings/embedding_texts.py backend/src/main/infrastructure/embeddings/precomputed_embedder.py backend/test/unit/infrastructure/embeddings/__init__.py backend/test/unit/infrastructure/embeddings/test_precomputed_embedder.py
git commit -m "feat(embeddings): shared embedding texts and PrecomputedEmbedder" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 2: Frozen embedding index (save, load, verify)

**Files:**
- Create: `backend/src/main/infrastructure/embeddings/frozen_embedding_index.py`
- Test: `backend/test/unit/infrastructure/embeddings/test_frozen_embedding_index.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `class EmbeddingIndexManifest(BaseModel)` (frozen) with fields: `index_name: str`, `n_rows: int`, `embedding_dimension: int`, `dtype: str = "float32"`, `normalization: str = "l2"`, `matrix_sha256: str`, `ids_sha256: str`, `model_name: str`, `model_revision: str`, `generation_device: str`, `batch_size: int`, `library_versions: dict[str, str]`, `source_sha256: dict[str, str]`, `generation_script_path: str`, `generation_script_commit: str`, `truncated_fraction: float`, `generated_at: str`, `batch_deviation: dict[str, Any] | None = None`
  - `@dataclass(frozen=True) class FrozenEmbeddingIndex` with `ids: tuple[str, ...]`, `matrix: np.ndarray`, `manifest: EmbeddingIndexManifest`
  - `save_index(directory: Path, name: str, ids: Sequence[str], matrix: np.ndarray, **manifest_fields: Any) -> EmbeddingIndexManifest`; `manifest_fields` are exactly: `model_name, model_revision, generation_device, batch_size, library_versions, source_sha256, generation_script_path, generation_script_commit, truncated_fraction` and optionally `batch_deviation`
  - `load_index(directory: Path, name: str) -> FrozenEmbeddingIndex`
  - files written: `<name>.npy`, `<name>.ids.json`, `<name>.manifest.json`

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/infrastructure/embeddings/test_frozen_embedding_index.py
import json

import numpy as np
import pytest

from infrastructure.embeddings.frozen_embedding_index import load_index, save_index

MANIFEST_FIELDS = {
    "model_name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "model_revision": "4328cf26390c98c5e3c738b4460a05b95f4911f5",
    "generation_device": "cpu",
    "batch_size": 1,
    "library_versions": {"torch": "2.5.1+cpu"},
    "source_sha256": {"publications.parquet": "ab" * 32},
    "generation_script_path": "scripts/generate_operational_embeddings.py",
    "generation_script_commit": "deadbeef",
    "truncated_fraction": 0.25,
}


def _unit_matrix() -> np.ndarray:
    return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.6, 0.8, 0.0]], dtype=np.float32)


class FrozenEmbeddingIndexTest:
    def test_should_round_trip_ids_matrix_and_manifest_when_saved_then_loaded(self, tmp_path):
        manifest = save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix(), **MANIFEST_FIELDS)
        index = load_index(tmp_path, "emb")
        assert index.ids == ("P1", "P2", "P3")
        assert np.array_equal(index.matrix, _unit_matrix())
        assert index.manifest == manifest
        assert manifest.n_rows == 3 and manifest.embedding_dimension == 3

    def test_should_fail_load_when_matrix_bytes_changed(self, tmp_path):
        save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix(), **MANIFEST_FIELDS)
        tampered = _unit_matrix()
        tampered[0, 0] = 0.0
        tampered[0, 1] = 1.0
        np.save(tmp_path / "emb.npy", tampered, allow_pickle=False)
        with pytest.raises(ValueError, match="sha256"):
            load_index(tmp_path, "emb")

    def test_should_fail_load_when_ids_file_changed(self, tmp_path):
        save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix(), **MANIFEST_FIELDS)
        (tmp_path / "emb.ids.json").write_text(json.dumps(["P1", "P3", "P2"]), encoding="utf-8")
        with pytest.raises(ValueError, match="sha256"):
            load_index(tmp_path, "emb")

    def test_should_reject_save_when_ids_and_rows_differ_in_count(self, tmp_path):
        with pytest.raises(ValueError, match="rows"):
            save_index(tmp_path, "emb", ["P1", "P2"], _unit_matrix(), **MANIFEST_FIELDS)

    def test_should_reject_save_when_ids_are_not_unique(self, tmp_path):
        with pytest.raises(ValueError, match="unique"):
            save_index(tmp_path, "emb", ["P1", "P1", "P3"], _unit_matrix(), **MANIFEST_FIELDS)

    def test_should_reject_save_when_matrix_is_not_float32(self, tmp_path):
        with pytest.raises(ValueError, match="float32"):
            save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix().astype(np.float64), **MANIFEST_FIELDS)

    def test_should_reject_save_when_rows_are_not_unit_norm(self, tmp_path):
        matrix = _unit_matrix() * 2.0
        with pytest.raises(ValueError, match="unit norm"):
            save_index(tmp_path, "emb", ["P1", "P2", "P3"], matrix.astype(np.float32), **MANIFEST_FIELDS)

    def test_should_reject_save_when_matrix_has_non_finite_values(self, tmp_path):
        matrix = _unit_matrix()
        matrix[1, 1] = np.nan
        with pytest.raises(ValueError, match="finite"):
            save_index(tmp_path, "emb", ["P1", "P2", "P3"], matrix, **MANIFEST_FIELDS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/embeddings/test_frozen_embedding_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.embeddings.frozen_embedding_index'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/main/infrastructure/embeddings/frozen_embedding_index.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/embeddings -v`
Expected: PASS (all tests in both files)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/embeddings/frozen_embedding_index.py backend/test/unit/infrastructure/embeddings/test_frozen_embedding_index.py
git commit -m "feat(embeddings): hash-verified frozen embedding index" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 3: `NumpyDenseRetriever` and the operational patent loader

**Files:**
- Create: `backend/src/main/infrastructure/matching/operational_corpus.py`
- Create: `backend/src/main/infrastructure/matching/numpy_dense.py`
- Test: `backend/test/unit/infrastructure/matching/test_numpy_dense_retriever.py`
- Test: `backend/test/unit/infrastructure/matching/test_operational_corpus.py`

**Interfaces:**
- Consumes: `PrecomputedEmbedder`, `demand_embedding_text` (Task 1); `PatentDocument`, `DemandSignal`, `Candidate`, `RetrievalMethod`, `PatentCandidateRetriever`, `PatentEligibilityPolicy`, `DefaultPatentEligibilityPolicy` (existing).
- Produces:
  - `load_operational_patents(parquet_path: Path) -> list[PatentDocument]` (row order = parquet order; `doc_number` is the middle segment of `publication_number` split on `-`)
  - `class NumpyDenseRetriever(PatentCandidateRetriever)` with `__init__(self, patents: Sequence[PatentDocument], matrix: np.ndarray, embedder: TextEmbedder, eligibility_policy: PatentEligibilityPolicy, min_threshold: float = 0.0)` and `retrieve(self, demand: DemandRecord | DemandSignal, *, limit: int = 100) -> list[Candidate]`; score is `round((cos + 1) / 2, 6)` under `RetrievalMethod.SEMANTIC`, sorted `(score DESC, publication_id ASC)`

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/infrastructure/matching/test_numpy_dense_retriever.py
import numpy as np
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import RetrievalMethod
from domain.models.patent import PatentDocument
from infrastructure.embeddings.embedding_texts import demand_embedding_text
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder, UnknownEmbeddingTextError
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy
from infrastructure.matching.numpy_dense import NumpyDenseRetriever


def _patent(pub_id: str, country: str = "ES", published: str = "2020-01-01") -> PatentDocument:
    return PatentDocument(
        publication_id=pub_id,
        country_code=country,
        doc_number=pub_id.split("-")[1],
        kind_code="A1",
        title=f"Title {pub_id}",
        abstract=f"Abstract {pub_id}",
        publication_date=published,
    )


def _demand(posted_date: str | None = "2022-01-01") -> DemandSignal:
    return DemandSignal(
        demand_id="INNOGET-1",
        title="Lighter vehicles",
        description="Seeking new materials",
        posted_date=posted_date,
    )


def _retriever(patents, matrix, demand_vector, demand=None):
    demand = demand or _demand()
    text = demand_embedding_text(demand.title, demand.description)
    return NumpyDenseRetriever(
        patents=patents,
        matrix=np.asarray(matrix, dtype=np.float32),
        embedder=PrecomputedEmbedder({text: demand_vector}),
        eligibility_policy=DefaultPatentEligibilityPolicy(target_jurisdiction="ES"),
    )


ROWS = [[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]]


class NumpyDenseRetrieverTest:
    def test_should_rank_by_cosine_descending_when_demand_aligned_with_one_patent(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        result = _retriever(patents, ROWS, [0.0, 1.0]).retrieve(_demand(), limit=3)
        assert [c.publication_id for c in result] == ["ES-2-A1", "ES-3-A1", "ES-1-A1"]

    def test_should_score_as_half_cosine_plus_half_when_ranking(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        result = _retriever(patents, ROWS, [0.0, 1.0]).retrieve(_demand(), limit=3)
        scores = {c.publication_id: c.retrieval_scores[RetrievalMethod.SEMANTIC] for c in result}
        assert scores["ES-2-A1"] == pytest.approx(1.0)
        assert scores["ES-3-A1"] == pytest.approx(round((0.8 + 1.0) / 2.0, 6))
        assert scores["ES-1-A1"] == pytest.approx(0.5)

    def test_should_break_ties_by_publication_id_ascending_when_scores_are_equal(self):
        patents = [_patent("ES-9-A1"), _patent("ES-2-A1")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand(), limit=2)
        assert [c.publication_id for c in result] == ["ES-2-A1", "ES-9-A1"]

    def test_should_return_identical_ranking_when_called_twice(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        retriever = _retriever(patents, ROWS, [0.6, 0.8])
        assert retriever.retrieve(_demand(), limit=3) == retriever.retrieve(_demand(), limit=3)

    def test_should_truncate_to_limit_when_more_eligible_patents_than_limit(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        result = _retriever(patents, ROWS, [0.0, 1.0]).retrieve(_demand(), limit=2)
        assert len(result) == 2

    def test_should_exclude_non_es_jurisdiction_when_country_is_ep(self):
        patents = [_patent("EP-1-A1", country="EP"), _patent("ES-2-A1")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand(), limit=5)
        assert [c.publication_id for c in result] == ["ES-2-A1"]

    def test_should_exclude_patents_published_after_demand_when_temporal_rule_applies(self):
        patents = [_patent("ES-1-A1", published="2023-05-01"), _patent("ES-2-A1", published="2021-05-01")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand("2022-01-01"), limit=5)
        assert [c.publication_id for c in result] == ["ES-2-A1"]

    def test_should_return_empty_list_when_no_patent_is_eligible(self):
        patents = [_patent("ES-1-A1", published="2024-01-01")]
        assert _retriever(patents, [[1.0, 0.0]], [1.0, 0.0]).retrieve(_demand("2022-01-01"), limit=5) == []

    def test_should_return_fewer_than_limit_when_eligible_set_is_small(self):
        patents = [_patent("ES-1-A1"), _patent("EP-2-A1", country="EP")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand(), limit=5)
        assert len(result) == 1

    def test_should_raise_value_error_when_patent_count_and_matrix_rows_differ(self):
        with pytest.raises(ValueError, match="rows"):
            _retriever([_patent("ES-1-A1")], ROWS, [1.0, 0.0])

    def test_should_raise_value_error_when_demand_vector_dimension_differs_from_matrix(self):
        patents = [_patent("ES-1-A1")]
        with pytest.raises(ValueError, match="dimension"):
            _retriever(patents, [[1.0, 0.0]], [1.0, 0.0, 0.0]).retrieve(_demand(), limit=5)

    def test_should_raise_unknown_text_when_demand_was_not_embedded_offline(self):
        patents = [_patent("ES-1-A1")]
        retriever = _retriever(patents, [[1.0, 0.0]], [1.0, 0.0])
        other = DemandSignal(demand_id="X", title="Free text", description="typed by a user", posted_date="2022-01-01")
        with pytest.raises(UnknownEmbeddingTextError):
            retriever.retrieve(other, limit=5)

    def test_should_return_empty_list_when_demand_text_is_blank(self):
        patents = [_patent("ES-1-A1")]
        retriever = NumpyDenseRetriever(
            patents=patents,
            matrix=np.asarray([[1.0, 0.0]], dtype=np.float32),
            embedder=PrecomputedEmbedder({"unused": [1.0, 0.0]}),
            eligibility_policy=DefaultPatentEligibilityPolicy(target_jurisdiction="ES"),
        )
        blank = DemandSignal(demand_id="B", title=" ", description="", posted_date="2022-01-01")
        assert retriever.retrieve(blank, limit=5) == []
```

```python
# backend/test/unit/infrastructure/matching/test_operational_corpus.py
import pyarrow as pa
import pyarrow.parquet as pq

from infrastructure.matching.operational_corpus import load_operational_patents


class OperationalCorpusTest:
    def test_should_load_patents_in_parquet_row_order_when_file_has_expected_columns(self, tmp_path):
        table = pa.table(
            {
                "publication_number": ["ES-2594181-A1", "EP-3000000-B1"],
                "country_code": ["ES", "EP"],
                "kind_code": ["A1", "B1"],
                "title": ["Dispositivo de campo de cocción", "Cooking device"],
                "abstract": ["Un dispositivo para cocinar.", "A device for cooking."],
                "publication_date": ["2016-12-16", "2019-03-06"],
            }
        )
        path = tmp_path / "publications.parquet"
        pq.write_table(table, path)

        patents = load_operational_patents(path)

        assert [p.publication_id for p in patents] == ["ES-2594181-A1", "EP-3000000-B1"]
        assert patents[0].doc_number == "2594181"
        assert patents[0].kind_code == "A1"
        assert patents[1].country_code == "EP"
        assert patents[1].publication_date == "2019-03-06"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/matching/test_numpy_dense_retriever.py backend/test/unit/infrastructure/matching/test_operational_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.matching.numpy_dense'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/main/infrastructure/matching/operational_corpus.py
from pathlib import Path

import pyarrow.parquet as pq

from domain.models.patent import PatentDocument

_COLUMNS = ["publication_number", "country_code", "kind_code", "title", "abstract", "publication_date"]


def load_operational_patents(parquet_path: Path) -> list[PatentDocument]:
    """Loads the operational corpus snapshot as PatentDocuments, preserving parquet row order."""
    rows = pq.read_table(parquet_path, columns=_COLUMNS).to_pylist()
    patents: list[PatentDocument] = []
    for row in rows:
        publication_id = str(row["publication_number"])
        parts = publication_id.split("-")
        patents.append(
            PatentDocument(
                publication_id=publication_id,
                country_code=str(row["country_code"] or ""),
                doc_number=parts[1] if len(parts) > 1 else "",
                kind_code=str(row["kind_code"] or ""),
                title=str(row["title"] or ""),
                abstract=str(row["abstract"] or ""),
                publication_date=str(row["publication_date"]) if row["publication_date"] else None,
            )
        )
    return patents
```

```python
# backend/src/main/infrastructure/matching/numpy_dense.py
from collections.abc import Sequence

import numpy as np

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import Candidate, RetrievalMethod
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy
from infrastructure.embeddings.embedding_texts import demand_embedding_text

from .dense_semantic import TextEmbedder


class NumpyDenseRetriever(PatentCandidateRetriever):
    """Dense retrieval over a frozen L2-normalized matrix: one matrix-vector product per demand.

    Same scoring and ordering contract as DuckDbDenseSemanticRetriever, without its per-row Python loop:
    eligibility filter first, score (cos + 1) / 2 rounded to 6 decimals, ties by (score DESC, publication_id ASC).
    Patent i in `patents` corresponds to row i of `matrix`.
    """

    def __init__(
        self,
        patents: Sequence[PatentDocument],
        matrix: np.ndarray,
        embedder: TextEmbedder,
        eligibility_policy: PatentEligibilityPolicy,
        min_threshold: float = 0.0,
    ) -> None:
        if matrix.ndim != 2 or matrix.shape[0] != len(patents):
            raise ValueError(f"patents ({len(patents)}) and matrix rows ({matrix.shape[0] if matrix.ndim else 0}) differ")
        self._patents = list(patents)
        self._matrix = matrix
        self._embedder = embedder
        self._eligibility_policy = eligibility_policy
        self._min_threshold = min_threshold

    def retrieve(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        text = demand_embedding_text(demand.title, demand.description)
        if not text:
            return []

        query = np.asarray(self._embedder.embed(text), dtype=np.float32)
        if query.shape != (self._matrix.shape[1],):
            raise ValueError(f"demand vector dimension {query.shape} does not match matrix dimension {self._matrix.shape[1]}")
        norm = float(np.linalg.norm(query))
        if norm <= 1e-9:
            return []
        query = query / norm

        similarities = np.clip(self._matrix @ query, -1.0, 1.0)

        scored: list[tuple[str, float]] = []
        for index, patent in enumerate(self._patents):
            if not self._eligibility_policy.evaluate(patent, demand).is_eligible:
                continue
            score = round((float(similarities[index]) + 1.0) / 2.0, 6)
            if score >= self._min_threshold:
                scored.append((patent.publication_id, score))

        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            Candidate(publication_id=pub_id, retrieval_scores={RetrievalMethod.SEMANTIC: score})
            for pub_id, score in scored[:limit]
        ]
```

- [ ] **Step 4: Run tests, then the architecture gates**

Run: `pytest backend/test/unit/infrastructure/matching backend/test/unit/infrastructure/embeddings -v`
Expected: PASS

Run: `ruff check backend/src/main backend/test scripts && mypy backend/src/main --ignore-missing-imports && python scripts/check_architecture.py && lint-imports`
Expected: all pass (no new violations). `lint-imports` runs the Import Linter contracts; if it is not installed, `pip install import-linter` first.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/matching/operational_corpus.py backend/src/main/infrastructure/matching/numpy_dense.py backend/test/unit/infrastructure/matching/test_numpy_dense_retriever.py backend/test/unit/infrastructure/matching/test_operational_corpus.py
git commit -m "feat(matching): NumpyDenseRetriever over a frozen matrix" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 4: Text extraction and embedding generation scripts

**Files:**
- Create: `scripts/extract_operational_texts.py`
- Create: `scripts/generate_operational_embeddings.py`
- Test: `backend/test/unit/test_operational_embedding_scripts.py`

**Interfaces:**
- Consumes: `demand_embedding_text`, `patent_embedding_text` (Task 1); `save_index` (Task 2).
- Produces:
  - `scripts/extract_operational_texts.py` writes `data/snapshots/operational_corpus_v1/embedding_sources_v1.json` with keys `patent_ids: list[str]`, `patent_texts: list[str]`, `demand_ids: list[str]`, `demand_texts: list[str]`, `source_sha256: {"publications.parquet": str, "demand_corpus_n39": str}`. The demand list is **all 39** `n39` demands (a superset of the 31 probe demands; exclusion of the 8 Lab Test demands happens only in the probe).
  - `scripts/generate_operational_embeddings.py` with `--sources PATH`, `--out-dir PATH`, `--batch-size INT` (default 1), `--limit INT` (throughput gate: encode only the first N patent texts, print texts/sec and projected hours, write nothing). Writes indexes `embeddings_patents_v1` and `embeddings_demands_v1` under `--out-dir`.
  - Pure helper importable by tests: `scripts/extract_operational_texts.py::build_sources(parquet_path: Path, demand_corpus_path: Path) -> dict`.

- [ ] **Step 1: Write the failing test** (only the pure extraction helper; the generator needs torch and is verified by running it in Task 7)

```python
# backend/test/unit/test_operational_embedding_scripts.py
import importlib.util
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtractOperationalTextsTest:
    def test_should_keep_parquet_row_order_and_embed_all_demands_when_building_sources(self, tmp_path):
        parquet = tmp_path / "publications.parquet"
        pq.write_table(
            pa.table(
                {
                    "publication_number": ["ES-2-A1", "ES-1-A1"],
                    "title": ["Titulo B", "Titulo A"],
                    "abstract": ["Resumen B", "Resumen A"],
                }
            ),
            parquet,
        )
        demands = tmp_path / "demands.json"
        demands.write_text(
            json.dumps(
                {
                    "demands": [
                        {"demand_id": "D-2", "title": "Two", "description": "second"},
                        {"demand_id": "D-1", "title": "One", "description": "first"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        sources = _load_script("extract_operational_texts").build_sources(parquet, demands)

        assert sources["patent_ids"] == ["ES-2-A1", "ES-1-A1"]
        assert sources["patent_texts"] == ["Titulo B Resumen B", "Titulo A Resumen A"]
        assert sources["demand_ids"] == ["D-2", "D-1"]
        assert sources["demand_texts"] == ["Two second", "One first"]
        assert set(sources["source_sha256"]) == {"publications.parquet", "demand_corpus_n39"}
        assert all(len(v) == 64 for v in sources["source_sha256"].values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/test_operational_embedding_scripts.py -v`
Expected: FAIL with `FileNotFoundError` for `scripts/extract_operational_texts.py`

- [ ] **Step 3: Write the implementation**

```python
# scripts/extract_operational_texts.py
"""Step 1 of 2 for the operational embeddings: plain-JSON texts for the isolated generation venv.

Runs in the main backend venv (it has pyarrow). The isolated generation environment has neither
pyarrow nor DuckDB, so it reads this JSON instead of the Parquet corpus.

All 39 demands of the n39 corpus are embedded (a superset of the 31 probe demands); excluding the
8 Lab Test demands is the probe's job, not this script's.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

import pyarrow.parquet as pq  # noqa: E402

from infrastructure.embeddings.embedding_texts import demand_embedding_text, patent_embedding_text  # noqa: E402

DEFAULT_PARQUET = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1" / "publications.parquet"
DEFAULT_DEMANDS = (
    REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data" / "dataset_phase2_demand_corpus_n39.json"
)
DEFAULT_OUT = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1" / "embedding_sources_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_sources(parquet_path: Path, demand_corpus_path: Path) -> dict:
    rows = pq.read_table(parquet_path, columns=["publication_number", "title", "abstract"]).to_pylist()
    demands = json.loads(demand_corpus_path.read_text(encoding="utf-8"))["demands"]
    return {
        "patent_ids": [str(r["publication_number"]) for r in rows],
        "patent_texts": [patent_embedding_text(str(r["title"] or ""), str(r["abstract"] or "")) for r in rows],
        "demand_ids": [d["demand_id"] for d in demands],
        "demand_texts": [demand_embedding_text(d["title"], d["description"]) for d in demands],
        "source_sha256": {
            "publications.parquet": _sha256(parquet_path),
            "demand_corpus_n39": _sha256(demand_corpus_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract texts for the operational embedding generation")
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--demands", type=Path, default=DEFAULT_DEMANDS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    sources = build_sources(args.parquet, args.demands)
    args.out.write_text(json.dumps(sources, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out}: {len(sources['patent_ids'])} patents, {len(sources['demand_ids'])} demands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```python
# scripts/generate_operational_embeddings.py
"""Step 2 of 2: offline embedding generation for the operational corpus (spec 2026-09-30, section 4).

Run ONLY inside .venv-embedding-generation (requirements/evaluation-generation.txt):
    .venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py --limit 500   # throughput gate
    .venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py               # full run

Model, revision, CPU, L2 normalization as in ADR 0014. batch_size defaults to 1. A larger batch is a
recorded deviation: the manifest stores the batch size and the max absolute difference against
batch_size=1 on the first 500 patent texts.
"""

import argparse
import json
import subprocess
import sys
import time
from importlib.metadata import version as pkg_version
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from infrastructure.embeddings.frozen_embedding_index import save_index  # noqa: E402

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
MODEL_REVISION = "4328cf26390c98c5e3c738b4460a05b95f4911f5"
SCRIPT_PATH = "scripts/generate_operational_embeddings.py"
MAX_SEQ_TOKENS = 128
OVERLAP_CHECK_SIZE = 500
DEFAULT_DIR = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1"


def _encode(model: SentenceTransformer, texts: list[str], batch_size: int, progress: bool = False) -> np.ndarray:
    return model.encode(
        texts, normalize_embeddings=True, batch_size=batch_size, device="cpu", show_progress_bar=progress
    ).astype(np.float32)


def _truncated_fraction(model: SentenceTransformer, texts: list[str]) -> float:
    over = 0
    for start in range(0, len(texts), 1000):
        ids = model.tokenizer(texts[start : start + 1000], add_special_tokens=True, truncation=False)["input_ids"]
        over += sum(1 for seq in ids if len(seq) > MAX_SEQ_TOKENS)
    return over / len(texts)


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate operational corpus embeddings (offline, CPU)")
    parser.add_argument("--sources", type=Path, default=DEFAULT_DIR / "embedding_sources_v1.json")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None, help="Throughput gate: encode N patent texts, write nothing")
    args = parser.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    print(f"Loading {MODEL_NAME} @ {MODEL_REVISION} (CPU)...")
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    if model.get_sentence_embedding_dimension() != 768:
        raise ValueError("Pinned model no longer reports 768 dimensions (ADR 0014 section 8)")

    if args.limit is not None:
        sample = sources["patent_texts"][: args.limit]
        start = time.perf_counter()
        _encode(model, sample, args.batch_size)
        rate = len(sample) / (time.perf_counter() - start)
        hours = len(sources["patent_texts"]) / rate / 3600
        print(f"GATE batch_size={args.batch_size}: {rate:.2f} texts/s; projected full run {hours:.2f} h (limit 4 h)")
        return 0

    patent_texts, demand_texts = sources["patent_texts"], sources["demand_texts"]
    demand_vectors = _encode(model, demand_texts, args.batch_size)
    if not np.array_equal(demand_vectors, _encode(model, demand_texts, args.batch_size)):
        raise RuntimeError("Determinism check failed: re-encoding the demand texts produced different vectors")
    print("Determinism check passed (bit-identical re-encode of demand texts)")

    deviation = None
    if args.batch_size != 1:
        overlap = patent_texts[:OVERLAP_CHECK_SIZE]
        diff = float(np.max(np.abs(_encode(model, overlap, 1) - _encode(model, overlap, args.batch_size))))
        deviation = {"batch_size": args.batch_size, "overlap_texts": len(overlap), "max_abs_diff_vs_batch_1": diff}
        print(f"Recorded batch deviation: {deviation}")

    patent_vectors = _encode(model, patent_texts, args.batch_size, progress=True)

    common = {
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "generation_device": "cpu",
        "batch_size": args.batch_size,
        "library_versions": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "torch": pkg_version("torch"),
            "transformers": pkg_version("transformers"),
            "sentence-transformers": pkg_version("sentence-transformers"),
            "numpy": pkg_version("numpy"),
        },
        "source_sha256": sources["source_sha256"],
        "generation_script_path": SCRIPT_PATH,
        "generation_script_commit": _git_commit(),
        "batch_deviation": deviation,
    }
    patents_manifest = save_index(
        args.out_dir, "embeddings_patents_v1", sources["patent_ids"], patent_vectors,
        truncated_fraction=_truncated_fraction(model, patent_texts), **common,
    )
    save_index(
        args.out_dir, "embeddings_demands_v1", sources["demand_ids"], demand_vectors,
        truncated_fraction=_truncated_fraction(model, demand_texts), **common,
    )
    print(f"Wrote indexes to {args.out_dir}; patents truncated at {MAX_SEQ_TOKENS} tokens: "
          f"{patents_manifest.truncated_fraction:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes, then lint**

Run: `pytest backend/test/unit/test_operational_embedding_scripts.py -v`
Expected: PASS

Run: `ruff check scripts/extract_operational_texts.py scripts/generate_operational_embeddings.py backend/test/unit/test_operational_embedding_scripts.py`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_operational_texts.py scripts/generate_operational_embeddings.py backend/test/unit/test_operational_embedding_scripts.py
git commit -m "feat(scripts): operational text extraction and offline embedding generation" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 5: Probe scoring library

**Files:**
- Create: `experiments/operational-dense-probe/dense_probe.py`
- Test: `experiments/operational-dense-probe/test_dense_probe.py`

**Interfaces:**
- Consumes: `compute_iaa` (`application.evaluation.iaa`), `paired_bootstrap_ci` (`application.evaluation.statistics.bootstrap`), `AnnotationJudgment`, `RelevanceGrade` (existing).
- Produces (all in `dense_probe.py`):
  - constants `TOP_K = 5`, `RELEVANT_MIN_GRADE = 2`, `P5_THRESHOLD = 0.40`, `DELTA_THRESHOLD = 0.15`, `KAPPA_THRESHOLD = 0.70`, `SEED = 42`, `COMMON_FRACTION = 0.2`
  - `Pair = tuple[str, str]` (demand_id, publication_id); `Label = int | None` (`None` = excluded)
  - `union_pairs(bm25: Mapping[str, Sequence[str]], dense: Mapping[str, Sequence[str]]) -> list[Pair]`
  - `blind_order(pairs: Collection[Pair], seed: int = SEED) -> list[Pair]`
  - `draw_common_sample(ordered_pairs: Sequence[Pair], fraction: float = COMMON_FRACTION, seed: int = SEED) -> list[Pair]`
  - `final_labels(grades_a: Mapping[Pair, Label], adjudicated: Mapping[Pair, Label], common: Collection[Pair]) -> dict[Pair, Label]`
  - `precision_at_5(demand_id: str, top5: Sequence[str], labels: Mapping[Pair, Label]) -> float | None`
  - `@dataclass(frozen=True) class PairedMacro` with `p5_bm25: float`, `p5_dense: float`, `delta: float`, `n_used: int`, `n_dropped: int`
  - `paired_macro(bm25: Mapping[str, float | None], dense: Mapping[str, float | None]) -> PairedMacro`
  - `class Outcome(StrEnum)`: `RESOLVED_YES = "RESOLVED-YES"`, `RESOLVED_NO = "RESOLVED-NO"`, `UNRESOLVED = "UNRESOLVED"`
  - `classify_outcome(p5_dense: float, p5_bm25: float, weighted_kappa: float) -> Outcome`
  - `bootstrap_summary(bm25: Mapping[str, float | None], dense: Mapping[str, float | None]) -> dict | None`
  - `@dataclass(frozen=True) class KappaResult` with `weighted_kappa: float`, `binary_kappa: float`, `n_used: int`, `n_excluded: int`
  - `common_sample_kappa(grades_a: Mapping[Pair, Label], grades_b: Mapping[Pair, Label], common: Collection[Pair]) -> KappaResult`
  - `guess_language(text: str) -> str` (returns `"es"` or `"en"`; heuristic, recorded as such)

- [ ] **Step 1: Write the failing test**

```python
# experiments/operational-dense-probe/test_dense_probe.py
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402


def _labels(demand: str, grades: dict[str, int | None]) -> dict[dp.Pair, dp.Label]:
    return {(demand, pub): grade for pub, grade in grades.items()}


class PairsAndSampleTest:
    def test_should_dedupe_pair_when_both_methods_return_same_patent(self):
        pairs = dp.union_pairs({"D1": ["P1", "P2"]}, {"D1": ["P2", "P3"]})
        assert pairs == [("D1", "P1"), ("D1", "P2"), ("D1", "P3")]

    def test_should_return_same_blind_order_when_seed_is_fixed(self):
        pairs = [("D1", f"P{i}") for i in range(20)]
        assert dp.blind_order(pairs) == dp.blind_order(list(reversed(pairs)))

    def test_should_not_keep_sorted_order_when_blind_shuffling_many_pairs(self):
        pairs = [("D1", f"P{i:02d}") for i in range(20)]
        assert dp.blind_order(pairs) != sorted(pairs)

    def test_should_draw_ceil_of_twenty_percent_when_sampling_common_pairs(self):
        ordered = dp.blind_order([("D1", f"P{i}") for i in range(23)])
        assert len(dp.draw_common_sample(ordered)) == 5

    def test_should_draw_exactly_twenty_percent_when_float_product_overshoots(self):
        ordered = dp.blind_order([("D1", f"P{i}") for i in range(15)])
        assert len(dp.draw_common_sample(ordered)) == 3

    def test_should_draw_same_common_sample_when_called_twice_with_seed_42(self):
        ordered = dp.blind_order([("D1", f"P{i}") for i in range(40)])
        assert dp.draw_common_sample(ordered) == dp.draw_common_sample(ordered)


class FinalLabelsTest:
    def test_should_use_adjudicated_grade_when_pair_is_in_common_sample(self):
        a = {("D1", "P1"): 1, ("D1", "P2"): 3}
        adjudicated = {("D1", "P1"): 2}
        result = dp.final_labels(a, adjudicated, common={("D1", "P1")})
        assert result == {("D1", "P1"): 2, ("D1", "P2"): 3}

    def test_should_exclude_pair_when_evaluator_a_marked_uncertain_outside_common_sample(self):
        result = dp.final_labels({("D1", "P1"): None}, {}, common=set())
        assert result == {("D1", "P1"): None}

    def test_should_raise_when_common_pair_has_no_adjudication(self):
        with pytest.raises(KeyError):
            dp.final_labels({("D1", "P1"): 2}, {}, common={("D1", "P1")})


class PrecisionAtFiveTest:
    def test_should_divide_relevant_by_five_when_all_five_judged(self):
        labels = _labels("D1", {"P1": 3, "P2": 2, "P3": 1, "P4": 0, "P5": 2})
        assert dp.precision_at_5("D1", ["P1", "P2", "P3", "P4", "P5"], labels) == pytest.approx(0.6)

    def test_should_keep_empty_slots_in_denominator_when_list_is_short(self):
        labels = _labels("D1", {"P1": 3, "P2": 2})
        assert dp.precision_at_5("D1", ["P1", "P2"], labels) == pytest.approx(0.4)

    def test_should_leave_denominator_when_pair_is_excluded(self):
        labels = _labels("D1", {"P1": 3, "P2": None, "P3": 0, "P4": 0, "P5": 0})
        assert dp.precision_at_5("D1", ["P1", "P2", "P3", "P4", "P5"], labels) == pytest.approx(0.25)

    def test_should_return_none_when_all_five_pairs_are_excluded(self):
        labels = _labels("D1", {f"P{i}": None for i in range(1, 6)})
        assert dp.precision_at_5("D1", [f"P{i}" for i in range(1, 6)], labels) is None

    def test_should_return_zero_when_list_is_empty(self):
        assert dp.precision_at_5("D1", [], {}) == 0.0

    def test_should_raise_when_a_listed_pair_has_no_judgment(self):
        with pytest.raises(KeyError, match="Unjudged"):
            dp.precision_at_5("D1", ["P1"], {})

    def test_should_reject_list_longer_than_five(self):
        with pytest.raises(ValueError):
            dp.precision_at_5("D1", [f"P{i}" for i in range(6)], {})


class PairedMacroTest:
    def test_should_average_demands_available_for_both_methods_when_one_is_dropped(self):
        result = dp.paired_macro({"D1": 0.2, "D2": None, "D3": 0.4}, {"D1": 0.6, "D2": 0.8, "D3": 0.4})
        assert result.n_used == 2 and result.n_dropped == 1
        assert result.p5_bm25 == pytest.approx(0.3)
        assert result.p5_dense == pytest.approx(0.5)
        assert result.delta == pytest.approx(0.2)

    def test_should_raise_when_no_demand_is_usable_for_both_methods(self):
        with pytest.raises(ValueError):
            dp.paired_macro({"D1": None}, {"D1": 0.5})


class OutcomeTest:
    def test_should_be_yes_when_both_thresholds_met_and_kappa_ok(self):
        assert dp.classify_outcome(0.50, 0.30, 0.80) == dp.Outcome.RESOLVED_YES

    def test_should_be_yes_when_delta_is_exactly_threshold_despite_float_fuzz(self):
        # 0.41 - 0.26 == 0.14999999999999997 in IEEE-754
        assert dp.classify_outcome(0.41, 0.26, 0.70) == dp.Outcome.RESOLVED_YES

    def test_should_be_no_when_dense_below_absolute_threshold(self):
        assert dp.classify_outcome(0.39, 0.10, 0.90) == dp.Outcome.RESOLVED_NO

    def test_should_be_no_when_improvement_below_threshold(self):
        assert dp.classify_outcome(0.60, 0.50, 0.90) == dp.Outcome.RESOLVED_NO

    def test_should_be_unresolved_when_kappa_below_threshold_even_if_thresholds_met(self):
        assert dp.classify_outcome(0.90, 0.10, 0.69) == dp.Outcome.UNRESOLVED

    def test_should_be_unresolved_when_kappa_below_threshold_even_if_thresholds_failed(self):
        assert dp.classify_outcome(0.10, 0.50, 0.30) == dp.Outcome.UNRESOLVED


class BootstrapSummaryTest:
    def test_should_report_paired_intervals_when_enough_demands(self):
        bm25 = {f"D{i}": 0.2 for i in range(10)}
        dense = {f"D{i}": 0.6 for i in range(10)}
        summary = dp.bootstrap_summary(bm25, dense)
        assert summary["delta"]["estimate"] == pytest.approx(0.4)
        assert summary["delta"]["ci_lower"] <= summary["delta"]["estimate"] <= summary["delta"]["ci_upper"]
        assert summary["dense"]["estimate"] == pytest.approx(0.6)

    def test_should_return_none_when_fewer_than_two_paired_demands(self):
        assert dp.bootstrap_summary({"D1": 0.2}, {"D1": 0.6}) is None


class KappaTest:
    def test_should_compute_kappa_over_common_pairs_graded_by_both_evaluators(self):
        common = {("D1", f"P{i}") for i in range(8)}
        a = {("D1", "P0"): 0, ("D1", "P1"): 1, ("D1", "P2"): 2, ("D1", "P3"): 3,
             ("D1", "P4"): 0, ("D1", "P5"): 1, ("D1", "P6"): 2, ("D1", "P7"): 3}
        b = dict(a)
        result = dp.common_sample_kappa(a, b, common)
        assert result.weighted_kappa == pytest.approx(1.0)
        assert result.n_used == 8 and result.n_excluded == 0

    def test_should_exclude_pair_from_kappa_when_either_evaluator_marked_uncertain(self):
        common = {("D1", "P0"), ("D1", "P1"), ("D1", "P2")}
        a = {("D1", "P0"): 0, ("D1", "P1"): 3, ("D1", "P2"): None}
        b = {("D1", "P0"): 0, ("D1", "P1"): 3, ("D1", "P2"): 1}
        result = dp.common_sample_kappa(a, b, common)
        assert result.n_used == 2 and result.n_excluded == 1


class LanguageTest:
    def test_should_guess_english_when_english_stopwords_dominate(self):
        assert dp.guess_language("Seeking the best materials for the vehicles and with low weight") == "en"

    def test_should_guess_spanish_when_spanish_stopwords_dominate(self):
        assert dp.guess_language("Buscamos los mejores materiales para el peso de los vehiculos que con una") == "es"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest experiments/operational-dense-probe/test_dense_probe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dense_probe'`

- [ ] **Step 3: Write the implementation**

```python
# experiments/operational-dense-probe/dense_probe.py
"""Pre-registered scoring library for the operational dense-retrieval probe.

Spec: docs/superpowers/specs/2026-09-30-operational-dense-retrieval-design.md, section 7.
Pure functions only; the two CLIs in this directory do the file I/O.
"""

import math
import random
import re
import sys
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.evaluation.iaa import compute_iaa  # noqa: E402
from application.evaluation.statistics.bootstrap import paired_bootstrap_ci  # noqa: E402
from domain.models.annotation import AnnotationJudgment  # noqa: E402
from domain.models.evaluation import RelevanceGrade  # noqa: E402

TOP_K = 5
RELEVANT_MIN_GRADE = 2
P5_THRESHOLD = 0.40
DELTA_THRESHOLD = 0.15
KAPPA_THRESHOLD = 0.70
SEED = 42
COMMON_FRACTION = 0.2
_EPS = 1e-9  # the 0.15 threshold must survive float fuzz (0.41 - 0.26 == 0.14999999999999997)

Pair = tuple[str, str]
Label = int | None  # None = excluded (unresolved UNCERTAIN), never imputed as 0


class Outcome(StrEnum):
    RESOLVED_YES = "RESOLVED-YES"
    RESOLVED_NO = "RESOLVED-NO"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class PairedMacro:
    p5_bm25: float
    p5_dense: float
    delta: float
    n_used: int
    n_dropped: int


@dataclass(frozen=True)
class KappaResult:
    weighted_kappa: float
    binary_kappa: float
    n_used: int
    n_excluded: int


def union_pairs(bm25: Mapping[str, Sequence[str]], dense: Mapping[str, Sequence[str]]) -> list[Pair]:
    pairs: set[Pair] = set()
    for by_demand in (bm25, dense):
        for demand_id, publication_ids in by_demand.items():
            pairs.update((demand_id, pub) for pub in publication_ids)
    return sorted(pairs)


def blind_order(pairs: Collection[Pair], seed: int = SEED) -> list[Pair]:
    ordered = sorted(set(pairs))
    random.Random(seed).shuffle(ordered)
    return ordered


def draw_common_sample(
    ordered_pairs: Sequence[Pair], fraction: float = COMMON_FRACTION, seed: int = SEED
) -> list[Pair]:
    size = math.ceil(round(fraction * len(ordered_pairs), 9))  # 0.2 * 15 == 3.0000000000000004 in IEEE-754
    return sorted(random.Random(seed).sample(sorted(ordered_pairs), size))


def final_labels(
    grades_a: Mapping[Pair, Label], adjudicated: Mapping[Pair, Label], common: Collection[Pair]
) -> dict[Pair, Label]:
    common_set = set(common)
    labels: dict[Pair, Label] = {}
    for pair, grade in grades_a.items():
        if pair in common_set:
            if pair not in adjudicated:
                raise KeyError(f"Common-sample pair {pair} has no adjudicated grade")
            labels[pair] = adjudicated[pair]
        else:
            labels[pair] = grade
    return labels


def precision_at_5(demand_id: str, top5: Sequence[str], labels: Mapping[Pair, Label]) -> float | None:
    if len(top5) > TOP_K:
        raise ValueError(f"top list has {len(top5)} items, expected at most {TOP_K}")
    relevant = 0
    excluded = 0
    for publication_id in top5:
        key = (demand_id, publication_id)
        if key not in labels:
            raise KeyError(f"Unjudged pair {key}: every pair in a top-5 list needs a final label")
        label = labels[key]
        if label is None:
            excluded += 1
        elif label >= RELEVANT_MIN_GRADE:
            relevant += 1
    denominator = TOP_K - excluded
    return None if denominator == 0 else relevant / denominator


def paired_macro(bm25: Mapping[str, float | None], dense: Mapping[str, float | None]) -> PairedMacro:
    demands = sorted(set(bm25) & set(dense))
    usable = [d for d in demands if bm25[d] is not None and dense[d] is not None]
    if not usable:
        raise ValueError("No demand has a usable P@5 for both methods")
    p5_bm25 = sum(bm25[d] for d in usable) / len(usable)  # type: ignore[misc]
    p5_dense = sum(dense[d] for d in usable) / len(usable)  # type: ignore[misc]
    return PairedMacro(
        p5_bm25=p5_bm25,
        p5_dense=p5_dense,
        delta=p5_dense - p5_bm25,
        n_used=len(usable),
        n_dropped=len(demands) - len(usable),
    )


def classify_outcome(p5_dense: float, p5_bm25: float, weighted_kappa: float) -> Outcome:
    if weighted_kappa < KAPPA_THRESHOLD - _EPS:
        return Outcome.UNRESOLVED
    passes = p5_dense >= P5_THRESHOLD - _EPS and (p5_dense - p5_bm25) >= DELTA_THRESHOLD - _EPS
    return Outcome.RESOLVED_YES if passes else Outcome.RESOLVED_NO


def _ci(result) -> dict[str, float]:
    return {"estimate": result.estimate, "ci_lower": result.ci_lower, "ci_upper": result.ci_upper}


def bootstrap_summary(bm25: Mapping[str, float | None], dense: Mapping[str, float | None]) -> dict | None:
    """Informative uncertainty only (spec 7.7). Never used to change an outcome."""
    usable = [d for d in sorted(set(bm25) & set(dense)) if bm25[d] is not None and dense[d] is not None]
    if len(usable) < 2:
        return None
    b = [bm25[d] for d in usable]
    t = [dense[d] for d in usable]
    zeros = [0.0] * len(usable)
    return {
        "n_demands": len(usable),
        "delta": _ci(paired_bootstrap_ci(b, t, seed=SEED)),
        "dense": _ci(paired_bootstrap_ci(zeros, t, seed=SEED)),
        "bm25": _ci(paired_bootstrap_ci(zeros, b, seed=SEED)),
    }


def common_sample_kappa(
    grades_a: Mapping[Pair, Label], grades_b: Mapping[Pair, Label], common: Collection[Pair]
) -> KappaResult:
    usable = sorted(p for p in common if grades_a.get(p) is not None and grades_b.get(p) is not None)
    judgments_a = [
        AnnotationJudgment(demand_id=d, publication_id=p, annotator_id="A", grade=RelevanceGrade(grades_a[(d, p)]))
        for d, p in usable
    ]
    judgments_b = [
        AnnotationJudgment(demand_id=d, publication_id=p, annotator_id="B", grade=RelevanceGrade(grades_b[(d, p)]))
        for d, p in usable
    ]
    report = compute_iaa(judgments_a, judgments_b)
    return KappaResult(
        weighted_kappa=report.weighted_kappa,
        binary_kappa=report.binary_kappa,
        n_used=len(usable),
        n_excluded=len(set(common)) - len(usable),
    )


_ES_WORDS = re.compile(r"\b(el|la|los|las|del|que|para|con|una|por)\b")
_EN_WORDS = re.compile(r"\b(the|and|of|for|with|is|are|that)\b")


def guess_language(text: str) -> str:
    """Stopword heuristic, recorded as a heuristic: 'es' if Spanish stopwords outnumber English ones."""
    lowered = text.lower()
    return "es" if len(_ES_WORDS.findall(lowered)) > len(_EN_WORDS.findall(lowered)) else "en"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest experiments/operational-dense-probe/test_dense_probe.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add experiments/operational-dense-probe/dense_probe.py experiments/operational-dense-probe/test_dense_probe.py
git commit -m "feat(probe): pre-registered P@5 scoring library for the dense probe" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 6: Probe CLIs (build blinded sheets, score judgments)

**Files:**
- Create: `experiments/operational-dense-probe/build_probe_sheets.py`
- Create: `experiments/operational-dense-probe/score_probe.py`
- Test: `experiments/operational-dense-probe/test_probe_cli.py`

**Interfaces:**
- Consumes: everything in `dense_probe.py` (Task 5); `load_index` (Task 2); `NumpyDenseRetriever`, `load_operational_patents`, `PrecomputedEmbedder`, `DuckDbBM25Retriever`, `DefaultPatentEligibilityPolicy`, `DemandSignal`.
- Produces:
  - `build_probe_sheets.py` writes into `--out-dir` (default `experiments/operational-dense-probe/outputs`):
    - `judging_sheet_A.csv` — columns `pair_id, demand_title, demand_description, patent_title, patent_abstract, abstract_language, grade, note` (rows in blind order; `grade` empty for the evaluator to fill with `0-3` or `U`)
    - `judging_sheet_B_common.csv` — same columns, only the common-sample rows
    - `provenance_DO_NOT_OPEN.json` — `{"pairs": {pair_id: [demand_id, publication_id]}, "methods": {demand_id: {"bm25": [...], "dense": [...]}}, "eligible_sizes": {demand_id: int}, "demand_language": {demand_id: "es"|"en"}, "common_sample": [pair_id, ...]}`
  - `score_probe.py` reads `judging_sheet_A.csv`, `judging_sheet_B_common.csv`, `adjudication.csv` (columns `pair_id, final_grade` with `0-3` or `U`), and the provenance file; writes `probe_result.json` and prints the outcome.
  - pure helpers (importable, tested): `parse_grade(cell: str) -> int | None` (`"0".."3"` -> int, `"U"`/`"u"` -> `None`, anything else raises `ValueError`), `read_sheet_grades(path: Path, pair_ids: Mapping[str, Pair]) -> dict[Pair, Label]`.

- [ ] **Step 1: Write the failing test**

```python
# experiments/operational-dense-probe/test_probe_cli.py
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_probe as sp  # noqa: E402


class ParseGradeTest:
    @pytest.mark.parametrize("cell,expected", [("0", 0), ("1", 1), ("2", 2), ("3", 3), (" 3 ", 3)])
    def test_should_parse_integer_grade_when_cell_is_zero_to_three(self, cell, expected):
        assert sp.parse_grade(cell) == expected

    @pytest.mark.parametrize("cell", ["U", "u", " U "])
    def test_should_return_none_when_cell_marks_uncertain(self, cell):
        assert sp.parse_grade(cell) is None

    @pytest.mark.parametrize("cell", ["", "4", "-1", "2.5", "yes"])
    def test_should_raise_when_cell_is_empty_or_invalid(self, cell):
        with pytest.raises(ValueError):
            sp.parse_grade(cell)


class ReadSheetGradesTest:
    def test_should_map_pair_ids_to_pairs_and_grades_when_sheet_is_complete(self, tmp_path):
        path = tmp_path / "sheet.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade"])
            writer.writeheader()
            writer.writerow({"pair_id": "P001", "grade": "3"})
            writer.writerow({"pair_id": "P002", "grade": "U"})
        pairs = {"P001": ("D1", "ES-1-A1"), "P002": ("D1", "ES-2-A1")}
        assert sp.read_sheet_grades(path, pairs) == {("D1", "ES-1-A1"): 3, ("D1", "ES-2-A1"): None}

    def test_should_raise_when_any_grade_cell_is_left_empty(self, tmp_path):
        path = tmp_path / "sheet.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade"])
            writer.writeheader()
            writer.writerow({"pair_id": "P001", "grade": ""})
        with pytest.raises(ValueError, match="P001"):
            sp.read_sheet_grades(path, {"P001": ("D1", "ES-1-A1")})

    def test_should_raise_when_sheet_contains_unknown_pair_id(self, tmp_path):
        path = tmp_path / "sheet.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade"])
            writer.writeheader()
            writer.writerow({"pair_id": "P999", "grade": "2"})
        with pytest.raises(KeyError):
            sp.read_sheet_grades(path, {"P001": ("D1", "ES-1-A1")})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest experiments/operational-dense-probe/test_probe_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'score_probe'`

- [ ] **Step 3: Write the implementation**

```python
# experiments/operational-dense-probe/score_probe.py
"""Scores the pre-registered probe from the evaluators' sheets. Spec section 7.

Usage: python experiments/operational-dense-probe/score_probe.py [--dir outputs]
Reads judging_sheet_A.csv, judging_sheet_B_common.csv, adjudication.csv and provenance_DO_NOT_OPEN.json
from --dir, writes probe_result.json there.
"""

import argparse
import csv
import json
import sys
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402

DEFAULT_DIR = Path(__file__).resolve().parent / "outputs"


def parse_grade(cell: str) -> int | None:
    value = cell.strip()
    if value.upper() == "U":
        return None
    if value in {"0", "1", "2", "3"}:
        return int(value)
    raise ValueError(f"Invalid grade {cell!r}: expected 0-3 or U")


def read_sheet_grades(path: Path, pair_ids: Mapping[str, dp.Pair], grade_column: str = "grade") -> dict[dp.Pair, dp.Label]:
    grades: dict[dp.Pair, dp.Label] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pair_id = row["pair_id"]
            if pair_id not in pair_ids:
                raise KeyError(f"{path.name}: unknown pair_id {pair_id!r}")
            try:
                grades[pair_ids[pair_id]] = parse_grade(row[grade_column])
            except ValueError as err:
                raise ValueError(f"{path.name}: pair {pair_id}: {err}") from err
    return grades


def main() -> int:
    parser = argparse.ArgumentParser(description="Score the operational dense-retrieval probe")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    provenance = json.loads((args.dir / "provenance_DO_NOT_OPEN.json").read_text(encoding="utf-8"))
    pair_ids = {pid: (d, p) for pid, (d, p) in provenance["pairs"].items()}
    common = {pair_ids[pid] for pid in provenance["common_sample"]}

    grades_a = read_sheet_grades(args.dir / "judging_sheet_A.csv", pair_ids)
    grades_b = read_sheet_grades(args.dir / "judging_sheet_B_common.csv", pair_ids)
    adjudicated = read_sheet_grades(args.dir / "adjudication.csv", pair_ids, grade_column="final_grade")
    labels = dp.final_labels(grades_a, adjudicated, common)

    methods = provenance["methods"]
    p5 = {
        method: {d: dp.precision_at_5(d, lists[method], labels) for d, lists in methods.items()}
        for method in ("bm25", "dense")
    }
    macro = dp.paired_macro(p5["bm25"], p5["dense"])
    kappa = dp.common_sample_kappa(grades_a, grades_b, common)
    outcome = dp.classify_outcome(macro.p5_dense, macro.p5_bm25, kappa.weighted_kappa)

    by_language: dict[str, dict[str, float]] = {}
    for language in sorted(set(provenance["demand_language"].values())):
        subset = {d for d, lang in provenance["demand_language"].items() if lang == language}
        try:
            sub = dp.paired_macro({d: p5["bm25"][d] for d in subset}, {d: p5["dense"][d] for d in subset})
            by_language[language] = {"p5_bm25": sub.p5_bm25, "p5_dense": sub.p5_dense, "n": sub.n_used}
        except ValueError:
            by_language[language] = {"n": 0}

    result = {
        "outcome": outcome.value,
        "p5_bm25": macro.p5_bm25,
        "p5_dense": macro.p5_dense,
        "delta": macro.delta,
        "n_demands_used": macro.n_used,
        "n_demands_dropped": macro.n_dropped,
        "weighted_kappa": kappa.weighted_kappa,
        "binary_kappa": kappa.binary_kappa,
        "kappa_pairs_used": kappa.n_used,
        "kappa_pairs_excluded": kappa.n_excluded,
        "excluded_pairs_total": sum(1 for v in labels.values() if v is None),
        "short_lists": {m: sum(1 for lst in (methods[d][m] for d in methods) if len(lst) < dp.TOP_K) for m in ("bm25", "dense")},
        "by_language_stratum": by_language,
        "per_demand_p5": p5,
        "bootstrap_informative_only": dp.bootstrap_summary(p5["bm25"], p5["dense"]),
        "eligible_sizes": provenance["eligible_sizes"],
    }
    (args.dir / "probe_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"OUTCOME {outcome.value}: P@5 dense={macro.p5_dense:.3f} bm25={macro.p5_bm25:.3f} "
          f"delta={macro.delta:.3f} kappa_w={kappa.weighted_kappa:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```python
# experiments/operational-dense-probe/build_probe_sheets.py
"""Builds the blinded judging sheets for the pre-registered probe. Spec sections 7.1-7.5.

Usage: python experiments/operational-dense-probe/build_probe_sheets.py [--out-dir outputs]
Requires the operational embeddings (Task 7) and the operational corpus snapshot.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402

from domain.models.demand import DemandSignal  # noqa: E402
from infrastructure.embeddings.embedding_texts import demand_embedding_text  # noqa: E402
from infrastructure.embeddings.frozen_embedding_index import load_index  # noqa: E402
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder  # noqa: E402
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402
from infrastructure.matching.numpy_dense import NumpyDenseRetriever  # noqa: E402
from infrastructure.matching.operational_corpus import load_operational_patents  # noqa: E402

CORPUS_DIR = dp.REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1"
LAB_DATA = dp.REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data"
DEFAULT_OUT = Path(__file__).resolve().parent / "outputs"
SHEET_COLUMNS = ["pair_id", "demand_title", "demand_description", "patent_title", "patent_abstract",
                 "abstract_language", "grade", "note"]


def probe_demands() -> list[DemandSignal]:
    corpus = json.loads((LAB_DATA / "dataset_phase2_demand_corpus_n39.json").read_text(encoding="utf-8"))["demands"]
    test_ids = set(json.loads((LAB_DATA / "devtest_split_n18_v2.json").read_text(encoding="utf-8"))["test"])
    selected = [d for d in corpus if d["demand_id"] not in test_ids]
    if len(corpus) - len(selected) != len(test_ids):
        raise ValueError("Not all Lab Test demand ids were found in the n39 corpus")
    return [
        DemandSignal(
            demand_id=d["demand_id"], title=d["title"], description=d["description"],
            posted_date=d.get("posted_date"), origin_country=d.get("origin_country"),
        )
        for d in selected
    ]


def _write_sheet(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build blinded judging sheets for the dense probe")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    parquet = CORPUS_DIR / "publications.parquet"
    patents = load_operational_patents(parquet)
    language_by_id = {
        r["publication_number"]: r["abstract_language"]
        for r in pq.read_table(parquet, columns=["publication_number", "abstract_language"]).to_pylist()
    }
    patent_index = load_index(CORPUS_DIR, "embeddings_patents_v1")
    demand_index = load_index(CORPUS_DIR, "embeddings_demands_v1")
    if patent_index.ids != tuple(p.publication_id for p in patents):
        raise ValueError("Embedding ids are not aligned with the corpus parquet row order")

    demands = probe_demands()
    demand_vectors = {
        demand_embedding_text(d.title, d.description): demand_index.matrix[demand_index.ids.index(d.demand_id)]
        for d in demands
    }
    policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    dense = NumpyDenseRetriever(patents, patent_index.matrix, PrecomputedEmbedder(demand_vectors), policy)

    con = duckdb.connect()
    con.execute(
        "CREATE TABLE patents AS SELECT publication_number, country_code, kind_code, title, abstract, "
        f"publication_date FROM read_parquet('{parquet}')"
    )
    bm25 = DuckDbBM25Retriever(con, eligibility_policy=policy)

    methods: dict[str, dict[str, list[str]]] = {}
    eligible_sizes: dict[str, int] = {}
    for demand in demands:
        methods[demand.demand_id] = {
            "bm25": [c.publication_id for c in bm25.retrieve(demand, limit=dp.TOP_K)],
            "dense": [c.publication_id for c in dense.retrieve(demand, limit=dp.TOP_K)],
        }
        eligible_sizes[demand.demand_id] = sum(1 for p in patents if policy.evaluate(p, demand).is_eligible)

    ordered = dp.blind_order(dp.union_pairs(
        {d: m["bm25"] for d, m in methods.items()}, {d: m["dense"] for d, m in methods.items()}
    ))
    pair_ids = {f"P{i:03d}": pair for i, pair in enumerate(ordered, start=1)}
    common = set(dp.draw_common_sample(ordered))

    demand_by_id = {d.demand_id: d for d in demands}
    patent_by_id = {p.publication_id: p for p in patents}
    rows = []
    for pair_id, (demand_id, publication_id) in pair_ids.items():
        demand, patent = demand_by_id[demand_id], patent_by_id[publication_id]
        rows.append({
            "pair_id": pair_id, "demand_title": demand.title, "demand_description": demand.description,
            "patent_title": patent.title, "patent_abstract": patent.abstract,
            "abstract_language": language_by_id[publication_id], "grade": "", "note": "",
        })
    _write_sheet(args.out_dir / "judging_sheet_A.csv", rows)
    _write_sheet(args.out_dir / "judging_sheet_B_common.csv",
                 [r for r in rows if pair_ids[r["pair_id"]] in common])

    provenance = {
        "pairs": {pid: list(pair) for pid, pair in pair_ids.items()},
        "methods": methods,
        "eligible_sizes": eligible_sizes,
        "demand_language": {d.demand_id: dp.guess_language(f"{d.title} {d.description}") for d in demands},
        "demand_language_method": "stopword heuristic (dense_probe.guess_language)",
        "common_sample": [pid for pid, pair in pair_ids.items() if pair in common],
    }
    (args.out_dir / "provenance_DO_NOT_OPEN.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"{len(demands)} demands, {len(rows)} pairs to judge, {len(common)} in the common sample")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest experiments/operational-dense-probe -v`
Expected: PASS (Task 5 and Task 6 tests)

- [ ] **Step 5: Commit**

```bash
git add experiments/operational-dense-probe/build_probe_sheets.py experiments/operational-dense-probe/score_probe.py experiments/operational-dense-probe/test_probe_cli.py
git commit -m "feat(probe): blinded sheet builder and probe scorer" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 7: Run the pipeline and hand the sheets to the evaluators

This task produces data, not code. It has two human gates (judging and adjudication) that no agent may skip or fill in.

**Files:**
- Create (not committed): `data/snapshots/operational_corpus_v1/embedding_sources_v1.json`, `embeddings_patents_v1.*`, `embeddings_demands_v1.*`
- Create: `experiments/operational-dense-probe/outputs/` (sheets and provenance; commit after judging, see Step 7)
- Create after judging: `docs/operational-dense-probe-result.md`

- [ ] **Step 1: Full test and gate run on the finished code**

Run: `pytest backend/test experiments/operational-dense-probe -q && ruff check backend/src/main backend/test scripts && mypy backend/src/main --ignore-missing-imports && python scripts/check_architecture.py && lint-imports`
Expected: all pass. Fix any failure before generating data.

- [ ] **Step 2: Extract texts (main venv)**

Run: `python scripts/extract_operational_texts.py`
Expected: `Wrote .../embedding_sources_v1.json: 54997 patents, 39 demands`

- [ ] **Step 3: Throughput gate, then record the batch-size decision**

Run: `.venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py --limit 500`
Expected: a line `GATE batch_size=1: X texts/s; projected full run H h (limit 4 h)`.
Decision, written into the commit message of Step 8 before the full run: if `H <= 4`, keep `batch_size=1`. If `H > 4`, rerun the gate with `--batch-size 16`, and use the largest batch size whose projection is under 4 hours; the manifest then records the deviation. Do not change the decision after seeing probe results.

- [ ] **Step 4: Full generation (long; run in the background)**

Run: `.venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py [--batch-size N]`
Expected: `Determinism check passed`, then `Wrote indexes to ...; patents truncated at 128 tokens: P%`. Files `embeddings_patents_v1.{npy,ids.json,manifest.json}` and `embeddings_demands_v1.*` exist.

- [ ] **Step 5: Smoke-check the retriever on real data**

Run:
```bash
python - <<'E'
import sys
sys.path.insert(0, "backend/src/main")
from pathlib import Path
from domain.models.demand import DemandSignal
from infrastructure.embeddings.embedding_texts import demand_embedding_text
from infrastructure.embeddings.frozen_embedding_index import load_index
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy
from infrastructure.matching.numpy_dense import NumpyDenseRetriever
from infrastructure.matching.operational_corpus import load_operational_patents
import json, time
d = Path("data/snapshots/operational_corpus_v1")
patents = load_operational_patents(d / "publications.parquet")
pi, di = load_index(d, "embeddings_patents_v1"), load_index(d, "embeddings_demands_v1")
assert pi.ids == tuple(p.publication_id for p in patents)
raw = json.load(open("experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.json"))["demands"][0]
demand = DemandSignal(demand_id=raw["demand_id"], title=raw["title"], description=raw["description"], posted_date=raw["posted_date"])
emb = PrecomputedEmbedder({demand_embedding_text(demand.title, demand.description): di.matrix[di.ids.index(demand.demand_id)]})
t = time.perf_counter()
out = NumpyDenseRetriever(patents, pi.matrix, emb, DefaultPatentEligibilityPolicy("ES")).retrieve(demand, limit=5)
print(f"{time.perf_counter()-t:.2f}s", demand.title[:70])
by_id = {p.publication_id: p for p in patents}
for c in out: print(c.retrieval_scores, by_id[c.publication_id].title[:80])
E
```
Expected: five candidates returned; the top titles are topically related to the demand. This is a smoke check only; it is not judged and not part of the probe.

- [ ] **Step 6: Build the blinded sheets**

Run: `python experiments/operational-dense-probe/build_probe_sheets.py`
Expected: `31 demands, N pairs to judge, ceil(0.2*N) in the common sample`, and three files in `experiments/operational-dense-probe/outputs/`.
Open neither `provenance_DO_NOT_OPEN.json` nor any method list until both evaluators have finished.

- [ ] **Step 7: Human gate 1, independent judging (no agent action)**

- Valentín fills `grade` in every row of `judging_sheet_A.csv` with `0-3` or `U`, using the rubric in `docs/empirical-study-protocol.md` section 6.2.
- Lydia fills `grade` in every row of `judging_sheet_B_common.csv` without seeing Valentín's grades.
- Then both discuss the pairs where their grades differ and write `experiments/operational-dense-probe/outputs/adjudication.csv` with columns `pair_id,final_grade` for **every** common-sample pair (agreed pairs carry the shared grade). One-grade gaps: integer after joint re-review. Two-or-more-grade gaps or any `U`: joint adjudication; if no agreed integer, write `U` (the pair is then excluded, never imputed as 0).
Do not proceed until all three files are complete; `score_probe.py` fails on empty cells by design.

- [ ] **Step 8: Score**

Run: `python experiments/operational-dense-probe/score_probe.py`
Expected: one line `OUTCOME RESOLVED-YES|RESOLVED-NO|UNRESOLVED: P@5 dense=... bm25=... delta=... kappa_w=...` and `outputs/probe_result.json`.

- [ ] **Step 9: Write the result document and commit**

Create `docs/operational-dense-probe-result.md` stating, from `probe_result.json` only: the outcome, `P@5` for both methods, delta, `kappa_w` and `kappa`, pairs excluded, eligible-set sizes (min, median, max), short-list counts, truncation rate from the manifest, the informative bootstrap intervals (described as uncertainty, not as a gate), the per-language stratum, and the threats to validity from spec section 9 including that Evaluator A built the system. Do not reinterpret the outcome or adjust thresholds.

```bash
python scripts/check_docs_correctness.py
git add experiments/operational-dense-probe/outputs docs/operational-dense-probe-result.md
git commit -m "docs(probe): operational dense-retrieval probe result" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```
Expected: docs gate PASS, commit created. Put the batch-size decision from Step 3 in this commit's body if it was not already committed.
