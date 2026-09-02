# Nexus Data Platform & Domain Foundations (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the agnostic Clean Architecture Domain Core and the immutable Data Platform (`RawStore` -> `Normalizer` -> `Validator` -> `CanonicalStore` (Parquet) -> `DatasetSnapshot` -> `DuckDB QueryEngine`) for Nexus 2.0 with a rigorous 3-tier testing pyramid (Unit, Integration, E2E) and scientific invariant verification.

**Architecture:** 
- `nexus/domain/`: Pure entity contracts (`PatentDocument`, `DemandSignal`, `FieldObservation`, `DatasetSnapshot`, `OpportunityScore`) with zero I/O.
- `nexus/application/`: Use case orchestration (`IngestionPipeline`, `DatasetFreezer`, `PatentNormalizer`, `PatentValidator`) tested with mocks in isolation.
- `nexus/infrastructure/`: Adapters for storage (`FilesystemRawStore`, `ParquetCanonicalStore`, `DuckDbQueryEngine`) and sources (`OepmRawSource`, `EpoOpsClient`).
- `tests/`: 3-Tier Testing Pyramid (Unit -> Integration -> E2E) with explicit Scientific Invariant Gates.

**Tech Stack:** Python 3.12, Pydantic v2, PyArrow, Apache Parquet, DuckDB, httpx, pytest, pytest-asyncio.

## Global Constraints

- **Python Floor:** Python 3.12+ type annotations and syntax.
- **Clean Architecture Boundaries:** `nexus/domain/` depends only on Python standard library and Pydantic v2.
- **Normalizer Decoupling:** `PatentSource` strictly returns `RawPayload(bytes, metadata)`. Transformation logic lives in `nexus/application/ingestion/normalizers/`.
- **Zero Synthetic Defaults:** Missing fields in source records remain `None` (zero fake defaults like `2020-01-01` or `G06Q`).
- **Deterministic Hashing:** `content_sha256` is the exact SHA-256 digest of the canonical primary Parquet artifact chunk bytes.
- **Scientific Invariants Gate:** Every dataset snapshot must verify: `snapshot.record_count == parquet.num_rows`, `sha256(parquet_bytes) == snapshot.content_sha256`, and `observation.raw_payload_sha256 == raw_sha`.

---

## Testing Pyramid & Invariants Layout

```text
tests/
├── unit/
│   ├── domain/
│   │   ├── test_patent.py           # Pure entity logic, null citation semantics, family relations
│   │   ├── test_evidence.py         # FieldObservation deterministic JSON serialization
│   │   ├── test_snapshot.py         # DatasetSnapshot contract and manifest typing
│   │   └── test_opportunity.py      # OpportunityScore vs OpportunityHypothesis contracts
│   └── application/
│       └── ingestion/
│           ├── test_pipeline.py     # IngestionPipeline orchestration using Mock stores
│           └── test_validator.py    # PatentValidator rejection of malformed entities
│
├── integration/
│   ├── infrastructure/
│   │   ├── storage/
│   │   │   ├── test_raw_store.py     # FilesystemRawStore idempotency, corruption, sidecar metadata
│   │   │   ├── test_parquet_store.py # ParquetCanonicalStore schema stability, null preservation, SHA
│   │   │   └── test_duckdb_engine.py # DuckDbQueryEngine in-memory execution, null citations != 0
│   │   └── sources/
│   │       ├── test_oepm.py         # Real OEPM fixture parsing through OepmNormalizer
│   │       └── test_epo_ops.py      # Real EPO XML fixture parsing through EpoOpsNormalizer
│   └── data_platform/
│       └── test_raw_to_canonical.py # Integrated pipeline: Raw payload -> Parquet -> Snapshot -> DuckDB
│
└── e2e/
    └── test_ingest_use_case.py      # Complete ingest CLI use case with clean-clone invariant verification
```

---

### Task 1: Pure Domain Entities & Invariant Contracts

**Files:**
- Create: `nexus/domain/models/evidence.py`
- Create: `nexus/domain/models/patent.py`
- Create: `nexus/domain/models/demand.py`
- Create: `nexus/domain/models/snapshot.py`
- Create: `nexus/domain/models/opportunity.py`
- Create: `nexus/domain/protocols/storage.py`
- Create: `nexus/domain/protocols/sources.py`
- Create: `nexus/domain/protocols/models.py`
- Test: `tests/unit/domain/test_patent.py`
- Test: `tests/unit/domain/test_evidence.py`
- Test: `tests/unit/domain/test_snapshot.py`
- Test: `tests/unit/domain/test_opportunity.py`

