# Design Spec: Empirical Study (Innoget vs. Spanish Patents) & Sovereign VPS Architecture

**Date:** 2026-09-01  
**Status:** Approved with modifications  
**Scope:** 
1. Scientific Methodology & Experiment Pipeline (Innoget Spain vs. Spanish ES Patents).
2. Decoupled VPS Implementation & Groq Inference Layer.

---

## 1. Overview & System Decomposition

This specification establishes:
1. **The Scientific Methodology Pipeline**: An audit-traceable, reproducible experimental pipeline measuring how domestic patent supply (OEPM / `ES` publications) aligns with industrial open-innovation demand in Spain (Innoget technology calls).
2. **The Sovereign Execution Layer (VPS)**: A decoupled, lightweight, CPU-only runtime leveraging Groq API via an OpenAI-compatible interface, replacing Google Cloud and Google ADK dependencies.

```text
=============================================================================
                      SCIENTIFIC METHODOLOGY PIPELINE (Decoupled)
=============================================================================
[Innoget Spain Calls]          [EPO OPS / OEPM ES Patents]
        │                                   │
        ▼                                   ▼
 [Snapshot & Normalization]       [Snapshot & Normalization]
        │                                   │
        └─────────────────┬─────────────────┘
                          ▼
            [Demand ➔ Concept ➔ CPC Mapping] (Deterministic & Rule-Validated)
                          ▼
            [Taxonomic & Semantic Clustering]
                          ▼
            [Feature Extraction & Citation Traction]
                          ▼
            [Demand-Supply Gap & White-Space Metrics]
                          ▼
            [Multi-Agent Candidate Synthesis & Adversarial Validation (Groq)]
                          ▼
            [Auditable Experiment Results: Tables, Matrices & Artifacts]
=============================================================================
                      RUNTIME IMPLEMENTATION LAYER (VPS)
=============================================================================
[DuckDB / Parquet Store] ── [FastAPI Engine] ── [Groq OpenAI-Compatible Client]
```

---

## 2. Scientific Methodology: Demand-to-Patent Mapping & Metrics

### 2.1 Formal Mapping Procedure (Innoget Demand ➔ Concepts ➔ CPC ➔ Cluster)

To ensure scientific rigor and strict reproducibility:

1. **Step 1: Demand Ingestion & Normalization (`D_k`)**
   * Input: Raw Innoget call records where `country == "Spain"`.
   * Extracted fields: `id`, `title`, `description`, `category`, `requirements`, `related_keywords`, `desired_outcome`.
   * Pre-processing: Lowercase normalization, tokenization, lemmatization, removal of administrative boilerplate.

2. **Step 2: Technical Concept Extraction (`C_k`)**
   * Extract key technical noun phrases and functional capabilities from requirements and desired outcomes (e.g., `"energy consumption monitoring"`, `"low-temperature detergent formulation"`, `"lead-free brass machining"`).

3. **Step 3: CPC Subclass Mapping & Validation Rules**
   * Direct lexical and keyword-to-CPC taxonomy mapping based on the WIPO/EPO Concordance Table and official CPC Definitions.
   * Deterministic scoring:
     $$S(k, c) = w_{title} \cdot \mathbb{I}(c \in C_{title}) + w_{req} \cdot \mathbb{I}(c \in C_{req}) + w_{kw} \cdot \mathbb{I}(c \in C_{kw})$$
   * Validation rule: At least one primary CPC subclass (e.g., `C11D`, `E03C`, `G05B`, `H02J`, `C22C`) is assigned per demand record. LLM assist (if used for concept expansion) is temperature-zero and validated against a fixed CPC whitelist dictionary.

4. **Step 4: Cluster Assignment**
   * Each cluster $i$ is defined by its primary 4-character CPC subclass (`CPC4`, e.g., `C11D` for Detergent compositions, `G05B` for Monitoring/Control systems).

---

## 2.2 Patent Supply Ingestion (`S_i`)

* **Source**: EPO Open Patent Services (OPS) API / OEPM bulk data for publications with `country_code == 'ES'`.
* **Fields per record**: `publication_number`, `title`, `abstract`, `cpc_codes`, `filing_date`, `publication_date`, `backward_citations_count`, `forward_citations_count`, `applicant_name`.
* **Snapshot**: Frozen DuckDB database (`data/snapshots/patents_es_snapshot.duckdb`) ensuring deterministic repeatability.

---

## 2.3 Formal Metric Definitions

For each technology cluster $i$ (CPC subclass) with $n_i$ total patents and $m_i$ matched Innoget demand signals:

### A. Relative Density ($d_i$)
Measures domestic patent volume saturation:
$$d_i = \frac{n_i}{\max_j n_j}$$

### B. Recency Horizon ($r_i$)
Measures the mean vintage of the domestic patent base against a $Y = 20$-year horizon ($y_{ref} = 2026$):
$$r_i = \max\left(0, 1 - \frac{\bar{a}_i}{Y}\right), \quad \bar{a}_i = \frac{1}{n_i} \sum_{p \in S_i} \max(1, y_{ref} - y_{filing, p})$$

### C. Citation Traction ($T_i$)
Distinguishes forward citations (external technology traction) from backward citations (prior-art foundation), avoiding the bias against newly published patents:
* For each patent $p$, let $f_p$ be forward citations received and $a_p = \max(1, y_{ref} - y_{pub, p})$ be publication age.
* **Annualized Forward Citation Rate:** $\tau_p = \frac{f_p}{a_p}$.
* For young patents ($a_p \le 3$ years), apply a dampening / prior-art foundation boost based on normalized backward citations $b_p$ to prevent denominator distortion:
  $$\tilde{\tau}_p = \begin{cases} \frac{f_p}{a_p} & \text{if } a_p > 3 \\ \frac{f_p + 0.2 \cdot \min(b_p, 5)}{3} & \text{if } a_p \le 3 \end{cases}$$
