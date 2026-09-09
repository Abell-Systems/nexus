# ADR 0024: Scientific Verification as an Independent Monorepo Workspace

**Status:** Accepted  
**Date:** 2026-09-09  
**Scope:** Monorepo architecture (`nexus-status/frontend`)  

## Context

[ADR 0023](0023-scientific-verification-as-external-consumer.md) established that Scientific Verification is an external presentation commodity, decoupled from the Nexus core engine, consuming exclusively the canonical `project_status.json` contract ([ADR 0022](0022-project-status-contract.md)). It prohibited embedding researcher verification views inside `frontend/src/main/components/` to prevent domain pollution and state re-calculation anti-patterns.

However, interpreting "external presentation consumer" as exiling the project to a completely separate Git repository introduces operational friction:
* multiple repositories to synchronize, configure, and maintain;
* disconnected issues, PR lifecycles, and release cadences;
* lack of atomic schema validation between the evidence producer and the visualizer;
* cognitive overhead for collaborators navigating multiple repositories for the same research initiative.

Nexus resolves this by adopting a **Bounded Monorepo Pattern**: a single repository housing distinct, independently bounded applications that share versioned governance, CI infrastructure, and contract artifacts, while maintaining strict architectural isolation.

## Decision

### 1. Monorepo Directory Architecture

The repository organizes product and presentation workspaces under distinct root boundaries:

```text
abell-systems/
└── nexus/                         # Monorepo
    ├── backend/                   # Core engine, patent pipelines & verification scripts
    ├── frontend/                  # Primary industrial patent intelligence UI
    │
    ├── nexus-status/
    │   ├── README.md              # Workspace governance and scope
    │   └── frontend/              # Scientific Verification application (Lydia's dashboard)
    │       ├── package.json       # Independent dependencies and scripts
    │       ├── tsconfig.json      # Isolated TypeScript configuration
    │       ├── vite.config.ts     # Standalone build configuration
    │       ├── src/
    │       │   ├── domain/        # Scientific verification models and status types
    │       │   ├── application/   # Contract ingestion and read-only orchestration
    │       │   ├── infrastructure/# Contract fetcher and schema validator
    │       │   └── ui/            # Pure presentation components
    │       └── test/              # Independent unit and contract tests
    │
    ├── project_status.json        # Canonical Contract (ADR 0022, Tier 3)
    ├── PROJECT_STATUS.md          # Human-auditable report (Tier 2)
    └── docs/
        └── adr/                   # Architecture Decision Records
```

### 2. Strict Boundary Invariants

The boundaries between workspaces are governed by mandatory architectural invariants:

1. **Zero Cross-Imports Between Applications:**
   * Code in `frontend/` MUST NEVER import from `nexus-status/`.
   * Code in `nexus-status/frontend/` MUST NEVER import from `frontend/` or `backend/`.
   * The applications do not share runtime dependencies, bundles, or component trees.

2. **No Core Backend Coupling:**
   * `nexus-status/frontend` does NOT invoke internal backend Python modules or dynamic backend endpoints.
   * It is strictly a consumer of the canonical `/project_status.json` contract.

3. **Autonomous Clean Architecture:**
   * `nexus-status/frontend` maintains its own Clean Architecture layers (`domain`, `application`, `infrastructure`, `ui`).
   * It has its own `package.json`, isolated build toolchain, and independent test runner.

4. **Single Source of Truth:**
   * `nexus-status/frontend` NEVER synthesizes, overrides, or re-calculates verdicts (`PASS`, `FAIL`, `SKIPPED`, `UNVERIFIED`, `N/A`).
   * It renders directly the verdicts emitted by `scripts/audit_project_status.py` in `project_status.json`.

5. **Independent Static Deployment:**
   * `nexus-status/frontend` can be built and deployed independently as a static site (e.g., GitHub Pages or static bucket) without coupling to the primary Nexus application deployment.

### 3. Machine-Verifiable Architectural Enforcement

The boundary invariants are enforced automatically in CI:
* `scripts/check_architecture.py` verifies that zero cross-imports exist between `frontend/` and `nexus-status/`.
* Any violation triggers an immediate CI failure before review.

## Consequences

### Positive
* **Single Repository Cohesion:** Issue tracking, PRs, CI workflows, and ADR governance remain unified under `abell-systems/nexus`.
* **Zero Domain Contamination:** The primary patent intelligence application remains 100% focused on industrial discovery and search, with zero out-of-domain verification code.
* **Epistemic Rigor Preserved:** Scientific verification remains a pure consumer of `project_status.json`, eliminating UI-side verdict fabrication.
* **Independent Evolution:** The verification UI can evolve its presentational style or deploy to separate static infrastructure without touching core Nexus code.

### Negative / Trade-offs
* CI workflows must manage two distinct frontend build/test pipelines (`frontend/` and `nexus-status/frontend/`).