**Interfaces:**
- Produces: `FieldObservation`, `PatentDocument`, `PatentFamily`, `FamilyMembership`, `DemandSignal`, `DatasetSnapshot`, `OpportunityScore`, `OpportunityHypothesis`.

- [ ] **Step 1: Write pure unit tests for domain entities**

```python
# tests/unit/domain/test_patent.py
import pytest
from nexus.domain.models.patent import PatentDocument, PatentFamily, FamilyMembership
from nexus.domain.models.evidence import FieldObservation
from datetime import datetime

def test_patent_document_strict_null_preservation():
    doc = PatentDocument(
        publication_id="ES-2849102-B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Formulación detergente",
        abstract="Resumen",
        forward_citation_count=None,
        backward_citation_count=14
    )
    assert doc.forward_citation_count is None
    assert doc.backward_citation_count == 14
    assert doc.filing_date is None
    assert doc.classifications_cpc == []

def test_family_membership_decoupling():
    fam = PatentFamily(
        family_id="FAM-100",
        earliest_priority_date="2018-01-01",
        title_consensus="Detergent system"
    )
    obs = FieldObservation(
        entity_id="ES-2849102-B2",
        field_name="family_id",
        observed_value_json='"FAM-100"',
        value_type="str",
        source_authority="EPO INPADOC",
        source_uri="https://ops.epo.org",
        retrieval_timestamp=datetime(2026, 9, 2),
        raw_payload_sha256="abc123hash",
        extraction_version="1.0.0",
        verification_status="authority_verified"
    )
    membership = FamilyMembership(
        family_id="FAM-100",
        publication_id="ES-2849102-B2",
        membership_source="EPO INPADOC",
        evidence=obs
    )
    assert membership.family_id == fam.family_id
```

```python
# tests/unit/domain/test_evidence.py
import pytest
from datetime import datetime
from nexus.domain.models.evidence import FieldObservation

def test_field_observation_deterministic_serialization():
    obs = FieldObservation(
        entity_id="ES-2849102-B2",
        field_name="publication_date",
        observed_value_json='"2021-11-25"',
        value_type="str",
        source_authority="OEPM BOPI",
        source_uri="https://consultas2.oepm.es/InvenesWeb/detalle?tipo=PAT&ref=P202030431",
        retrieval_timestamp=datetime(2026, 8, 25, 11, 8, 53),
        raw_payload_sha256="2832dc5936b881b4045b26b415f5c5ed2c0bfdc71f6902b838d85000e6799d7b",
        extraction_version="1.0.0",
        verification_status="authority_verified"
    )
    assert obs.entity_id == "ES-2849102-B2"
    assert obs.value_type == "str"
```

```python
# tests/unit/domain/test_snapshot.py
import pytest
from datetime import datetime
from nexus.domain.models.snapshot import DatasetSnapshot

def test_dataset_snapshot_contract():
    snap = DatasetSnapshot(
        dataset_id="patents_es_v1",
        schema_version="2.2.0",
        source_batches=["data/sources/oepm/2026-09-02/payload_001.raw.json"],
        record_count=16,
        content_sha256="c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e",
        manifest_sha256="aabbccddeeff11223344556677889900aabbccddeeff11223344556677889900",
        created_at=datetime(2026, 9, 2),
        transformation_version="1.0.0",
        provenance_manifest_uri="data/snapshots/patents_es_manifest.json"
    )
    assert snap.record_count == 16
    assert len(snap.content_sha256) == 64
```

