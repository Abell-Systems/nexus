# Spanish Innoget Demand vs. Spanish Patents Empirical Research Pipeline & Sovereign VPS Architecture

**Document Type:** System Architecture & Scientific Experiment Specification  
**Authors:** Abell Nexus Research & Engineering Team  
**Date:** 2026-09-01 (Updated 2026-09-02)  
**Status:** Approved for Implementation  

---

## 1. Executive Summary & Problem Statement

The goal of this initiative is twofold:
1. **Scientific & Empirical Pipeline**: Produce reproducible, publication-grade empirical results comparing real Spanish industrial innovation demand signals (extracted from the **Innoget / INDUSAC** network) against the domestic Spanish patent publication corpus (**OEPM** / **EPO OPS** `ES` records).
2. **Sovereign VPS Architecture**: Transition the Abell Nexus engine away from proprietary Google Cloud services (`google-adk`, Vertex AI, BigQuery) to a sovereign, CPU-only Linux VPS architecture powered by **DuckDB** and the **Groq API** (via OpenAI-compatible abstraction).

---

## 2. Scientific Methodology: Innoget Demand vs. Spanish Patent State-of-the-Art

### 2.1 Demand Extraction & Formal CPC Mapping

1. **Dataset Scope**: Real industrial technology demands extracted from Innoget/INDUSAC calls originating in Spain (`country == 'Spain'`) and EU cross-border industrial calls with Spanish enterprise participation.
2. **Key Demand Solicitations**:
   * **Call #2292 (INDUSAC / Spain - Consumer Chemistry)**: Project 3in1: Liquid detergent formulations, cold-water enzyme stability, biodegradable surfactants.
   * **Call #2293 (INDUSAC / Spain - Sanitary & Materials)**: Kitchen sink innovation, greywater recycling, IoT sensor integration, antimicrobial composites.
   * **Call #2297 (INDUSAC / Spain - Industrial IoT & Energy)**: Real-time machine monitoring, NILM non-intrusive electrical disaggregation, edge energy optimization.
   * **Call #2245 (INDUSAC / EU-Spain - Green Metallurgy)**: Lead-free brass alloys, high-speed micro-machining, chip evacuation.

3. **Step 3: Curated Deterministic Concept-to-CPC Mapping Rules**
   * Direct lexical and regex-to-CPC taxonomy mapping based on a curated concordance dictionary and official CPC Definitions.
   * Deterministic scoring:
     $$S(k, c) = w_{title} \cdot \mathbb{I}(c \in C_{title}) + w_{req} \cdot \mathbb{I}(c \in C_{req}) + w_{kw} \cdot \mathbb{I}(c \in C_{kw})$$
   * Validation rule: At least one primary CPC subclass (e.g., `C11D`, `E03C`, `G05B`, `H02J`, `C22C`, `H01M`, `C08L`) is assigned per demand record.

4. **Step 4: Cluster Assignment**
   * Each cluster $i$ is defined by its primary 4-character CPC subclass (`CPC4`, e.g., `C11D` for Detergent compositions, `G05B` for Monitoring/Control systems). Cross-sector comparison evaluated across a predefined analytical set: `["C11D", "E03C", "G05B", "C22C", "H01M", "C08L"]`.

---

## 2.2 Patent Supply Ingestion (`S_i`)

* **Source**: EPO Open Patent Services (OPS) API and OEPM open data catalog publications with `country_code == 'ES'`.
* **Fields per record**: `publication_number`, `title`, `abstract`, `cpc_codes`, `filing_date`, `publication_date`, `citation_count`, `backward_citation_count`, `country_code`.
* **Snapshot**: Content-addressed Parquet snapshot (`data/snapshots/patents_es_corpus.parquet`) and DuckDB database verified via SHA-256 manifest.

---

## 2.3 Formal Metric Definitions

For each technology cluster $i$ (CPC subclass) with $n_i$ total patents and $m_i$ matched Innoget demand signals:

### A. Relative Density ($d_i$)
Measures domestic patent volume saturation:
$$d_i = \frac{n_i}{\max_j n_j}$$

### B. Recency Horizon ($r_i$)
Measures the mean vintage of the domestic patent base against a $Y = 20$-year horizon ($y_{ref} = 2026$):
$$r_i = \max\left(0, 1 - \frac{\bar{a}_i}{Y}\right), \quad \bar{a}_i = \frac{1}{n_i} \sum_{p \in S_i} \max(1, y_{ref} - y_{filing, p})$$

