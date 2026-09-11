# Phase-2 Demand Corpus Expansion Operational Protocol

**Document ID:** `PROTOCOL-PHASE2-CORPUS-EXPANSION-V1`  
**Binding Architecture:** ADR 0008, ADR 0009, ADR 0025, ADR 0026, ADR 0029, ADR 0030, ADR 0031  
**Target Population:** European Industrial Technology Demands ($N_{\mathrm{power}} = N_{\mathrm{eligible, independent}} \ge 60$)  
**Status:** Frozen Operational Protocol (Pre-Acquisition)  
**Date:** 2026-09-11  

---

## 1. Executive Summary & Scientific Purpose

The confirmatory empirical evaluation of the Nexus hybrid matching engine (Hypothesis $H_1$, evaluating $\text{nDCG}@10$ gain against the best single-signal baseline via paired Wilcoxon signed-rank testing) requires a minimum statistical power of $1 - \beta = 0.80$ at pre-registered standardized effect size $\theta = 0.2$ ($\alpha = 0.05$).

As established in `docs/empirical-study-protocol.md` §3.2 and `data/experiments/power_analysis_wilcoxon.json`, achieving this statistical power requires:
$$N_{\mathrm{power}} = |\mathcal{D}_{\mathrm{independent}}| \ge 60$$

The Phase-1 pilot and initial Phase-2 screening established an operational organization-audited corpus of $N=18$ demands (`dataset_phase2_organization_audited_corpus_v1.json`), comprising 12 verified independent observations and 6 observations of indeterminate (`UNKNOWN`) organization identity. Neither $N=18$ nor $N=12$ satisfies the confirmatory power requirement.

This protocol specifies the **operational rules, acquisition bounds, hierarchical evidence definitions, anti-concentration guidelines, and automated validation gates** that govern Phase-2 corpus expansion.

### Golden Rule of Acquisition Integrity
> **Acquisition and filtering must be fully governed by pre-specified declarative policy (`corpus_expansion_policy_v1.json`). No candidate demand may be selected, retained, or excluded based on retrieved patents, similarity scores, relevance grades, or expected benchmark difficulty.**

---

## 2. Sampling Frame & Explicit Geographic Stratification

### 2.1 European Sampling Frame
The sampling frame encompasses public industrial technology demands published by European enterprises, institutions, and innovation consortia.

### 2.2 Geographic Strata
To ensure transparency and prevent hidden geographic bias, candidates are acquired under two explicit strata:
1. **`spain`:** Domestic Spanish demand stratum, maintaining longitudinal continuity with Phase-1 and early Phase-2 solicitations.
2. **`international_european`:** Complementary European and international cross-border demand stratum, providing technological domain diversity and broader industry representation.

### 2.3 Strata Principles
* **No Artificial Quotas:** No rigid pre-allocation (e.g. 20 Spain / 40 International) is imposed. Sampling yield, eligibility rates, text length, and domain representation will be reported per stratum.
* **Stratum as Descriptive Characteristic:** Geographic stratum is an observational classification variable, never a quality filter.
* **Separation of Demand Origin and Patent Corpus:** The prior-art patent evaluation universe remains strictly grounded in the domestic technology base (OEPM gazette publications). Broadening the demand sampling frame evaluates engine generalization without altering the patent corpus.

---

## 3. Authorized Primary Sources & Source Qualification Gate

### 3.1 Authorized Primary Sources
Only sources formally registered in the active versioned policy (`corpus_expansion_policy_v1.json`) may contribute candidate records:

| Source ID | Platform Name | Authorized Construct | Access Mode | Minimum Word Count |
| :--- | :--- | :--- | :--- | :---: |
| `innoget` | InnoGet Open Innovation Network | `Technology call` | Public unauthenticated HTTP | 25 |
| `een_pod` | Enterprise Europe Network / POD | `Technology request` | Public unauthenticated HTTP | 25 |

### 3.2 Inadmissible Constructs
The following constructs are strictly incompatible and trigger immediate candidate rejection (`INCOMPATIBLE_CONSTRUCT`):
* Commercial offers, marketing brochures, distributor searches, or supplier sales catalogs (`Technology offer`, `Commercial offer`).
* Generalized corporate calls lacking articulated technical problems.
* Partnership search profiles seeking capital, equity investment, or business acquisition.

### 3.3 New Source Qualification Gate (`ADMISSIBLE_SOURCE_CANDIDATE`)
No new platform, syndicator, or registry may contribute candidate records to the corpus without completing an independent, peer-reviewed source qualification audit. The audit must establish:
1. **Public Access:** Records are publicly accessible via standard HTTP without authentication, subscriptions, paywalls, or bot-mitigation evasion.
2. **Persistence & Archival Stability:** Records carry persistent URLs or unique identifiers resolvable to static public snapshots.
3. **Identity Provenance:** Source explicitly records either requesting organization identity or authenticated institutional intermediary.
4. **Publication Date Verifiability:** Source exposes verifiable original publication date evidence.
5. **Construct Fidelity:** Solicitations conform strictly to technical problem calls.

