# ADR 0022: Project Status Contract and Observability Telemetry

**Status:** Accepted  
**Date:** 2026-09-08  
**Scope:** Entire Nexus repository  

## Context

Nexus is both an industrial clean-architecture software system and a reproducible scientific research platform. Its engineering and scientific health are governed by automated quality gates (ADR 0008), invariant tests, and a strict non-regression policy (ADR 0021).

Prior to this decision, individual quality gates (Ruff, Mypy, Vitest, Pytest, Import Linter, SonarCloud, dataset identity audit) produced isolated, heterogeneous signals across CI jobs and terminal outputs without a single, machine-readable, canonical contract. Furthermore, superficial indicators (such as decorative repository badges) risked reporting unverified passes or concealing gaps when evidence was missing.

To establish authentic technical and scientific observability, Nexus requires a formal Project Status contract that:
1. defines a symmetrical, non-binary status vocabulary where absence of evidence is never equated with success;
2. decouples evaluation results from the raw evidence that substantiates them;
3. formalizes a conservative aggregation procedure across required and optional dimensions;
4. specifies a machine-readable JSON schema ([`docs/schemas/project-status-v1.json`](../schemas/project-status-v1.json));
5. establishes a three-tier representation model connecting public README badges directly to underlying auditable evidence.

This ADR intentionally does **not** introduce regression enforcement, historical trend analysis, automated commit loops, or alterations to existing CI failure thresholds. It establishes solely the observational and contract boundary for current-state evaluation.

## Decision

### 1. Symmetrical Canonical Vocabulary

Status evaluation in Nexus MUST adhere to a symmetrical 5-state vocabulary:

* **`PASS`**: Verified positively by direct, deterministic evidence produced during the current evaluation (e.g., exit code 0, 100% passing tests, line coverage strictly meeting or exceeding threshold).
* **`FAIL`**: Verified negatively by direct evidence of non-compliance (e.g., non-zero exit code, test failure, invariant violation, coverage below threshold).
* **`SKIPPED`**: Deliberately and explicitly omitted due to known, documented unsatisfied preconditions (e.g., absence of external credentials such as `SONAR_TOKEN`, or a suite deactivated by explicit configuration flag).
* **`UNVERIFIED`**: Total absence of verified evidence during the current evaluation (e.g., report file not found, check omitted without explicit skip justification).
* **`N/A`**: Formally not applicable to the execution scope or environment (e.g., ADK provider tests in an isolated core-only environment).

#### Binding Epistemic Invariants:
* **`PASS != "looks good"`**: A pass cannot be assumed; it requires affirmative verification evidence.
* **`UNVERIFIED != PASS`**: The absence of evidence is never evidence of compliance. Unverified checks must never be folded into a passing aggregate.
* **`SKIPPED != UNVERIFIED`**: `SKIPPED` acknowledges an explicit, documented omission; `UNVERIFIED` acknowledges missing or uncollected evidence. Neither is a pass.
* **`FAIL = explicit evidence of breach`**: A failure documents observable non-compliance with a stated contract or threshold.

### 2. Separation of Result from Evidence

A status report must never present a naked verdict without its supporting provenance. In the canonical JSON contract, each evaluated dimension MUST report:

```text
status:               PASS | FAIL | SKIPPED | UNVERIFIED | N/A
requirement_level:    required | optional
evidence_source:      File path or tool invocation generating raw data
evidence_available:   true | false
metrics:              Dictionary of scalar measurements extracted directly from evidence
checks:               List of discrete boolean assertions with individual values and thresholds
```

If `evidence_available` is `false`, the dimension status MUST evaluate to `UNVERIFIED` (unless explicitly configured as `SKIPPED` under valid preconditions).

### 3. Canonical Dimensions and Evidence Sources

The repository evaluates ten canonical dimensions grouped under four domains:

| Domain | Dimension Key | Requirement Level | Evidence Source | Passing Criterion |
| :--- | :--- | :---: | :--- | :--- |
| **Backend** | `backend_testing` | `required` | `pytest` execution report | `failed == 0` and `total > 0` |
| **Backend** | `backend_coverage` | `required` | `coverage.xml` | `line-rate >= 0.80` (80.0%) |
| **Backend** | `python_quality` | `required` | `ruff check` & `mypy` | `errors == 0` across all files |
| **Frontend** | `frontend_testing` | `required` | Vitest test report | `failed == 0` and `total > 0` |
| **Frontend** | `frontend_coverage` | `required` | `frontend/coverage/lcov.info` | `line_coverage >= 0.80` (80.0%) |
| **Frontend** | `frontend_quality` | `required` | `oxlint` & `tsc --noEmit` | `errors == 0` and `warnings == 0` |
| **Architecture** | `architecture` | `required` | `scripts/check_architecture.py` | Exit code 0 (AST & `.importlinter`) |
| **Docs** | `documentation` | `required` | `scripts/check_docs_correctness.py` | Exit code 0 (all links & ADRs valid) |
| **Science** | `scientific_integrity`| `required` | `scripts/audit_dataset_identity.py` | Sealed manifests and SHA-256 match |
| **External** | `sonar_cloud` | `optional` | SonarQube Cloud API / CI step output | Quality Gate `OK` (or `SKIPPED`/`UNVERIFIED`) |

