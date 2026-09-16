# Clean Dev/Test Split with Organization Isolation (PR #100) — Design

**Status:** Proposed  
**Context:** Resolves experimental contamination discovered in ADR 0029 (#99) where the historical split `devtest_split_n13_v1.json` exhibited 38.5% cross-partition leakage. Replaces the contaminated split for future Phase 2 evaluation runs while preserving the historical split as an immutable audit record.  
**Binding Directives:** AGENTS.md §1–§4, ADR 0026 (Experiment/Domain Separation), ADR 0029 (Demand Independence Audit Contract).

---

## 1. Scientific Problem & Motivation

In PR #99 (ADR 0029), an exact-match organization independence audit of the eligible demand universe ($N=24$) revealed that the historical split `devtest_split_n13_v1.json` suffered from **38.5% cross-partition leakage**:
* **2 of 2** multi-demand organizations crossed the partition boundary.
* **5 of 13** observations in the split were contaminated by organizational pseudoreplication (e.g. `Lacer, S.A` had demands in both Dev and Test; `SMAR3TS` had demands in both Dev and Test).

Testing a model on demands originating from the same organization whose demands were used for development/tuning violates observation independence, inflating apparent generalization.

Closing this methodological flaw is scientifically mandatory before scaling the corpus toward $N=60$ or conducting confirmatory testing.

---

## 2. Scope & Invariants (Option A′ Contract)

### 2.1 Partition Universe ($N=18$)
The partition universe is strictly the 18 demands of the frozen audited corpus:
* Input artifact: `dataset_phase2_organization_audited_corpus_v1.json` ($N=18$).
* Confirmed independent observations: exactly the 12 `INDEPENDENT` demands.
* Indeterminate observations: the 6 `UNKNOWN` demands (4 `"Anonymous Organization"` + 2 `None`).

### 2.2 Treatment of `UNKNOWN` (`unknown_split_policy = "dev_only"`)
Absence of evidence is not proof of independence (AGENTS.md §3). Anonymized or missing organization metadata cannot be presumed independent of each other or of named organizations:
* Demands with `DemandIndependenceStatus.UNKNOWN` are deterministically routed to **Dev**.
* `UNKNOWN` demands **never consume PRNG state**.
* **Test contains strictly zero `UNKNOWN` demands**: every Test observation belongs to the `INDEPENDENT` audit class.

### 2.3 Priority Hierarchy
The split algorithm enforces constraints in strict order of priority:
1. **Organization Isolation (Hard Invariant):** Zero observed organizations shared between Dev and Test.
2. **UNKNOWN Treatment (Hard Policy):** Routed 100% to Dev; zero in Test.
3. **Determinism (Hard Invariant):** Seed and canonical sort eliminate all runtime or environment nondeterminism.
4. **Existing Stratification Primitives (ADR 0026):** Reuse existing vetted `stratified_split()` mechanism; no new ad-hoc allocator.
5. **Sector Balance:** Secondary objective, subject to feasibility floors.

---

## 3. Architecture & Clean Architecture Separation (ADR 0026)

Following ADR 0026 and ADR 0029, code and policy are strictly decoupled:

```text
backend/src/main
  domain/models/evaluation.py
    └── DevPartition, TestPartition (frozen structural types, immutable demand_ids tuple)
  application/evaluation/organization_aware_split.py
    └── organization_aware_split() (generic application service composing UNKNOWN routing
        and atomic stratified_split across independent clusters)

experiments/wpi-demand-patent-matching
  config/
    ├── devtest_split_v2.json          (versioned configuration: dev_fraction, base_seed, policies)
    └── devtest_split_v2.sha256
  data/
    ├── devtest_split_n13_v1.json      (HISTORICAL ARTIFACT: UNTOUCHED, IMMUTABLE AUDIT RECORD)
    ├── devtest_split_n18_v2.json      (NEW FROZEN ARTIFACT: N=18 clean organization-isolated split)
    ├── devtest_split_n18_v2.sha256
    └── devtest_split_n18_v2.manifest.json
  checks/
    ├── generate_devtest_split_v2.py   (deterministic generator from pinned inputs)
    └── check_devtest_split_v2.py      (independent verification gate for CI and local verification)
```

**Zero Hardcoded Domain Data in Backend:**  
`backend/src/main` knows nothing of WPI sector names, `N=18`, `seed=42`, or `0.5`. All policies are injected via callers from versioned experiment configuration.

---

## 4. Algorithmic Specification

### 4.1 Input Parameters
* `items`: Sequence of items $T$.
* `item_id`: $T \to \text{str}$ (unique identifier).
* `org_key`: $T \to \text{str} \mid \text{None}$ (observed organization string).
* `status_key`: $T \to \text{DemandIndependenceStatus}$ (`INDEPENDENT`, `UNKNOWN`, `PSEUDOREPLICATE`).
* `stratum_key`: $T \to \text{str}$ (sector label or fallback, e.g. `"_NO_SECTOR"`).
* `dev_fraction`: float in $(0, 1)$ (e.g. `0.5`).
* `base_seed`: int (e.g. `42`).
* `unknown_policy`: `"dev_only"`.

### 4.2 Step-by-Step Procedure

1. **Validation & Fail-Fast:**
   * Assert `items` is non-empty and all `item_id`s are strictly unique.
   * If any item has `status == PSEUDOREPLICATE`, raise an immediate `ValueError` (the audited corpus must contain no pseudoreplicates).

2. **Partition UNKNOWN Observations:**
   * Partition items where `status_key(item) == DemandIndependenceStatus.UNKNOWN` directly into `Dev`.
   * Record `dev_unknown_ids = [item_id(item) for item in unknown_items]`.
   * These items consume zero PRNG draws.

3. **Cluster Independent Observations:**
   * For items with `status_key(item) == DemandIndependenceStatus.INDEPENDENT`:
     * Verify that no two independent items share the same observed organization string. (Each independent organization is an atomic unit).
   * Group independent items by stratum $S = \text{stratum\_key}(item)$.

4. **Deterministic Per-Stratum Stratification (ADR 0026):**
   * For each stratum $S$ with members $M_S$:
     * Pre-sort members in ascending lexicographical order by `item_id`:
       $$\text{ordered}_S = \text{sorted}(M_S, \text{key}=\text{item\_id})$$
     * Construct isolated stratum PRNG:
       $$\text{stratum\_seed} = f"\{\text{base\_seed}\}:\{S\}"$$
       $$\text{rng}_S = \text{random.Random}(\text{stratum\_seed})$$
     * Compute Dev count using the feasibility floor:
       $$\text{dev\_count}_S = \begin{cases} 0 & \text{if } |M_S| = 1 \\ \lfloor \text{dev\_fraction} \times |M_S| + 0.5 \rfloor & \text{if } |M_S| > 1 \end{cases}$$
       (Ensuring $1 \le \text{dev\_count}_S < |M_S|$ when $|M_S| > 1$).
     * Apply Fisher-Yates shuffle:
       $$\text{shuffled}_S = \text{ordered}_S[:] ; \quad \text{rng}_S.\text{shuffle}(\text{shuffled}_S)$$
     * Slice:
       $$\text{stratum\_dev}_S = \text{shuffled}_S[:\text{dev\_count}_S]$$
       $$\text{stratum\_test}_S = \text{shuffled}_S[\text{dev\_count}_S:]$$

5. **Assembly & Canonical Serialization:**
   * $\text{Dev} = \text{sorted}(\text{dev\_unknown\_ids} \cup \bigcup_S \text{stratum\_dev}_S)$
   * $\text{Test} = \text{sorted}(\bigcup_S \text{stratum\_test}_S)$
   * Return `DevPartition` and `TestPartition`.

---

## 5. Concrete Output on Audited Corpus ($N=18$, seed=42, dev_fraction=0.5)

### 5.1 Stratum Counts

| Stratum | Total Audited | Dev | Test | Notes |
| :--- | :---: | :---: | :---: | :--- |
| `BIOTECHNOLOGY` | 2 | 1 | 1 | Multi-item stratum split 50/50 |
| `METALLURGY` | 1 | 0 | 1 | Singleton stratum $\to$ Test |
| `INDUSTRIAL_MACHINERY_IOT` | 1 | 0 | 1 | Singleton stratum $\to$ Test |
| `ENERGY_STORAGE` | 1 | 0 | 1 | Singleton stratum $\to$ Test |
| `SANITARY_MATERIALS` | 1 | 0 | 1 | Singleton stratum $\to$ Test |
| `_NO_SECTOR` | 6 | 3 | 3 | Multi-item stratum split 50/50 |
| **Independent Subtotal** | **12** | **4** | **8** | Verified independent degrees of freedom |
| **UNKNOWN (`dev_only`)** | **6** | **6** | **0** | Quarantined to Dev |
| **Total Corpus** | **18** | **10** | **8** | Exact deterministic allocation |

### 5.2 Exact Partition Allocations

* **Dev Partition ($N=10$):**
  * Verified Independent ($N=4$):
    * `INNOGET-1607` (`ALLIANCE project`, `_NO_SECTOR`)
    * `INNOGET-1726` (`Familia Torres`, `BIOTECHNOLOGY`)
    * `INNOGET-2301` (`INDUSAC`, `_NO_SECTOR`)
    * `INNOGET-2401` (`SMAR3TS`, `_NO_SECTOR`)
  * Unknown ($N=6$):
    * `INNOGET-1625` (`Anonymous Organization`, `_NO_SECTOR`)
    * `INNOGET-1932` (`Anonymous Organization`, `_NO_SECTOR`)
    * `INNOGET-1935` (`Anonymous Organization`, `INDUSTRIAL_MACHINERY_IOT`)
    * `INNOGET-1972` (`Anonymous Organization`, `BIOTECHNOLOGY`)
    * `LOMBARDIA-860` (`None`, `_NO_SECTOR`)
    * `LOMBARDIA-947` (`None`, `INDUSTRIAL_MACHINERY_IOT`)

* **Test Partition ($N=8$ — 100% `INDEPENDENT` audit class):**
  * `INNOGET-1605` (`Bax & Company`, `_NO_SECTOR`)
  * `INNOGET-1689` (`Celsa Group`, `METALLURGY`)
  * `INNOGET-1870` (`Fundingbox`, `INDUSTRIAL_MACHINERY_IOT`)
  * `INNOGET-1965` (`Blue Room Innovation`, `_NO_SECTOR`)
  * `INNOGET-2006` (`Alberto from Pharmactive Biotech Products`, `BIOTECHNOLOGY`)
  * `INNOGET-2173` (`Indira from Bax&Co`, `_NO_SECTOR`)
  * `INNOGET-2258` (`Repsol`, `ENERGY_STORAGE`)
  * `INNOGET-2491` (`Lacer, S.A`, `SANITARY_MATERIALS`)

---

## 6. Manifest & Traceability Contract

The split manifest `devtest_split_n18_v2.manifest.json` records complete audit provenance:

```json
{
  "split_dataset_id": "nexus-phase2-devtest-split-n18-v2",
  "total_demands": 18,
  "independent_demands": 12,
  "unknown_demands": 6,
  "dev_count": 10,
  "test_count": 8,
  "dev_verified_independent_count": 4,
  "test_verified_independent_count": 8,
  "split_policy": "organization_aware_stratified",
  "unknown_split_policy": "dev_only",
  "stratification_key": "sector",
  "missing_stratum": "_NO_SECTOR",
  "dev_fraction": 0.5,
  "base_seed": 42,
  "atomic_unit": "demand",
  "organization_isolation": "exact",
  "organization_overlap": false,
  "content_sha256": "...",
  "derived_from": {
    "corpus": "dataset_phase2_organization_audited_corpus_v1.json",
    "corpus_sha256": "...",
    "audit": "phase2_demand_independence_audit_n24_v1.json",
    "audit_sha256": "...",
    "sectors": "sector_assignments_n24_v1.json",
    "sectors_sha256": "...",
    "config": "devtest_split_v2.json",
    "config_sha256": "..."
  }
}
```

---

## 7. Machine-Verifiable Invariants (Independent Check Gate)

`experiments/wpi-demand-patent-matching/checks/check_devtest_split_v2.py` must verify in CI:
1. **$Dev \cap Test = \emptyset$**: Zero demand overlap.
2. **$Dev \cup Test = \text{Audited Corpus}$**: Exact set equality with the 18 audited demands.
3. **$Test \cap UNKNOWN = \emptyset$**: Zero unknown or missing organization observations in Test. Every Test observation belongs strictly to `INDEPENDENT`.
4. **$\text{Orgs}(Dev \cap INDEPENDENT) \cap \text{Orgs}(Test) = \emptyset$**: Zero verified organization overlap between Dev and Test.
5. **Exact Re-Derivation**: Running the algorithm against the pinned configuration reproduces the committed JSON byte-for-byte.
6. **Sidecar Integrity**: All `.sha256` sidecars pass verification.

---

## 8. Non-Goals & Explicit Exclusions

* **Historical Split Untouched:** `devtest_split_n13_v1.json` is preserved as an immutable historical artifact demonstrating the 38.5% contamination finding.
* **No Runner / Metric Modification:** `EvaluationExecutionContext`, `DefaultEvaluationRunner`, and ranking/metrics algorithms are completely untouched.
* **No Fuzzy Org Matching:** Grouping and isolation are strictly exact string equality on observed metadata.
* **No Sector Inference:** Demands without sector assignments remain `_NO_SECTOR`.
* **No Heuristic Optimization:** No seed hunting, greedy balancing, or manual reallocations.
* **No Power Claim:** The resulting $N=8$ Test sample is an audited partition of the current pilot universe; it does not satisfy the pre-registered confirmatory sample size of $N=60$.