* **Cluster Citation Traction ($T_i$):**
  $$T_i = \text{clip}\left(\frac{1}{n_i} \sum_{p \in S_i} \frac{\tilde{\tau}_p}{\tau_{max}}, 0, 1\right)$$
  *(Where $\tau_{max} = 5.0$ citations/year serves as scaling ceiling).*

### D. Industrial Demand Intensity ($q_i$)
Normalized industrial demand volume for cluster $i$:
$$q_i = \begin{cases} \frac{m_i}{\max_j m_j} & \text{if } m_i > 0 \\ 0 & \text{otherwise} \end{cases}$$

### E. Composite White-Space Score ($W_i$)
Combines low saturation, active recency, state-of-the-art traction, and verified market demand:
$$W_i = 0.40(1 - d_i) + 0.20 r_i + 0.15 T_i + 0.25 q_i$$
* **Threshold:** $W_i \ge 0.50$ flags high-opportunity innovation white space.

---

## 2.4 Multi-Agent Synthesis & Adversarial Validation Protocol

For prioritized white-space clusters:
1. **Inventor Agent**: Synthesizes structured `InventionCandidate` addressing the unmet requirements of the Innoget demand while differentiating from the retrieved `ES` representative patents.
2. **Adversarial Agent**: Challenges the candidate using the retrieved domestic and international prior art, requiring mandatory `cited_patents` in the structured verdict (`survives` vs. `rejected`).
3. **Governor Agent**: Calculates verifiable multi-dimensional scorecards (`novelty`, `prior_art_risk`, `differentiation`, `evidence`).

---

## 3. Paper Outputs & Deliverables

The experimental pipeline will generate the following artifacts:
1. **Dataset Snapshot Metadata**: `data/snapshots/metadata.json` (exact counts, timestamps, query signatures).
2. **Demand-to-Patent Alignment Matrix**: Table summarizing each Spanish Innoget call, mapped CPC subclass, $n_i$ (patent count), $d_i$, $r_i$, $T_i$, $q_i$, and $W_i$.
3. **Quadrant Classification**:
   * *Quadrant I (Unmet Opportunity)*: High Demand ($q_i > 0.5$), Low Domestic IP ($d_i < 0.3$).
   * *Quadrant II (Co-developed / Saturated)*: High Demand, High Domestic IP.
   * *Quadrant III (Dormant / Established IP)*: Low Demand, High Domestic IP.
   * *Quadrant IV (Niche / Emerging)*: Low Demand, Low Domestic IP.
4. **Synthesized Case Study Briefs**: 2 complete candidate invention logs with verbatim prompt traces, adversarial citation trees, and governor scorecards.

---

## 4. Sovereign VPS Architecture & Implementation

### 4.1 Technology Stack (100% De-Googled)

| Role | Component | Justification |
|---|---|---|
| **Inference Engine** | **Groq API** (`llama-3.3-70b-versatile` / `mixtral-8x7b-32768`) | Ultra-fast inference, OpenAI-compatible endpoint, low cost, no GPU required. |
| **Provider Abstraction** | `backend/patent_agent/provider.py` | Universal OpenAI-compatible client (`httpx` / `openai` SDK), swappable via env vars. |
| **Agent Orchestrator** | Native Async State Machine (`backend/patent_agent/orchestrator.py`) | Replaces `google-adk`, pure Python async/await with Pydantic typing and loop control. |
| **Storage & Retrieval** | **DuckDB** (`patents_es.duckdb`) | High-speed columnar analytics, zero daemon overhead, embedded in Python process. |
| **API Server** | FastAPI (`backend/main.py`) | Async REST API for pipeline execution and status queries. |
| **Hosting Target** | Standard CPU VPS (2 vCPU, 4GB RAM) | Runs in standard Linux environment with minimal memory footprint. |

### 4.2 Decoupled Phasing Strategy

* **Phase 1 (Immediate - Paper Focus)**:
  1. Build EPO OPS / OEPM ingestion script and snapshot DuckDB database.
  2. Implement Demand $\rightarrow$ CPC mapping engine with validation.
  3. Implement Citation Traction ($T_i$) and White-Space calculation scripts.
  4. Implement Groq OpenAI-compatible multi-agent synthesis loop.
  5. Run experiments, export tables, matrices, and candidate case studies.
* **Phase 2 (Subsequent - Packaging & Deployment)**:
  1. Package backend and frontend into self-contained Docker Compose stack.
  2. Configure reverse proxy (Caddy) and deploy to VPS.

---

## 5. Verification & Acceptance Criteria

1. **Deterministic Reproducibility**: Running the experiment script against the frozen DuckDB snapshot with fixed seeds yields identical metric tables.
2. **Traceability**: Every synthesized candidate in the paper case studies includes non-empty, valid `cited_patents` publication numbers from the Spanish patent corpus.
3. **No Google Cloud Lock-in**: Pipeline runs successfully without `google-adk`, Google BigQuery, or Google Vertex AI credentials.
4. **Audit Log Integrity**: All prompt templates, LLM responses, and metric calculations are logged in `data/experiments/YYYY-MM-DD_run/`.
