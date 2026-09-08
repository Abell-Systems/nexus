# Nexus Project Status

> **Overall Status:** `[PASS]` | **Commit:** `2ef0d1b057768b4ceda4b171158dee91f5cc6dd8` | **Evaluated At:** `2026-09-08T16:49:26.613418+00:00`

![Status](https://img.shields.io/badge/Project_Status-PASS-brightgreen)

## Executive Summary
Nexus Project Status evaluates to PASS. All required dimensions verified and passed.

---

## Dimensions Summary

| Dimension | Level | Status | Evidence Available | Evidence Source | Message / Metric |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **backend_testing** | `required` | **`PASS`** | ✓ | `pytest-results.xml` | Backend test suites completed successfully: 491 passed, 0 skipped in 491 tests |
| **backend_coverage** | `required` | **`PASS`** | ✓ | `coverage.xml` | Line coverage is 80.24% (threshold: 80.0%) |
| **python_quality** | `required` | **`PASS`** | ✓ | `ruff & mypy CLI` | Python static quality status: PASS |
| **frontend_testing** | `required` | **`PASS`** | ✓ | `frontend/coverage/junit.xml` | Frontend Vitest test suite completed successfully: 40 passed in 40 tests |
| **frontend_coverage** | `required` | **`PASS`** | ✓ | `frontend/coverage/lcov.info` | Frontend line coverage is 90.88% (target: 80.0%) |
| **frontend_quality** | `required` | **`PASS`** | ✓ | `npm run typecheck & npm run lint` | Frontend quality status: PASS |
| **architecture** | `required` | **`PASS`** | ✓ | `scripts/check_architecture.py` | Architecture check passed |
| **documentation** | `required` | **`PASS`** | ✓ | `scripts/check_docs_correctness.py` | Documentation correctness passed |
| **scientific_integrity** | `required` | **`PASS`** | ✓ | `scripts/audit_dataset_identity.py` | Scientific dataset identity and hashes verified |
| **sonar_cloud** | `optional` | **`UNVERIFIED`** | ✗ | `environment:SONAR_TOKEN` | SONAR_TOKEN not configured; analysis skipped in this environment |

---

## Detailed Checks

### `backend_testing` (`PASS`)
- `[PASS]` **report_pytest-results** — pytest-results.xml: 491/491 passed (0 failed, 0 errors, 0 skipped)

### `backend_coverage` (`PASS`)
- `[PASS]` **line_coverage_threshold** — Line coverage is 80.24% (threshold: 80.0%)

### `python_quality` (`PASS`)
- `[PASS]` **ruff_check** — 0 lint errors
- `[PASS]` **mypy_typecheck** — 0 type errors

### `frontend_testing` (`PASS`)
- `[PASS]` **vitest_execution** — 40/40 tests passed (0 failures)

### `frontend_coverage` (`PASS`)
- `[PASS]` **frontend_line_coverage** — 259/285 lines covered

### `frontend_quality` (`PASS`)
- `[PASS]` **tsc_typecheck** — 0 type errors
- `[PASS]` **oxlint** — 0 lint errors

### `architecture` (`PASS`)
- `[PASS]` **clean_architecture_layers** — Architecture check: PASS (Clean Architecture 3-Tier Layer Invariants & Import Linter Contracts Validated)

### `documentation` (`PASS`)
- `[PASS]` **docs_correctness** — Docs correctness gate: PASS (64 markdown files, 22 ADRs checked)

### `scientific_integrity` (`PASS`)
- `[PASS]` **dataset_sha_sidecar**
- `[PASS]` **dataset_sha_manifest**
- `[PASS]` **manifest_counts**
- `[FAIL]` **temporal_eligibility_strict** — 3 frozen violations in pilot

### `sonar_cloud` (`UNVERIFIED`)
- `[UNVERIFIED]` **sonar_token_present** — SONAR_TOKEN not set; Sonar Quality Gate is UNVERIFIED

---

## Epistemic Guarantees (ADR 0022)

- **`PASS != "looks good"`**: Affirmative evidence required for every pass.
- **`UNVERIFIED != PASS`**: Absence of evidence is never reported as success.
- **`SKIPPED != UNVERIFIED`**: Explicit precondition omission is distinguished from missing reports.
- **`FAIL = explicit evidence of breach`**: Documents observable non-compliance.

*(Document generated deterministically by `scripts/audit_project_status.py`)*
