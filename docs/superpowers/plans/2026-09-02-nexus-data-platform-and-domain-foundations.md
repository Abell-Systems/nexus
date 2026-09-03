# Nexus Data Platform & Domain Foundations (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the agnostic Clean Architecture Domain Core and the immutable Data Platform (`RawStore` -> `Normalizer` -> `Validator` -> `CanonicalStore` (Parquet) -> `DatasetSnapshot` -> `DuckDB QueryEngine`) for Nexus 2.0 with a 3-tier testing pyramid (Unit, Integration, E2E) and 8 Scientific Invariant Gates.

**Architecture:** 
- `nexus/domain/`: Pure entity contracts (`PatentDocument`, `DemandSignal`, `FieldObservation`, `RawBatch`, `DatasetSnapshot`, `OpportunityScore`) with Pydantic v2 and 64-character hex SHA validation.
- `nexus/application/`: Streaming ingestion use cases (`IngestionPipeline`, `OepmNormalizer`, `PatentValidator`, `DatasetFreezer`) with batched processing (`Iterator[RawPayload] -> Iterator[PatentDocument]`).
- `nexus/infrastructure/`: Relational Parquet storage (`patents/`, `observations/`, `family_memberships/`), filesystem content-addressed `FilesystemRawStore`, and zero-copy DuckDB views (`CREATE VIEW ... AS SELECT * FROM read_parquet(...)`).
- `tests/`: 3-Tier Testing Pyramid with property-based and clean-clone A/B determinism gates.

**Tech Stack:** Python 3.12, Pydantic v2, PyArrow, Apache Parquet, DuckDB, httpx, pytest, pytest-asyncio, Hypothesis.

## Global Constraints

- **Python Floor:** Python 3.12+ type annotations and syntax.
- **Clean Architecture Boundaries:** `nexus/domain/` depends only on Python standard library and Pydantic v2.
- **Streaming Ingestion Contract:** Ingestion processes batches via iterables without accumulating full corpora in Python RAM.
- **Stable Identity:** `DatasetSnapshot` references `RawBatch(batch_id, source_id, retrieval_timestamp, payload_sha256)` rather than local filesystem paths.
- **Deterministic Multi-Part Hashing:** `dataset_content_sha256` is the SHA-256 of the sorted manifest of canonical Parquet partition parts `(part_name, row_count, file_sha256)`.
- **Zero Corpus Duplication:** DuckDB registers Parquet via `CREATE VIEW ... AS SELECT * FROM read_parquet(...)`.
- **Strict Null Semantics:** Missing fields remain `None` (zero fake defaults like `2020-01-01` or `G06Q`). Unobserved forward citations do not pull cluster citation averages to zero.
- **A/B Determinism Gate:** Independent clean-clone executions on the same raw payload must produce identical `dataset_content_sha256` and `manifest_sha256`.

---

## Testing Pyramid & Invariants Layout

```text
tests/
├── unit/
│   ├── domain/
│   │   ├── test_patent.py           # Pure entity logic, null citation semantics, family relations
│   │   ├── test_evidence.py         # FieldObservation 64-char SHA validation & VerificationStatus
│   │   ├── test_snapshot.py         # DatasetSnapshot, RawBatch, and DatasetPart contracts
│   │   └── test_opportunity.py      # OpportunityScore vs OpportunityHypothesis contracts
│   └── application/
│       └── ingestion/
│           ├── test_pipeline.py     # Streaming IngestionPipeline orchestration with Mock stores
│           └── test_validator.py    # PatentValidator rejection of malformed / synthetic default records
│
├── integration/
│   ├── infrastructure/
│   │   ├── storage/
│   │   │   ├── test_raw_store.py     # FilesystemRawStore idempotency, corruption, sidecar metadata
│   │   │   ├── test_parquet_store.py # Relational ParquetStore, PyArrow schema stability, part hashing
│   │   │   └── test_duckdb_engine.py # DuckDbQueryEngine zero-copy view, NULL != 0 in average citations
│   │   └── sources/
│   │       ├── test_oepm.py         # Real OEPM fixture parsing through OepmNormalizer
│   │       └── test_epo_ops.py      # Real EPO XML fixture parsing through EpoOpsNormalizer
│   └── data_platform/
│       └── test_raw_to_canonical.py # Integrated pipeline: Raw payload -> Parquet -> Snapshot -> DuckDB
│
└── e2e/
    └── test_ingest_use_case.py      # Clean-clone A/B reproducibility gate (Run A == Run B)
```

---

