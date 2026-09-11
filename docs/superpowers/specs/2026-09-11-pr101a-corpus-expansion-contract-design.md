# Design Specification — PR #101a: Phase-2 Demand Corpus Expansion Contract ($N \ge 60$)

**Document ID:** `SPEC-2026-09-11-PR101A`  
**Status:** Approved by User (Brainstorming Phase Complete)  
**Date:** 2026-09-11  
**Authors:** Valentín Liñeiro; Lydia Bares; Antigravity Agent  
**Binding Directives:** AGENTS.md, ADR 0008, ADR 0009, ADR 0025, ADR 0029, ADR 0030  

---

## 1. Executive Summary & Problem Statement

Following the completion of ADR 0030 (#100), the historical 38.5% organizational contamination across the Dev/Test split was successfully resolved, establishing an operational organization-audited corpus of $N=18$ ($12$ verified independent + $6$ unknown organization) and a clean partition of 10 Dev / 8 Test demands (`devtest_split_n18_v2.json`).

However, as formally pre-registered in `docs/empirical-study-protocol.md` §3.2 and `data/experiments/power_analysis_wilcoxon.json`, statistical testing with 80% power at standardized effect size $\theta = 0.2$ requires a confirmatory sample size of:
$$N_{\mathrm{power}} = |\mathcal{D}_{\mathrm{independent}}| \ge 60$$

Neither $N=18$ nor the verified independent sample $N=12$ satisfies this statistical power target.

To expand the corpus to $N \ge 60$ independent observations without introducing selection bias, survivorship bias, or post-hoc convenience sampling (*"searching for 42 demands that happen to work"*), **PR #101a establishes a pre-specified, binding acquisition and sampling contract prior to collecting, selecting, or processing any new demand data**.

### Golden Rule of PR #101a
> **PR #101a establishes the acquisition contract; it does not acquire, select, rank, or transform any demand records.**

---

## 2. Experimental Milestones & PR Sequencing

The expansion and evaluation pipeline is strictly decomposed into decoupled, sequential PRs:

1. **Milestone #101a (Current / PR #101):** Frozen corpus expansion contract, declarative policy configuration (`corpus_expansion_policy_v1.json`), canonical candidate record contract, typed policy validator, and ADR 0031. Zero new data records.
2. **Milestone #101b:** Data acquisition against the frozen contract. Produces raw acquired candidates and partitions them deterministically into `POLICY_ACCEPTED` and `POLICY_REJECTED` candidate sets with exhaustive exclusion reasons.
3. **PR #102:** Multidimensional independence audit over accepted candidates (organization, sector, technology-family, and duplicate industrial problem). Resolves `INDEPENDENT`, `PSEUDOREPLICATE`, and `UNKNOWN` status. Evaluates corpus sufficiency ($N_{\mathrm{independent}} \ge 60$) and sector concentration ($>0.35 \to \text{CONCENTRATION\_WARNING}$).
4. **PR #103:** Deterministic Dev/Test split freeze (`devtest_split_v3.json`) over the expanded audited corpus using ADR 0030's `organization_aware_split` algorithm, preserving historical `v2` artifacts and enforcing strict UNKNOWN quarantine (`unknown_split_policy = "dev_only"`).
5. **PR #104:** Dual blind multi-expert annotation on the expanded candidate pool and Cohen's $\kappa$ inter-annotator agreement at scale.
6. **PR #105:** Family-aware evaluation integration (`allow`, `collapse`, `exclude_related`) with authentic patent family metadata.
7. **PR #106:** Confirmatory powered efficacy evaluation on the untouched Test split ($H_1$ Wilcoxon signed-rank test on primary endpoint nDCG@10, secondary endpoints with Benjamini–Hochberg FDR control).

---

## 3. Core Scientific Decisions & Principles (ADR 0031 Basis)

### 3.1 European Sampling Frame with Explicit Geographic Stratification
* **Sampling Frame:** Public, verifiable industrial technology demands from European sources, encompassing both Spain and broader European/international solicitations.
* **Explicit Strata:**
  1. `spain`: Domestic Spanish demand stratum (continuity with Phase 1).
  2. `international_european`: Complementary European/international stratum providing domain and geographical diversity.
* **No Artificial Quotas:** No rigid $N_{\mathrm{Spain}} / N_{\mathrm{Int}}$ quotas (e.g. 20/40) are imposed ex ante. Stratum prevalence, eligibility rates, text length, and sector distributions will be reported transparently. Geographic origin is a descriptive sampling stratum, never a quality filter.
* **Demand Origin $\neq$ Patent Corpus:** The patent evaluation universe remains grounded in the domestic technology base (e.g., OEPM gazette publications and domestic prior-art base). Expanding demand diversity does not alter the patent corpus.

### 3.2 Permitted Primary Sources & Source Qualification Gate
* **Permitted Sources:**
  1. **InnoGet (`source_id = "innoget"`):** Permitted construct `Technology call`. Public HTTP access without authentication.
  2. **Enterprise Europe Network / POD (`source_id = "een_pod"`):** Permitted construct `Technology request`. Public HTTP access without authentication (central portal or regional mirrors such as Lombardia). Substantive technical problem $\ge 25$ words.
* **New Source Gate (`ADMISSIBLE_SOURCE_CANDIDATE`):** No additional platform or registry may contribute observations to the corpus without completing an independent, peer-reviewed source qualification protocol auditing public access, persistence, identity resolution, publication date verifiable evidence, and construct fidelity.

### 3.3 Temporal Window & Hierarchical Date Evidence
* **Permitted Window:** `2020-01-01` to `2025-12-31` inclusive.
* **Exclusion of 2026:** Solicitations from 2026 are excluded to decouple benchmark construction from unresolved, actively evolving industrial contexts.
* **Canonical $t_{\mathrm{demand}}$:** Must represent the verifiable **public publication date** of the demand. Crawl dates, access dates, cache dates, or syndicate republishing dates are prohibited.
* **Date Evidence Provenance:** Source adapters must explicitly provide `publication_date_evidence_field` and `publication_date_evidence_text` documenting the exact source artifact verifying $t_{\mathrm{demand}}$.
* **Indeterminate Dates:** Missing or unverifiable publication dates trigger immediate candidate rejection (`OUT_OF_TEMPORAL_WINDOW` / unresolvable date).

### 3.4 Observation Unit, Independence, and Anti-Concentration
* **Statistical Observation Unit:** Individual technical demand $d$ identified by canonical immutable `demand_id`.
* **Definition of $N_{\mathrm{power}}$:**
  $$N_{\mathrm{power}} = N_{\mathrm{eligible, independent}}$$
  Raw records, ineligible candidates, pseudoreplicates, and `UNKNOWN` observations do not count toward the $N \ge 60$ target.
* **Organization Independence Rule:** Exact string grouping (ADR 0029) is maintained without exception. Each identifiable organization contributes at most one `INDEPENDENT` observation (lexicographically smallest `demand_id` representative); all siblings are `PSEUDOREPLICATE`. Non-identifiable organizations evaluate to `UNKNOWN`, never `INDEPENDENT`.
* **Sector Concentration Monitoring:**
  - No artificial hard caps or minimum sector quotas.
  - If any single sector represents $>35\%$ of independent observations upon audit, it triggers a `CONCENTRATION_WARNING` and an explicit provenance audit. It does not cause automatic exclusion of valid observations.
  - Robustness across sectors is evaluated post-hoc in sensitivity analyses.

### 3.5 Pre-Specified Candidate Exclusion Criteria
A candidate is deterministically evaluated by the policy validator and rejected (`POLICY_REJECTED`) if any of the following apply:
1. `UNAUTHORIZED_SOURCE`: Source not in authorized primary sources.
2. `UNAUTHORIZED_RECORD_TYPE`: Record type not permitted for the source.
3. `OUTSIDE_TEMPORAL_WINDOW`: Publication date outside [2020-01-01, 2025-12-31] or unverified.
4. `UNAUTHORIZED_GEOGRAPHIC_STRATUM`: Stratum not recognized by policy.
5. `CONTENT_TOO_SHORT`: Problem description text under 25 canonical words (`calculate_canonical_word_count`).
6. `NO_TECHNICAL_PROBLEM`: Demand does not articulate an authentic technical problem with verifiable evidence text.
7. `CONFIDENTIALITY_REDACTED`: Source record explicitly states that key technical details or problem formulation are confidential or redacted.
8. `ACCESS_NOT_PUBLIC`: Record requires user credentials, active login, or defeats bot challenges.

### 3.6 Absolute Prohibition of Outcome-Dependent Selection
> **No candidate demand may be included or excluded based on retrieved patents, ranking scores, relevance judgments, expected benchmark difficulty, or any downstream matching result.**

### 3.7 Language Invariant
Language is not an exclusion criterion. Solicitations in European languages (English, Spanish, Italian, German, French, etc.) are valid candidates. The original text is preserved immutable; any downstream translation or normalisation must be documented as an auditable transformation distinct from source text.

### 3.8 UNKNOWN Organization Policy & Dev/Test Split Preservation
* **Quarantine Policy:** All `UNKNOWN` organization demands are quarantined strictly to `Dev` (`unknown_split_policy = "dev_only"`). Test contains strictly zero `UNKNOWN` demands; 100% of Test demands are demonstrated `INDEPENDENT`.
* **Historical Split Preservation:** `devtest_split_n18_v2.json` remains immutable as a historical audit artifact.
* **Global Resplit for Expanded Corpus (Approach B):** Once the expanded corpus is frozen and audited in #102, a global deterministic resplit will be computed in #103 using ADR 0030's `organization_aware_split` algorithm, yielding `devtest_split_v3.json`.

---

## 4. Architectural Boundaries & System Components

### 4.1 Component Diagram

```text
                    docs/adr/0031-corpus-expansion-contract.md
                                       │
                                       ▼
                  docs/phase2-corpus-expansion-protocol.md
                                       │
                                       ▼
           config/policies/data/corpus_expansion_policy_v1.json
           config/policies/data/corpus_expansion_policy_v1.sha256
                                       │
                         [Application Loader & Hash Audit]
                                       │
                                       ▼
       backend/src/main/domain/models/corpus_expansion.py
       ├── PermittedSourceConfig
       ├── TemporalWindowConfig
       ├── GeographicStratumConfig
       ├── ContentRequirementsConfig
       ├── ConcentrationMonitoringConfig
       ├── UnknownHandlingConfig
       ├── CorpusExpansionPolicy
       ├── DemandCandidateContractRecord (Canonical normalized input)
       ├── CandidateRejectionReason (Enum)
       └── CandidateValidationResult (ACCEPT / REJECT + exhaustive reasons)
                                       │
                                       ▼
       backend/src/main/application/corpus/expansion_policy_validator.py
       ├── load_corpus_expansion_policy(path: Path) -> CorpusExpansionPolicy
       │   └── [Fail-fast on missing config, schema invalidity, or hash mismatch]
       └── validate_demand_candidate(candidate, policy) -> CandidateValidationResult
           └── [Evaluates candidate rules deterministically; produces exhaustive reasons]
```

### 4.2 Separation of Concerns

1. **Policy Model vs. Candidate Contract:**
   - `CorpusExpansionPolicy` defines the declarative constraints.
   - `DemandCandidateContractRecord` defines the canonical payload expected by the validator, insulating the domain from source-specific ingestion schemas.
2. **Fail-Fast Policy Loading vs. Deterministic Candidate Rejection:**
   - Invalid, missing, or altered configuration files trigger immediate fatal exceptions (`FileNotFoundError`, `PolicyIntegrityError`, `ValueError`).
   - Non-compliant demand candidates (e.g. published in 2019, or under 25 words) do not crash execution; they are deterministically rejected with `CandidateValidationResult(status=REJECT, rejection_reasons=[...])`.
3. **Candidate Validation vs. Independence Audit:**
   - The validator evaluates individual candidate compliance against policy.
   - Multi-candidate relationships (organization grouping, pseudoreplication, sector dominance, and $N \ge 60$ sufficiency) belong strictly to downstream audit modules in #102.
4. **No Scrapers or Network Code in Core:**
   - Neither `domain` nor `application` contains HTTP clients, scrapers, HTML parsers, or network dependencies. Source acquisition tooling belongs to the experiment scripts boundary in Milestone #101b.

---

## 5. Declarative Policy Specification (`corpus_expansion_policy_v1.json`)

The policy file will be committed at `config/policies/data/corpus_expansion_policy_v1.json` with an accompanying `.sha256` sidecar:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "policy_version": "corpus_expansion_policy_v1",
  "description": "Binding acquisition and sampling frame policy for Phase-2 demand corpus expansion towards N>=60 independent observations.",
  "target_sample_size": {
    "target_independent_demands": 60,
    "power_analysis_reference": "data/experiments/power_analysis_wilcoxon.json"
  },
  "sources": [
    {
      "source_id": "innoget",
      "display_name": "InnoGet Open Innovation Network",
      "permitted_constructs": ["Technology call"],
      "public_access_mode": "unauthenticated_public_http"
    },
    {
      "source_id": "een_pod",
      "display_name": "Enterprise Europe Network Partnering Opportunities Database",
      "permitted_constructs": ["Technology request"],
      "public_access_mode": "unauthenticated_public_http"
    }
  ],
  "temporal_window": {
    "min_publication_date": "2020-01-01",
    "max_publication_date": "2025-12-31",
    "date_interpretation": "public_publication_date"
  },
  "geographic_strata": [
    {
      "stratum_id": "spain",
      "description": "Domestic Spanish demand stratum (continuity with Phase 1)"
    },
    {
      "stratum_id": "international_european",
      "description": "Complementary European/International demand stratum"
    }
  ],
  "content_requirements": {
    "min_word_count": 25,
    "require_technical_problem": true,
    "allow_explicit_confidentiality_redaction": false
  },
  "concentration_monitoring": {
    "sector_warning_threshold": 0.35,
    "max_independent_per_organization": 1
  },
  "unknown_handling": {
    "unknown_organization_split_policy": "dev_only",
    "counts_towards_independent_target": false
  }
}
```

---

## 6. Verification and Test Strategy

Automated test suites will enforce:
1. **Model Invariants (`test_corpus_expansion_models.py`):**
   - Immutability (`frozen=True`) and rejection of undeclared fields (`extra="forbid"`).
   - Validation that `min_publication_date <= max_publication_date`.
   - Rejection of negative word count or warning threshold outside $(0.0, 1.0]$.
   - Validation of `DemandCandidateContractRecord` fields and date evidence types.
2. **Application Validator Tests (`test_corpus_expansion_validator.py`):**
   - **Load & Integrity:** Verifies successful loading with valid SHA-256 sidecar; verifies fatal `PolicyIntegrityError` upon corrupted hash or altered content.
   - **Candidate Validation Acceptance:** Valid candidate meeting all criteria produces `status == ACCEPT` and empty rejection list.
   - **Exhaustive Deterministic Rejection:** Candidate failing multiple criteria (e.g. publication date in 2019 AND 10 words) produces `status == REJECT` with both `OUT_OF_TEMPORAL_WINDOW` and `CONTENT_TOO_SHORT` in deterministic sorted order.
   - **Boundary Tests:** Edge cases for dates (`2020-01-01`, `2025-12-31` accepted; `2019-12-31`, `2026-01-01` rejected) and word count (24 rejected, 25 accepted).
   - **Confidentiality & Access Tests:** Redacted technical content or non-public access rejected with typed reasons.
3. **Architecture & Linting Quality Gates:**
   - Full pass of `ruff check .`
   - Strict `mypy backend/src/main`
   - Pass of `python scripts/check_architecture.py` and `lint-imports`

---

## 7. Deliverables Checklist for PR #101a

- [ ] `docs/adr/0031-corpus-expansion-contract.md`
- [ ] `docs/phase2-corpus-expansion-protocol.md`
- [ ] `config/policies/data/corpus_expansion_policy_v1.json`
- [ ] `config/policies/data/corpus_expansion_policy_v1.sha256`
- [ ] `backend/src/main/domain/models/corpus_expansion.py`
- [ ] `backend/src/main/application/corpus/expansion_policy_validator.py`
- [ ] `backend/test/unit/domain/test_corpus_expansion_models.py`
- [ ] `backend/test/unit/application/test_corpus_expansion_validator.py`
- [ ] `docs/roadmap.md` updated
- [ ] `docs/empirical-study-protocol.md` updated
