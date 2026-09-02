# Nexus Innovation Intelligence Engine: Clean Architecture & Research Infrastructure Design

**Document Version:** 2.3.0 (Scientific Invariants & Streaming Data Platform)  
**Date:** 2026-09-02  
**Status:** Approved for Implementation  
**Target:** Sovereign Modular Monolith Clean Architecture for Innovation Analytics & Scientific Research

---

## 1. Executive Summary & Design Vision

### 1.1 Product vs. Experiment Separation

The fundamental premise of Nexus 2.0 is the complete decoupling between the **Product Core** (the generalizable Innovation Intelligence Engine) and individual **Research Experiments** (case studies, empirical evaluations, and paper benchmarks).

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         NEXUS INNOVATION INTELLIGENCE ENGINE                     │
│                                                                                  │
│   ┌───────────────────────────┐      ┌───────────────────────────┐               │
│   │       DOMINIO CORE        │      │       DATA PLATFORM       │               │
│   │ PatentDocument, Family,   │      │ Raw Store (Immutable)     │               │
│   │ DemandSignal, Evidence,   │◄─────┤ Canonical Parquet Datasets│               │
│   │ DatasetSnapshot           │      │ In-Memory DuckDB Views    │               │
│   └─────────────┬─────────────┘      └───────────────────────────┘               │
│                 │                                                                │
│                 ▼                                                                │
│   ┌───────────────────────────┐      ┌───────────────────────────┐               │
│   │    OPPORTUNITY ENGINE     │      │     AGENTIC SYNTHESIS     │               │
│   │ Pluggable Models & Math   │─────►│ Propose-Critique Loop     │               │
│   │ Sensitivity Analyzer      │      │ Grounded Evidence Defense │               │
│   └─────────────┬─────────────┘      └───────────────────────────┘               │
└─────────────────┼────────────────────────────────────────────────────────────────┘
                  │ consumes via clean API
                  ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          RESEARCH & EXPERIMENTS LAYER                            │
