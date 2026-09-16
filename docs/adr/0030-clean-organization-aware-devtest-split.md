# ADR 0030: Clean Organization-Aware Dev/Test Split Contract

**Status:** Accepted  
**Date:** 2026-09-11  
**Scope:** Defines the generic application contract and experimental instantiation for a clean, deterministic, organization-isolated Dev/Test split over the Phase 2 organization-audited demand corpus ($N=18$), resolves the historical 38.5% experimental contamination, guarantees zero cross-partition organizational leakage, and establishes the "UNKNOWN to Dev" quarantine policy.

---

## 1. Context & Problem Statement

In ADR 0029 (#99), an exact-match organization independence audit of the Phase 2 construct-eligible demand corpus ($N=24$) uncovered a critical flaw in the historical split (`devtest_split_n13_v1.json`):
* **38.5% cross-partition leakage:** 5 of 13 observations in the historical split were contaminated by organizational pseudoreplication.
* **100% of multi-demand organizations crossed partitions:** Both `SMAR3TS` and `Lacer, S.A` had demands simultaneously assigned to `Dev` and `Test`.

Evaluating ranking or retrieval performance on test demands that share an organization with development/tuning demands violates sample independence, threatening the validity of confirmatory empirical claims.

To resolve this issue while maintaining scientific reproducibility, this ADR defines the clean Dev/Test split contract (**Option A′**), replacing the contaminated historical split for all future Phase 2 evaluation runs while preserving the historical split artifact as an immutable audit record.

---

## 2. Core Decisions & Scientific Invariants

### 2.1 Partition Universe ($N=18$)
The partition universe is strictly the 18 demands of the frozen audited corpus ([`dataset_phase2_organization_audited_corpus_v1.json`](../../experiments/wpi-demand-patent-matching/data/dataset_phase2_organization_audited_corpus_v1.json)):
* **12 `INDEPENDENT` demands:** Verified independent organizations.
* **6 `UNKNOWN` demands:** Indeterminate organization independence (4 `"Anonymous Organization"` + 2 `None`).

### 2.2 Strict UNKNOWN Quarantine to Dev (`unknown_split_policy = "dev_only"`)
Per AGENTS.md §3 (*Symmetrical Tripartite Classification*), absence of evidence is not proof of independence. Because anonymous or missing organization identities cannot be demonstrated to be independent from one another or from named organizations:
1. All 6 `UNKNOWN` demands are routed deterministically to **Dev**.
2. `UNKNOWN` demands consume **zero PRNG state**.
3. **Test contains strictly zero `UNKNOWN` demands; every Test observation belongs to the `INDEPENDENT` audit class.**

This ensures that the Test partition contains exclusively observations whose organizational independence is evidenced by observed metadata.

### 2.3 Priority Hierarchy of the Split
Constraints are enforced in strict hierarchical priority:
1. **Organization Isolation (Hard Invariant):** Zero observed organizations shared between Dev and Test.
2. **UNKNOWN Treatment (Hard Policy):** Routed 100% to Dev; zero in Test.
3. **Determinism (Hard Invariant):** Isolated PRNG and canonical ASCII sort eliminate environment nondeterminism.
4. **Existing Stratification Primitives (ADR 0026):** Reuse existing `stratified_split()` mechanism; no ad-hoc allocators.
5. **Sector Balance:** Secondary objective, subject to feasibility floors.

### 2.4 Deterministic Seeding & Feasibility Floor
* **Base Seed:** Fixed at `base_seed = 42`.
* **Stratum Seed:** Isolated per stratum via `f"{base_seed}:{stratum}"` (e.g. `"42:BIOTECHNOLOGY"`, `"42:_NO_SECTOR"`).
* **Pre-Sort:** Ascending lexicographical sort by `demand_id` before Fisher–Yates permutation.
* **Feasibility Floor Allocation:**
  $$\text{dev\_count}_S = \begin{cases} 0 & \text{if } |M_S| = 1 \\ \lfloor 0.5 \times |M_S| + 0.5 \rfloor & \text{if } |M_S| > 1 \end{cases}$$
  Singleton strata ($|M_S|=1$: Metallurgy, Industrial Machinery, Energy Storage, Sanitary Materials) allocate their single item to Test. Multi-item strata ($|M_S|=2$: Biotechnology; $|M_S|=6$: `_NO_SECTOR`) split 50/50.
* **Output Serialization:** Partitions are serialized with `demand_ids` sorted in canonical ascending ASCII order.

---

## 3. Concrete Partition Outcome ($N=18$)

| Partition | Total Demands | Verified Independent | Unknown (`dev_only`) | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Dev** | **10** | 4 | 6 | Tuning & development set |
| **Test** | **8** | 8 | 0 | 100% verified independent organizations |
| **Total** | **18** | **12** | **6** | Zero organization leakage |

### Concrete Demand IDs
* **Dev ($N=10$):** `INNOGET-1607`, `INNOGET-1625`, `INNOGET-1726`, `INNOGET-1932`, `INNOGET-1935`, `INNOGET-1972`, `INNOGET-2301`, `INNOGET-2401`, `LOMBARDIA-860`, `LOMBARDIA-947`
* **Test ($N=8$):** `INNOGET-1605`, `INNOGET-1689`, `INNOGET-1870`, `INNOGET-1965`, `INNOGET-2006`, `INNOGET-2173`, `INNOGET-2258`, `INNOGET-2491`

---

## 4. Architectural Boundaries (ADR 0026 Compliance)

* **Generic Application Layer:** `backend/src/main/application/evaluation/organization_aware_split.py` implements the generic algorithm accepting callables (`item_id`, `org_key`, `status_key`, `stratum_key`). It contains zero knowledge of WPI sector names, corpus sizes, or hardcoded seed values.
* **Domain Layer:** Reuses frozen `DevPartition` and `TestPartition` from `domain/models/evaluation.py`.
* **Experiment Layer:** `experiments/wpi-demand-patent-matching/` binds versioned configuration (`config/devtest_split_v2.json`), generates the frozen artifact (`data/devtest_split_n18_v2.json`), and enforces verification via `checks/check_devtest_split_v2.py`.

---

## 5. Non-Goals & Invariants

1. **Historical Split Preserved:** `devtest_split_n13_v1.json` is preserved as an immutable historical artifact demonstrating the 38.5% contamination finding.
2. **Untouched Runner & Metrics:** `EvaluationExecutionContext`, `DefaultEvaluationRunner`, ranking algorithms, and metric evaluators are unchanged.
3. **No Inferred Identities:** Organization matching is strictly exact string equality on observed metadata; zero fuzzy matching or corporate name heuristics.
4. **No Statistical Power Claim:** $N=8$ Test demands does not satisfy the pre-registered confirmatory sample target ($N=60$).
