# PR-E.1: Blind Re-Annotation Candidate Pool under Strict Temporal Eligibility

**Status:** Approved Design  
**Date:** 2026-09-09  
**Roadmap Anchor:** `docs/roadmap.md` §3, Table Row **PR-E** ("Blinded re-annotation + IAA dry-run + CPC-auto card"), Phase 1 of 3  
**Governing ADRs:** ADR 0008 (Architectural Enforcement), ADR 0018 (Temporal Pool Eligibility Contract), ADR 0021 (Engineering Quality Non-Regression)  

---

## 1. Purpose & Scope Boundary

### 1.1 Purpose
Generate the canonical, blinded annotation candidate pool for the 3 pilot demands (`INNOGET-1605`, `INNOGET-2292`, `INNOGET-2301`) under `strict` temporal eligibility (ADR 0018). This artifact serves as the un-biased, un-scored input for independent dual human annotation (PR-E.2) and subsequent Inter-Annotator Agreement (IAA) evaluation, ensuring that human judgments are collected without exposure to retrieval scores, ranking positions, retrieval methods (M0/M1), or publication dates.

### 1.2 Non-Negotiable Boundaries (ADR 0021)
- **Sealed Benchmark Untouched:** The existing sealed pilot dataset (`data/benchmark/dataset_pilot_benchmark.json`) and historical experiment records are immutable and untouched.
- **Strictly Scoped to PR-E.1:**
  - **In Scope:** Temporal pool extraction, exact eligible set verification, canonical pre-sorting, deterministic seeded shuffle (`seed=42`), blind evidence projection, artifact serialization, sidecar hash generation, and CI verification tests.
  - **Out of Scope:** Human judgments and Cohen's $\kappa$ evaluation (deferred to **PR-E.2**); automated CPC card evaluation (deferred to **PR-E.3**); M0 vs M1 efficacy claims or Dev/Test splits (deferred to **PR-F**).

---

## 2. Artifact Contract & Schema

### 2.1 Model Hierarchy (`domain/models/annotation.py` & `infrastructure/annotation/blind_export.py`)

```text
BlindedAnnotationSet
├── schema_version: str = "1.0.0"       (required, explicit, no implicit default)
├── dataset_id: str                      (identity of input benchmark)
├── dataset_sha256: str                  (verified SHA-256 of source benchmark)
├── temporal_pool_mode: str = "strict"   (binding ADR 0018 eligibility contract)
├── seed: int = 42                       (shuffle seed)
└── demands: list[AnnotationBatch]
    └── AnnotationBatch
        ├── demand_id: str
        ├── demand_title: str
        ├── demand_description: str
        └── entries: list[AnnotationCandidateEntry]
            └── AnnotationCandidateEntry
                ├── publication_id: str
                └── evidence: PatentCandidateEvidence
                    ├── title: str
                    ├── abstract: str
                    └── classifications_cpc: list[str]
```

### 2.2 Blind Invariant & Excluded Fields
To prevent cognitive or methodological contamination:
1. **Forbidden Fields in Candidate Entries:** Serialized candidate records MUST NOT contain:
   - `retrieval_scores` or any numeric score.
   - `rank` or sequential position indicator.
   - `retrieval_method` or retriever identifier (e.g. M0, M1, BM25, semantic).
   - `publication_date` (avoids conflating technical relevance with legal/temporal validity).
2. **Deterministic Reproducibility:** No non-deterministic timestamps (such as `created_at`) inside the canonical payload. The artifact identity is 100% deterministic and reproducible bit-for-bit from `(source_benchmark, temporal_policy, seed)`.

---

## 3. Pipeline Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Source Dataset Verification (data/benchmark/)            │
│ • Verify SHA-256 of dataset_pilot_benchmark.json            │
│ • Fail-fast if missing or hash mismatch                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 2. Temporal Policy Binding (ADR 0018)                       │
│ • Verify temporal_pool_mode == "strict"                     │
│ • Verify policy is bound to target benchmark metadata       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 3. Strict Eligibility Filtering                             │
│ • Evaluate (demand, patent) publication dates               │
│ • Exclude EXCLUDED_TEMPORAL candidates                      │
│ • Assert exact candidate sets per demand (15, 12, 15)       │
│ • Assert exact 3 excluded publications for INNOGET-2292     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 4. Canonical Pre-Sorting & Deterministic Shuffle            │
│ • Sort eligible publication_ids alphabetically              │
│ • Apply random.Random(seed=42).shuffle(sorted_ids)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 5. Blind Evidence Projection                                │
│ • Extract PatentCandidateEvidence (title, abstract, CPC)    │
│ • Discard all scores, methods, dates, ranks                 │
│ • Assemble AnnotationBatch per demand                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 6. Artifact & Sidecar Serialization                         │
│ • Emit data/annotations/pilot_strict_annotation_batch.json  │
│ • Emit .sha256 sidecar file                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Exact Set Identity Specification

The generation engine and unit tests verify exact set identity:
- **`INNOGET-1605` (15 eligible candidates):**
  `ES-2300054-A1`, `ES-2317182-A1`, `ES-2339317-A1`, `ES-2342371-A1`, `ES-2357907-A1`, `ES-2365440-A1`, `ES-2384666-A1`, `ES-2391629-A1`, `ES-2423985-A1`, `ES-2443048-A1`, `ES-2457813-A1`, `ES-2475459-A1`, `ES-2524317-A1`, `ES-2538188-A1`, `ES-2544253-A1`.
- **`INNOGET-2292` (12 eligible candidates, 3 excluded):**
  - Eligible: `ES-2076110-A1`, `ES-2081548-A1`, `ES-2101031-A1`, `ES-2104085-A1`, `ES-2114798-A1`, `ES-2122692-A1`, `ES-2150993-A1`, `ES-2180424-A1`, `ES-2180425-A1`, `ES-2195325-A1`, `ES-2234032-A1`, `ES-2277437-A1`.
  - Excluded (temporally invalid under ADR 0018): `ES-2345423-A1`, `ES-2364775-A1`, `ES-2374944-A1`.
- **`INNOGET-2301` (15 eligible candidates):**
  `ES-2045564-A1`, `ES-2067718-A1`, `ES-2081702-A1`, `ES-2086259-A1`, `ES-2106093-A1`, `ES-2117565-A1`, `ES-2139618-A1`, `ES-2144795-A1`, `ES-2151608-A1`, `ES-2178051-A1`, `ES-2200259-A1`, `ES-2223447-A1`, `ES-2239634-A1`, `ES-2244243-A1`, `ES-2280261-A1`.
- **Total Eligible Set:** Exactly **42 unique publication pairs** across the 3 demands.

---

## 5. Automated Verification & Quality Gates

Automated pytest tests in `backend/test/unit/infrastructure/annotation/test_blind_export.py` enforce:
1. **Dataset & Policy Fail-Fast:** Missing benchmark, corrupted hash, or mismatched temporal policy raises immediate explicit errors.
2. **Exact Eligible Set Assertion:** Emitted candidates match the expected sets by value and count; excluded publications are asserted absent.
3. **Canonical Shuffle Invariance:** Permuting the raw benchmark candidate array does not alter the emitted batch (guaranteed by alphabetical pre-sorting before seeded shuffle).
4. **Structural Blindness Gate:** Scanning raw serialized JSON payload asserts the complete absence of forbidden keys: `score`, `retriever_id`, `rank`, `publication_date`, `method`.
5. **Sidecar Integrity:** Emitted `.sha256` sidecar strictly matches the SHA-256 digest of the emitted JSON payload.