│                                                                                  │
│   experiments/                                                                   │
│   └── innoget_es_2026/          experiments/another_benchmark/                   │
│       ├── config.yaml               ├── config.yaml                              │
│       ├── hypothesis.md             └── ...                                      │
│       ├── manifest.json                                                          │
│       └── run.py                                                                 │
└──────────────────────────────────────────────────────────────────────────────────┘
```

The product does not know about Spain, Innoget, or specific CPC codes. Instead:
* **The Product** provides general domain abstractions, ingestion pipelines, canonical storage, opportunity scoring algorithms, and agentic workflows.
* **The Experiment** provides configuration parameters, dataset bindings, scientific hypotheses, and generates publication artifacts.

---

## 2. Technology Stack & Operational Resource Principles

### 2.1 Pragmatic Clean Stack

| Layer | Technology | Rationale & Architectural Scope |
|---|---|---|
| **Runtime & Language** | **Python 3.12+** | Type hinting, structural pattern matching, robust async I/O. |
| **Domain Contracts & Validation** | **Pydantic v2** | Minimal external dependency; Pydantic v2 serves as the sole standard contract and boundary validation dependency. |
| **HTTP Client & API Adapters** | **httpx** | Resilient connection pooling, retry handling, async streaming. |
| **Raw Ingestion Store** | **Filesystem / S3 Adapter** | Immutable storage of raw HTTP responses, XML payloads, and API metadata. |
| **Canonical Data Storage** | **Apache Parquet + PyArrow** | Columnar, compressed, typed, content-addressed dataset files. |
| **Vectorized Analytics Engine** | **DuckDB** | In-memory (`:memory:`) SQL analytics directly over Parquet views without duplicating data in RAM. |
| **CLI Framework** | **Typer / Argparse** | Type-annotated command line interface for data ops and experiments. |
| **LLM Inference Provider** | **Groq API** (`httpx`) | Fast inference via OpenAI-compatible API format (CPU VPS friendly). |
| **Experiment Configuration** | **YAML + Pydantic** | Declarative research configurations validated against Pydantic schemas. |
| **Scientific Testing & Verification** | **pytest + Hypothesis** | Invariant-driven testing, property-based verification, clean-clone A/B determinism. |

### 2.2 Operational Efficiency on Sovereign VPS

To ensure low operational cost and deterministic execution on standard compute (e.g. 2 vCPU, 4GB RAM VPS):
1. **Zero Unnecessary Daemons:** No PostgreSQL, Redis, Kafka, Elasticsearch, or Spark dependencies.
2. **Streaming Batch Processing:** Ingestion proceeds via `Iterator[RawPayload] -> normalize_stream -> validate_batch -> write_parquet_chunk -> release_memory -> next_batch` rather than accumulating millions of records in memory.
3. **No Python Instance Explosion & Zero Memory Duplication:** Analytics queries run in DuckDB C++ vectorized kernels over Parquet via `CREATE VIEW patents AS SELECT * FROM read_parquet(...)`. Pydantic domain models are instantiated strictly at boundary interfaces where domain validation is required.

---

## 3. Modular Monolith Directory Structure

```text
nexus/
├── domain/                          # Domain contracts & entity models (Pydantic standard)
│   ├── models/
│   │   ├── patent.py                # PatentDocument, PatentFamily, FamilyMembership, CitationLink
│   │   ├── demand.py                # DemandSignal, DemandRequirement
│   │   ├── evidence.py              # FieldObservation, SourceProvenance, VerificationStatus (Enum)
│   │   ├── snapshot.py              # DatasetSnapshot, RawBatch, PartManifest, SnapshotManifest
│   │   └── opportunity.py           # OpportunityScore, OpportunityHypothesis, QuadrantClassification
│   └── protocols/
│       ├── sources.py               # PatentSourceProtocol, DemandSourceProtocol, RawPayload
│       ├── classifiers.py           # ClassificationProtocol
│       ├── storage.py               # RawStoreProtocol, CanonicalStoreProtocol, QueryEngineProtocol
│       ├── models.py                # OpportunityModelProtocol
│       └── sensitivity.py           # SensitivityAnalyzerProtocol
│
├── application/                     # Use cases and orchestration workflows
│   ├── ingestion/
│   │   ├── normalizers/             # Decoupled transformation logic
│   │   │   ├── base.py              # PatentNormalizerProtocol
│   │   │   ├── oepm_normalizer.py   # OEPM JSON -> PatentDocument stream
│   │   │   └── epo_normalizer.py    # EPO XML -> PatentDocument stream
│   │   ├── validator.py             # PatentValidator (Strict rejection of synthetic defaults)
│   │   ├── pipeline.py              # Streaming IngestionPipeline (Batched I/O)
│   │   └── dataset_freezer.py       # Deterministic Parquet & Merkle content-hashing
│   ├── landscape/
│   │   └── clusterer.py             # Patent and demand grouping by classification taxonomy
│   ├── opportunity/
│   │   ├── service.py               # OpportunityService (Evaluates models against landscape)
│   │   └── sensitivity.py           # Mathematical sensitivity & rank-perturbation engine
│   └── synthesis/
│       └── agent_loop.py            # Two-stage multi-agent propose-critique coordinator
│
├── infrastructure/                  # External adapters, I/O, storage, and API clients
│   ├── sources/
│   │   ├── patent/
│   │   │   ├── epo_ops_client.py    # EPO OPS 3.2 REST client returning raw XML bytes
│   │   │   └── oepm_raw_source.py   # OEPM open data source returning raw JSON bytes
│   │   └── demand/
│   │       └── innoget_source.py    # Innoget demand source adapter
│   ├── storage/
│   │   ├── raw_store.py             # Immutable filesystem raw payload store
│   │   ├── parquet_store.py         # Relational Parquet store (patents, observations, memberships)
│   │   └── duckdb_engine.py         # DuckDB engine creating views over Parquet
│   ├── classifiers/
│   │   └── cpc_taxonomy.py          # Deterministic CPC regex and concordance classifier
│   └── llm/
│       ├── groq_client.py           # OpenAI-compatible Groq API client
│       └── prompts.py               # Versioned system prompts for synthesis & critique
│
├── interfaces/                      # Entrypoints for users and external consumers
│   └── cli/
│       ├── main.py                  # Nexus unified CLI (`nexus ingest`, `nexus analyze`, `nexus experiment`)
│       └── formatters.py            # Markdown and terminal table formatters
│
├── experiments/                     # Research experiment configurations and reports
│   └── innoget_es_2026/
│       ├── config.yaml              # Declarative experiment parameters
│       ├── hypothesis.md            # Scientific research hypotheses (H1, H2, H3, H4)
│       ├── dataset_manifest.json    # Cryptographic snapshot binding
│       ├── run.py                   # Lightweight experiment runner script
│       └── results/                 # Exported empirical metrics, sensitivity tables, and paper summaries
│
└── tests/                           # 3-Tier Testing Pyramid with Scientific Invariant Gates
    ├── unit/
    │   ├── domain/
    │   └── application/ingestion/
    ├── integration/
    │   ├── infrastructure/storage/
    │   ├── infrastructure/sources/
    │   └── data_platform/
    └── e2e/