### C. Citation Traction ($T_i$) & Citation Observation Coverage ($C_i$)
*Note: Citation Traction ($T_i$) is an experimental composite heuristic metric defined specifically for this study.*
Distinguishes forward citations (external technology traction) from backward citations (prior-art foundation), avoiding the bias against newly published patents:
* For each patent $p$ with observed citation data, let $f_p$ be forward citations received and $a_p = \max(1, y_{ref} - y_{pub, p})$ be publication age.
* **Annualized Forward Citation Rate:** $\tau_p = \frac{f_p}{a_p}$.
* For young patents ($a_p \le 3$ years), apply a dampening / prior-art foundation boost based on normalized backward citations $b_p$ to prevent denominator distortion:
  $$\tilde{\tau}_p = \begin{cases} \frac{f_p}{a_p} & \text{if } a_p > 3 \\ \frac{f_p + 0.2 \cdot \min(b_p, 5)}{3} & \text{if } a_p \le 3 \end{cases}$$
* **Cluster Citation Traction ($T_i$):**
  $$T_i = \text{clip}\left(\frac{1}{|S_{i, obs}|} \sum_{p \in S_{i, obs}} \frac{\tilde{\tau}_p}{\tau_{max}}, 0, 1\right)$$
  *(Where $\tau_{max} = 5.0$ citations/year serves as scaling ceiling, and $S_{i, obs}$ denotes the subset of patents with non-null citation observations).*
* **Citation Observation Coverage ($C_i$):**
  $$C_i = \frac{|S_{i, obs}|}{n_i}$$

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
2. **Adversarial Reviewer**: Evaluates novelty and prior-art differentiation against the retrieved domestic prior art evidence subset, requiring mandatory `cited_patents` in the structured verdict (`survives` vs. `rejected`).
3. **Governor Agent**: Calculates verifiable multi-dimensional scorecards (`novelty`, `prior_art_risk`, `differentiation`, `evidence`).

---

## 3. Paper Outputs & Deliverables

The experimental pipeline generates the following artifacts:
1. **Dataset Snapshot Metadata**: `data/snapshots/patents_es_manifest.json` (exact counts, timestamps, SHA-256 fingerprints).
2. **Demand-to-Patent Alignment Matrix**: Table summarizing each Spanish Innoget call, mapped CPC subclass, $n_i$ (patent count), $d_i$, $r_i$, $T_i$, $C_i$, $q_i$, and $W_i$.
3. **Quadrant Classification**:
   * *Quadrant I (Unmet Opportunity)*: High Demand ($q_i \ge 0.5$), Low Domestic IP ($d_i < 0.40$).
   * *Quadrant II (Co-developed / Saturated)*: High Demand ($q_i \ge 0.5$), High Domestic IP ($d_i \ge 0.40$).
   * *Quadrant III (Dormant / Established IP)*: Low Demand ($q_i < 0.5$), High Domestic IP ($d_i \ge 0.40$).
   * *Quadrant IV (Niche / Emerging)*: Low Demand ($q_i < 0.5$), Low Domestic IP ($d_i < 0.40$).
4. **Synthesized Case Study Briefs**: Candidate invention logs with verbatim prompt traces, adversarial citation trees, and governor scorecards.

---

## 4. Sovereign VPS Architecture & Implementation

### 4.1 Technology Stack (100% De-Googled)

| Role | Component | Justification |
|---|---|---|
| **Inference Engine** | **Groq API** (`llama-3.3-70b-versatile`) | Ultra-fast inference, OpenAI-compatible endpoint, low cost, zero local GPU required. |
| **Provider Abstraction** | `backend/patent_agent/groq_client.py` | Lightweight stdlib client, swappable via env vars. |
| **Agent Loop Engine** | `backend/patent_agent/synthesis_engine.py` | Decoupled propose-critique loop with Pydantic structured output validation. |
| **Storage & Retrieval** | **DuckDB** / **Parquet** | Columnar storage, in-memory query capability directly on verified Parquet snapshots. |
| **API Server** | FastAPI (`backend/main.py`) | Async REST API for pipeline execution and status queries. |
| **Hosting Target** | Standard CPU VPS (2 vCPU, 4GB RAM) | Runs in standard Linux environment with minimal memory footprint. |

---

## 5. Verification & Acceptance Criteria

1. **Deterministic Reproducibility**: Running the experiment runner against the verified Parquet snapshot yields identical metric tables across fresh checkouts.
2. **Traceability**: Every synthesized candidate in the paper case studies cites verified publication numbers from the Spanish patent corpus.
3. **No Google Cloud Lock-in**: Pipeline runs successfully without `google-adk`, Google BigQuery, or Google Vertex AI credentials.
4. **Evidence Tier Separation**: Clear, unforgeable tagging distinguishing empirical verified data from synthetic dry-run smoke tests.