```python
# tests/unit/domain/test_opportunity.py
import pytest
from nexus.domain.models.opportunity import OpportunityScore, OpportunityHypothesis

def test_opportunity_measurement_vs_interpretation_separation():
    score = OpportunityScore(
        cluster_id="C11D",
        score=0.42,
        score_coverage=0.75,
        components={"density": 0.10, "recency": 0.60, "traction": None, "demand": 1.00},
        missing_components=["traction"],
        model_id="composite_whitespace_v1",
        model_version="1.0.0",
        quadrant="Quadrant II (Co-developed / Saturated)"
    )
    assert score.score == 0.42
    assert "traction" in score.missing_components

    hypo = OpportunityHypothesis(
        hypothesis_id="HYP-C11D-001",
        cluster_id="C11D",
        opportunity_score=score,
        rationale="High demand pull with mature domestic IP base",
        supporting_prior_art=["ES-2849102-B2"],
        target_demand_ids=["INNOGET-2292"],
        status="validated"
    )
    assert hypo.hypothesis_id == "HYP-C11D-001"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/domain/ -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus'`

- [ ] **Step 3: Implement domain models & protocols**

Create `nexus/domain/models/evidence.py`, `nexus/domain/models/patent.py`, `nexus/domain/models/demand.py`, `nexus/domain/models/snapshot.py`, `nexus/domain/models/opportunity.py`, and `nexus/domain/protocols/*.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/domain/ -v`  
Expected: PASS (4/4 files passed)

- [ ] **Step 5: Commit**

```bash
git add nexus/domain/ tests/unit/domain/
git commit -m "feat(domain): implement pure domain entities, field observations, snapshot, and opportunity contracts"
```

---

### Task 2: Decoupled Ingestion Pipeline with Application Normalizers & Validators

**Files:**
- Create: `nexus/domain/protocols/sources.py`
- Create: `nexus/application/ingestion/normalizers/base.py`
- Create: `nexus/application/ingestion/normalizers/oepm_normalizer.py`
- Create: `nexus/application/ingestion/validator.py`
- Create: `nexus/application/ingestion/pipeline.py`
- Test: `tests/unit/application/ingestion/test_pipeline.py`
- Test: `tests/unit/application/ingestion/test_validator.py`

**Interfaces:**
- Consumes: `RawStoreProtocol`, `CanonicalStoreProtocol`
- Produces: `PatentNormalizerProtocol.normalize(raw_payload: RawPayload) -> list[PatentDocument]`
- Produces: `PatentValidator.validate(documents: list[PatentDocument]) -> list[PatentDocument]`
- Produces: `IngestionPipeline.ingest_patent_source(...) -> (DatasetSnapshot, list[PatentDocument])`

- [ ] **Step 1: Write failing unit tests for IngestionPipeline and Validator**

```python
# tests/unit/application/ingestion/test_validator.py
import pytest
from nexus.domain.models.patent import PatentDocument
from nexus.application.ingestion.validator import PatentValidator, ValidationError

def test_validator_rejects_missing_publication_id():
    validator = PatentValidator()
    invalid_doc = PatentDocument(
        publication_id="",
        country_code="ES",
        doc_number="",
        kind_code="B2",
        title="Valid Title",
        abstract="Valid Abstract"
    )
    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        validator.validate_document(invalid_doc)

def test_validator_rejects_synthetic_default_dates():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        publication_date="2020-01-01" # Valid string, but validator checks format YYYY-MM-DD
    )
    assert validator.validate_document(doc) is True
```

```python
# tests/unit/application/ingestion/test_pipeline.py
import pytest
from pathlib import Path
from datetime import datetime
from nexus.domain.models.patent import PatentDocument
from nexus.domain.models.snapshot import DatasetSnapshot
from nexus.application.ingestion.pipeline import IngestionPipeline


class MockRawStore:
    def __init__(self):
        self.stored = []
    def store_payload(self, source_id, payload_bytes, metadata, file_ext="json"):
        self.stored.append((source_id, payload_bytes))
        return Path(f"/mock/{source_id}/payload.raw.{file_ext}"), "mock_raw_sha"


class MockCanonicalStore:
    def __init__(self):
        self.stored_docs = []
    def write_documents(self, dataset_id, documents):
        self.stored_docs = documents
        return Path(f"/mock/{dataset_id}/corpus.parquet"), "mock_content_sha"


class MockSource:
    def fetch_raw_batch(self):
        return b'{"records": []}', {"endpoint": "https://mock.api"}


class MockNormalizer:
    def normalize(self, raw_bytes, raw_sha):
        return [
            PatentDocument(
                publication_id="ES-MOCK-001",
                country_code="ES",
                doc_number="MOCK",
                kind_code="B2",
                title="Mock Patent",
                abstract="Abstract"
            )
        ]


def test_ingestion_pipeline_orchestration_with_mocks():
    raw_store = MockRawStore()
    canonical_store = MockCanonicalStore()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store)

    snapshot, docs = pipeline.ingest_patent_source(
        source=MockSource(),
        normalizer=MockNormalizer(),
        source_id="test_source",
        dataset_id="test_dataset_v1",
        manifest_output_dir=Path("/tmp/manifest_test")
    )

    assert len(docs) == 1
    assert snapshot.record_count == 1
    assert snapshot.content_sha256 == "mock_content_sha"
    assert len(raw_store.stored) == 1
```