```

---

## 4. Data Platform & Ingestion Lifecycle

### 4.1 Immutable Two-Tier Storage Architecture

```text
[External Authority API / Local Archive]
               │
               ▼
1. RAW STORE (`data/sources/<source_id>/<YYYY-MM-DD>/<sha256[:16]>.raw.<ext>`)
   - Unmodified HTTP response bytes / raw XML / raw JSON
   - Query metadata sidecar (`.meta.json`) with strict 64-char hex SHA-256
   - Immutable content-addressed storage
               │
               ▼
2. STREAMING NORMALIZER & VALIDATOR (`nexus.application.ingestion`)
   - `PatentSource` yields `RawPayload(bytes, metadata)`
   - `PatentNormalizer` yields `Iterator[PatentDocument]` and `Iterator[FieldObservation]`
   - `PatentValidator` validates records in batches; missing dates/citations remain `None`
   - Zero synthetic fallbacks (no defaulting to `2020-01-01` or `G06Q`)
               │
               ▼
3. RELATIONAL CANONICAL PARQUET STORE (`data/canonical/<dataset_id>/`)
   - `patents/part-0000.parquet`: Primary publication attributes
   - `observations/part-0000.parquet`: Normalized field-level provenance records
   - `family_memberships/part-0000.parquet`: Cross-jurisdictional family links
   - Deterministic Dataset Content Hash:
     $$\text{file\_sha256} = \text{SHA256}(\text{bytes of each part})$$
     $$\text{dataset\_content\_sha256} = \text{SHA256}(\text{canonical JSON of sorted parts: } (\text{part\_name}, \text{row\_count}, \text{file\_sha256}))$$
               │
               ▼
4. ANALYTICAL QUERY ENGINE (`nexus.infrastructure.storage.duckdb_engine`)
   - Ephemeral in-memory DuckDB instance (`:memory:`)
   - Creates zero-copy views: `CREATE VIEW patents AS SELECT * FROM read_parquet(...)`
   - Direct SQL/vectorized operations; zero duplicate RAM allocations
```

---

## 5. Domain Models & Contracts

### 5.1 `VerificationStatus` & `FieldObservation`
```python
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re

class VerificationStatus(str, Enum):
    SOURCE_REPORTED = "source_reported"           # Extracted directly from primary source response
    INDEPENDENTLY_VERIFIED = "independently_verified" # Cross-checked against external registry
    DERIVED = "derived"                           # Computed / normalized by an algorithm
    UNAVAILABLE = "unavailable"                   # Not reported in source

