# Nexus Innovation Intelligence Engine: Clean Architecture & Research Infrastructure Design

**Document Version:** 2.0.0  
**Date:** 2026-09-02  
**Status:** Approved Architectural Specification  
**Target:** Modular Monolith Clean Architecture for Innovation Analytics & Scientific Research

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
│   │ OpportunityHypothesis     │      │ In-Memory DuckDB Query    │               │
│   └─────────────┬─────────────┘      └───────────────────────────┘               │
│                 │                                                                │
│                 ▼                                                                │
│   ┌───────────────────────────┐      ┌───────────────────────────┐               │
│   │    OPPORTUNITY ENGINE     │      │     AGENTIC SYNTHESIS     │               │
│   │ Pluggable Models & Math   │─────►│ Propose-Critique Loop     │               │
│   │ Sensitivity & Ranking     │      │ Grounded Evidence Defense │               │
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

## 2. Modular Monolith Directory Structure

The system is organized following Clean Architecture principles within a single modular Python package:

```text
nexus/
├── domain/                          # Pure business logic and entity contracts (zero external dependencies)
│   ├── models/
│   │   ├── patent.py                # PatentDocument, PatentFamily, CitationLink, Classification
│   │   ├── demand.py                # DemandSignal, DemandRequirement
│   │   ├── evidence.py              # EvidenceRecord, SourceProvenance, FieldObservation
│   │   └── opportunity.py           # OpportunityHypothesis, ClusterMetrics, QuadrantClassification
│   └── protocols/
│       ├── sources.py               # PatentSourceProtocol, DemandSourceProtocol
│       ├── classifiers.py           # ClassificationProtocol
│       └── models.py                # OpportunityModelProtocol, SensitivityProtocol
│
├── application/                     # Use cases and orchestration workflows
│   ├── ingestion/
│   │   ├── pipeline.py              # IngestionPipeline (Fetch -> Raw -> Normalize -> Validate -> Store)
│   │   └── dataset_freezer.py       # Snapshot freezing, SHA-256 fingerprinting, manifest generation
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
│   │   │   └── google_patents.py    # Google Patents / BigQuery adapter (optional)
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

## 3. Data Platform & Ingestion Lifecycle

### 3.1 Immutable Two-Tier Storage Architecture

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
   - Populates embedded `EvidenceRecord` (source URL, primary archive ref, observed fields)
               │
               ▼
3. CANONICAL PARQUET STORE (`data/canonical/<dataset_id>/corpus.parquet`)
   - Columnar, compressed, version-controlled Parquet dataset
   - Accompanying Content-Addressed Manifest (`manifest.json`)
               │
               ▼
4. ANALYTICAL QUERY ENGINE (`nexus.infrastructure.storage.duckdb_engine`)
   - Ephemeral in-memory DuckDB instance created on demand (`:memory:`)
   - Reads directly from verified Parquet snapshot (`read_parquet(?)`)
   - Zero local database drift or cache divergence
```

---

## 4. Domain Models & Contracts

### 4.1 `EvidenceRecord` (First-Class Provenance)
```python
class EvidenceRecord(BaseModel):
    """Immutable audit trail establishing primary authority provenance for any domain entity."""
    source_name: str                  # e.g., "OEPM BOPI", "EPO OPS", "Innoget INDUSAC"
    source_uri: str                   # Direct URL to authority lookup / archive
    retrieval_timestamp: datetime
    raw_payload_sha256: str           # Hash of untouched payload in Raw Store
    extraction_rule_version: str      # Git commit / version of normalizer
    observed_fields: list[str]        # Explicit whitelist of present fields
    unobserved_fields: list[str]      # Explicit list of missing fields (preserved as None)
    verification_status: str          # "authority_verified", "in_situ_harvested", "unverified_mock"
```

### 4.2 `PatentDocument` & `PatentFamily`
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
    evidence: EvidenceRecord

class PatentFamily(BaseModel):
    """Group of related patent documents sharing priority claims across jurisdictions."""
    family_id: str
    members: list[PatentDocument]
    earliest_priority_date: str
    title_consensus: str
    family_cpc_codes: list[str]
