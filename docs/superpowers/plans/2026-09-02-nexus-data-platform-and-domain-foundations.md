# Nexus Data Platform & Domain Foundations (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the agnostic Clean Architecture Domain Core and the immutable Data Platform (`RawStore` -> `Normalizer` -> `Validator` -> `CanonicalStore` (Parquet) -> `DatasetSnapshot` -> `DuckDB QueryEngine`) for Nexus 2.0.

**Architecture:** Domain entities (`PatentDocument`, `DemandSignal`, `FieldObservation`, `DatasetSnapshot`) define pure business contracts with Pydantic v2. The Data Platform enforces a strict two-tier storage model: raw payloads are stored immutably with SHA-256 fingerprinting, canonical datasets are saved as columnar Parquet via PyArrow, and analytical queries are executed directly in-memory via DuckDB without instantiating millions of Python objects in RAM.

**Tech Stack:** Python 3.12, Pydantic v2, PyArrow, Apache Parquet, DuckDB, httpx, pytest, pytest-asyncio.

## Global Constraints

- **Python Floor:** Python 3.12+ type annotations and syntax.
- **Clean Architecture Boundaries:** `nexus/domain/` depends only on Python standard library and Pydantic v2.
- **Zero Daemons / Minimal Memory:** Zero background database daemons (no PostgreSQL, Redis, Kafka, or Spark); streaming batch I/O only.
- **Strict Null Semantics:** Missing fields in source records remain `None` (zero fake defaults like `2020-01-01` or `G06Q`).
- **Deterministic Hashing:** `content_sha256` is the exact SHA-256 digest of the canonical primary Parquet artifact chunk bytes.
- **Vectorized Analytics:** Analytical queries run via DuckDB SQL kernels over Parquet, instantiating Pydantic objects strictly at API/domain boundaries.

---

### Task 1: Core Domain Entities & Protocols

**Files:**
- Create: `nexus/domain/models/evidence.py`
- Create: `nexus/domain/models/patent.py`
- Create: `nexus/domain/models/demand.py`
- Create: `nexus/domain/models/snapshot.py`
- Create: `nexus/domain/models/opportunity.py`
- Create: `nexus/domain/protocols/storage.py`
- Create: `nexus/domain/protocols/sources.py`
- Create: `nexus/domain/protocols/models.py`
- Test: `tests/unit/domain/test_domain_models.py`

**Interfaces:**
- Produces: `FieldObservation`, `PatentDocument`, `PatentFamily`, `FamilyMembership`, `DemandSignal`, `DatasetSnapshot`, `OpportunityScore`, `OpportunityHypothesis`.

- [ ] **Step 1: Write failing unit tests for domain entities**

```python
# tests/unit/domain/test_domain_models.py
import pytest
from datetime import datetime
from nexus.domain.models.evidence import FieldObservation
from nexus.domain.models.patent import PatentDocument, PatentFamily, FamilyMembership
from nexus.domain.models.demand import DemandSignal
from nexus.domain.models.snapshot import DatasetSnapshot
from nexus.domain.models.opportunity import OpportunityScore, OpportunityHypothesis


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


def test_patent_document_null_citation_preservation():
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
    assert doc.classifications_cpc == []


def test_opportunity_score_measurement_separation():
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

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_domain_models.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus'`

- [ ] **Step 3: Implement domain models & protocols**

```python
# nexus/domain/models/evidence.py
from datetime import datetime
from pydantic import BaseModel, Field


class FieldObservation(BaseModel):
    """Fine-grained provenance record tracking the origin and authority of a specific field observation."""
    entity_id: str
    field_name: str
    observed_value_json: str
    value_type: str
    source_authority: str
    source_uri: str
    retrieval_timestamp: datetime
    raw_payload_sha256: str
    extraction_version: str
    verification_status: str
```

