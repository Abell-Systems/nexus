# ADR 0029: Demand Independence Audit Contract

**Status:** Accepted  
**Date:** 2026-09-11  
**Scope:** Defines the generic backend contract and experiment derivation for organization-level demand independence, records the Phase 2 audit findings (N=24 eligible → N=18 independent), and formalizes the Dev/Test organization-leakage constraint.

---

## 1. Context & Problem Statement

`docs/roadmap.md` (§6, external scientific-rigor review) identified a critical methodological gap in the Phase-2 benchmark design:
> *"Demand independence audit: the existing Phase-2 audits (#84–#86) check whether each demand is a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). These are different questions; only the first has been done."*

In observational information retrieval benchmarks, treating multiple demands from the same organization as independent observations introduces **pseudoreplication**. An organization submitting multiple solicitations typically shares internal authoring style, vocabulary, technical background, and domain assumptions. Treating five demands from one enterprise as five independent statistical degrees of freedom artificially deflates standard errors and inflates test statistics.

Furthermore, `domain/models/demand.py`'s `RawExtractedDemandFields.organization_raw` and `DemandRecord.requesting_organization` captured authentic organization identity at acquisition time, preserved in `experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.origin_audit.json`. Prior to this ADR, that observed metadata had never been systematically joined against the frozen eligible corpus to evaluate sample independence or split integrity.

---

## 2. Core Scientific Distinctions

