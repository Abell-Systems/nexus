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
3. Hardcoded keyword taxonomies embedded directly in Python code.
4. Conflating candidate generation (retrieval recall) with scoring and ranking (precision).
5. Lack of a formal assessment contract explaining why a candidate matched, which features contributed, and whether evidence is sufficient.
6. Externalized policy being undermined by implicit filesystem loading and business-value fallbacks inside matching code.

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
                                 │
                                 ▼
                      MatchingEngine (Matcher)
                   (Consumes MatchingPolicyConfig)
                                 │
                                 ▼
                          MatchAssessment
                                 │
                                 ▼
                 Second-Stage CandidateRanker
            (Deterministic sorting, tie-breaking, pool)
```

---

### 1. Epistemological Decoupling: What is a "Match"?

A match is **not** a raw float and **not** a judicial verdict of legal patentability.

A match is an **evidence-based assessment (`MatchAssessment`)** measuring technological problem-solution alignment between a verified industrial demand and an eligible domestic patent publication.

The assessment contains factual evidence, deterministic derived features, an explainable score/confidence classification, evidence sufficiency, and the exact policy identity used for evaluation.

Business actions such as shortlisting, notification, commercial outreach, or research investment remain downstream decisions.

---

### 2. Input / Output Data Contract

#### Inputs

1. **Demand Document:** a clean, normalized domain entity produced by the ingestion pipeline.
2. **Patent Document:** a validated, canonical patent document.
3. **Matching Configuration (`MatchingPolicyConfig`):** an explicitly injected, versioned, cryptographically sealed policy containing weights, thresholds, concordance levels, operational limits, and vocabulary/taxonomy tables.

#### Outputs

`MatchFeatures` contains the lexical, semantic, taxonomic, temporal, and evidence-alignment features defined by the matching contract.

`MatchAssessment` contains:

- `demand_id`;
- `publication_id`;
- `overall_score` in `[0.0, 1.0]`;
- `confidence`;
- `sufficiency`;
- `features`;
- `rationale`;
- `policy_id`;
- `policy_version`;
- `policy_sha256`.

---

### 3. Configuration Over Hardcoding

In accordance with Section 3 of `AGENTS.md`, **no business lists, keyword taxonomies, scoring heuristics, operational limits, or scientific interpretation parameters are hardcoded in matching algorithm classes**.

The following are externalized into version-controlled, cryptographically sealed configuration (`config/policies/matching/`):

1. Fusion weights.
2. Hierarchical CPC concordance levels.
3. Confidence thresholds.
4. Evidence/sufficiency constraints.
5. Operational limits such as retrieval and candidate-pool limits.
6. Taxonomic concept-to-CPC mappings and descriptions.
7. Other vocabulary and normalization resources that materially alter matching behavior.

### 3.1 Explicit Policy Injection — Mandatory

Every production matching component whose behavior depends on matching policy MUST receive the active `MatchingPolicyConfig` explicitly from its caller.

The matching layer MUST NOT:

- load `default_matching_policy.json` itself;
- resolve configuration from a repository-relative path;
- use the process working directory to locate policy;
- create a default policy when none is supplied;
- substitute a business-relevant literal when policy is absent.

Policy loading, validation, SHA-256 verification, and selection belong to the application bootstrap/composition boundary. The resulting policy object is then injected through the complete evaluation path.

A public API with `policy=None` is non-compliant when omission changes matching behavior.

### 3.2 No Second Source of Truth

A value appearing in policy MUST NOT be duplicated as an independent executable literal elsewhere when changing that value could change matching behavior.

This includes, but is not limited to, CPC concordance scores, confidence thresholds, retrieval limits, candidate-pool limits, and sufficiency thresholds.

If a value is a mathematical invariant rather than policy, the code and ADR MUST state why it is immutable and why externalizing it would not represent a meaningful policy choice.

### 3.3 No Hidden Sufficiency Rules

Every rule that changes `EvidenceSufficiency` MUST be either:

- explicitly represented in `MatchingPolicyConfig`; or
- explicitly defined as an immutable algorithmic invariant in this ADR and covered by contract tests.

A threshold such as `active_signals >= 2` MUST NOT appear as an unexplained literal in the matching engine.

**Fail-Fast Invariant:** missing, corrupt, or tampered mandatory policy raises an explicit error. The engine never synthesizes an in-memory fallback policy.

---

### 4. Determinism & Null Semantics

Given identical `(DemandRecord, PatentDocument, MatchingPolicyConfig)`, the engine must produce bit-exact identical `MatchAssessment` across all supported runs and platforms.

Missing observations remain absent; they are never imputed with synthetic evidence.

Ineligible documents are explicitly marked and cannot silently become positive matches.

#### 4.1 Min-Max Normalization Semantics when `max == min`

When all candidate scores in a pool are identical, `min_max_normalize()` maps the values to `0.0`.

This represents zero discriminative power, not zero intrinsic relevance. It prevents a non-discriminative signal from becoming an artificial additive intercept in hybrid fusion. Deterministic publication-ID ordering resolves ties.

#### 4.2 Dual-Source CPC Concordance Resolution Semantics

In `DefaultMatchingEngine`, the CPC concordance signal $S_{\text{cpc}}$ may originate from two complementary observational paths:
1. **First-Stage Retrieval Score:** The pre-computed or indexed concordance produced during candidate retrieval ($S_{\text{cpc}}^{\text{retrieval}} \in [0, 1]$).
2. **Metadata-Derived Concordance:** Direct evaluation between the demand's target CPC prefix and the candidate's canonical `classifications_cpc` metadata using `compute_cpc_symbol_similarity_from_levels(d_cpc, p_cpc, policy.cpc_concordance_levels)`.

**Methodological Resolution:**
$$S_{\text{cpc}} = \max\left(S_{\text{cpc}}^{\text{retrieval}}, S_{\text{cpc}}^{\text{metadata}}\right)$$

*Rationale:* Both observations measure the exact same underlying epistemological fact: the highest taxonomic concordance between the demand's technology domain and the patent's registered classifications. Taking the supremum ($\max$) guarantees that candidates retrieved primarily via lexical or dense semantic channels whose rich classification metadata subsequently demonstrates strong CPC concordance are not penalized by an absent or unrecorded retrieval score ($0.0$), while preventing double-counting in linear fusion.

---

### 5. Architectural Alignment

**ADR 0001:** domain calculations and contracts are tested in isolation; orchestrators use stubs; infrastructure and E2E paths use deterministic fixtures.

**ADR 0002:** feature extraction, scoring, ranking, and configuration loading remain separate responsibilities.

**ADR 0003:** policy identity and provenance are cryptographically traceable.

**ADR 0005:** defines the mandatory runtime dependency-injection boundary and explicitly prohibits implicit configuration resolution and business fallbacks.

## Enforcement

A PR modifying matching behavior MUST be rejected if it introduces any of the following without an explicit ADR update and contract tests:

1. A business-policy literal in executable matching code.
2. Repository-relative policy loading outside the composition/bootstrap layer.
3. `policy=None` that silently selects a default policy.
4. A fallback operational limit or threshold.
5. A second executable representation of a policy value.
6. An undocumented sufficiency or evidence rule.

The test suite SHOULD contain a structural guard against these patterns in addition to behavioral tests.