```python
# nexus/domain/models/patent.py
from pydantic import BaseModel, Field
from .evidence import FieldObservation


class PatentDocument(BaseModel):
    """Publication-level patent document representing a specific gazette publication."""
    publication_id: str
    country_code: str
    doc_number: str
    kind_code: str
    application_number: str | None = None
    title: str
    abstract: str
    assignees: list[str] = Field(default_factory=list)
    inventors: list[str] = Field(default_factory=list)
    filing_date: str | None = None
    publication_date: str | None = None
    priority_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    classifications_ipc: list[str] = Field(default_factory=list)
    forward_citation_count: int | None = None
    backward_citation_count: int | None = None
    family_id: str | None = None
    observations: list[FieldObservation] = Field(default_factory=list)


class PatentFamily(BaseModel):
    """Metadata for a family of related patent documents sharing priority claims."""
    family_id: str
    earliest_priority_date: str | None = None
    title_consensus: str | None = None
    family_cpc_codes: list[str] = Field(default_factory=list)


class FamilyMembership(BaseModel):
    """Relational mapping linking a publication document to its family."""
    family_id: str
    publication_id: str
    membership_source: str
    evidence: FieldObservation
```

```python
# nexus/domain/models/demand.py
from pydantic import BaseModel, Field
from .evidence import FieldObservation


class DemandSignal(BaseModel):
    """Market-pull requirement extracted from industrial open innovation calls."""
    demand_id: str
    source_network: str
    title: str
    description: str
    technical_requirements: list[str] = Field(default_factory=list)
    origin_country: str | None = None
    posted_date: str | None = None
    deadline_date: str | None = None
    classified_cpc_prefixes: list[str] = Field(default_factory=list)
    observations: list[FieldObservation] = Field(default_factory=list)
```

```python
# nexus/domain/models/snapshot.py
from datetime import datetime
from pydantic import BaseModel, Field


class DatasetSnapshot(BaseModel):
    """Content-addressed snapshot representing a frozen, immutable analytical corpus."""
    dataset_id: str
    schema_version: str
    source_batches: list[str] = Field(default_factory=list)
    record_count: int
    content_sha256: str
    manifest_sha256: str
    created_at: datetime
    transformation_version: str
    provenance_manifest_uri: str
```

```python
# nexus/domain/models/opportunity.py
from pydantic import BaseModel, Field


class OpportunityScore(BaseModel):
    """Deterministic quantitative measurement of innovation gaps and saturation."""
    cluster_id: str
    score: float | None
    score_coverage: float
    components: dict[str, float | None]
    missing_components: list[str] = Field(default_factory=list)
    model_id: str
    model_version: str
    quadrant: str


class OpportunityHypothesis(BaseModel):
    """Qualitative research interpretation and candidate innovation opportunity."""
    hypothesis_id: str
    cluster_id: str
    opportunity_score: OpportunityScore
    rationale: str
    supporting_prior_art: list[str] = Field(default_factory=list)
    target_demand_ids: list[str] = Field(default_factory=list)
    status: str
```

```python
# nexus/domain/protocols/storage.py
from typing import Protocol, Iterator, Any
from pathlib import Path


class RawStoreProtocol(Protocol):
    def store_payload(self, source_id: str, payload_bytes: bytes, metadata: dict[str, Any], file_ext: str = "json") -> tuple[Path, str]:
        ...
    def get_payload(self, sha256_hash: str) -> bytes:
        ...


class CanonicalStoreProtocol(Protocol):
    def write_documents(self, dataset_id: str, documents: list[Any]) -> tuple[Path, str]:
        ...


class QueryEngineProtocol(Protocol):
    def execute_query(self, sql: str, params: list[Any] | None = None) -> Any:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/test_domain_models.py -v`  
Expected: PASS (3/3 passed)

- [ ] **Step 5: Commit**

```bash
git add nexus/domain/ tests/unit/domain/
git commit -m "feat(domain): define core clean architecture entities, protocols, and field observations"
```

---

### Task 2: Immutable Raw Storage Layer

**Files:**
- Create: `nexus/infrastructure/storage/raw_store.py`
- Test: `tests/unit/infrastructure/test_raw_store.py`

**Interfaces:**
- Implements: `RawStoreProtocol`
- Produces: `RawStore.store_payload(source_id, payload_bytes, metadata, file_ext) -> (Path, sha256_hash)`

- [ ] **Step 1: Write failing test for RawStore**

