# PR #23: Frozen Evaluation Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a sealed, tamper-evident evaluation boundary and execution context outside production code, connecting PR #22's inferential statistical testing framework to paired demand-level observations over pre-registered M0–M6 hypotheses, verified via a reproducible pilot run.

**Architecture:**
- **Product vs Science Boundary:** Evaluation harness lives outside the product core. Zero modification to `infrastructure/cli.py` and zero modification to `landscape/`.
- **Pre-registered Study Protocol:** Declarative protocol in `config/evaluations/comparisons_m0_m6.json` fixing hypotheses (ID, baseline, treatment, metric, scope, alternative, alpha, seed) before outcome inspection.
- **Protocol Provenance:** Stamping `study_protocol_id` and byte-exact `study_protocol_sha256` alongside dataset, policy, and engine commit hashes.
- **Demand-Level Comparative Evaluator:** Pure `application/evaluation/comparative.py` extracting paired observation vectors across identical `demand_id`s from `EvaluationRunReport` pairs, feeding raw arrays to PR #22 statistical primitives (`paired_wilcoxon_test`, `paired_bootstrap_ci`, `adjust_benjamini_hochberg`).
- **Pilot Execution:** `scripts/run_scientific_evaluation.py` generates `data/experiments/pilot_evaluation_report.json` with explicit `"study_status": "PILOT"`.

**Tech Stack:** Python 3.12 / Pydantic v2 / NumPy / SciPy / pytest / Import Linter / Ruff / Mypy.

---

## Global Constraints
- Preserve all 7 Import Linter contracts in `.importlinter`.
- **Zero changes to `landscape/`** (keep product decoupled from evaluation).
- **Zero changes to `infrastructure/cli.py`** (no `nexus evaluate` CLI feature; research execution belongs in `scripts/run_scientific_evaluation.py`).
- **No speculative models or DTO wrappers:** Re-use PR #22 dataclasses (`WilcoxonResult`, `BootstrapCIResult`, `BenjaminiHochbergResult`). Only introduce models that enforce real boundaries (`StudyHypothesis`, `StudyProtocol`, `ComparativeRunReport`).
- **Fail-fast on mismatched demands:** If baseline and treatment run reports do not have identical `demand_id` sets, raise `ValueError` immediately.
- **Unrounded precision:** Keep exact double-precision floating point in all outputs.
- **Pilot distinction:** Any artifact generated before final freeze must be tagged `"study_status": "PILOT"`.
- ADR 0011 recorded in `docs/adr/0011-frozen-evaluation-boundary-and-comparative-statistical-harness.md`.

---

## File Structure

| File | Role |
| :--- | :--- |
| `docs/adr/0011-frozen-evaluation-boundary-and-comparative-statistical-harness.md` | ADR 0011 documenting frozen boundary, pre-registered M0–M6 protocol, and paired demand-level testing |
| `config/evaluations/comparisons_m0_m6.json` | Pre-registered comparative study protocol and hypotheses for M0–M6 |
| `backend/src/main/domain/models/evaluation.py` | Add `StudyHypothesis`, `StudyProtocol`, and `HypothesisTestResult`, `ComparativeRunReport` |
| `backend/src/main/application/evaluation/comparative.py` | Pure comparative harness extracting paired demand observations and invoking statistical primitives |
| `backend/src/main/application/evaluation/__init__.py` | Clean exports |
| `scripts/run_scientific_evaluation.py` | Enhanced runner supporting protocol verification, execution context stamping, and comparative evaluation |
| `backend/test/unit/application/evaluation/test_frozen_benchmark_invariants.py` | Invariant tests: byte-level integrity, manifest count consistency, tamper rejection, CWD independence |
| `backend/test/unit/application/evaluation/test_comparative_evaluation.py` | Unit tests: demand pairing, missing demand fail-fast, Wilcoxon/bootstrap integration, BH-FDR monotonicity |
| `data/experiments/pilot_evaluation_report.json` | Reproducible pilot evaluation run stamped with `study_status: "PILOT"` |

---

## Tasks

### Task 1: Record ADR 0011 & Pre-registered Study Protocol Configuration

**Files:**
- Create: `docs/adr/0011-frozen-evaluation-boundary-and-comparative-statistical-harness.md`
- Create: `config/evaluations/comparisons_m0_m6.json`
- Test: `backend/test/unit/application/evaluation/test_study_protocol.py`

