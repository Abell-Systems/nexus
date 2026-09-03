# ADR 0004: Matching Engine Contract, Evidence-Based Assessment, and Configuration Boundary

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** `application/matching`, `domain/models/matching`, `domain/protocols/matching`  

## Context

Abell Nexus connects industrial technology demands with domestic patent publications.
Under ADR 0001 (Testing Strategy), ADR 0002 (Minimal Clean Code & SOLID), and ADR 0003 (Externalized Origin Policy & Evidence-Based Resolution), the system must maintain strict epistemological and architectural separation across data acquisition, policy resolution, and matching evaluation.

Previously, early prototypes suffered from:
1. Conflating retrieval similarity (a bare `float`) with decision and explainability.
2. Inconsistent demand representations (`DemandSignal` vs `DemandRecord`), allowing unnormalized HTML or raw metadata to bleed into matching.
3. Hardcoded keyword taxonomies (`CPC_TAXONOMY_MAP` in `cpc_taxonomy.py`) embedded directly in Python code.
4. Conflating candidate generation (retrieval recall) with scoring and ranking (precision).
5. Lack of a formal assessment contract explaining *why* a candidate matched, *which features* contributed to the match, and whether evidence is sufficient to justify a decision.

## Decision

We establish an immutable Clean Architecture contract for the Nexus Matching Engine, decoupling **Observed Facts**, **Feature Extraction**, **Matching Evaluation**, and **Ranking / Decision**:

```text
       Observed Facts (Clean Domain Records)
       ┌───────────────────────┐   ┌───────────────────────┐
       │     DemandRecord      │   │     PatentDocument    │
       │  (normalized, sealed) │   │ (canonical, validated)│
       └───────────┬───────────┘   └───────────┬───────────┘
                   │                           │
                   └─────────────┬─────────────┘
                                 ▼
                     MatchingFeatureExtractor
                                 │
                                 ▼
                           MatchFeatures
       ┌───────────────────────────────────────────────────┐
       │ • Lexical: token_overlap_ratio, bm25_score        │
       │ • Semantic: dense_cosine_similarity               │
       │ • Taxonomic: cpc_concordance_level (0.0 to 1.0)   │
       │ • Temporal: delta_days (t_demand - t_pub)         │
       │ • Eligibility: is_prior_art, is_jurisdiction_match│
       └─────────────────────────┬─────────────────────────┘
                                 │
                                 ▼
                      MatchingEngine (Matcher)
                   (Injects MatchingPolicyConfig)
                                 │
                                 ▼
                          MatchAssessment
       ┌───────────────────────────────────────────────────┐
       │ • overall_score: float [0.0, 1.0]                 │
       │ • confidence: MatchConfidence (STRONG / MED / LOW)│
       │ • features: MatchFeatures                         │
       │ • evidence_summary: tuple of explainable tokens   │
       │ • sufficiency: EvidenceSufficiency (SUFFICIENT...)│
       │ • policy_sha256: 64-char hex of active policy     │
       └─────────────────────────┬─────────────────────────┘
                                 │
                                 ▼
                 Second-Stage CandidateRanker
            (Deterministic sorting, tie-breaking, pool)
```

---

### 1. Epistemological Decoupling: What is a "Match"?

A match is **not** a raw float and **not** a judicial verdict of legal patentability.

A match is an **evidence-based assessment (`MatchAssessment`)** measuring the technological problem-solution alignment between a verified industrial demand and an eligible domestic patent publication:
* **Factual Evidence:** Concrete tokens, concepts, taxonomic codes, and dates observed in both documents.
* **Derived Features (`MatchFeatures`):** Deterministic, reproducible metrics calculated across lexical, dense semantic, taxonomic, and temporal dimensions.
* **Explainable Assessment (`MatchAssessment`):** A structured verdict containing the normalized score, confidence level, evidence tokens, evidence sufficiency classification, and cryptographic policy stamp.
* **Separation from Decision:** The matching engine assesses compatibility and affinity. Business actions (shortlisting, notification, commercial outreach, research investment) are decoupled downstream decisions.

---

### 2. The Input / Output Data Contract

#### Inputs:
1. **Demand Document (`DemandRecord`):** The clean, normalized domain entity produced by the ingestion pipeline (complying with ADR 0003). It contains canonical text, verified origin level, and optional taxonomic indicators.
2. **Patent Document (`PatentDocument`):** The validated, canonical patent document (complying with ADR 0001/0002).
3. **Matching Configuration (`MatchingPolicyConfig`):** Injected versioned policy containing weights, thresholds, concordance matrices, and vocabulary tables.

#### Outputs:
1. **`MatchFeatures`:**
   * `lexical_score`: float $\ge 0.0$ (normalized to $[0, 1]$ in context or raw BM25).
   * `semantic_score`: float $\in [0, 1]$ (scaled cosine similarity).
   * `cpc_concordance`: float $\in \{0.0, 0.25, 0.50, 0.75, 1.0\}$.
   * `temporal_valid`: bool (True if $t_{\text{pub}} < t_{\text{demand}}$).
   * `delta_days`: int | None.
   * `shared_terms`: tuple[str, ...] (concrete overlapping technical stems/keywords).
   * `concordant_cpc_pairs`: tuple[tuple[str, str], ...] (matched demand vs patent symbols).