### Task 1: Domain Entities, 64-char Hex Validation & Protocols

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
- Produces: `VerificationStatus`, `FieldObservation`, `PatentDocument`, `PatentFamily`, `FamilyMembership`, `DemandSignal`, `RawBatch`, `DatasetPart`, `DatasetSnapshot`, `OpportunityScore`, `OpportunityHypothesis`.

- [ ] **Step 1: Write pure unit tests for domain entities**

```python
# tests/unit/domain/test_evidence.py
import pytest
from datetime import datetime
from nexus.domain.models.evidence import FieldObservation, VerificationStatus

def test_field_observation_strict_64_hex_sha():
    # Valid 64-char hex SHA passes
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
        verification_status=VerificationStatus.SOURCE_REPORTED
    )
    assert obs.verification_status == VerificationStatus.SOURCE_REPORTED

    # Invalid SHA lengths or non-hex characters fail validation
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        FieldObservation(
            entity_id="ES-2849102-B2",
            field_name="publication_date",
            observed_value_json='"2021-11-25"',
            value_type="str",
            source_authority="OEPM BOPI",
            source_uri="https://consultas2.oepm.es/InvenesWeb/",
            retrieval_timestamp=datetime(2026, 8, 25, 11, 8, 53),
            raw_payload_sha256="abc123short",
            extraction_version="1.0.0",
            verification_status=VerificationStatus.SOURCE_REPORTED
        )
```

```python
# tests/unit/domain/test_patent.py
import pytest
from nexus.domain.models.patent import PatentDocument, PatentFamily, FamilyMembership
from nexus.domain.models.evidence import FieldObservation, VerificationStatus
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
        raw_payload_sha256="a" * 64,
        extraction_version="1.0.0",
        verification_status=VerificationStatus.SOURCE_REPORTED
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
# tests/unit/domain/test_snapshot.py
import pytest
from datetime import datetime
from nexus.domain.models.snapshot import DatasetSnapshot, RawBatch, DatasetPart

def test_dataset_snapshot_stable_batch_identity():
    batch = RawBatch(
        batch_id="batch_001",
        source_id="oepm_bopi",
        retrieval_timestamp=datetime(2026, 9, 2, 10, 0, 0),
        payload_sha256="2832dc5936b881b4045b26b415f5c5ed2c0bfdc71f6902b838d85000e6799d7b"
    )
    part = DatasetPart(
        part_name="patents/part-0000.parquet",
        row_count=16,
        file_sha256="c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e"
    )
    snap = DatasetSnapshot(
        dataset_id="patents_es_v1",
        schema_version="2.3.0",
        source_batches=[batch],
        record_count=16,
        parts=[part],
        dataset_content_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        manifest_sha256="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        created_at=datetime(2026, 9, 2),
        transformation_version="1.0.0"
    )
    assert snap.record_count == 16
    assert snap.source_batches[0].batch_id == "batch_001"
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

- [ ] **Step 2: Run unit tests to verify they fail**

Run: `pytest tests/unit/domain/ -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement domain models & protocols**

Create `nexus/domain/models/evidence.py`, `nexus/domain/models/patent.py`, `nexus/domain/models/demand.py`, `nexus/domain/models/snapshot.py`, `nexus/domain/models/opportunity.py`, and `nexus/domain/protocols/*.py`.

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `pytest tests/unit/domain/ -v`  
Expected: PASS (4/4 files passed)

- [ ] **Step 5: Commit**

```bash
git add nexus/domain/ tests/unit/domain/
git commit -m "feat(domain): implement domain entities, 64-char hex SHA validation, and snapshot protocols"
```

---

### Task 2: Streaming Ingestion Pipeline with Decoupled Normalizers & Validators

**Files:**
- Create: `nexus/domain/protocols/sources.py`
- Create: `nexus/application/ingestion/normalizers/base.py`
- Create: `nexus/application/ingestion/normalizers/oepm_normalizer.py`
- Create: `nexus/application/ingestion/validator.py`
- Create: `nexus/application/ingestion/pipeline.py`
- Test: `tests/unit/application/ingestion/test_pipeline.py`
- Test: `tests/unit/application/ingestion/test_validator.py`

**Interfaces:**
- Produces: `PatentNormalizerProtocol.normalize_stream(raw_payload: RawPayload) -> Iterator[tuple[PatentDocument, list[FieldObservation]]]`
- Produces: `PatentValidator.validate_batch(documents: list[PatentDocument]) -> list[PatentDocument]`
- Produces: `IngestionPipeline.ingest_source(...) -> IngestionSummary`

- [ ] **Step 1: Write unit tests with mocks for streaming ingestion**

