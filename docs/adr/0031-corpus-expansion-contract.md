# ADR 0031: Phase-2 Demand Corpus Expansion Contract

**Status:** Accepted  
**Date:** 2026-09-11  
**Scope:** Defines the binding acquisition and sampling frame contract for Phase-2 demand corpus expansion towards $N \ge 60$ independent observations, establishes permitted primary sources, temporal window boundaries, explicit geographic stratification, pre-specified candidate exclusion criteria, and strict prohibition of outcome-dependent selection prior to data collection.

---

## 1. Context & Problem Statement

Following the completion of ADR 0029 (#99) and ADR 0030 (#100), the historical 38.5% organizational contamination across the Dev/Test split was successfully resolved. This established an operational organization-audited corpus of $N=18$ ($12$ verified independent + $6$ unknown organization independence) and a clean, organization-isolated partition of 10 Dev / 8 Test demands (`devtest_split_n18_v2.json`).

However, as formally pre-registered in `docs/empirical-study-protocol.md` §3.2 and `data/experiments/power_analysis_wilcoxon.json`, confirmatory statistical hypothesis testing for $H_1$ (Wilcoxon signed-rank test on primary endpoint $\text{nDCG}@10$) with 80% power at standardized effect size $\theta = 0.2$ requires a minimum sample size of:
$$N_{\mathrm{power}} = |\mathcal{D}_{\mathrm{independent}}| \ge 60$$

Neither the operational audited corpus ($N=18$) nor the verified independent subset ($N=12$) satisfies this statistical power target.

### 1.1 Prohibition of Convenience Sampling
Expanding the corpus cannot be approached by searching opportunistically for 42 demands that "happen to work" or meet subjective expectations. In empirical information retrieval, convenience sampling, retrospective selection, or iterative searching against ranking outcomes introduces severe methodological vulnerabilities:
1. **Selection Bias & Cherry-Picking:** Curating demands based on familiar terminology or observed retrieval success artificially inflates baseline retrieval and ranking metrics.
2. **Survivorship Bias:** Retaining only demands that retrieve familiar patents hides true retrieval failure modes.
3. **Hypothesizing After Results Are Known (HARKing):** Modifying corpus boundaries after observing retrieval outcomes compromises statistical false-positive rate ($\alpha = 0.05$) control.

To ensure scientific integrity, **PR #101a establishes a pre-specified, binding acquisition and sampling contract prior to collecting, selecting, or processing any new demand data**.

### 1.2 Golden Rule of PR #101a
> **PR #101a establishes the acquisition contract; it does not acquire, select, rank, or transform any demand records.**

---

## 2. Core Scientific Decisions & Principles

### 2.1 European Sampling Frame with Explicit Geographic Stratification
* **Sampling Frame:** Public, verifiable industrial technology demands from European sources, encompassing both Spain and broader European/international solicitations.
* **Explicit Strata:**
  1. `spain`: Domestic Spanish demand stratum (continuity with Phase 1).
  2. `international_european`: Complementary European/international stratum providing domain and geographical diversity.
* **No Artificial Quotas:** No rigid $N_{\mathrm{Spain}} / N_{\mathrm{Int}}$ quotas (e.g. 20/40) are imposed ex ante. Stratum prevalence, eligibility rates, text length, and sector distributions will be reported transparently. Geographic origin serves as a descriptive sampling stratum, never as a quality filter.
* **Demand Origin $\neq$ Patent Corpus:** The patent evaluation universe remains grounded in the domestic technology base (OEPM gazette publications). Expanding demand diversity does not alter the patent corpus or dilute the domestic prior-art evaluation context.

### 2.2 Authorized Primary Sources & Source Qualification Gate
* **Permitted Primary Sources:**
  1. **InnoGet (`source_id = "innoget"`):** Permitted construct `Technology call`. Public HTTP access without authentication.
  2. **Enterprise Europe Network / POD (`source_id = "een_pod"`):** Permitted construct `Technology request`. Public HTTP access without authentication (central portal or regional mirrors such as Lombardia). Substantive technical problem description $\ge 25$ words.
* **New Source Gate (`ADMISSIBLE_SOURCE_CANDIDATE`):** No additional platform, intermediary, or registry may contribute observations to the corpus without completing an independent, peer-reviewed source qualification protocol auditing public access, persistence, identity resolution, publication date verifiable evidence, and construct fidelity.

### 2.3 Temporal Window & Hierarchical Date Evidence
* **Permitted Window:** `2020-01-01` to `2025-12-31` inclusive.
* **Exclusion of 2026:** Solicitations published in 2026 are excluded to decouple benchmark construction from unresolved, actively evolving industrial contexts.
* **Canonical $t_{\mathrm{demand}}$:** Must represent the verifiable **public publication date** of the demand. Crawl dates, scrape dates, access dates, cache timestamps, or syndicate republishing dates are strictly prohibited.
* **Date Evidence Provenance:** Source adapters must explicitly provide `publication_date_evidence_field` and `publication_date_evidence_text` documenting the exact source artifact verifying $t_{\mathrm{demand}}$.
* **Indeterminate Dates:** Missing, ambiguous, or unverifiable publication dates trigger immediate candidate rejection (`OUT_OF_TEMPORAL_WINDOW`).

### 2.4 Statistical Observation Unit, Independence, and Anti-Concentration
* **Statistical Observation Unit:** Individual technical demand $d$ identified by canonical immutable `demand_id`.
* **Definition of $N_{\mathrm{power}}$:**
  $$N_{\mathrm{power}} = N_{\mathrm{eligible, independent}}$$
  Raw records, ineligible candidates, pseudoreplicates, and `UNKNOWN` observations do not count toward the $N \ge 60$ confirmatory target.
* **Organization Independence Rule (ADR 0029):** Exact string grouping is maintained without exception. Each identifiable organization contributes at most one `INDEPENDENT` observation (lexicographically smallest `demand_id` representative); all sibling demands from that organization are designated `PSEUDOREPLICATE`. Non-identifiable organizations evaluate strictly to `UNKNOWN`, never `INDEPENDENT`.
* **Sector Concentration Monitoring:**
  - No artificial hard caps or minimum sector quotas are enforced during candidate acquisition.
  - If any single sector represents $>35\%$ of independent observations upon audit, it triggers a `CONCENTRATION_WARNING` and an explicit provenance audit. It does not cause automatic exclusion of valid observations.
  - Robustness across sectors will be evaluated in pre-registered sensitivity analyses.

### 2.5 Pre-Specified Candidate Exclusion Criteria
A candidate record is deterministically evaluated by the policy validator and rejected (`POLICY_REJECTED`) if any of the following pre-specified criteria apply:
1. `UNAUTHORIZED_SOURCE`: Source not registered in the active expansion policy.
2. `INCOMPATIBLE_CONSTRUCT`: Document construct not permitted for the source (e.g., commercial offers or marketing calls).
3. `OUT_OF_TEMPORAL_WINDOW`: Publication date earlier than 2020-01-01 or later than 2025-12-31.
4. `UNAUTHORIZED_GEOGRAPHIC_STRATUM`: Geographic stratum not recognized by policy.
5. `CONTENT_TOO_SHORT`: Problem description text contains fewer than 25 words.
6. `CONFIDENTIALITY_REDACTED`: Source record explicitly states that key technical details or problem formulation are confidential or redacted.
7. `ACCESS_NOT_PUBLIC`: Record requires user credentials, active login, paywall access, or bot-mitigation bypass.

### 2.6 Absolute Prohibition of Outcome-Dependent Selection
> **No candidate demand may be included or excluded based on retrieved patents, ranking scores, relevance judgments, expected benchmark difficulty, or any downstream matching result.**

All candidate filtering decisions must occur strictly at the acquisition and policy validation boundary prior to candidate pooling and retrieval execution.

### 2.7 Language Invariant
Language is not an exclusion criterion per se. Solicitations formulated in European languages (English, Spanish, Italian, German, French, etc.) are valid candidates. The original text is preserved immutable; any downstream translation or normalization must be documented as an auditable transformation distinct from source text.

### 2.8 UNKNOWN Organization Policy & Dev/Test Split Preservation
* **Quarantine Policy (ADR 0030):** All `UNKNOWN` organization demands are quarantined strictly to `Dev` (`unknown_split_policy = "dev_only"`). Test contains strictly zero `UNKNOWN` demands; 100% of Test demands are demonstrated `INDEPENDENT`.
* **Historical Split Preservation:** `devtest_split_n18_v2.json` remains immutable as a historical audit artifact.
* **Global Resplit for Expanded Corpus (PR #103):** Once the expanded corpus is frozen and audited in PR #102, a global deterministic resplit will be computed in PR #103 using ADR 0030's `organization_aware_split` algorithm, yielding `devtest_split_v3.json`.

---

## 3. Architectural Boundaries & Technical Contracts

Per ADR 0008, ADR 0009, and ADR 0026:
1. **Declarative Policy Configuration:** All acquisition boundaries, permitted sources, temporal bounds, and monitoring thresholds are stored in `config/policies/data/corpus_expansion_policy_v1.json`, guarded by a SHA-256 sidecar (`corpus_expansion_policy_v1.sha256`).
2. **Domain Models (`backend/src/main/domain/models/corpus_expansion.py`):** Immutable Pydantic models (`CorpusExpansionPolicy`, `DemandCandidateContractRecord`, `CandidateValidationResult`, `CandidateRejectionReason`) define types, invariants, and canonical candidate schemas.
3. **Application Validator (`backend/src/main/application/corpus/expansion_policy_validator.py`):**
   - `load_corpus_expansion_policy`: Enforces fail-fast integrity (raising `PolicyIntegrityError` or `FileNotFoundError` on corrupt or missing policy).
   - `validate_demand_candidate`: Evaluates candidate compliance deterministically, returning exhaustive rejection reasons in stable order without side effects.
4. **Provider-Agnostic Core:** Neither `domain` nor `application` contains HTTP clients, web scrapers, HTML parsers, or network dependencies. Acquisition scripts exist exclusively in experiment tooling boundaries (PR #101).

---

## 4. Experimental Milestones & PR Sequencing

The expansion and evaluation pipeline is strictly decomposed into decoupled, sequential PRs:

1. **PR #101a (Current):** Frozen corpus expansion contract, declarative policy configuration (`corpus_expansion_policy_v1.json`), canonical candidate record contract, typed policy validator, and ADR 0031. Zero new data records.
2. **PR #101:** Data acquisition against the frozen contract. Produces raw acquired candidates and partitions them deterministically into `POLICY_ACCEPTED` and `POLICY_REJECTED` candidate sets with exhaustive exclusion reasons.
3. **PR #102:** Multidimensional independence audit over accepted candidates (organization, sector, technology-family, and duplicate industrial problem). Resolves `INDEPENDENT`, `PSEUDOREPLICATE`, and `UNKNOWN` status. Evaluates corpus sufficiency ($N_{\mathrm{independent}} \ge 60$) and sector concentration ($>0.35 \to \text{CONCENTRATION\_WARNING}$).
4. **PR #103:** Deterministic Dev/Test split freeze (`devtest_split_v3.json`) over the expanded audited corpus using ADR 0030's `organization_aware_split` algorithm, preserving historical `v2` artifacts and enforcing strict UNKNOWN quarantine (`unknown_split_policy = "dev_only"`).
5. **PR #104:** Dual blind multi-expert annotation on the expanded candidate pool and Cohen's $\kappa$ inter-annotator agreement at scale.
6. **PR #105:** Family-aware evaluation integration (`allow`, `collapse`, `exclude_related`) with authentic patent family metadata.
7. **PR #106:** Confirmatory powered efficacy evaluation on the untouched Test split ($H_1$ Wilcoxon signed-rank test on primary endpoint nDCG@10, secondary endpoints with Benjamini–Hochberg FDR control).

---

## 5. Non-Goals & Invariants

1. **Zero Data Acquisition in PR #101a:** No demands are scraped, downloaded, or added in this PR.
2. **No Fallback Policy Synthesis:** In-memory fallback policies are strictly prohibited. Missing or modified policy configuration fails fast.
3. **No Relaxation of Independence:** The exact-match organization independence rule and UNKNOWN quarantine rule from ADR 0029 and ADR 0030 are invariant across all expansion phases.
4. **No Premature Efficacy Claims:** Efficacy evaluation remains strictly blocked until PR #106 executes on the frozen, untouched Test split.