class FieldObservation(BaseModel):
    """Fine-grained provenance record tracking the origin and authority of a specific field observation."""
    entity_id: str
    field_name: str
    observed_value_json: str          # Deterministically serialized JSON string of the observed value
    value_type: str                   # e.g. "str", "int", "list[str]"
    source_authority: str             # e.g. "OEPM BOPI", "EPO OPS"
    source_uri: str                   # Direct archive / query URL
    retrieval_timestamp: datetime
    raw_payload_sha256: str           # Must match exact 64-char lowercase hex
    extraction_version: str
    verification_status: VerificationStatus

    @field_validator("raw_payload_sha256")
    @classmethod
    def validate_sha256_format(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v
```

### 5.2 `PatentDocument`, `PatentFamily` & `FamilyMembership`
```python
class PatentDocument(BaseModel):
    """Publication-level patent document representing a specific gazette publication."""
    publication_id: str               # Canonical ID: e.g. "ES-2849102-B2"
    country_code: str                 # e.g. "ES", "EP", "US"
    doc_number: str                   # e.g. "2849102"
    kind_code: str                    # e.g. "B2", "A1"
    application_number: str | None = None
    title: str
    abstract: str
    assignees: list[str] = Field(default_factory=list)
    inventors: list[str] = Field(default_factory=list)
    filing_date: str | None = None    # YYYY-MM-DD or None
    publication_date: str | None = None # YYYY-MM-DD or None
    priority_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    classifications_ipc: list[str] = Field(default_factory=list)
    forward_citation_count: int | None = None    # None = unobserved; int >= 0 = verified count
    backward_citation_count: int | None = None   # None = unobserved; int >= 0 = verified count
    family_id: str | None = None

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
    membership_source: str            # e.g., "EPO DOCDB", "INPADOC"
    evidence: FieldObservation
```

### 5.3 `DatasetSnapshot` & `RawBatch`
```python
class RawBatch(BaseModel):
    """Stable, machine-independent identity of an ingested raw batch."""
    batch_id: str
    source_id: str
    retrieval_timestamp: datetime
    payload_sha256: str

class DatasetPart(BaseModel):
    """Metadata for an individual Parquet partition chunk."""
    part_name: str
    row_count: int
    file_sha256: str

class DatasetSnapshot(BaseModel):
    """Content-addressed snapshot representing a frozen, immutable analytical corpus."""
    dataset_id: str
    schema_version: str
    source_batches: list[RawBatch]
    record_count: int
    parts: list[DatasetPart]
    dataset_content_sha256: str
    manifest_sha256: str
    created_at: datetime
    transformation_version: str
```

### 5.4 `OpportunityScore` vs. `OpportunityHypothesis`
```python
class OpportunityScore(BaseModel):
    """Deterministic quantitative measurement of innovation gaps and saturation."""
    cluster_id: str
    score: float | None               # None if required signals are unobserved under strict mode
    score_coverage: float             # Ratio of observed signal weight [0.0, 1.0]
    components: dict[str, float | None] # {"density": d_i, "recency": r_i, "traction": T_i, "demand": q_i}
    missing_components: list[str]     # e.g. ["traction"] when forward citations are unobserved
    model_id: str
    model_version: str
    quadrant: str

class OpportunityHypothesis(BaseModel):
    """Qualitative research interpretation and candidate innovation opportunity."""
    hypothesis_id: str
    cluster_id: str
    opportunity_score: OpportunityScore
    rationale: str
    supporting_prior_art: list[str]   # Cited verified publication IDs
    target_demand_ids: list[str]
    status: str                       # "validated", "rejected", "exploratory"
```

---

## 6. Pluggable Opportunity & Sensitivity Architecture

### 6.1 Decoupled Protocol Interfaces
```python
class OpportunityModelProtocol(Protocol):
    """Protocol for calculating innovation gap and white-space metrics across clusters."""
    def compute_opportunity(
        self,
        cluster_id: str,
        patents: list[PatentDocument],
        demands: list[DemandSignal],
        context: LandscapeContext,
        strict_mode: bool = False
    ) -> OpportunityScore:
        ...

class SensitivityAnalyzerProtocol(Protocol):
    """Protocol for evaluating mathematical model robustness and ranking stability."""
    def evaluate_stability(
        self,
        model: OpportunityModelProtocol,
        clusters: list[str],
        landscape: LandscapeContext,
        perturbation_regimes: list[WeightRegime]
    ) -> SensitivityReport:
        ...
```

### 6.2 Mathematical Formulation & Null Signal Handling

For each cluster $i$:
1. **Relative Volume Density ($d_i$):**
   $$d_i = \frac{n_i}{\max_j n_j}$$
2. **Mean Vintage Recency ($r_i$):**
   $$r_i = \max\left(0, 1 - \frac{\bar{a}_i}{Y}\right), \quad \text{where } \bar{a}_i = \frac{1}{n_i}\sum_{p \in S_i} \max(1, y_{ref} - y_{filing, p})$$
3. **Citation Observation Coverage ($C_i$) & Traction ($T_i$):**
   $$C_i = \frac{|S_{i, obs}|}{n_i}$$
   $$T_i = \begin{cases} \text{clip}\left(\frac{1}{|S_{i, obs}|} \sum_{p \in S_{i, obs}} \frac{\tilde{\tau}_p}{\tau_{max}}, 0, 1\right) & \text{if } |S_{i, obs}| > 0 \\ \text{None (unobserved)} & \text{if } |S_{i, obs}| = 0 \end{cases}$$
4. **Demand Pull Intensity ($q_i$):**
   $$q_i = \begin{cases} \frac{m_i}{\max_j m_j} & \text{if } \max_j m_j > 0 \\ 0 & \text{otherwise} \end{cases}$$
5. **Composite White-Space Metric ($W_i$):**
   * **Strict Mode:** If any required component (e.g. $T_i$) is `None`, $W_i = \text{None}$ and `missing_components = ["traction"]`.
   * **Renormalized Mode:** $W_i = \frac{\sum_{k \in \text{observed}} w_k s_k}{\sum_{k \in \text{observed}} w_k}$, and `score_coverage = \sum_{k \in \text{observed}} w_k`.
   * **Zero Silent Imputation:** Missing observations are explicitly tracked and never silently converted to zeros.

---

## 7. Declarative Research & Experiment Framework

### 7.1 Experiment Configuration (`experiments/innoget_es_2026/config.yaml`)
```yaml
experiment:
  id: innoget_es_2026_evaluation
  title: "Empirical Alignment of Spanish Innoget Demand vs OEPM Patent Publications"
  version: "1.0.0"
  reference_year: 2026
  horizon_years: 20

datasets:
  patent_snapshot:
    manifest: "data/snapshots/patents_es_manifest.json"
    expected_dataset_content_sha256: "c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e"
    jurisdiction: "ES"
  demand_dataset:
    file: "data/raw/innoget_demands.json"
    filter:
      country: "Spain"

evaluation:
  predefined_analytical_set: ["C11D", "E03C", "G05B", "C22C", "H01M", "C08L"]
  opportunity_model: "composite_whitespace_v1"
  weights:
    density: 0.40
    recency: 0.20
    traction: 0.15
    demand: 0.25
  thresholds:
    white_space: 0.50
    quadrant_unmet_density: 0.40

synthesis:
  enabled: true
  provider: "groq"
  model: "llama-3.3-70b-versatile"
  max_iterations: 3
```

---

## 8. Scientific Invariant Gates

The system enforces 8 mandatory scientific invariant gates across Unit, Integration, and E2E tiers:

| Invariant Gate | Description | Verified In |
|---|---|---|
| **Gate 1: `None != 0`** | Unobserved citation counts remain strictly `None` and are excluded from averages without becoming false zeros. | Unit, Integration, E2E |
| **Gate 2: SHA-256 Strict Hex** | Every raw payload and parquet part verifies against a strictly validated 64-character lowercase hex digest. | Unit, Integration, E2E |
| **Gate 3: RAW Byte Immutability** | `store_payload()` is idempotent; stored payload bytes match input bytes exactly; corrupted files raise an explicit integrity error. | Integration |
| **Gate 4: Full Provenance Chain** | Every `FieldObservation` references an existing `raw_payload_sha256` and non-empty authority URI. | Unit, Integration |
| **Gate 5: Zero Synthetic Defaults** | Parser and validator reject silent date or CPC fallbacks (no defaulting to `2020-01-01` or `G06Q`). | Unit, Integration |
| **Gate 6: Stable PyArrow Schema** | Canonical Parquet datasets conform to a fixed, typed PyArrow schema regardless of batch size. | Integration |
| **Gate 7: Clean-Clone A/B Determinism** | Two independent ingestion runs from identical raw bytes produce identical `dataset_content_sha256` and `manifest_sha256`. | E2E |
| **Gate 8: Zero Corpus Duplication** | DuckDB queries execute over Parquet views without duplicating dataset rows in Python memory. | Integration, E2E |