```python
# tests/unit/application/ingestion/test_validator.py
import pytest
from nexus.domain.models.patent import PatentDocument
from nexus.application.ingestion.validator import PatentValidator, ValidationError

def test_validator_rejects_missing_publication_id():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="",
        country_code="ES",
        doc_number="",
        kind_code="B2",
        title="Valid Title",
        abstract="Valid Abstract"
    )
    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        validator.validate_document(doc)

def test_validator_checks_date_format():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        publication_date="2021-05-10"
    )
    assert validator.validate_document(doc) is True
```

```python
# tests/unit/application/ingestion/test_pipeline.py
import pytest
from pathlib import Path
from datetime import datetime
from nexus.domain.models.patent import PatentDocument
from nexus.domain.models.evidence import FieldObservation, VerificationStatus
from nexus.domain.protocols.sources import RawPayload
from nexus.application.ingestion.pipeline import IngestionPipeline


class MockRawStore:
    def __init__(self):
        self.stored = []
    def store_payload(self, source_id, payload_bytes, metadata, file_ext="json"):
        self.stored.append((source_id, payload_bytes))
        return Path(f"/mock/{source_id}/payload.raw.{file_ext}"), "a" * 64


class MockCanonicalStore:
    def __init__(self):
        self.written_batches = []
    def write_batch(self, dataset_id, documents, observations):
        self.written_batches.append((documents, observations))
    def seal_dataset(self, dataset_id):
        return [("patents/part-0000.parquet", len(self.written_batches[0][0]), "b" * 64)], "c" * 64


class MockSource:
    def fetch_batches(self):
        yield RawPayload(
            source_id="test_src",
            batch_id="batch_01",
            payload_bytes=b'{"items": []}',
            metadata={"source_uri": "https://test.api"},
            retrieval_timestamp=datetime(2026, 9, 2)
        )


class MockNormalizer:
    def normalize_stream(self, raw_payload):
        doc = PatentDocument(
            publication_id="ES-MOCK-001",
            country_code="ES",
            doc_number="MOCK",
            kind_code="B2",
            title="Mock Patent",
            abstract="Abstract"
        )
        obs = FieldObservation(
            entity_id="ES-MOCK-001",
            field_name="title",
            observed_value_json='"Mock Patent"',
            value_type="str",
            source_authority="Mock Authority",
            source_uri="https://test.api",
            retrieval_timestamp=datetime(2026, 9, 2),
            raw_payload_sha256="a" * 64,
            extraction_version="1.0.0",
            verification_status=VerificationStatus.SOURCE_REPORTED
        )
        yield doc, [obs]


def test_streaming_ingestion_pipeline_orchestration():
    raw_store = MockRawStore()
    canonical_store = MockCanonicalStore()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store)

    summary = pipeline.ingest_patent_source(
        source=MockSource(),
        normalizer=MockNormalizer(),
        dataset_id="test_dataset_v1",
        manifest_output_dir=Path("/tmp/manifest_test")
    )

    assert summary.snapshot.record_count == 1
    assert summary.snapshot.dataset_content_sha256 == "c" * 64
    assert len(raw_store.stored) == 1
    assert len(canonical_store.written_batches) == 1
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
git commit -m "feat(ingestion): implement streaming IngestionPipeline, PatentValidator, and OepmNormalizer"
```

---

### Task 3: Relational Parquet Store & Zero-Copy DuckDB Engine

**Files:**
- Create: `nexus/infrastructure/storage/raw_store.py`
- Create: `nexus/infrastructure/storage/parquet_store.py`
- Create: `nexus/infrastructure/storage/duckdb_engine.py`
- Test: `tests/integration/infrastructure/storage/test_raw_store.py`
- Test: `tests/integration/infrastructure/storage/test_parquet_store.py`
- Test: `tests/integration/infrastructure/storage/test_duckdb_engine.py`

**Scientific Invariants Verified:**
- Gate 1: `None != 0` in aggregate citation calculations (`avg == 10.0` when 1 doc has 10 and 1 has `None`, not 5.0).
- Gate 2 & 3: Strict 64-char SHA validation and byte immutability in `FilesystemRawStore`.
- Gate 6: Stable PyArrow schema across `patents/` and `observations/` tables.
- Gate 8: DuckDB engine registers zero-copy views via `CREATE VIEW patents AS SELECT * FROM read_parquet(...)`.

- [ ] **Step 1: Write integration tests with scientific invariants**

