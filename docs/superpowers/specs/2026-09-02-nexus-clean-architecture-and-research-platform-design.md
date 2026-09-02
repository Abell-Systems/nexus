# Nexus Innovation Intelligence Engine: Clean Architecture & Research Infrastructure Design

**Document Version:** 2.1.0  
**Date:** 2026-09-02  
**Status:** Approved Architectural Specification  
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
│   │ DatasetSnapshot           │      │ In-Memory DuckDB Query    │               │
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
| **Domain Contracts & Validation** | **Pydantic v2** | Boundary validation only (APIs, CLI, ingestion boundaries). |
| **HTTP Client & API Adapters** | **httpx** | Resilient connection pooling, retry handling, async streaming. |
| **Raw Ingestion Store** | **Filesystem / S3 Adapter** | Immutable storage of raw HTTP responses, XML payloads, and API metadata. |
| **Canonical Data Storage** | **Apache Parquet + PyArrow** | Columnar, compressed, typed, content-addressed dataset files. |
| **Vectorized Analytics Engine** | **DuckDB** | In-memory (`:memory:`) SQL analytics directly over Parquet without Python object overhead. |
| **CLI Framework** | **Typer** | Type-annotated command line interface for data ops and experiments. |
| **LLM Inference Provider** | **Groq API** (`httpx`) | Fast inference via OpenAI-compatible API format (CPU VPS friendly). |
| **Experiment Configuration** | **YAML + Pydantic** | Declarative research configurations validated against Pydantic schemas. |
| **Scientific Testing & Verification** | **pytest + pytest-asyncio** | Invariant-driven testing, clean-clone verification, SHA validation. |

### 2.2 Operational Efficiency on Sovereign VPS

To ensure low operational cost and deterministic execution on standard compute (e.g. 2 vCPU, 4GB RAM VPS):
1. **Zero Unnecessary Daemons:** No PostgreSQL, Redis, Kafka, Elasticsearch, or Spark dependencies.
2. **Streaming Batch Processing:** Ingestion proceeds via `fetch_batch -> normalize -> validate -> write_parquet_chunk -> release_memory -> next_batch` rather than accumulating millions of records in memory.
3. **No Python Instance Explosion:** Analytics queries run in DuckDB C++ vectorized kernels over Parquet. Pydantic domain models are instantiated strictly at boundary interfaces where domain validation is required.

---

## 3. Modular Monolith Directory Structure

```text
nexus/
├── domain/                          # Pure business logic and entity contracts (zero external dependencies)
│   ├── models/
│   │   ├── patent.py                # PatentDocument, PatentFamily, FamilyMembership, CitationLink
│   │   ├── demand.py                # DemandSignal, DemandRequirement
│   │   ├── evidence.py              # FieldObservation, SourceProvenance, VerificationStatus
│   │   ├── snapshot.py              # DatasetSnapshot, SnapshotManifest
│   │   └── opportunity.py           # OpportunityHypothesis, ClusterMetrics, QuadrantClassification
│   └── protocols/
│       ├── sources.py               # PatentSourceProtocol, DemandSourceProtocol
│       ├── classifiers.py           # ClassificationProtocol
│       ├── storage.py               # RawStoreProtocol, CanonicalStoreProtocol, QueryEngineProtocol
│       ├── models.py                # OpportunityModelProtocol
│       └── sensitivity.py           # SensitivityAnalyzerProtocol
│
├── application/                     # Use cases and orchestration workflows
│   ├── ingestion/
│   │   ├── pipeline.py              # IngestionPipeline (Fetch -> Raw -> Normalize -> Validate -> Store)
│   │   └── dataset_freezer.py       # Dataset freezing, SHA-256 fingerprinting, manifest generation
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
│   │   │   ├── epo_ops.py           # EPO OPS 3.2 REST client & XML parser
│   │   │   ├── oepm_bopi.py         # OEPM open data / BOPI adapter
│   │   │   └── google_patents.py    # Google Patents adapter (optional)
│   │   └── demand/
│   │       ├── innoget.py           # Innoget open innovation adapter
│   │       └── sbir.py              # SBIR/STTR solicitation adapter
│   ├── storage/
│   │   ├── raw_store.py             # Immutable filesystem raw payload store
│   │   ├── parquet_store.py         # Canonical Parquet dataset repository
│   │   └── duckdb_engine.py         # Ephemeral / in-memory DuckDB analytical engine
│   ├── classifiers/
│   │   ├── cpc_taxonomy.py          # Deterministic CPC regex and concordance classifier
│   │   └── keyword_classifier.py    # Lexical keyword classification
│   └── llm/
│       ├── groq_client.py           # OpenAI-compatible Groq API client
│       └── prompts.py               # Versioned system prompts for synthesis & critique
│
├── interfaces/                      # Entrypoints for users and external consumers
│   ├── cli/
│   │   ├── main.py                  # Nexus unified CLI (`nexus ingest`, `nexus analyze`, `nexus experiment`)
│   │   └── formatters.py            # Markdown and terminal table formatters
│   └── api/
│       └── server.py                # FastAPI server (optional web UI / headless integration)
│
├── experiments/                     # Research experiment configurations and reports
│   └── innoget_es_2026/
│       ├── config.yaml              # Declarative experiment parameters
│       ├── hypothesis.md            # Scientific research hypotheses (H1, H2, H3, H4)
│       ├── dataset_manifest.json    # Cryptographic snapshot binding
│       ├── run.py                   # Lightweight experiment runner script
│       └── results/                 # Exported empirical metrics, sensitivity tables, and paper summaries
│
└── tests/                           # Comprehensive test suite organized by architectural layer
    ├── unit/domain/
    ├── unit/application/
    ├── unit/infrastructure/
    └── integration/experiments/
```