### 4. Conservative Aggregation Procedure

The top-level `overall_status` is evaluated deterministically over all dimensions declaring `requirement_level == "required"`:

1. **Failure Precedence:** If **ANY** required dimension has status `FAIL`, `overall_status` MUST evaluate to `FAIL`.
2. **Unverified Precedence:** If no required dimension is `FAIL`, but **ANY** required dimension has status `UNVERIFIED` (or `SKIPPED` where skip is not explicitly permitted for that required dimension), `overall_status` MUST evaluate to `UNVERIFIED`.
3. **Affirmative Pass:** Only when **ALL** required dimensions have status `PASS` does `overall_status` evaluate to `PASS`.
4. **Non-Participating States:** Dimensions with status `N/A` or `requirement_level == "optional"` (such as `sonar_cloud` when unconfigured) do NOT participate in deciding a failure or unverified outcome for `overall_status`.

### 5. Three-Tier Representation Model

To prevent status indicators from becoming decorative or disconnected from reality, Nexus defines three synchronized tiers of observability:

```text
Tier 1: README (Surface)
  └─ Public badges reflecting immediate overall and dimensional state, each linking to Tier 2.

Tier 2: PROJECT_STATUS.md (Human-Auditable Document)
  └─ Complete tabular breakdown, timestamps, metrics, failed checks, and evidence paths.

Tier 3: project_status.json (Machine Contract)
  └─ Deterministic payload conforming to docs/schemas/project-status-v1.json.
```

#### README Badges Specification
Badges displayed on the repository README MUST derive directly from the canonical status contract:
* `[Project Status: PASS | FAIL | UNVERIFIED]`
* `[CI Gates: PASS | FAIL]`
* `[Architecture: PASS | FAIL]`
* `[Backend: PASS | FAIL]`
* `[Frontend: PASS | FAIL]`
* `[Docs: PASS | FAIL]`
* `[Scientific Integrity: PASS | FAIL]`
* `[SonarCloud: PASS | UNVERIFIED | FAIL]`

Every badge MUST link directly to `PROJECT_STATUS.md` or to the corresponding CI workflow execution, never to a static external placeholder.

### 6. Distinction Between Commit Identity and Evaluation Instant

To prevent confusion between code version and audit execution:
* `commit_sha` records the exact Git commit SHA being audited.
* `evaluated_at` records the UTC ISO-8601 timestamp at which the audit script was executed.

An audit may be re-run at a later timestamp for the same `commit_sha` (for example, in a nightly observability job or upon configuring external credentials). The distinction ensures that historical telemetry tracks both the target artifact and the observation event.

## Consequences

### Positive
* Eliminates ambiguity regarding repository health: no hidden failures, no fake passes.
* Protects external consumers and auditors by clearly signaling `UNVERIFIED` when external tools (like SonarCloud) are skipped.
* Unifies frontend, backend, architectural, and scientific quality under a single deterministic contract.
* Prepares the foundation for reproducible historical telemetry (history.jsonl) without modifying CI gating rules.

### Negative / Trade-offs
* Requires maintaining the schema and evidence parsers whenever underlying tool output formats change.
* External contributors without external credentials (e.g. `SONAR_TOKEN`) will observe `sonar_cloud: UNVERIFIED`, which is structurally correct but requires clear documentation to avoid alarm.

## Relationship to Existing ADRs

* **ADR 0001 (Testing Strategy):** ADR 0022 formalizes the aggregation of the multi-tier test suites.
* **ADR 0003 & ADR 0008 (Symmetrical Classification & Architectural Enforcement):** Extends tripartite classification (`POSITIVE`, `NEGATIVE`, `UNVERIFIED`) from domain models into project-level engineering telemetry.
* **ADR 0021 (Engineering Quality & Non-Regression):** ADR 0022 provides the canonical observation substrate that ADR 0021 non-regression assessments will consume.

## Normative Rule

> **Never assert a pass without affirmative deterministic evidence. Never hide missing evidence behind a green badge. Project status is an evidence-backed factual record, not an informal aspiration.**