```python
# tests/integration/infrastructure/storage/test_duckdb_engine.py
import pytest
from nexus.domain.models.patent import PatentDocument
from nexus.domain.models.evidence import FieldObservation, VerificationStatus
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine
from datetime import datetime

def test_duckdb_query_engine_null_citation_invariant(tmp_path):
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
        forward_citation_count=None, # Invariant: unobserved citations MUST NOT drag average to 5.0
        backward_citation_count=3
    )
    store.write_batch("dataset_inv", [doc1, doc2], [])
    parts, content_sha = store.seal_dataset("dataset_inv")

    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / "canonical" / "dataset_inv")

    # Invariant: average must strictly be 10.0, not 5.0
    stats = engine.get_cluster_aggregates("C11D")
    assert stats["patent_count"] == 2
    assert stats["observed_citations_count"] == 1
    assert stats["avg_forward_citations"] == 10.0 # NOT 5.0!
```

```python
# tests/integration/infrastructure/storage/test_raw_store.py
import pytest
import hashlib
from pathlib import Path
from nexus.infrastructure.storage.raw_store import FilesystemRawStore

def test_raw_store_invariants(tmp_path):
    store = FilesystemRawStore(base_dir=tmp_path / "raw")
    payload = b'{"status": "ok", "items": [1, 2, 3]}'
    meta = {"source_uri": "https://test.portal"}

    # Invariant: same bytes -> exact SHA-256
    expected_sha = hashlib.sha256(payload).hexdigest()
    path1, sha1 = store.store_payload("src_a", payload, meta)
    assert sha1 == expected_sha

    # Invariant: idempotent write
    path2, sha2 = store.store_payload("src_a", payload, meta)
    assert sha1 == sha2
    assert path1 == path2
    assert store.get_payload(sha1) == payload

    # Invariant: corruption detection
    path1.write_bytes(b'{"corrupted": true}')
    with pytest.raises(ValueError, match="Integrity verification failed"):
        store.verify_payload_integrity(sha1)
```

```python
# tests/integration/infrastructure/storage/test_parquet_store.py
import pytest
import pyarrow.parquet as pq
from nexus.domain.models.patent import PatentDocument
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore

def test_relational_parquet_store_layout(tmp_path):
    store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
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
    store.write_batch("dataset_rel", [doc], [])
    parts, content_sha = store.seal_dataset("dataset_rel")

    assert len(parts) >= 1
    assert len(content_sha) == 64

    # Verify Parquet file can be read independently and preserves None
    table = pq.read_table(str(tmp_path / "canonical" / "dataset_rel" / "patents" / "part-0000.parquet"))
    assert table.num_rows == 1
    assert table.column("forward_citation_count")[0].as_py() is None
    assert table.column("backward_citation_count")[0].as_py() == 14
```

- [ ] **Step 2: Run integration tests to verify they fail**

Run: `pytest tests/integration/infrastructure/storage/ -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement storage infrastructure adapters**

Implement `FilesystemRawStore`, `ParquetCanonicalStore` (writing relational `patents/` and `observations/` parts with deterministic content hashing), and `DuckDbQueryEngine` (using `CREATE VIEW ... AS SELECT * FROM read_parquet(...)`).

- [ ] **Step 4: Run integration tests to verify they pass**

Run: `pytest tests/integration/infrastructure/storage/ -v`  
Expected: PASS (3/3 files passed)

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/storage/ tests/integration/infrastructure/storage/
git commit -m "feat(storage): implement relational ParquetCanonicalStore, FilesystemRawStore, and zero-copy DuckDbQueryEngine"
```

---

### Task 4: Source Adapters (OEPM & EPO OPS) and Normalizer Integration

**Files:**
- Create: `nexus/infrastructure/sources/patent/oepm_raw_source.py`
- Create: `nexus/infrastructure/sources/patent/epo_ops_client.py`
- Test: `tests/integration/infrastructure/sources/test_oepm.py`
- Test: `tests/integration/infrastructure/sources/test_epo_ops.py`

**Interfaces:**
- Produces: `OepmRawSource.fetch_batches() -> Iterator[RawPayload]`
- Produces: `EpoOpsClient.fetch_batches(cql_query) -> Iterator[RawPayload]`

- [ ] **Step 1: Write integration tests with real controlled fixtures**