---

## 4. Data Platform & Ingestion Lifecycle

### 4.1 Immutable Two-Tier Storage Architecture

```text
[External Authority API / Portal]
               │
               ▼
1. RAW STORE (`data/sources/<source_id>/<YYYY-MM-DD>/payload_xxx.json`)
   - Unmodified HTTP response bytes / raw XML / raw JSON
   - Query metadata, endpoint URL, timestamp, HTTP status
   - Immutable SHA-256 fingerprint computed immediately
               │
               ▼
2. NORMALIZER & VALIDATOR (`nexus.application.ingestion`)
   - Parses raw format into `PatentDocument` / `DemandSignal` domain entities
   - Strict validation: missing dates remain `None`, unobserved citations remain `None`
   - Zero synthetic fallbacks (no defaulting to `2020-01-01` or `G06Q`)
   - Populates field-level `FieldObservation` entries (source URL, primary archive ref, observed value)
               │
               ▼
3. CANONICAL PARQUET STORE (`data/canonical/<dataset_id>/corpus.parquet`)
   - Columnar, compressed, version-controlled Parquet dataset
   - Accompanying Content-Addressed `DatasetSnapshot` Manifest (`manifest.json`)
               │
               ▼
4. ANALYTICAL QUERY ENGINE (`nexus.infrastructure.storage.duckdb_engine`)
   - Ephemeral in-memory DuckDB instance created on demand (`:memory:`)
   - Reads directly from verified Parquet snapshot (`read_parquet(?)`)
   - Zero local database drift or cache divergence
```

---

## 5. Domain Models & Contracts

### 5.1 `FieldObservation` & Provenance
```python
class FieldObservation(BaseModel):
    """Fine-grained provenance record tracking the origin and authority of a specific field observation."""
    field_name: str
    observed_value: Any
    source_authority: str             # e.g., "OEPM BOPI", "EPO OPS"
    source_uri: str                   # Direct archive / query URL
    retrieval_timestamp: datetime
    raw_payload_sha256: str           # SHA-256 of raw response in Raw Store
    extraction_version: str           # Version/commit of parser rule
    verification_status: str          # "authority_verified", "in_situ_harvested", "unverified_mock"
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
    filing_date: str | None = None
    publication_date: str | None = None
    priority_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    classifications_ipc: list[str] = Field(default_factory=list)
    forward_citation_count: int | None = None    # None = unobserved; int >= 0 = verified count
    backward_citation_count: int | None = None   # None = unobserved; int >= 0 = verified count
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
    membership_source: str            # e.g., "EPO DOCDB", "INPADOC"
    evidence: FieldObservation
```

### 5.3 `DemandSignal`
```python
class DemandSignal(BaseModel):
    """Market-pull requirement extracted from industrial open innovation calls."""
    demand_id: str                    # e.g. "INNOGET-2292"
    source_network: str               # e.g. "Innoget", "INDUSAC"
    title: str
    description: str
    technical_requirements: list[str]
    origin_country: str | None = None
    posted_date: str | None = None
    deadline_date: str | None = None
    classified_cpc_prefixes: list[str] # Primary CPC subclasses assigned (or empty if unclassified)
    observations: list[FieldObservation] = Field(default_factory=list)
```

