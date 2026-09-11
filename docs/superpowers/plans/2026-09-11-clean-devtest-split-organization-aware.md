# Clean Organization-Aware Dev/Test Split (PR #100) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a clean, deterministic, organization-isolated Dev/Test split over the $N=18$ audited corpus (10 Dev / 8 Test), eliminating the 38.5% historical contamination while leaving historical split `devtest_split_n13_v1.json` untouched.

**Architecture:** Clean Architecture (ADR 0026). A domain-agnostic generic mechanism `organization_aware_split()` in `backend/src/main/application/evaluation/` routes `UNKNOWN` observations to Dev and delegates independent atomic clusters to `stratified_split()`. The WPI experiment layer in `experiments/wpi-demand-patent-matching/` binds the frozen audited corpus ($N=18$) with `base_seed=42`, `dev_fraction=0.5`, producing `devtest_split_n18_v2.json` and a CI verification check.

**Tech Stack:** Python 3.12+, Pydantic v2, standard library `random.Random`, `hashlib`, `json`, pytest.

## Global Constraints

- Historical split `devtest_split_n13_v1.json` must remain 100% untouched.
- Evaluation runner, ranking, and metrics code must not be modified.
- Zero hardcoded domain/policy lists in `backend/src/main` (ADR 0008, ADR 0026).
- Symmetrical tripartite classification (AGENTS.md §3): `UNKNOWN` is not evidence of independence.
- Zero `UNKNOWN` demands in Test (`unknown_split_policy = "dev_only"`).
- Exact-match organization isolation: no observed organization may appear in both Dev and Test.
- Deterministic seeding: `stratum_seed = f"{base_seed}:{stratum}"` with `base_seed = 42`.
- Canonical ASCII sorting of `demand_id` for PRNG input and final JSON serialization.

---

### Task 1: Generic Organization-Aware Split Mechanism (Backend)

**Files:**
- Create: `backend/src/main/application/evaluation/organization_aware_split.py`
- Test: `backend/test/unit/application/test_organization_aware_split.py`

**Interfaces:**
- Consumes:
  - `domain.models.evaluation.DevPartition`
  - `domain.models.evaluation.TestPartition`
  - `application.evaluation.stratified_split.stratified_split`
  - `domain.models.annotation.DemandIndependenceStatus`
- Produces:
  - `organization_aware_split(items, item_id, org_key, status_key, stratum_key, dev_fraction, base_seed, unknown_policy="dev_only") -> OrganizationAwareSplitResult`
  - `OrganizationAwareSplitResult` (frozen Pydantic model with `.dev: DevPartition`, `.test: TestPartition`, `.per_stratum_counts`, `.independent_count`, `.unknown_count`)

- [ ] **Step 1: Write unit tests for `organization_aware_split`**
  Cover:
  - Empty items raises `ValueError`.
  - Duplicate `item_id` raises `ValueError`.
  - Any item with `DemandIndependenceStatus.PSEUDOREPLICATE` raises `ValueError` (fail-fast).
  - Unknown policy other than `"dev_only"` raises `ValueError`.
  - All `UNKNOWN` items land in `Dev`, 0 in `Test`.
  - Items with identical observed organizations are never split across Dev and Test.
  - Reproducibility across multiple runs with identical `base_seed`.
  - Singleton strata place items in Test under feasibility floor ($n_s=1 \implies \text{test}=1$).

- [ ] **Step 2: Run test to confirm failure**
  `pytest backend/test/unit/application/test_organization_aware_split.py -v` (Must fail with ModuleNotFoundError).

- [ ] **Step 3: Implement `organization_aware_split.py`**
  - Implement validation (non-empty, unique IDs, no pseudoreplicates, dev_fraction in (0, 1), integer base_seed).
  - Filter items where `status_key(item) == DemandIndependenceStatus.UNKNOWN`: append to `dev_unknown_ids`.
  - For `INDEPENDENT` items: verify no two items share the same non-None organization string.
  - Call `stratified_split` on independent items with stratum = `stratum_key(item)`, `dev_fraction=dev_fraction`, `seed=base_seed`.
  - Combine `dev = sorted(dev_unknown_ids + list(res.dev.demand_ids))` and `test = sorted(res.test.demand_ids)`.
  - Return frozen `OrganizationAwareSplitResult`.

- [ ] **Step 4: Run test to confirm passing**
  `pytest backend/test/unit/application/test_organization_aware_split.py -v` (Must pass).

- [ ] **Step 5: Run ruff and mypy**
  `ruff check backend/src/main backend/test/unit`
  `python -m mypy backend/src/main`

- [ ] **Step 6: Commit Task 1**
  `git add backend/src/main/application/evaluation/organization_aware_split.py backend/test/unit/application/test_organization_aware_split.py`
  `git commit -m "feat(evaluation): generic organization-aware split mechanism (ADR 0030)"`

---

### Task 2: Experiment Configuration, Generator, and Frozen Artifacts

**Files:**
- Create: `experiments/wpi-demand-patent-matching/config/devtest_split_v2.json`
- Create: `experiments/wpi-demand-patent-matching/config/devtest_split_v2.sha256`
- Create: `experiments/wpi-demand-patent-matching/checks/generate_devtest_split_v2.py`
- Create: `experiments/wpi-demand-patent-matching/data/devtest_split_n18_v2.json`
- Create: `experiments/wpi-demand-patent-matching/data/devtest_split_n18_v2.sha256`
- Create: `experiments/wpi-demand-patent-matching/data/devtest_split_n18_v2.manifest.json`

**Interfaces:**
- Consumes:
  - `experiments/wpi-demand-patent-matching/data/dataset_phase2_organization_audited_corpus_v1.json`
  - `experiments/wpi-demand-patent-matching/data/phase2_demand_independence_audit_n24_v1.json`
  - `experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json`
  - `application.evaluation.organization_aware_split.organization_aware_split`