2. **`MatchAssessment`:**
   * `demand_id`: str.
   * `publication_id`: str.
   * `overall_score`: float $\in [0.0, 1.0]$.
   * `confidence`: `MatchConfidence` (`STRONG`, `MODERATE`, `WEAK`, `NONE`).
   * `sufficiency`: `EvidenceSufficiency` (`SUFFICIENT`, `PARTIAL`, `INSUFFICIENT_EVIDENCE`, `INELIGIBLE_TEMPORAL`).
   * `features`: `MatchFeatures`.
   * `rationale`: str (human-readable, audit-verifiable synthesis of observed alignments).
   * `policy_id`: str.
   * `policy_version`: str.
   * `policy_sha256`: str (64-character hexadecimal SHA-256 digest).

---

### 3. Configuration Over Hardcoding

In accordance with Section 3 of `AGENTS.md`, **no business lists, keyword taxonomies, or scoring heuristics are hardcoded in matching algorithm classes**.

The following parameters are externalized into version-controlled, cryptographically sealed configuration (`config/policies/matching/`):
1. **Fusion Weights:** $\alpha$ (lexical), $\beta$ (semantic), $\gamma$ (taxonomic CPC), constrained to $\alpha + \beta + \gamma = 1.0$.
2. **Hierarchical CPC Concordance Levels:** Exact values for subgroup ($1.00$), main group ($0.75$), subclass ($0.50$), section ($0.25$).
3. **Confidence Thresholds:** Minimum scores required for `STRONG` (e.g. $\ge 0.70$), `MODERATE` ($\ge 0.40$), `WEAK` ($> 0.0$).
4. **Sufficiency Constraints:** Minimum required signals (e.g., must have non-zero semantic or lexical signal to be `SUFFICIENT`).
5. **Taxonomic Concordance Mappings:** Externalized concept-to-CPC dictionary tables loaded from JSON/YAML, eliminating the in-code `CPC_TAXONOMY_MAP`.
6. **Stopwords and Normalization Rules:** Externalized linguistic resources.

**Fail-Fast Invariant:** Missing, corrupt, or tampered matching policy files raise immediate explicit errors (`FileNotFoundError`, `ValueError`). The engine **never synthesizes an in-memory fallback policy**.

---

### 4. Determinism & Null Semantics

* **Determinism:** Given identical `(DemandRecord, PatentDocument, MatchingPolicyConfig)`, the engine must produce bit-exact identical `MatchAssessment` across all runs and platforms.
* **Strict Null Semantics:** Missing abstract, unobserved dates, or missing CPC codes remain `None` and produce zero contribution to the corresponding feature; they are never imputed with synthetic default strings or fake zero timestamps.
* **Ineligible Documents:** If a patent violates prior-art temporality ($t_{\text{pub}} \ge t_{\text{demand}}$) or jurisdiction, the engine evaluates `sufficiency = INELIGIBLE_TEMPORAL`, flags `overall_score = 0.0`, and records the exact temporal difference in `MatchFeatures`.

#### 4.1 Min-Max Normalization Semantics when $\max == \min$ (Zero Spread)

In second-stage ranking (`min_max_normalize()`), when all candidate scores in a pool are identical ($\max = \min$):
* **Operational Behavior:** The normalizer maps all values to `0.0` rather than dividing by zero or synthesizing arbitrary rankings.
* **Scientific Semantics:** This outcome explicitly signifies that **the signal provides zero discriminative power (zero variance) across the candidate pool**, rather than implying that candidates have zero intrinsic relevance.
* **Protocol Justification:** In additive linear fusion ($S_{\text{hybrid}} = \alpha S_{\text{lex}} + \beta S_{\text{sem}} + \gamma S_{\text{cpc}}$), a non-discriminative signal that mapped to `1.0` would act as an artificial intercept boosting all candidates equally, distorting relative contributions of the remaining discriminative signals. Assigning `0.0` ensures that non-discriminative signals neither penalize nor artificially inflate candidates, preserving the relative ranking established by discriminative signals. Ties are broken deterministically by canonical publication ID (`publication_id ASC`).

---

### 5. Architectural Alignment with ADR 0001 / 0002 / 0003

* **ADR 0001 (Testing Strategy):**
  * Domain contracts and calculations (`MatchFeatures`, `compute_cpc_similarity`, `MatchAssessment`) tested with fast, isolated unit tests.
  * Matching orchestrators (`CandidateMatchingService`) tested with stubs.
  * Real retrieval vertical slices (DuckDB BM25, MPNet dense vector, CPC hierarchy) tested in infrastructure tests with real database connections and deterministic fixtures.
  * E2E acceptance tests verify complete flow from `DemandRecord` to `MatchingResult` and telemetry artifacts.
* **ADR 0002 (Minimal Clean Code & SOLID):**
  * Single responsibility: feature extraction is decoupled from scoring; scoring is decoupled from ranking.
  * Zero speculative abstractions: no generic multi-objective optimization frameworks or paper-specific wrappers.
* **ADR 0003 (Externalized Policy & Provenance):**
  * Uses canonical cryptographic digest checking (`policy_sha256`).
  * Emits canonical `FieldObservation` provenance for verified alignments.