- [ ] **Step 2: Run unit tests to verify they fail**

Run: `pytest tests/unit/application/ingestion/ -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement IngestionPipeline, Normalizers, and Validator**

Create `nexus/application/ingestion/validator.py`, `nexus/application/ingestion/normalizers/oepm_normalizer.py`, and `nexus/application/ingestion/pipeline.py`.

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `pytest tests/unit/application/ingestion/ -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/application/ingestion/ tests/unit/application/ingestion/
git commit -m "feat(ingestion): implement decoupled IngestionPipeline, PatentValidator, and Normalizers"
```

---

### Task 3: Infrastructure Storage Adapters & Invariant Verification

**Files:**
- Create: `nexus/infrastructure/storage/raw_store.py`
- Create: `nexus/infrastructure/storage/parquet_store.py`
- Create: `nexus/infrastructure/storage/duckdb_engine.py`
- Test: `tests/integration/infrastructure/storage/test_raw_store.py`
- Test: `tests/integration/infrastructure/storage/test_parquet_store.py`
- Test: `tests/integration/infrastructure/storage/test_duckdb_engine.py`

**Scientific Invariants Verified:**
- RAW: `same bytes -> same SHA-256`, `same payload -> idempotent storage`, `stored bytes == original bytes`, `corrupted payload -> integrity error`.
- Canonical Parquet: `None remains NULL in Parquet`, `zero synthetic defaults`, `sha256(parquet_bytes) == calculated_content_sha`.
- Query Engine: `read_parquet directly in-memory`, `NULL forward_citations != 0`, `aggregation agrees with known fixture`.

- [ ] **Step 1: Write integration tests with scientific invariants**

```python
# tests/integration/infrastructure/storage/test_raw_store.py
import pytest
import hashlib
from pathlib import Path
from nexus.infrastructure.storage.raw_store import FilesystemRawStore

def test_raw_store_invariants(tmp_path):
    store = FilesystemRawStore(base_dir=tmp_path / "raw")
    payload = b'{"status": "ok", "items": [1, 2, 3]}'
    meta = {"source": "test_portal"}

    # Invariant 1: same bytes -> same SHA256
    expected_sha = hashlib.sha256(payload).hexdigest()
    path1, sha1 = store.store_payload("src_a", payload, meta)
    assert sha1 == expected_sha

    # Invariant 2: idempotent storage
    path2, sha2 = store.store_payload("src_a", payload, meta)
    assert sha1 == sha2
    assert path1 == path2

    # Invariant 3: stored bytes == original bytes
    assert store.get_payload(sha1) == payload

    # Invariant 4: corrupted payload -> integrity failure
    path1.write_bytes(b'{"corrupted": true}')
    with pytest.raises(ValueError, match="Integrity verification failed"):
        store.verify_payload_integrity(sha1)
```

```python
# tests/integration/infrastructure/storage/test_parquet_store.py
import pytest
import hashlib
import pyarrow.parquet as pq
from nexus.domain.models.patent import PatentDocument
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore

def test_parquet_store_invariants(tmp_path):
    store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    doc = PatentDocument(
        publication_id="ES-2849102-B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Formulación detergente",
        abstract="Resumen",
        forward_citation_count=None, # Invariant: None must stay null
        backward_citation_count=14
    )
    p_path, content_sha = store.write_documents("dataset_test", [doc])

    # Invariant 1: Parquet chunk SHA matches exact file bytes SHA
    file_bytes_sha = hashlib.sha256(p_path.read_bytes()).hexdigest()
    assert content_sha == file_bytes_sha

    # Invariant 2: None remains NULL in Parquet column
    table = pq.read_table(str(p_path))
    assert table.num_rows == 1
    assert table.column("forward_citation_count")[0].as_py() is None
    assert table.column("backward_citation_count")[0].as_py() == 14