- Produces:
  - `devtest_split_n18_v2.json` ($N=18$: 10 Dev, 8 Test)

- [ ] **Step 1: Create config file `devtest_split_v2.json` and its sha256 sidecar**
  Pins:
  - `corpus_sha256`
  - `audit_sha256`
  - `assignments_sha256`
  - `base_seed = 42`
  - `dev_fraction = 0.5`
  - `unknown_split_policy = "dev_only"`
  - `stratification_key = "sector_code"`
  - `missing_stratum = "_NO_SECTOR"`

- [ ] **Step 2: Implement generator script `generate_devtest_split_v2.py`**
  - Verifies sidecars of all input artifacts.
  - Verifies input sha256 pins in `devtest_split_v2.json`.
  - Loads 18 demands from `dataset_phase2_organization_audited_corpus_v1.json`.
  - Maps status from `phase2_demand_independence_audit_n24_v1.json` (12 INDEPENDENT, 6 UNKNOWN).
  - Maps sector from `sector_assignments_n24_v1.json` (missing $\to$ `_NO_SECTOR`).
  - Calls `organization_aware_split`.
  - Writes `devtest_split_n18_v2.json` formatted with indent=2 and trailing newline.
  - Generates `.sha256` and `.manifest.json`.

- [ ] **Step 3: Run generator script to produce frozen artifacts**
  `python experiments/wpi-demand-patent-matching/checks/generate_devtest_split_v2.py`

- [ ] **Step 4: Verify generated outputs match exact specification**
  - Dev contains 10 IDs: `INNOGET-1607`, `INNOGET-1625`, `INNOGET-1726`, `INNOGET-1932`, `INNOGET-1935`, `INNOGET-1972`, `INNOGET-2301`, `INNOGET-2401`, `LOMBARDIA-860`, `LOMBARDIA-947`.
  - Test contains 8 IDs: `INNOGET-1605`, `INNOGET-1689`, `INNOGET-1870`, `INNOGET-1965`, `INNOGET-2006`, `INNOGET-2173`, `INNOGET-2258`, `INNOGET-2491`.
  - Check historical split `devtest_split_n13_v1.json` was not modified (`git diff experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json` is empty).

- [ ] **Step 5: Commit Task 2**
  `git add experiments/wpi-demand-patent-matching/config/devtest_split_v2.* experiments/wpi-demand-patent-matching/checks/generate_devtest_split_v2.py experiments/wpi-demand-patent-matching/data/devtest_split_n18_v2.*`
  `git commit -m "data(lab): generate clean organization-isolated Dev/Test split v2 (N=18)"`

---

### Task 3: Independent Check Gate, Protocol, Roadmap, and ADR 0030

**Files:**
- Create: `experiments/wpi-demand-patent-matching/checks/check_devtest_split_v2.py`
- Create: `docs/adr/0030-clean-organization-aware-devtest-split.md`
- Modify: `docs/empirical-study-protocol.md`
- Modify: `docs/roadmap.md`

**Interfaces:**
- `check_devtest_split_v2.py`: exits 0 on valid invariants, non-zero on any violation.
- ADR 0030: binding architectural record of the split contract.

- [ ] **Step 1: Implement check script `check_devtest_split_v2.py`**
  Verifies:
  1. Sidecars `.sha256` match artifact bytes.
  2. $Dev \cap Test = \emptyset$.
  3. $Dev \cup Test = \text{Audited Corpus}$ ($N=18$).
  4. $Test \cap UNKNOWN = \emptyset$ (every Test observation belongs strictly to `INDEPENDENT`).
  5. $\text{Orgs}(Dev \cap INDEPENDENT) \cap \text{Orgs}(Test) = \emptyset$.
  6. Re-derivation via `organization_aware_split()` matches `devtest_split_n18_v2.json` byte-for-byte.
  7. Historical split `devtest_split_n13_v1.json` sha256 matches its sidecar.

- [ ] **Step 2: Run check script to verify pass**
  `python experiments/wpi-demand-patent-matching/checks/check_devtest_split_v2.py`

- [ ] **Step 3: Create ADR 0030 (`docs/adr/0030-clean-organization-aware-devtest-split.md`)**
  - Header: Status: Accepted, Date: 2026-09-11.
  - Context: 38.5% historical leakage finding from ADR 0029.
  - Decision: Option A′ contract ($N=18$, `unknown_split_policy = "dev_only"`, $N=8$ verified independent Test, $N=10$ Dev).
  - Invariants and non-goals.

- [ ] **Step 4: Update `docs/empirical-study-protocol.md` and `docs/roadmap.md`**
  - Protocol §3: Reference the new clean split `devtest_split_n18_v2.json` and ADR 0030, explaining the historical audit and transition to uncontaminated evaluation.
  - Roadmap: Mark clean organization-aware Dev/Test split milestone complete.

- [ ] **Step 5: Run full verification suite**
  - `python3 scripts/check_docs_correctness.py`
  - `ruff check .`
  - `python -m mypy backend/src/main`
  - `python scripts/check_architecture.py`
  - `PYTHONPATH=backend/src/main lint-imports`
  - `pytest backend/test/unit -q`
  - `python experiments/wpi-demand-patent-matching/checks/check_devtest_split_v2.py`

- [ ] **Step 6: Commit Task 3**
  `git add experiments/wpi-demand-patent-matching/checks/check_devtest_split_v2.py docs/adr/0030-clean-organization-aware-devtest-split.md docs/empirical-study-protocol.md docs/roadmap.md`
  `git commit -m "feat(evaluation): independent check gate, ADR 0030, and protocol update for clean split v2"`
