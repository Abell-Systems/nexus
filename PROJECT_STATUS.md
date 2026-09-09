# Nexus Project Status

> **Overall Status:** `[PASS]` | **Commit:** `093bcc013a7fede9193864cb6c8f658b7ec0f6f7` | **Evaluated At:** `2026-09-09T07:48:34.837778+00:00`

![Status](https://img.shields.io/badge/Project_Status-PASS-brightgreen)

## Executive Summary
Nexus Project Status evaluates to PASS. All required dimensions verified and passed.

---

## Dimensions Summary

| Dimension | Level | Status | Evidence Available | Evidence Source | Message / Metric |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **backend_testing** | `required` | **`PASS`** | ✓ | `pytest-results.xml` | Backend test suites completed successfully: 497 passed, 0 skipped in 497 tests |
| **backend_coverage** | `required` | **`PASS`** | ✓ | `coverage.xml` | Line coverage is 80.24% (threshold: 80.0%) |
| **python_quality** | `required` | **`PASS`** | ✓ | `ruff & mypy CLI` | Python static quality status: PASS |
| **frontend_testing** | `required` | **`PASS`** | ✓ | `frontend/coverage/junit.xml` | Frontend Vitest test suite completed successfully: 40 passed in 40 tests |
| **frontend_coverage** | `required` | **`PASS`** | ✓ | `frontend/coverage/lcov.info` | Frontend line coverage is 90.88% (target: 80.0%) |
| **frontend_quality** | `required` | **`PASS`** | ✓ | `npm run typecheck & npm run lint` | Frontend quality status: PASS |
| **architecture** | `required` | **`PASS`** | ✓ | `scripts/check_architecture.py` | Architecture check passed |
| **documentation** | `required` | **`PASS`** | ✓ | `scripts/check_docs_correctness.py` | Documentation correctness passed |
| **scientific_integrity** | `required` | **`PASS`** | ✓ | `scripts/audit_dataset_identity.py` | Scientific dataset identity, manifests, and temporal integrity verified |
| **sonar_cloud** | `optional` | **`UNVERIFIED`** | ✗ | `environment:SONAR_TOKEN` | SONAR_TOKEN not configured; analysis skipped in this environment |

---

## Detailed Checks

### `backend_testing` (`PASS`)
- `[PASS]` **report_pytest-results** — pytest-results.xml: 497/497 passed (0 failed, 0 errors, 0 skipped)

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
- `[PASS]` **docs_correctness** — Docs correctness gate: PASS (66 markdown files, 24 ADRs checked)

### `scientific_integrity` (`PASS`)
- `[PASS]` **dataset_sha_sidecar** — file=bf7c501f817f... sidecar=['bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453', 'dataset_pilot_benchmark.json']
- `[PASS]` **dataset_sha_manifest** — manifest=bf7c501f817f... file=bf7c501f817f...
- `[PASS]` **manifest_counts** — manifest=(3,15,23) actual=(3,15,23)
- `[PASS]` **no_duplicate_demand_ids** — 3 demands
- `[PASS]` **no_duplicate_patent_ids** — 15 patents
- `[PASS]` **annotations_reference_known_ids** — dangling=[]
- `[PASS]` **embeddings_artifact_sha** — declared=2ba27432607e...
- `[PASS]` **embeddings_dataset_sha** — artifact_ds=bf7c501f817f... dataset=bf7c501f817f...
- `[PASS]` **embeddings_demand_ids** — artifact=['INNOGET-2292', 'INNOGET-2415', 'INNOGET-2501']
- `[PASS]` **embeddings_patent_ids** — artifact=15 dataset=15
- `[PASS]` **embeddings_dimension** — expected_dim=768
- `[PASS]` **snapshots_raw_sha** — manifest=2832dc5936b8... file=2832dc5936b8...
- `[PASS]` **snapshots_count** — manifest=16 jsonl=16
- `[PASS]` **evaluation_subset_of_snapshots** — snapshot_only=['ES-2918450-A1'] evaluation_only=[]
- `[PASS]` **temporal_policy_binding** — policy=(nexus-pilot-16-evaluation-corpus-v1, bf7c501f817f...) actual=(nexus-pilot-16-evaluation-corpus-v1, bf7c501f817f...)
- `[SKIPPED]` **temporal_eligibility** — 3 temporal violations formally accepted as exceptions under ADR-0018/ADR-0019 (accepted_temporal_exception)

### `sonar_cloud` (`UNVERIFIED`)
- `[UNVERIFIED]` **sonar_token_present** — SONAR_TOKEN not set; Sonar Quality Gate is UNVERIFIED

---

## Epistemic Guarantees (ADR 0022)

- **`PASS != "looks good"`**: Affirmative evidence required for every pass.
- **`UNVERIFIED != PASS`**: Absence of evidence is never reported as success.
- **`SKIPPED != UNVERIFIED`**: Explicit precondition omission is distinguished from missing reports.
- **`FAIL = explicit evidence of breach`**: Documents observable non-compliance.
- **`Tests count reflects executed reports`**: The test metric dynamically represents tests executed and recorded in observed JUnit XML artifacts for the specific evaluation run, not a static repository estimate.
- **`Exceptions must be formally explicit`**: Formally exempted legacy conditions (e.g. ADR 0018 §6 frozen temporal violations) evaluate to `SKIPPED`, never masking failures as undocumented passes.

*(Document generated deterministically by `scripts/audit_project_status.py`)*