```

### 4.3 `DemandSignal`
```python
class DemandSignal(BaseModel):
    """Market-pull requirement extracted from industrial open innovation calls."""
    demand_id: str                    # e.g. "INNOGET-2292"
    source_network: str               # e.g. "Innoget", "INDUSAC"
    title: str
    description: str
    technical_requirements: list[str]
    origin_country: str               # e.g. "Spain", "Germany"
    posted_date: str | None = None
    deadline_date: str | None = None
    classified_cpc_prefixes: list[str] # Primary CPC subclasses assigned
    evidence: EvidenceRecord
```

---

## 5. Pluggable Opportunity & White-Space Engine

### 5.1 Protocol Abstraction
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

    def evaluate_sensitivity(
        self,
        cluster_metrics: list[OpportunityHypothesis]
    ) -> SensitivityReport:
        ...
```

### 5.2 Mathematical Formulation & Sensitivity Framework

For each cluster $i$:
1. **Relative Volume Density ($d_i$):**
   $$d_i = \frac{n_i}{\max_j n_j}$$
2. **Mean Vintage Recency ($r_i$):**
   $$r_i = \max\left(0, 1 - \frac{\bar{a}_i}{Y}\right), \quad \text{where } \bar{a}_i = \frac{1}{n_i}\sum_{p \in S_i} \max(1, y_{ref} - y_{filing, p})$$
3. **Citation Observation Coverage ($C_i$) & Traction ($T_i$):**
   $$C_i = \frac{|S_{i, obs}|}{n_i}$$
   $$T_i = \begin{cases} \text{clip}\left(\frac{1}{|S_{i, obs}|} \sum_{p \in S_{i, obs}} \frac{\tilde{\tau}_p}{\tau_{max}}, 0, 1\right) & \text{if } |S_{i, obs}| > 0 \\ \text{null / unobserved baseline} & \text{if } |S_{i, obs}| = 0 \end{cases}$$
4. **Demand Pull Intensity ($q_i$):**
   $$q_i = \frac{m_i}{\max_j m_j}$$
5. **Composite White-Space Metric ($W_i$):**
   $$W_i = w_d(1 - d_i) + w_r r_i + w_T T_i + w_q q_i$$

### 5.3 Automated Statistical Sensitivity Analysis
To prevent *researcher degrees of freedom*, the engine evaluates 5 distinct mathematical regimes:
* **Baseline Regime:** $(0.40, 0.20, 0.15, 0.25)$
* **Demand-Dominant Regime:** $(0.30, 0.15, 0.15, 0.40)$
* **IP-Dominant Regime:** $(0.50, 0.20, 0.20, 0.10)$
* **Traction-Dominant Regime:** $(0.30, 0.20, 0.30, 0.20)$
* **Equi-Weighted Regime:** $(0.25, 0.25, 0.25, 0.25)$

Calculates Spearman rank correlation ($\rho_s$) across regimes and flags ranking invariance.

---

## 6. Two-Stage Decoupled Multi-Agent Synthesis

### 6.1 Strict Evidence Demarcation

```text
STAGE 1: DETERMINISTIC QUANTITATIVE GROUND TRUTH
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

## 8. Migration Roadmap & Execution Phases

| Phase | Objective | Deliverables |
|---|---|---|
| **Phase 1: Domain & Ingestion Foundations** | Clean Domain Models & Immutable Raw Data Store | `nexus/domain/models/*`, `nexus/infrastructure/storage/raw_store.py`, `nexus/infrastructure/storage/parquet_store.py` |
| **Phase 2: Product Opportunity Engine** | Agnostic Opportunity Models & Statistical Sensitivity | `nexus/application/opportunity/*`, `OpportunityModelProtocol`, sensitivity ranking tests |
| **Phase 3: Agentic Synthesis Layer** | Decoupled Propose-Critique Coordinator | `nexus/application/synthesis/*`, `nexus/infrastructure/llm/*` |
| **Phase 4: Declarative Experiment Client** | Config-driven experiment runner & paper exporter | `experiments/innoget_es_2026/run.py`, CLI integration (`nexus experiment run`) |
| **Phase 5: Verification & Full CI Suite** | 100% test coverage and CI workflow verification | GitHub Actions CI workflow, clean-clone validation, reproducibility benchmarks |
