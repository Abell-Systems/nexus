# Data Provenance & Experimental Dataset Lineage

**Document Version:** 1.2.0  
**Updated:** 2026-09-02  
**Corpus Authority:** Oficina Española de Patentes y Marcas (OEPM) & European Patent Office (EPO Open Patent Services)

---

## 1. Overview & Content-Addressed Lineage Architecture

To guarantee scientific rigor, empirical reproducibility, and source fingerprinting, all datasets in **Abell Nexus** follow a strict content-addressed lineage:

```text
[Official Authority Catalog / Live API]
                 │
                 ▼
[Fingerprinted Raw Baseline: data/raw/oepm_open_data_es.json (SHA-256: 2832dc59...)]
                 │
                 ▼
[Normalized Storage: Parquet / JSONL (SHA-256: c158bdaa...)]
                 │
                 ▼
[Content-Addressed Manifest: data/snapshots/patents_es_manifest.json]
                 │
                 ▼
[Deterministic Query Engine: In-Memory DuckDB from Verified Parquet]
```

---

## 2. Spanish Industrial Demand Dataset (`innoget_demands.json`)

* **Source Authority:** Innoget Open Innovation Network & INDUSAC (EU Horizon Project).
* **Extraction Date:** 2026-08-25T11:08:53Z.
* **Extraction Methodology:** Structured web extraction of active and completed industrial open innovation challenges across European and global corporate partners.
* **Target Domestic Scope:** Records originating in Spain (`country == 'Spain'`) and EU-wide industrial calls with Spanish R&D designation.
* **Key Spanish Demand Solicitations:**
  1. **Call #2292 (INDUSAC / Spain - Consumer Chemistry):**
     * *Title:* *Project 3in1: Innovative Approaches to Discovering Consumer Needs. Liquid Detergent Formulation & Low-Temperature Washing.*
     * *Technical Requirements:* Low-temperature active surfactants (15–25°C), biodegradable enzyme complexes, microencapsulation of bioactives, stain removal efficiency, zero phosphates.
     * *Canonical CPC Mapping:* `C11D` (Detergent Compositions; Soap), `B01J` (Microencapsulation).
  2. **Call #2293 (INDUSAC / Spain - Sanitary & Materials):**
     * *Title:* *Seeking Kitchen Sink: The Centerpiece of Your Kitchen (Smart Home & Sustainability).*
     * *Technical Requirements:* IoT touchless sensor integration, greywater recycling, thermal modulation, antimicrobial composite materials, water consumption reduction.
     * *Canonical CPC Mapping:* `E03C` (Sanitary Plumbing Installations; Sinks), `A47J` (Kitchen Equipment), `C08L` (Composite Polymers).
  3. **Call #2297 (INDUSAC / Spain - Industrial IoT & Energy):**
     * *Title:* *Seeking Green Efficiency: Real-Time Machine Performance & Energy Consumption Monitoring.*
     * *Technical Requirements:* Non-intrusive electrical load monitoring (NILM), edge sensorization, cyber-physical energy optimization, harmonic load disaggregation in manufacturing.
     * *Canonical CPC Mapping:* `G05B` (Monitoring, Testing & Control Systems), `G01R` (Measuring Electric Variables), `H02J` (Power Distribution).
  4. **Call #2245 (INDUSAC / EU-Spain - Green Metallurgy):**
     * *Title:* *Lead-Free Brass & Precision Machining in High-Speed Production Lines.*
     * *Technical Requirements:* Lead content < 100 ppm, microdrilling machinability, chip evacuation, tool durability.
     * *Canonical CPC Mapping:* `C22C` (Non-Ferrous Alloys), `B23B` (Machining/Turning).

---

## 3. Spanish Patent Corpus (`patents_es_corpus.parquet`)

* **Catalog Source:** Oficina Española de Patentes y Marcas (OEPM) - Boletín Oficial de la Propiedad Industrial (BOPI).
* **Official Data Portal:** [datos.gob.es - Patentes Solicitadas y Concedidas BOPI](https://datos.gob.es/es/catalogo/e05024401-patentes-solicitadas-y-concedidas-bopi) | [OEPM Datos Abiertos](https://www.oepm.es/es/sobre-oepm/datos-abiertos/)
* **Invenes Official Search Archive:** [OEPM Invenes Portal](https://consultas2.oepm.es/InvenesWeb/)
* **Live API Engine:** European Patent Office Open Patent Services (EPO OPS 3.2).
* **Corpus Scope:** *Frozen baseline corpus derived from OEPM-indexed sources; publication-level source verification pending.*
* **Date Semantics & Inclusion Criteria:**
  * **Publication Jurisdiction:** `country_code == 'ES'` (Spanish National Patents `ES...A1/B1/B2` and European Patents validated in Spain).
  * **Publication Date (`pd` / `publication_date`):** 2016–2024.
  * **Filing / Application Date (`filing_date`):** 2015–2023.
  * **Classification Scope:** Multi-sector IPC/CPC coverage across Sections A, B, C, E, G, H.
  * **Analytical Evaluation Set:** Cross-sector comparison evaluated across a predefined analytical set: `["C11D", "E03C", "G05B", "C22C", "H01M", "C08L"]`.
* **Dataset Artifacts & Cryptographic Checksums:**
  * **Raw Source Baseline:** `data/raw/oepm_open_data_es.json`  
    * *SHA-256 Fingerprint:* `2832dc5936b881b4045b26b415f5c5ed2c0bfdc71f6902b838d85000e6799d7b`
  * **Normalized Parquet Snapshot:** `data/snapshots/patents_es_corpus.parquet`  
    * *SHA-256 Digest:* `c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e`
  * **Content-Addressed Manifest:** `data/snapshots/patents_es_manifest.json`

---

## 4. Ingestion Pipeline & Execution Modes

### Ingestion CLI (`scripts/ingest_oepm_ops.py`)

* `python3 scripts/ingest_oepm_ops.py --source oepm_raw`: Verified local ingestion from `data/raw/oepm_open_data_es.json` with SHA-256 fingerprinting.
* `python3 scripts/ingest_oepm_ops.py --source ops`: Queries live EPO OPS published-data REST API via OAuth2 client credentials. **Fails fast if credentials are missing; no silent fallback.**

### Experiment Runner Modes (`scripts/run_spanish_paper_experiment.py`)

| Mode | Dataset Used | LLM Engine | Valid for Scientific Paper? |
|---|---|---|---|
| **`ExecutionMode.FIXTURE`** | `SAMPLE_ES_PATENTS_FIXTURE` (in-memory mock) | Mock Client | ❌ No (Unit Testing Only) |
| **`ExecutionMode.PILOT`** | Unverified / Local DB | Mock / Dry-Run | ❌ No (Smoke Test Only) |
| **`ExecutionMode.EMPIRICAL`** | `patents_es_corpus.parquet` (In-Memory from SHA-256 Verified Snapshot) | Deterministic Math for Metrics; Groq API for Case Studies | ✅ **Yes (Empirical Evidence)** |

In `EMPIRICAL` mode:
* The runner verifies the SHA-256 of `patents_es_corpus.parquet` against the manifest.
* The query engine queries the verified Parquet snapshot directly in memory to prevent any stale local `.duckdb` state contamination.
* Citation traction ($T_i$) is computed as an experimental composite metric over observed citation data, reporting explicit observation coverage ($C_i$).