```python
# tests/unit/infrastructure/test_raw_store.py
import json
from pathlib import Path
from nexus.infrastructure.storage.raw_store import FilesystemRawStore


def test_raw_store_payload_immutability(tmp_path):
    store = FilesystemRawStore(base_dir=tmp_path / "raw_store")
    payload = json.dumps({"publications": [{"id": "ES-001"}]}).encode("utf-8")
    meta = {"source_url": "https://example.com/api", "retrieval_date": "2026-09-02"}

    saved_path, sha_hash = store.store_payload(
        source_id="oepm_bopi",
        payload_bytes=payload,
        metadata=meta,
        file_ext="json"
    )

    assert saved_path.exists()
    assert len(sha_hash) == 64
    assert store.get_payload(sha_hash) == payload

    # Meta file sidecar exists
    meta_path = saved_path.with_suffix(".meta.json")
    assert meta_path.exists()
    assert json.loads(meta_path.read_text())["source_url"] == "https://example.com/api"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/test_raw_store.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus.infrastructure.storage.raw_store'`

- [ ] **Step 3: Implement FilesystemRawStore**

```python
# nexus/infrastructure/storage/raw_store.py
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any


class FilesystemRawStore:
    """Immutable two-tier raw storage writing untouched bytes with cryptographic sidecars."""

    def __init__(self, base_dir: Path | str = "data/sources"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_payload(
        self,
        source_id: str,
        payload_bytes: bytes,
        metadata: dict[str, Any],
        file_ext: str = "json"
    ) -> tuple[Path, str]:
        """Store immutable raw payload with computed SHA-256 hash and metadata sidecar."""
        hasher = hashlib.sha256(payload_bytes)
        sha_hash = hasher.hexdigest()

        date_str = datetime.now().strftime("%Y-%m-%d")
        target_dir = self.base_dir / source_id / date_str
        target_dir.mkdir(parents=True, exist_ok=True)

        payload_path = target_dir / f"{sha_hash[:16]}.raw.{file_ext}"
        meta_path = payload_path.with_suffix(".meta.json")

        if not payload_path.exists():
            payload_path.write_bytes(payload_bytes)

        full_meta = {
            "source_id": source_id,
            "sha256_hash": sha_hash,
            "stored_at": datetime.now().isoformat(),
            "file_size_bytes": len(payload_bytes),
            **metadata
        }
        meta_path.write_text(json.dumps(full_meta, indent=2, ensure_ascii=False), encoding="utf-8")

        return payload_path, sha_hash

    def get_payload(self, sha256_hash: str) -> bytes:
        """Retrieve raw payload bytes by matching SHA-256 hash across stored files."""
        for path in self.base_dir.glob(f"**/{sha256_hash[:16]}.raw.*"):
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() == sha256_hash:
                return content
        raise FileNotFoundError(f"Raw payload with SHA-256 {sha256_hash} not found in {self.base_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/test_raw_store.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/storage/raw_store.py tests/unit/infrastructure/test_raw_store.py
git commit -m "feat(storage): implement immutable FilesystemRawStore with SHA-256 metadata sidecars"
```

---

### Task 3: Canonical Parquet Storage & Ingestion Pipeline

**Files:**
- Create: `nexus/infrastructure/storage/parquet_store.py`
- Create: `nexus/application/ingestion/pipeline.py`
- Test: `tests/unit/application/test_ingestion_pipeline.py`

**Interfaces:**
- Consumes: `RawStoreProtocol`, `PatentDocument`
- Produces: `ParquetCanonicalStore.write_documents(dataset_id, documents) -> (Path, sha256_hash)`
- Produces: `IngestionPipeline.ingest_source(source, dataset_id) -> (DatasetSnapshot, list[PatentDocument])`

- [ ] **Step 1: Write failing test for IngestionPipeline & ParquetStore**