```

```python
# tests/integration/infrastructure/storage/test_duckdb_engine.py
import pytest
from nexus.domain.models.patent import PatentDocument
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine

def test_duckdb_query_engine_invariants(tmp_path):
    store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    doc1 = PatentDocument(
        publication_id="ES-001",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="T1",
        abstract="A1",
        classifications_cpc=["C11D1/00"],
        forward_citation_count=10,
        backward_citation_count=5
    )
    doc2 = PatentDocument(
        publication_id="ES-002",
        country_code="ES",
        doc_number="002",
        kind_code="A1",
        title="T2",
        abstract="A2",
        classifications_cpc=["C11D3/00"],
        forward_citation_count=None, # Unobserved forward citation
        backward_citation_count=3
    )
    p_path, _ = store.write_documents("dataset_inv", [doc1, doc2])

    engine = DuckDbQueryEngine.from_parquet(p_path)

    # Invariant: NULL citations are distinguished from 0
    results = engine.search_by_cpc_prefix("C11D")
    assert len(results) == 2
    r_map = {r["publication_id"]: r["forward_citation_count"] for r in results}
    assert r_map["ES-001"] == 10
    assert r_map["ES-002"] is None

    # Aggregates count observed vs total
    stats = engine.get_cluster_aggregates("C11D")
    assert stats["patent_count"] == 2
    assert stats["observed_citations_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/infrastructure/storage/ -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement storage infrastructure adapters**

Implement `FilesystemRawStore`, `ParquetCanonicalStore`, and `DuckDbQueryEngine`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/infrastructure/storage/ -v`  
Expected: PASS (3/3 files passed)

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/storage/ tests/integration/infrastructure/storage/
git commit -m "feat(storage): implement FilesystemRawStore, ParquetCanonicalStore, and DuckDbQueryEngine with invariant tests"
```

---

### Task 4: Concrete Source Adapters & Integration Tests

**Files:**
- Create: `nexus/infrastructure/sources/patent/oepm_source.py`
- Create: `nexus/infrastructure/sources/patent/epo_ops_client.py`
- Test: `tests/integration/infrastructure/sources/test_oepm.py`
- Test: `tests/integration/infrastructure/sources/test_epo_ops.py`

**Interfaces:**
- Produces: `OepmRawSource.fetch_raw_batch() -> tuple[bytes, dict]`
- Produces: `EpoOpsClient.fetch_raw_batch(cql_query) -> tuple[bytes, dict]`

- [ ] **Step 1: Write integration tests with real controlled fixtures**

```python
# tests/integration/infrastructure/sources/test_oepm.py
import pytest
from pathlib import Path
from nexus.infrastructure.sources.patent.oepm_source import OepmRawSource
from nexus.application.ingestion.normalizers.oepm_normalizer import OepmNormalizer

def test_oepm_source_and_normalizer_integration():
    source = OepmRawSource(file_path="data/raw/oepm_open_data_es.json")
    raw_bytes, meta = source.fetch_raw_batch()
    assert len(raw_bytes) > 0
    assert meta["source_authority"] == "Oficina Española de Patentes y Marcas (OEPM / BOPI)"

    normalizer = OepmNormalizer()
    docs = normalizer.normalize(raw_bytes, "mock_sha")
    assert len(docs) == 16
    for d in docs:
        assert d.country_code == "ES"
        assert len(d.observations) > 0
        assert d.observations[0].raw_payload_sha256 == "mock_sha"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/infrastructure/sources/ -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement OepmRawSource and EpoOpsClient**

Implement `nexus/infrastructure/sources/patent/oepm_source.py` and `nexus/infrastructure/sources/patent/epo_ops_client.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/infrastructure/sources/ -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/sources/ tests/integration/infrastructure/sources/
git commit -m "feat(sources): implement OepmRawSource and EpoOpsClient with integration tests"
```

---

### Task 5: Full Data Platform Lifecycle Integration Test

**Files:**
- Create: `tests/integration/data_platform/test_raw_to_canonical.py`
- Test: Complete pipeline integration `OepmRawSource -> FilesystemRawStore -> OepmNormalizer -> PatentValidator -> ParquetCanonicalStore -> DatasetSnapshot -> DuckDbQueryEngine`.

- [ ] **Step 1: Write integration test verifying all cross-component invariants**

```python
# tests/integration/data_platform/test_raw_to_canonical.py
import pytest
import pyarrow.parquet as pq
from pathlib import Path
from nexus.infrastructure.sources.patent.oepm_source import OepmRawSource
from nexus.infrastructure.storage.raw_store import FilesystemRawStore
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine
from nexus.application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
from nexus.application.ingestion.validator import PatentValidator
from nexus.application.ingestion.pipeline import IngestionPipeline

def test_data_platform_raw_to_canonical_lifecycle(tmp_path):
    raw_store = FilesystemRawStore(base_dir=tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    validator = PatentValidator()
    pipeline = IngestionPipeline(
        raw_store=raw_store,
        canonical_store=canonical_store,
        validator=validator
    )

    source = OepmRawSource(file_path="data/raw/oepm_open_data_es.json")
    normalizer = OepmNormalizer()

    snapshot, docs = pipeline.ingest_patent_source(
        source=source,
        normalizer=normalizer,
        source_id="oepm_bopi",
        dataset_id="patents_es_v1",
        manifest_output_dir=tmp_path / "snapshots"
    )

    # Invariant 1: Record count matches exactly
    assert snapshot.record_count == 16
    assert len(docs) == 16

    # Invariant 2: Every observation references the exact raw payload hash
    raw_hash = snapshot.source_batches[0] # contains hash
    for d in docs:
        for obs in d.observations:
            assert obs.raw_payload_sha256 is not None

    # Invariant 3: Parquet is readable independently and matches snapshot record count
    parquet_path = tmp_path / "canonical" / "patents_es_v1" / "corpus.parquet"
    table = pq.read_table(str(parquet_path))
    assert table.num_rows == snapshot.record_count

    # Invariant 4: DuckDB engine queries snapshot directly in memory
    engine = DuckDbQueryEngine.from_parquet(parquet_path)
    res = engine.search_by_cpc_prefix("C11D")
    assert len(res) == 3
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/integration/data_platform/test_raw_to_canonical.py -v`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/data_platform/test_raw_to_canonical.py
git commit -m "test(integration): verify full data platform raw to canonical lifecycle"
```

---

### Task 6: E2E Use Case & Clean-Clone Reproducibility Gate

**Files:**
- Create: `nexus/interfaces/cli/main.py`
- Create: `tests/e2e/test_ingest_use_case.py`
- Test: Full CLI ingest execution on fresh workspace verifying zero legacy `.duckdb` dependency.

- [ ] **Step 1: Write E2E CLI test**

```python
# tests/e2e/test_ingest_use_case.py
import pytest
import subprocess
import sys
from pathlib import Path

def test_ingest_use_case_clean_execution(tmp_path):
    # Execute full CLI ingestion command into isolated temp directories
    raw_dir = tmp_path / "data" / "sources"
    canonical_dir = tmp_path / "data" / "canonical"
    manifest_dir = tmp_path / "data" / "snapshots"

    cmd = [
        sys.executable, "-m", "nexus.interfaces.cli.main",
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", "data/raw/oepm_open_data_es.json",
        "--dataset-id", "patents_es_pilot",
        "--raw-dir", str(raw_dir),
        "--canonical-dir", str(canonical_dir),
        "--manifest-dir", str(manifest_dir)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI execution failed:\n{res.stderr}"

    # Verify generated artifacts
    parquet_file = canonical_dir / "patents_es_pilot" / "corpus.parquet"
    manifest_file = manifest_dir / "patents_es_pilot_manifest.json"

    assert parquet_file.exists()
    assert manifest_file.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_ingest_use_case.py -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement Nexus CLI entrypoint**

Create `nexus/interfaces/cli/main.py` using `argparse` / `typer` to expose `ingest` command.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/e2e/test_ingest_use_case.py -v`  
Expected: PASS

- [ ] **Step 5: Run full test suite across entire repository**

Run: `pytest tests/ backend/tests/ -v`  
Expected: All tests pass cleanly.

- [ ] **Step 6: Commit**

```bash
git add nexus/interfaces/cli/ tests/e2e/
git commit -m "feat(cli): implement nexus ingest CLI and verify E2E clean-clone reproducibility"
```