---

## 4. Temporal Window & Date Evidence Hierarchy

### 4.1 Temporal Boundaries
* **Start Date:** `2020-01-01` (inclusive).
* **End Date:** `2025-12-31` (inclusive).
* **Exclusion of 2026:** Solicitations from 2026 are excluded to decouple benchmark evaluation from active, unresolved, or currently evolving industrial solicitations.

### 4.2 Definition of Canonical Publication Date ($t_{\mathrm{demand}}$)
The demand timestamp $t_{\mathrm{demand}}$ represents the verifiable **original public publication date** of the solicitation.
* **Forbidden Date Types:**
  - Scraping timestamp or crawler run date.
  - Snapshot or archive access date.
  - In-memory cache timestamp.
  - Syndicate re-publishing or aggregator modification date.
* Any candidate whose timestamp reflects crawler execution rather than original publication is rejected.

### 4.3 Evidence Provenance Hierarchy
Every acquired candidate record must supply verifiable date provenance:
1. `publication_date_evidence_field`: The exact attribute name or metadata key in the source payload (e.g. `call_published_date`, `pod_creation_date`).
2. `publication_date_evidence_text`: The raw date string as extracted directly from the source payload before ISO 8601 parsing.

If the publication date cannot be independently evidenced or falls outside `[2020-01-01, 2025-12-31]`, the candidate is deterministically rejected (`OUT_OF_TEMPORAL_WINDOW`).

---

## 5. Technical Content & Problem Description Requirements

Each candidate demand must articulate a substantive technical challenge:
1. **Word Count Invariant & Canonical Procedure:** The technical description text (`problem_description`) must contain at least **25 words** under the canonical normalization procedure (`calculate_canonical_word_count`). Shorter records lack sufficient technological context for semantic or taxonomic retrieval and are rejected (`CONTENT_TOO_SHORT`).
   - **Markup Stripping:** Replace all HTML/XML tags (`<[^>]+>`) with a single whitespace.
   - **Entity Unescaping:** Decode standard HTML entities (e.g. `&amp;` $\to$ `&`, `&nbsp;` $\to$ ` `).
   - **Tokenization:** Match Unicode alphanumeric sequences permitting internal hyphens and apostrophes (`\b[\w]+(?:[-'][\w]+)*\b`).
   - **Normative Examples:**
     - `"state-of-the-art"` $\to$ 1 word.
     - `"high-performance"` $\to$ 1 word.
     - `"company's"` $\to$ 1 word.
     - `"<p>Hello &amp; world!</p>"` $\to$ 2 words (`Hello`, `world`).
     - `"15-25 °C temperature range"` $\to$ 4 words (`15-25`, `C`, `temperature`, `range`).
     - `""` or whitespace $\to$ 0 words.