```python
# tests/integration/infrastructure/sources/test_oepm.py
import pytest
from nexus.infrastructure.sources.patent.oepm_raw_source import OepmRawSource
from nexus.application.ingestion.normalizers.oepm_normalizer import OepmNormalizer

def test_oepm_raw_source_and_normalizer():
    source = OepmRawSource(file_path="data/raw/oepm_open_data_es.json")
    normalizer = OepmNormalizer()

    batches = list(source.fetch_batches())
    assert len(batches) == 1
    assert len(batches[0].payload_bytes) > 0

    records = list(normalizer.normalize_stream(batches[0]))
    assert len(records) == 16
    for doc, obs_list in records:
        assert doc.country_code == "ES"
        assert len(obs_list) > 0
        assert obs_list[0].raw_payload_sha256 == batches[0].payload_sha256
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/infrastructure/sources/ -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement OepmRawSource and EpoOpsClient**

Implement `nexus/infrastructure/sources/patent/oepm_raw_source.py` and `nexus/infrastructure/sources/patent/epo_ops_client.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/infrastructure/sources/ -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/sources/ tests/integration/infrastructure/sources/
git commit -m "feat(sources): implement OepmRawSource and EpoOpsClient with decoupled normalizer tests"
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
from nexus.infrastructure.sources.patent.oepm_raw_source import OepmRawSource
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

    summary = pipeline.ingest_patent_source(
        source=source,
        normalizer=normalizer,
        dataset_id="patents_es_v1",
        manifest_output_dir=tmp_path / "snapshots"
    )

    # Invariant 1: Record count matches exactly
    assert summary.snapshot.record_count == 16

    # Invariant 2: Provenance references valid raw SHA
    assert len(summary.snapshot.source_batches) == 1
    raw_sha = summary.snapshot.source_batches[0].payload_sha256
    assert len(raw_sha) == 64

    # Invariant 3: Parquet is readable independently
    parquet_path = tmp_path / "canonical" / "patents_es_v1" / "patents" / "part-0000.parquet"
    table = pq.read_table(str(parquet_path))
    assert table.num_rows == summary.snapshot.record_count

    # Invariant 4: DuckDB engine queries snapshot directly via zero-copy view
    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / "canonical" / "patents_es_v1")
    res = engine.search_by_cpc_prefix("C11D")
    assert len(res) == 3
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/integration/data_platform/test_raw_to_canonical.py -v`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/data_platform/test_raw_to_canonical.py
git commit -m "test(integration): verify complete Data Platform lifecycle from raw source to DuckDB view"
```

---

### Task 6: E2E Clean-Clone Reproducibility Gate (Run A == Run B)

**Files:**
- Create: `nexus/interfaces/cli/main.py`
- Create: `tests/e2e/test_ingest_use_case.py`
- Test: Independent dual ingestion runs from identical raw source to verify exact cryptographic identity ($A == B$).

- [ ] **Step 1: Write E2E Clean-Clone A/B Reproducibility Test**

```python
# tests/e2e/test_ingest_use_case.py
import pytest
import subprocess
import sys
import json
from pathlib import Path

def test_ingest_clean_clone_ab_reproducibility_gate(tmp_path):
    # Run A
    run_a_dir = tmp_path / "run_a"
    cmd_a = [
        sys.executable, "-m", "nexus.interfaces.cli.main",
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", "data/raw/oepm_open_data_es.json",
        "--dataset-id", "patents_es_repro",
        "--output-dir", str(run_a_dir)
    ]
    res_a = subprocess.run(cmd_a, capture_output=True, text=True)
    assert res_a.returncode == 0, f"Run A failed:\n{res_a.stderr}"

    # Run B (Independent run on clean directory)
    run_b_dir = tmp_path / "run_b"
    cmd_b = [
        sys.executable, "-m", "nexus.interfaces.cli.main",
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", "data/raw/oepm_open_data_es.json",
        "--dataset-id", "patents_es_repro",
        "--output-dir", str(run_b_dir)
    ]
    res_b = subprocess.run(cmd_b, capture_output=True, text=True)
    assert res_b.returncode == 0, f"Run B failed:\n{res_b.stderr}"

    # Scientific Invariant Gate 7: Deterministic A/B Equivalence
    manifest_a = json.loads((run_a_dir / "snapshots" / "patents_es_repro_manifest.json").read_text())
    manifest_b = json.loads((run_b_dir / "snapshots" / "patents_es_repro_manifest.json").read_text())

    assert manifest_a["dataset_content_sha256"] == manifest_b["dataset_content_sha256"]
    assert manifest_a["record_count"] == manifest_b["record_count"]
    assert manifest_a["schema_version"] == manifest_b["schema_version"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_ingest_use_case.py -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement Nexus CLI entrypoint**

Create `nexus/interfaces/cli/main.py` using `argparse` to expose `ingest` command.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/e2e/test_ingest_use_case.py -v`  
Expected: PASS

- [ ] **Step 5: Run full test suite across entire repository**

Run: `pytest tests/ backend/tests/ -v`  
Expected: All tests pass cleanly.

- [ ] **Step 6: Commit**

```bash
git add nexus/interfaces/cli/ tests/e2e/
git commit -m "feat(cli): implement nexus ingest CLI and verify clean-clone A/B reproducibility gate"
```
