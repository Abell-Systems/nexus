# ADR 0008: Automated Architectural Enforcement and Machine-Verifiable Dependency Contracts

**Status:** Accepted  
**Date:** 2026-09-04  
**Scope:** Repository-wide (`AGENTS.md`, `.importlinter`, `scripts/check_architecture.py`, `.github/workflows/ci.yml`, `backend/test/unit/architecture/`)  

---

## Context

Under ADR 0001 (Testing Strategy), ADR 0002 (Clean Architecture), and AGENTS.md directives, Nexus enforces strict decoupling between domain entities, application orchestration, and infrastructure adapters:
- `domain` must remain completely pure: no knowledge of `application`, `infrastructure`, or external framework runtime dependencies.
- `application` orchestrates use cases: depends strictly on `domain`, zero knowledge of `infrastructure`.
- `infrastructure` adapts concrete persistence, external services, and file I/O: depends on `application` and `domain`, never vice versa.
- Subsystems operating as independent auditors (such as `application.evaluation`) must remain decoupled from specific domain models of collaborators (e.g. `domain.models.matching`).

Previously, architectural invariants relied on two mechanisms:
1. Documentation and review guidelines in `AGENTS.md`.
2. Ad-hoc Python AST parsing in custom test files (`test_adr_0007_invariants.py`, `scripts/check_architecture.py`).

While custom AST tests catch specific infractions, ad-hoc AST checks are difficult to maintain, easy to miss during refactoring, and fail to provide declarative, static dependency graph analysis. Furthermore, relying on human code review alone creates regression risks where bounded context coupling is masked via `Any` or implicit imports.

## Decision

We establish that **architectural invariants are executable, machine-verifiable contracts that block CI**.

We formalize a **4-tier automated architectural enforcement stack**:

```text
┌─────────────────────────────────────────────────────────────┐
│ Level 4: SonarQube / SonarCloud                             │
│ • Code smells, cognitive complexity, test coverage gates   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Level 3: Import Linter & Architecture Invariant Tests       │
│ • Declarative dependency contracts (.importlinter)          │
│ • Clean Architecture layer isolation:                       │
│     - domain forbidden: application, infrastructure         │
│     - application forbidden: infrastructure                 │
│ • Independent auditor isolation:                            │
│     - application.evaluation.runner forbidden: matching     │
│ • Python AST & pytest architecture invariants in CI        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Level 2: Static Typing (Mypy)                               │
│ • Protocol contracts, structural subtyping without Any      │
│ • Explicit DI enforcement and non-nullable parameters       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Level 1: Static Linter & Formatter (Ruff)                   │
│ • PEP 8, import sorting, complexity, banned syntax          │
└─────────────────────────────────────────────────────────────┘
```

### 1. Declarative Dependency Contracts via Import Linter (`.importlinter`)

We adopt `import-linter` as the standard tool for declarative cross-module dependency enforcement. Contracts are stored in `.importlinter` at the repository root and executed against `backend/src/main`.

Initial declared contracts:
1. **`domain-isolation`**: `domain` must not depend on `application` or `infrastructure`.
2. **`application-isolation`**: `application` must not depend on `infrastructure`.
3. **`evaluation-metrics-purity`**: `application.evaluation.metrics` must not depend on `infrastructure` or any matching-domain module (`domain.models.matching`, `domain.protocols.matching`, `application.matching`).
4. **`evaluation-runner-isolation`**: `application.evaluation.runner` must not depend on `infrastructure` or matching-domain modules (`domain.models.matching`, `domain.protocols.matching`, `application.matching`).
5. **`evaluation-adapter-boundary`**: Only `application.evaluation.matching_adapter` may adapt evaluation protocols to matching types.

### 2. Integration into CI Quality Gates

`lint-imports` is added to:
- `backend/requirements-dev.txt`
- `scripts/check_architecture.py` (which runs in Job 1 of `.github/workflows/ci.yml`)
- CI workflow Job 2 (`python-quality`) or Job 1 (`architecture`) to guarantee that any PR breaking a layer contract fails fast before test execution.

### 3. Prohibition of "Any" to Hide Cross-Context Coupling

Under ADR 0007 and ADR 0008, agents MUST NOT use `typing.Any` to bypass static type checks or circumvent import restrictions across bounded contexts. Bounded context boundaries must be bridged with:
- Minimal structural protocols owned by the consumer domain, or
- Explicit adapter classes in the application layer (e.g. `DefaultMatchingAdapter`).

---

## Consequences

### Positive
- **Deterministic CI Blocking:** Architectural drift is caught by the compiler and import graph analyzer before code review.
- **Declarative & Self-Documenting:** New contracts are added as declarative INI sections in `.importlinter` rather than repetitive AST visitors.
- **Fail-Fast Feedback:** Contract violations are reported with exact import chains and line numbers in milliseconds.

### Negative
- Additional development dependency (`import-linter`, `grimp`).
- Strict layering requires deliberate adapter construction when integrating multiple sub-domains.

---

## Enforcement

1. PRs introducing forbidden imports fail `scripts/check_architecture.py` and `lint-imports` in CI.
2. Invariant unit tests in `backend/test/unit/architecture/` verify that `.importlinter` contracts remain active, synchronized, and unbroken.