### 2.1 Construct Eligibility vs. Demand Independence
* **Construct Eligibility (ADR 0025, #84–#86):** Evaluates whether an individual demand $d \in \mathcal{D}$ represents an authentic, technically articulated industrial technology solicitation (meeting word count, technical clarity, and problem formulation criteria). This answers: *"Is this observation valid?"*
* **Demand Independence (ADR 0029):** Evaluates whether two or more construct-eligible demands are statistically and methodologically independent observations of the underlying matching problem. This answers: *"Are these observations independent replicates?"*

### 2.2 N=24 Eligible vs. N=18 Organization-Independent vs. N=60 Powered Target
* **N=24 Eligible Corpus (`dataset_phase2_eligible_corpus_n24_v1.json`):** The frozen construct-eligible demand universe derived from the N=39 raw acquisition pool.
* **N=18 Organization-Independent Corpus (`dataset_phase2_independent_corpus_v1.json`):** The derived subset after exact-match organization-level deduplication.
* **Critical Principle:** **N=18 is NOT automatically the new powered-study sample.** It is an audit finding and a derived independent corpus, not evidence that the final study target has been satisfied. The pre-registered minimum sample size required for 80% statistical power at standardized effect size $\theta = 0.2$ remains **$|\mathcal{D}| = 60$** (pre-registered in `docs/empirical-study-protocol.md` §3.2 and `data/experiments/power_analysis_wilcoxon.json`). N=18 represents the current un-replicated sample size, highlighting that the statistical power gap is larger than previously visible when pseudoreplicates were pooled.

---

## 3. Decisions & Architectural Contracts

### 3.1 Observed Metadata Only (Accept-Only, Never Inferred)
The generic backend contract accepts organization identity strictly from existing observed metadata (`requesting_organization`).
* No organization identity is ever synthesized, guessed, or inferred.
* Production algorithms must never compute organization identity from demand title, description, CPC codes, or external databases.

### 3.2 Exact String Match Grouping Only
Grouping is strictly exact string match (`a.requesting_organization == b.requesting_organization`).
* **Why fuzzy, text, and semantic duplication detection are deliberately deferred:** Heuristic name-matching (e.g., attempting to merge `"Bax & Company"` and `"Indira from Bax&Co"`) or semantic text similarity over problem descriptions introduces acute circularity risks. Any text-similarity or taxonomic embedding signal strong enough to detect duplicate problem formulations is correlated with the very retrieval and relevance signals that the IR benchmark exists to evaluate. Building an ad-hoc heuristic would contaminate the evaluation harness with unvalidated matching assumptions.

### 3.3 Non-Identifying Placeholder Exclusion List
Known non-identifying sentinel values (such as `"Anonymous Organization"` in InnoGet data, where individual demands are anonymized at source) must not cause unrelated anonymized demands to be clustered together.
* The exclusion list is caller-supplied from experiment configuration (`non_identifying_values`), preserving clean architecture: generic backend code contains zero source-specific literal strings.
* Any observation with `requesting_organization is None` or belonging to `non_identifying_values` receives `independence_group_id = None` and `status = INDEPENDENT`, and is never grouped with other missing/placeholder entries.

### 3.4 Deterministic Representative Selection
When an organization group contains $M > 1$ demands, exactly one representative is designated `INDEPENDENT`, and the remaining $M - 1$ members are designated `PSEUDOREPLICATE`.
* The representative is selected deterministically by lexicographically smallest `demand_id` (mirroring ADR 0027 §2's patent-family collapse tie-break).
* This is a deterministic convention for auditable reproducibility, not a scientific assertion that the selected demand is superior to its group-mates.

### 3.5 Corpus Construction Decision, Not Runtime Evaluation Context
Unlike `family_policy` (ADR 0027), which is a runtime evaluation toggle in `EvaluationExecutionContext`, demand independence is an offline **corpus construction and audit decision**, exactly like construct eligibility. It does not alter `EvaluationExecutionContext`, `DefaultEvaluationRunner`, or ranking models.

---

## 4. Empirical Audit Findings (Phase 2 N=24 Corpus)

Applying the exact-match grouping rule to `dataset_phase2_eligible_corpus_n24_v1.json` via acquisition-time metadata in `dataset_phase2_demand_corpus_n39.origin_audit.json` yields:
* **Total eligible demands:** 24
* **Organization-independent demands:** 18
* **Pseudoreplicate demands:** 6
* **Multi-member organization groups identified:**
  1. **`SMAR3TS`:** 5 demands (`INNOGET-2401`, `INNOGET-2403`, `INNOGET-2404`, `INNOGET-2405`, `INNOGET-2417`).
     - Representative retained: `INNOGET-2401` (`INDEPENDENT`).
     - Excluded: `INNOGET-2403`, `INNOGET-2404`, `INNOGET-2405`, `INNOGET-2417` (`PSEUDOREPLICATE`).
  2. **`Lacer, S.A`:** 3 demands (`INNOGET-2491`, `INNOGET-2492`, `INNOGET-2493`).
     - Representative retained: `INNOGET-2491` (`INDEPENDENT`).
     - Excluded: `INNOGET-2492`, `INNOGET-2493` (`PSEUDOREPLICATE`).
* **Non-identifying / Missing organizations:**
  - `"Anonymous Organization"`: 4 demands (`INNOGET-1625`, `INNOGET-1932`, `INNOGET-1935`, `INNOGET-1972`) — all retained as 4 separate independent observations.
  - `None`: 2 demands (`LOMBARDIA-860`, `LOMBARDIA-947`) — both retained as separate independent observations.
* **Singleton organizations:** 10 organizations appear exactly once (`Bax & Company`, `ALLIANCE project`, `Celsa Group`, `Familia Torres`, `Fundingbox`, `Blue Room Innovation`, `Alberto from Pharmactive Biotech Products`, `Indira from Bax&Co`, `Repsol`, `INDUSAC`).

---

## 5. Critical Dev/Test Leakage Finding & Invariant

### 5.1 Observed Contamination in Frozen Split `devtest_split_n13_v1.json`
Auditing the frozen split `devtest_split_n13_v1.json` against organization membership revealed substantial cross-boundary contamination:
* **`SMAR3TS`:** `INNOGET-2404` is assigned to **Dev**, while `INNOGET-2403` is assigned to **Test**.
* **`Lacer, S.A`:** `INNOGET-2491` is assigned to **Dev**, while `INNOGET-2492` and `INNOGET-2493` are assigned to **Test**.
* **Extent of Contamination:**
  - 100% (2 of 2) of multi-member organization groups present in the split straddle the Dev/Test boundary.
  - 5 out of 13 demands in the split (38.46%) belong to straddling organization groups.
  - 2 of 5 Dev demands (40.0%) and 3 of 8 Test demands (37.5%) are contaminated by sibling demands across the boundary.

### 5.2 Binding Architectural Invariant
> **For the powered efficacy comparison, organization-level independent observations must not cross the Dev/Test boundary.**

The historical split `devtest_split_n13_v1.json` is contaminated at the organization level. It is preserved immutably as a historical artifact, but cannot serve as the evaluation split for the confirmatory powered experiment. Any future split used for powered evaluation must be generated from the independent corpus or enforce organization grouping as a hard stratification boundary.

---

## 6. What Is Enforced Now vs. What Remains Unresolved

### 6.1 Enforced Now
1. Generic domain contracts (`DemandIndependenceStatus`, `DemandOrganizationObservation`, `DemandIndependenceGroupEntry`) in `backend/src/main/domain/models/annotation.py`.
2. Pure grouping function (`derive_independence_groups`) in `backend/src/main/application/annotation/demand_independence.py`.
3. Provenance sidecar for `dataset_phase2_demand_corpus_n39.origin_audit.json.sha256`.
4. Frozen inspectable audit artifact `experiments/wpi-demand-patent-matching/data/phase2_demand_independence_audit_n24_v1.json` with hash sidecar and manifest, encoding group membership, retained/excluded IDs, and Dev/Test leakage quantification.
5. Frozen independent corpus `experiments/wpi-demand-patent-matching/data/dataset_phase2_independent_corpus_v1.json` (N=18) with hash sidecar and manifest.
6. Re-derivation and verification scripts (`check_independence_audit.py`, `check_independent_corpus.py`).

### 6.2 Explicitly Unresolved (Out of Scope for this ADR)
1. **Near-duplicate organization names:** No string normalization is performed. `"Bax & Company"` and `"Indira from Bax&Co"` remain separate singletons.
2. **Sector-level non-independence:** Potential correlation among demands within the same industrial sector is not addressed here.
3. **Technology-family non-independence:** Demand-side technological lineage is unaddressed.
4. **Duplicate industrial problem solicitations:** Independent organizations articulating equivalent technical problems are not detected or deduplicated.
5. **Clean Dev/Test re-partitioning:** Re-generating an un-contaminated split over the independent corpus is deferred to a subsequent dedicated PR.
6. **Sample size expansion:** N=18 does not satisfy the N=60 power requirement; expanding the corpus to reach adequate statistical power remains an open imperative.