```python
# tests/unit/application/test_ingestion_pipeline.py
import pytest
import pyarrow.parquet as pq
from datetime import datetime
from nexus.domain.models.patent import PatentDocument
from nexus.infrastructure.storage.raw_store import FilesystemRawStore
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.application.ingestion.pipeline import IngestionPipeline


class DummyPatentSource:
    def fetch_raw_batch(self):
        raw_bytes = b'{"records": [{"pub": "ES-001", "title": "Invention A", "pd": "2021-05-10"}]}'
        meta = {"endpoint": "https://dummy.api/patents"}
        return raw_bytes, meta

    def normalize(self, raw_bytes, raw_sha):
        return [
            PatentDocument(
                publication_id="ES-001",
                country_code="ES",
                doc_number="001",
                kind_code="A1",
                title="Invention A",
                abstract="Sample abstract",
                publication_date="2021-05-10",
                forward_citation_count=None,
                backward_citation_count=5
            )
        ]


def test_ingestion_pipeline_end_to_end(tmp_path):
    raw_store = FilesystemRawStore(base_dir=tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store)

    source = DummyPatentSource()
    snapshot, docs = pipeline.ingest_patent_source(
        source=source,
        source_id="dummy_oepm",
        dataset_id="patents_test_v1"
    )

    assert len(docs) == 1
    assert snapshot.record_count == 1
    assert len(snapshot.content_sha256) == 64
    assert Path(snapshot.provenance_manifest_uri).exists()

    # Read back parquet directly to verify schema and null preservation
    table = pq.read_table(tmp_path / "canonical" / "patents_test_v1" / "corpus.parquet")
    assert table.num_rows == 1
    assert table.column("publication_id")[0].as_py() == "ES-001"
    assert table.column("forward_citation_count")[0].as_py() is None
    assert table.column("backward_citation_count")[0].as_py() == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_ingestion_pipeline.py -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement ParquetCanonicalStore & IngestionPipeline**

```python
# nexus/infrastructure/storage/parquet_store.py
import hashlib
from pathlib import Path
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq
from nexus.domain.models.patent import PatentDocument


