# Data Provenance & Experimental Dataset Lineage

**Document Version:** 1.0.0  
**Updated:** 2026-09-02  
**Corpus Authority:** Oficina Española de Patentes y Marcas (OEPM) & Innoget Open Innovation

---

## 1. Overview & Lineage Architecture

To guarantee scientific rigor, empirical validity, and full reproducibility, all datasets in **Abell Nexus** follow a strict immutable lineage:

```text
[Raw Source API / Gazettes]
            │
            ▼
[Normalized Storage: JSONL / Parquet]
            │
            ▼
[Cryptographic Verification: SHA-256 Manifest]
            │
            ▼
[Local Analytical Database: DuckDB]
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

* **Source Authority:** Oficina Española de Patentes y Marcas (OEPM) & European Patent Office (EPO Open Patent Services 3.2).
* **Inclusion Criteria:**
  * Publication jurisdiction: `country_code == 'ES'` (Spanish National Patents `ES...A1/B1/B2` and European Patents validated in Spain).
  * Filing Date Window: 2016–2023.
  * Multi-sector IPC/CPC coverage across Sections A, B, C, E, G, H (Chemistry, Metallurgy, Sanitary, Control, Energy, Polymers).
* **Dataset Artifacts:**
  * **Normalized Parquet:** `data/snapshots/patents_es_corpus.parquet`
  * **Normalized JSONL:** `data/snapshots/patents_es_corpus.jsonl`
  * **Analytical Snapshot:** `data/snapshots/patents_es_snapshot.duckdb`
  * **Cryptographic Manifest:** `data/snapshots/patents_es_manifest.json`
* **Dataset Cryptographic Hash (SHA-256):**
  `c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e`
* **Recorded Institutions & Assignees:**
  * *Public Research & Universities:* CSIC, Universidad Politécnica de Madrid (UPM), Universidad del País Vasco (UPV/EHU), Universidad de Barcelona (UB), CIC energiGUNE, AIMPLAS, ITQ-CSIC-UPV.
  * *Industrial Leaders:* Roca Sanitario S.A., Teka Industrial S.A., Cosentino R&D, Circutor S.A., Repsol S.A., Mondragon S. Coop., Irizar e-mobility, Telefónica S.A., Laboratorios Bilper S.A.

---

## 4. Execution Mode Enforcement

The experiment runner strictly distinguishes between execution modes:

| Mode | Dataset Used | LLM Engine | Valid for Scientific Paper? |
|---|---|---|---|
| **`ExecutionMode.FIXTURE`** | `SAMPLE_ES_PATENTS_FIXTURE` (in-memory mock) | Mock Client | ❌ No (Unit Testing Only) |
| **`ExecutionMode.PILOT`** | Unverified / Local DB | Mock / Dry-Run | ❌ No (Smoke Test Only) |
| **`ExecutionMode.EMPIRICAL`** | `patents_es_corpus.parquet` (SHA-256 Verified) | Deterministic Math for Metrics; Groq API for Case Studies | ✅ **Yes (Empirical Evidence)** |

In `EMPIRICAL` mode:
* The quantitative Demand-Patent alignment matrix ($W_i$, $d_i$, $r_i$, $T_i$, $q_i$) is 100% deterministic and requires zero LLM calls.
* The qualitative Case Studies require live Groq API keys with verifiable prior-art citation checks. If Groq is not available, the Case Study section is explicitly flagged as synthetic while the quantitative results remain certified as empirical.