### 5.4 `DatasetSnapshot` (First-Class Research Entity)
```python
class DatasetSnapshot(BaseModel):
    """Content-addressed snapshot representing a frozen, immutable analytical corpus."""
    dataset_id: str
    schema_version: str
    source_batches: list[str]
    record_count: int
    content_sha256: str
    created_at: datetime
    transformation_version: str
    provenance_manifest_uri: str
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
        context: LandscapeContext
    ) -> OpportunityHypothesis:
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

### 6.2 Mathematical Formulation

For each cluster $i$:
1. **Relative Volume Density ($d_i$):**
   $$d_i = \frac{n_i}{\max_j n_j}$$
2. **Mean Vintage Recency ($r_i$):**
   $$r_i = \max\left(0, 1 - \frac{\bar{a}_i}{Y}\right), \quad \text{where } \bar{a}_i = \frac{1}{n_i}\sum_{p \in S_i} \max(1, y_{ref} - y_{filing, p})$$
3. **Citation Observation Coverage ($C_i$) & Traction ($T_i$):**
   $$C_i = \frac{|S_{i, obs}|}{n_i}$$
   $$T_i = \begin{cases} \text{clip}\left(\frac{1}{|S_{i, obs}|} \sum_{p \in S_{i, obs}} \frac{\tilde{\tau}_p}{\tau_{max}}, 0, 1\right) & \text{if } |S_{i, obs}| > 0 \\ \text{null / unobserved baseline} & \text{if } |S_{i, obs}| = 0 \end{cases}$$
4. **Demand Pull Intensity ($q_i$):**
   $$q_i = \begin{cases} \frac{m_i}{\max_j m_j} & \text{if } \max_j m_j > 0 \\ 0 & \text{otherwise} \end{cases}$$
5. **Composite White-Space Metric ($W_i$):**
   $$W_i = w_d(1 - d_i) + w_r r_i + w_T T_i + w_q q_i$$

### 6.3 Automated Statistical Sensitivity Analysis
The `SensitivityAnalyzer` evaluates 5 distinct mathematical regimes configured by the experiment client:
* **Baseline Regime:** $(0.40, 0.20, 0.15, 0.25)$
* **Demand-Dominant Regime:** $(0.30, 0.15, 0.15, 0.40)$
* **IP-Dominant Regime:** $(0.50, 0.20, 0.20, 0.10)$
* **Traction-Dominant Regime:** $(0.30, 0.20, 0.30, 0.20)$
* **Equi-Weighted Regime:** $(0.25, 0.25, 0.25, 0.25)$

Computes pairwise Spearman rank correlations ($\rho_s$) and ranking invariance metrics across regimes.

---

## 7. Two-Stage Decoupled Multi-Agent Synthesis

### 7.1 Strict Evidence Demarcation

```text
STAGE 1: DETERMINISTIC EMPIRICAL ANALYSIS
   - Pure mathematical landscape execution (Zero LLM involvement)
   - Outputs: `empirical_metrics_matrix.csv`, `sensitivity_analysis.csv`, `empirical_summary.md`
   - Complete cryptographic provenance and audit trail
                           │
                           ▼ (passes top opportunity clusters)
STAGE 2: QUALITATIVE EXPLORATORY SYNTHESIS (OPTIONAL)
   - Powered by Groq API (`llama-3.3-70b-versatile`)
   - Propose-Critique loop with European patent-law adversarial persona
   - Mandatory prior-art evidence citation from retrieved cluster documents
   - Output: `qualitative_case_studies.json` explicitly tagged as exploratory hypothesis generation
```

---

## 8. Declarative Research & Experiment Framework

### 8.1 Experiment Configuration (`experiments/innoget_es_2026/config.yaml`)
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
    expected_sha256: "c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e"
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

## 9. Migration Roadmap & Execution Phases

| Phase | Objective | Deliverables |
|---|---|---|
| **Phase 1: Domain & Ingestion Foundations** | Clean Domain Models, Field Observations & Immutable Raw Data Store | `nexus/domain/models/*`, `nexus/infrastructure/storage/raw_store.py`, `nexus/infrastructure/storage/parquet_store.py` |
| **Phase 2: Product Opportunity Engine** | Agnostic Opportunity Models & Decoupled Sensitivity Analyzer | `nexus/application/opportunity/*`, `OpportunityModelProtocol`, `SensitivityAnalyzerProtocol` |
| **Phase 3: Agentic Synthesis Layer** | Decoupled Propose-Critique Coordinator | `nexus/application/synthesis/*`, `nexus/infrastructure/llm/*` |
| **Phase 4: Declarative Experiment Client** | Config-driven experiment runner & paper exporter | `experiments/innoget_es_2026/run.py`, CLI integration (`nexus experiment run`) |
| **Phase 5: Invariant-Driven Verification** | Invariant verification, reproducibility validation & clean-clone tests | Full pytest suite testing RAW integrity, schema validation, missing data semantics, and sensitivity determinism |