**Interfaces:**
- Consumes: ADR 0006, ADR 0007, ADR 0010
- Produces: ADR 0011 and validated `config/evaluations/comparisons_m0_m6.json` defining hypotheses H01–H06 across M0–M6 with fixed alpha, seed, and metrics.

- [ ] **Step 1: Write failing test verifying study protocol structure and fail-fast invariants**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Create `docs/adr/0011-...md` and `config/evaluations/comparisons_m0_m6.json`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit ADR 0011 and study protocol**

---

### Task 2: Domain Models for Study Protocol & Comparative Outcome

**Files:**
- Modify: `backend/src/main/domain/models/evaluation.py`
- Test: `backend/test/unit/domain/test_comparative_models.py`

**Interfaces:**
- Consumes: `WilcoxonResult`, `BootstrapCIResult`, `EvaluationRunReport`
- Produces: `StudyHypothesis`, `StudyProtocol`, `HypothesisTestResult`, `ComparativeRunReport`

- [ ] **Step 1: Write failing unit test for `StudyHypothesis`, `StudyProtocol`, `HypothesisTestResult`, and `ComparativeRunReport`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add minimal models to `domain/models/evaluation.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit comparative models**

---

### Task 3: Paired Demand-Level Comparative Evaluator (`comparative.py`)

**Files:**
- Create: `backend/src/main/application/evaluation/comparative.py`
- Modify: `backend/src/main/application/evaluation/__init__.py`
- Test: `backend/test/unit/application/evaluation/test_comparative_evaluation.py`

**Interfaces:**
- Consumes: `EvaluationRunReport`, `StudyProtocol`, `paired_wilcoxon_test`, `paired_bootstrap_ci`, `adjust_benjamini_hochberg`
- Produces: `evaluate_study_protocol(runs: dict[str, EvaluationRunReport], protocol: StudyProtocol) -> ComparativeRunReport`

Key Invariants:
1. Extract paired per-demand vectors ($y_i, x_i$) for each hypothesis matching `(baseline_model, treatment_model)`.
2. Fail fast with `ValueError` if any demand in `baseline.demand_reports` is missing from `treatment.demand_reports` or vice versa.
3. Compute `paired_wilcoxon_test`, `paired_bootstrap_ci`, and pass raw $p$-values to `adjust_benjamini_hochberg` across all hypotheses in the protocol.
4. Zero matching imports, zero infrastructure imports.

- [ ] **Step 1: Write failing tests for `evaluate_study_protocol` covering demand pairing, missing demand fail-fast, and statistical wiring**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `backend/src/main/application/evaluation/comparative.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit comparative evaluator**

---

### Task 4: Scientific Runner & Pilot Artifact Generation

**Files:**
- Modify: `scripts/run_scientific_evaluation.py`
- Create: `data/experiments/pilot_evaluation_report.json`
- Test: `backend/test/unit/application/evaluation/test_frozen_benchmark_invariants.py`

**Interfaces:**
- Consumes: `DefaultEvaluationDatasetLoader`, `DefaultEvaluationRunner`, `evaluate_study_protocol`
- Produces: Verified pilot run output stamped with `"study_status": "PILOT"` and full provenance hashes (dataset SHA, policy SHA, protocol SHA, engine commit).

- [ ] **Step 1: Write frozen benchmark invariant tests (byte-level integrity, manifest counts, tamper rejection, CWD independence)**
- [ ] **Step 2: Run tests to verify they pass**
- [ ] **Step 3: Update `scripts/run_scientific_evaluation.py` to support protocol stamping and pilot output**
- [ ] **Step 4: Execute pilot benchmark to produce `data/experiments/pilot_evaluation_report.json`**
- [ ] **Step 5: Commit pilot artifact and invariant tests**

---

### Task 5: Quality Gate & Architectural Invariant Verification

**Files:**
- Verify: Ruff, Mypy, Import Linter, Full Pytest Suite

- [ ] **Step 1: Run `ruff check .`**
- [ ] **Step 2: Run `mypy backend/src/main`**
- [ ] **Step 3: Run `python scripts/check_architecture.py && PYTHONPATH=backend/src/main lint-imports`**
- [ ] **Step 4: Run full test pipeline (unit + integration + e2e)**
- [ ] **Step 5: Push branch `feature/frozen-evaluation` and open PR #23**