2. **Articulated Technical Problem Invariant:** The candidate must provide an authentic articulated technical problem. The source adapter must set `has_articulated_technical_problem = True` and supply `technical_problem_evidence_text` containing the excerpt articulating the problem statement. Candidates with `has_articulated_technical_problem = False` or empty evidence text are rejected (`NO_TECHNICAL_PROBLEM`). Downstream construct eligibility audit (Milestone #102) independently verifies this evidence against ADR 0025.
3. **No Confidentiality Redactions:** Demands that explicitly indicate that technical parameters or specifications have been withheld under non-disclosure agreements or confidentiality redaction are rejected (`CONFIDENTIALITY_REDACTED`).
4. **Public Access Invariant:** Demands requiring registered user access or session tokens are rejected (`ACCESS_NOT_PUBLIC`).

---

## 6. Independence Invariants & Anti-Concentration Guidelines

### 6.1 Statistical Observation Unit
The statistical observation unit is the individual technical demand $d \in \mathcal{D}$.
Confirmatory sample size is strictly defined over verified independent observations:
$$N_{\mathrm{power}} = N_{\mathrm{eligible, independent}}$$

### 6.2 Organization Independence (ADR 0029 Invariant)
* **Exact String Grouping:** Identified organizations are grouped by exact string match on `requesting_organization`.
* **Single Independent Representative:** Exactly one representative per organization group (the candidate with lexicographically smallest `demand_id`) is designated `INDEPENDENT`.
* **Pseudoreplicate Designations:** All other members of the organization group are designated `PSEUDOREPLICATE` and do not contribute to $N_{\mathrm{power}}$.
* **Tripartite Unknown Handling:** If organization identity is absent (`None`) or a non-identifying placeholder (e.g. `"Anonymous Organization"`), the status is `UNKNOWN`. Per ADR 0030, `UNKNOWN` observations are quarantined strictly to `Dev` (`unknown_split_policy = "dev_only"`) and excluded from the test benchmark.

### 6.3 Sector Concentration Monitoring
* **Warning Threshold:** $\tau_{\mathrm{warning}} = 0.35$ (35% of independent observations).
* **Concentration Audit:** If upon completion of Milestone #102 any single industrial sector accounts for more than 35% of independent observations, the audit script emits a `CONCENTRATION_WARNING` and logs an explicit provenance review.
* **No Artificial Pruning:** Valid independent demands are not artificially dropped or excluded to force an equal sector distribution; rather, domain heterogeneity is preserved and reported transparently, with sector sensitivity evaluations conducted in downstream analyses.

---

## 7. Pre-Specified Candidate Rejection Taxonomy

The policy validator evaluates each candidate against the 8 pre-specified rejection codes:

| Rejection Code | Policy Invariant Trigger |
| :--- | :--- |
| `UNAUTHORIZED_SOURCE` | Candidate `source_id` is not present in `policy.sources`. |
| `INCOMPATIBLE_CONSTRUCT` | Candidate `source_construct` is not in `permitted_constructs` for the source. |
| `OUT_OF_TEMPORAL_WINDOW` | Publication date is before `2020-01-01` or after `2025-12-31`, or unresolvable. |
| `UNAUTHORIZED_GEOGRAPHIC_STRATUM` | Candidate `geographic_stratum` is not in `policy.geographic_strata`. |
| `CONTENT_TOO_SHORT` | Canonical word count of `description_text` is strictly fewer than 25 words. |
| `NO_TECHNICAL_PROBLEM` | Candidate lacks articulated technical problem (`has_articulated_technical_problem is False` or empty evidence). |
| `CONFIDENTIALITY_REDACTED` | Candidate contains explicit confidentiality disclaimers or redacted technical core. |
| `ACCESS_NOT_PUBLIC` | Candidate record requires private authentication, login, or defeats bot challenge. |

---

## 8. Step-by-Step Acquisition & Validation Workflow

```text
Phase 2 Expansion Execution Workflow:

  ┌─────────────────────────────────────────────────────────────┐
  │ Milestone #101a: Frozen Expansion Contract & Declarative   │
  │ • corpus_expansion_policy_v1.json + .sha256                 │
  │ • DemandCandidateContractRecord & ExpansionPolicyValidator  │
  │ • ADR 0031 & Operational Protocol Document                 │
  │ • Zero data records acquired                                │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Milestone #101b: Data Acquisition & Deterministic Policy    │
  │ • Acquisition scripts harvest raw European candidates       │
  │ • Map raw records -> DemandCandidateContractRecord          │
  │ • Execute validate_demand_candidate()                       │
  │ • Deterministic partition:                                  │
  │   - dataset_phase2_expansion_candidates_accepted.json       │
  │   - dataset_phase2_expansion_candidates_rejected.json       │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PR #102: Multidimensional Independence Audit                │
  │ • Exact-match organization clustering (ADR 0029)            │
  │ • Classify INDEPENDENT, PSEUDOREPLICATE, UNKNOWN            │
  │ • Verify N_independent >= 60 target sufficiency            │
  │ • Sector concentration check (>0.35 -> WARNING)             │
  │ • Freeze dataset_phase2_organization_audited_corpus_v2.json │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ PR #103: Deterministic Dev/Test Split Freeze (v3)           │
  │ • Execute organization_aware_split algorithm (ADR 0030)     │
  │ • UNKNOWN quarantined to Dev; 100% INDEPENDENT in Test      │
  │ • Zero cross-partition organization overlap guaranteed      │
  │ • Freeze devtest_split_v3.json with SHA-256 sidecar         │
  └─────────────────────────────────────────────────────────────┘
```

---

## 9. Quality & Integrity Checklist

Before freezing accepted candidates at the conclusion of PR #101:
* [ ] Policy SHA-256 hash matches `corpus_expansion_policy_v1.sha256`.
* [ ] Every accepted candidate passed `validate_demand_candidate()` with zero rejection reasons.
* [ ] Every rejected candidate has at least one explicit typed reason from `CandidateRejectionReason`.
* [ ] Date evidence fields and raw snippet texts are populated for 100% of candidates.
* [ ] Word count verification was computed after stripping markup and whitespace.
* [ ] No candidate was filtered or ranked based on downstream retrieval results or patent queries.
* [ ] All acquired artifacts are cryptographically signed with `.sha256` sidecars.