class ParquetCanonicalStore:
    """Writes domain document batches directly into typed, columnar Apache Parquet datasets."""

    def __init__(self, base_dir: Path | str = "data/canonical"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_documents(self, dataset_id: str, documents: list[PatentDocument]) -> tuple[Path, str]:
        target_dir = self.base_dir / dataset_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_parquet = target_dir / "corpus.parquet"

        # Construct PyArrow Table preserving explicit typing and nulls
        data = {
            "publication_id": [d.publication_id for d in documents],
            "country_code": [d.country_code for d in documents],
            "doc_number": [d.doc_number for d in documents],
            "kind_code": [d.kind_code for d in documents],
            "application_number": [d.application_number for d in documents],
            "title": [d.title for d in documents],
            "abstract": [d.abstract for d in documents],
            "assignees": [d.assignees for d in documents],
            "inventors": [d.inventors for d in documents],
            "filing_date": [d.filing_date for d in documents],
            "publication_date": [d.publication_date for d in documents],
            "priority_date": [d.priority_date for d in documents],
            "classifications_cpc": [d.classifications_cpc for d in documents],
            "classifications_ipc": [d.classifications_ipc for d in documents],
            "forward_citation_count": pa.array([d.forward_citation_count for d in documents], type=pa.int64()),
            "backward_citation_count": pa.array([d.backward_citation_count for d in documents], type=pa.int64()),
            "family_id": [d.family_id for d in documents],
        }

        table = pa.Table.from_pydict(data)
        pq.write_table(table, str(target_parquet), compression="SNAPPY")

        # Deterministic SHA-256 over raw parquet chunk bytes
        hasher = hashlib.sha256()
        with open(target_parquet, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        content_sha = hasher.hexdigest()

        return target_parquet, content_sha
```

```python
# nexus/application/ingestion/pipeline.py
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from nexus.domain.models.snapshot import DatasetSnapshot
from nexus.infrastructure.storage.raw_store import FilesystemRawStore
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore


class IngestionPipeline:
    def __init__(self, raw_store: FilesystemRawStore, canonical_store: ParquetCanonicalStore):
        self.raw_store = raw_store
        self.canonical_store = canonical_store

    def ingest_patent_source(
        self,
        source: Any,
        source_id: str,
        dataset_id: str,
        transformation_version: str = "1.0.0"
    ) -> tuple[DatasetSnapshot, list[Any]]:
        raw_bytes, metadata = source.fetch_raw_batch()
        raw_path, raw_sha = self.raw_store.store_payload(
            source_id=source_id,
            payload_bytes=raw_bytes,
            metadata=metadata
        )

        documents = source.normalize(raw_bytes, raw_sha)
        parquet_path, content_sha = self.canonical_store.write_documents(
            dataset_id=dataset_id,
            documents=documents
        )

        manifest_path = parquet_path.parent / "manifest.json"
        manifest_data = {
            "dataset_id": dataset_id,
            "schema_version": "2.2.0",
            "source_batches": [str(raw_path)],
            "raw_payload_sha256": raw_sha,
            "record_count": len(documents),
            "content_sha256": content_sha,
            "created_at": datetime.now().isoformat(),
            "transformation_version": transformation_version,
            "canonical_parquet": str(parquet_path)
        }
        manifest_bytes = json.dumps(manifest_data, indent=2, ensure_ascii=False).encode("utf-8")
        manifest_path.write_bytes(manifest_bytes)
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()

        snapshot = DatasetSnapshot(
            dataset_id=dataset_id,
            schema_version="2.2.0",
            source_batches=[str(raw_path)],
            record_count=len(documents),
            content_sha256=content_sha,
            manifest_sha256=manifest_sha,
            created_at=datetime.now(),
            transformation_version=transformation_version,
            provenance_manifest_uri=str(manifest_path)
        )
        return snapshot, documents
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_ingestion_pipeline.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/storage/parquet_store.py nexus/application/ingestion/pipeline.py tests/unit/application/test_ingestion_pipeline.py
git commit -m "feat(ingestion): implement streaming ParquetCanonicalStore and IngestionPipeline"
```

---

### Task 4: Ephemeral DuckDB Analytical Query Engine

**Files:**
- Create: `nexus/infrastructure/storage/duckdb_engine.py`
- Test: `tests/unit/infrastructure/test_duckdb_engine.py`

**Interfaces:**
- Implements: `QueryEngineProtocol`
- Produces: `DuckDbQueryEngine.from_snapshot(snapshot_manifest_path) -> DuckDbQueryEngine`
- Produces: `DuckDbQueryEngine.search_by_cpc(cpc_prefix, limit) -> pa.Table / list[dict]`

- [ ] **Step 1: Write failing test for DuckDbQueryEngine**

```python
# tests/unit/infrastructure/test_duckdb_engine.py
import pytest
from pathlib import Path
from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.domain.models.patent import PatentDocument


def test_duckdb_query_engine_ephemeral_parquet_query(tmp_path):
    canonical = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    doc1 = PatentDocument(
        publication_id="ES-001",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Detergent cleaner",
        abstract="Detergent composition",
        classifications_cpc=["C11D1/00"],
        forward_citation_count=8,
        backward_citation_count=12
    )
    doc2 = PatentDocument(
        publication_id="ES-002",
        country_code="ES",
        doc_number="002",
        kind_code="B1",
        title="Sanitary sink",
        abstract="Kitchen sink",
        classifications_cpc=["E03C1/00"],
        forward_citation_count=None,
        backward_citation_count=4
    )
    p_path, sha = canonical.write_documents("patents_test", [doc1, doc2])

    engine = DuckDbQueryEngine.from_parquet(p_path)
    res = engine.search_by_cpc_prefix("C11D")

    assert len(res) == 1
    assert res[0]["publication_id"] == "ES-001"
    assert res[0]["forward_citation_count"] == 8

    # Verify cluster aggregation without python object instantiation
    stats = engine.get_cluster_aggregates("C11D", ref_year=2026)
    assert stats["patent_count"] == 1
    assert stats["observed_citations_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/test_duckdb_engine.py -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement DuckDbQueryEngine**

```python
# nexus/infrastructure/storage/duckdb_engine.py
from pathlib import Path
from typing import Any
import duckdb


class DuckDbQueryEngine:
    """In-memory DuckDB analytical engine querying Parquet snapshots directly via SQL."""

    def __init__(self, parquet_path: Path | str):
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet dataset missing at {self.parquet_path}")

        self.conn = duckdb.connect(":memory:")
        self.conn.execute("""
            CREATE TABLE patents AS SELECT * FROM read_parquet(?)
        """, [str(self.parquet_path)])

    @classmethod
    def from_parquet(cls, parquet_path: Path | str) -> "DuckDbQueryEngine":
        return cls(parquet_path=parquet_path)

    def search_by_cpc_prefix(self, cpc_prefix: str, limit: int = 1000) -> list[dict[str, Any]]:
        query = """
            SELECT * FROM patents
            WHERE EXISTS (
                SELECT 1 FROM unnest(classifications_cpc) AS t(c)
                WHERE t.c LIKE ?
            )
            ORDER BY COALESCE(forward_citation_count, 0) DESC
            LIMIT ?
        """
        df = self.conn.execute(query, [f"{cpc_prefix}%", limit]).df()
        return df.to_dict(orient="records")

    def get_cluster_aggregates(self, cpc_prefix: str, ref_year: int = 2026) -> dict[str, Any]:
        query = """
            SELECT 
                count(*) as patent_count,
                count(forward_citation_count) as observed_citations_count,
                avg(COALESCE(forward_citation_count, 0)) as avg_citations
            FROM patents
            WHERE EXISTS (
                SELECT 1 FROM unnest(classifications_cpc) AS t(c)
                WHERE t.c LIKE ?
            )
        """
        row = self.conn.execute(query, [f"{cpc_prefix}%"]).fetchone()
        return {
            "patent_count": row[0] if row else 0,
            "observed_citations_count": row[1] if row else 0,
            "avg_citations": float(row[2]) if row and row[2] is not None else 0.0
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/test_duckdb_engine.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/storage/duckdb_engine.py tests/unit/infrastructure/test_duckdb_engine.py
git commit -m "feat(storage): implement in-memory DuckDbQueryEngine over canonical Parquet datasets"
```

---

### Task 5: Concrete Ingestor Adapters (OEPM Open Data & EPO OPS Client)

**Files:**
- Create: `nexus/infrastructure/sources/patent/oepm_bopi.py`
- Create: `nexus/infrastructure/sources/patent/epo_ops.py`
- Test: `tests/unit/infrastructure/test_sources.py`

**Interfaces:**
- Produces: `OepmBopiSource.fetch_raw_batch() -> (bytes, dict)`
- Produces: `OepmBopiSource.normalize(raw_bytes, raw_sha) -> list[PatentDocument]`
- Produces: `EpoOpsSource.fetch_raw_batch(cql_query) -> (bytes, dict)`
- Produces: `EpoOpsSource.normalize(raw_bytes, raw_sha) -> list[PatentDocument]`

- [ ] **Step 1: Write failing test for OEPM & EPO OPS sources**

```python
# tests/unit/infrastructure/test_sources.py
import pytest
from pathlib import Path
from nexus.infrastructure.sources.patent.oepm_bopi import OepmBopiSource


def test_oepm_bopi_source_normalization():
    source = OepmBopiSource(file_path="data/raw/oepm_open_data_es.json")
    raw_bytes, meta = source.fetch_raw_batch()
    docs = source.normalize(raw_bytes, "mock_sha")

    assert len(docs) == 16
    for d in docs:
        assert d.country_code == "ES"
        assert len(d.observations) > 0
        assert d.publication_id.startswith("ES-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/test_sources.py -v`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement OepmBopiSource with explicit FieldObservation tracking**

```python
# nexus/infrastructure/sources/patent/oepm_bopi.py
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from nexus.domain.models.patent import PatentDocument
from nexus.domain.models.evidence import FieldObservation


class OepmBopiSource:
    def __init__(self, file_path: str = "data/raw/oepm_open_data_es.json"):
        self.file_path = Path(file_path)

    def fetch_raw_batch(self) -> tuple[bytes, dict[str, Any]]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"OEPM source file not found at {self.file_path}")
        raw_bytes = self.file_path.read_bytes()
        meta = {
            "source_authority": "Oficina Española de Patentes y Marcas (OEPM / BOPI)",
            "official_catalog_url": "https://datos.gob.es/es/catalogo/e05024401-patentes-solicitadas-y-concedidas-bopi",
            "source_file": str(self.file_path)
        }
        return raw_bytes, meta

    def normalize(self, raw_bytes: bytes, raw_sha: str) -> list[PatentDocument]:
        data = json.loads(raw_bytes.decode("utf-8"))
        pubs = data.get("publications", [])
        documents = []

        for p in pubs:
            pub_id = p["publication_number"]
            invenes_url = p.get("invenes_url", f"https://consultas2.oepm.es/InvenesWeb/detalle?tipo=PAT&ref={p.get('application_number', '')}")

            obs = [
                FieldObservation(
                    entity_id=pub_id,
                    field_name="title",
                    observed_value_json=json.dumps(p["title"]),
                    value_type="str",
                    source_authority="OEPM BOPI",
                    source_uri=invenes_url,
                    retrieval_timestamp=datetime(2026, 8, 25, 11, 8, 53),
                    raw_payload_sha256=raw_sha,
                    extraction_version="1.0.0",
                    verification_status=p.get("verification_status", "authority_verified")
                )
            ]

            assignees = [p["assignee"]] if isinstance(p["assignee"], str) else p["assignee"]
            inventors = p.get("inventors", [])

            doc = PatentDocument(
                publication_id=pub_id,
                country_code=p.get("country_code", "ES"),
                doc_number=pub_id.split("-")[1] if "-" in pub_id else pub_id,
                kind_code=pub_id.split("-")[2] if len(pub_id.split("-")) > 2 else "B2",
                application_number=p.get("application_number"),
                title=p["title"],
                abstract=p["abstract"],
                assignees=assignees,
                inventors=inventors,
                filing_date=p.get("filing_date"),
                publication_date=p.get("publication_date"),
                classifications_cpc=p.get("cpc_codes", []),
                forward_citation_count=p.get("citation_count"),
                backward_citation_count=p.get("backward_citation_count"),
                observations=obs
            )
            documents.append(doc)

        return documents
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/test_sources.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nexus/infrastructure/sources/ tests/unit/infrastructure/test_sources.py
git commit -m "feat(sources): implement OepmBopiSource adapter with fine-grained FieldObservation tracking"
```

---

### Task 6: Invariant-Driven Verification & Pipeline Validation

**Files:**
- Create: `tests/integration/test_data_platform_lifecycle.py`
- Test: Full end-to-end integration test of RawStore -> Normalizer -> CanonicalStore -> Parquet -> DatasetSnapshot -> DuckDbQueryEngine.

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_data_platform_lifecycle.py
import pytest
from pathlib import Path
from nexus.infrastructure.sources.patent.oepm_bopi import OepmBopiSource
from nexus.infrastructure.storage.raw_store import FilesystemRawStore
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine
from nexus.application.ingestion.pipeline import IngestionPipeline


def test_full_data_platform_lifecycle(tmp_path):
    raw_store = FilesystemRawStore(base_dir=tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store)

    source = OepmBopiSource(file_path="data/raw/oepm_open_data_es.json")
    snapshot, docs = pipeline.ingest_patent_source(
        source=source,
        source_id="oepm_bopi",
        dataset_id="patents_es_v1"
    )

    assert snapshot.record_count == 16
    assert len(snapshot.content_sha256) == 64

    # Query directly in-memory via DuckDbQueryEngine
    engine = DuckDbQueryEngine.from_parquet(snapshot.provenance_manifest_uri.replace("manifest.json", "corpus.parquet"))
    c11d_pats = engine.search_by_cpc_prefix("C11D")

    assert len(c11d_pats) == 3
    pub_ids = [p["publication_id"] for p in c11d_pats]
    assert "ES-2849102-B2" in pub_ids
    assert "ES-2715482-B2" in pub_ids
    assert "ES-2634129-B1" in pub_ids
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_data_platform_lifecycle.py -v`  
Expected: PASS

- [ ] **Step 3: Run full pytest suite across whole codebase**

Run: `pytest tests/ backend/tests/ -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_data_platform_lifecycle.py
git commit -m "test(integration): verify complete Data Platform lifecycle from raw source to DuckDB query"
```
