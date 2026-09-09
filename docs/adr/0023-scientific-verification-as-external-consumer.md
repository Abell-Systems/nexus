# ADR 0023: Scientific Verification as an External Presentation Artifact

**Status:** Accepted  
**Date:** 2026-09-09  
**Scope:** Entire Nexus repository  

## Context

Abell Nexus is an autonomous deep-tech intelligence system and an empirical scientific research engine. Its architectural boundaries are strictly governed by Clean Architecture (ADR 0008), invariant test suites, and the canonical Project Status Contract ([ADR 0022](0022-project-status-contract.md)).

Under ADR 0022, Nexus executes deterministic audits across canonical dimensions (architecture, backend testing, coverage, python quality, frontend quality, documentation, and scientific dataset integrity), serializing the resulting evidence into a machine-readable contract (`project_status.json`) and a human-auditable document (`PROJECT_STATUS.md`).

An initiative to make this scientific verification accessible to non-technical stakeholders (such as legal and domain researchers) led to an attempt to embed a dedicated verification dashboard directly inside the Nexus web application (`frontend/src/main/`). This attempt introduced significant architectural tensions:
1. **Coupling Presentation to Core:** Nexus UI exists to serve technology discovery, patent analysis, and adversarial prior-art defense. Embedding a separate scientific verification application inside `frontend/src/main/components/` bloated the frontend with out-of-domain concerns.
2. **Re-implementation of State Evaluation:** Presentational hooks in the UI began re-aggregating checks and re-interpreting status rules (e.g. mapping `SKIPPED` checks or check counts into synthetic UI passes), violating the foundational ADR 0022 rule that `project_status.json` is the sole source of truth.
3. **Artifact Duplication:** In an attempt to serve static files locally, secondary copies (`frontend/public/project_status.json`) were generated, breaching the single-source-of-truth invariant.
4. **Leakage of Implementation Details:** The UI layer required knowledge of internal check names, dataset file paths, and ADR references, instead of consuming an abstract, standardized contract.

## Decision

### 1. Scientific Verification is an External Presentation Commodity

Scientific Verification is classified as an **external presentation consumer**, completely decoupled from the Nexus core engine:
* It **MUST NOT** be embedded within `frontend/src/main/` or treated as a sub-feature of the Nexus patent agent.
* It **MUST NOT** import domain, application, or infrastructure modules from Nexus.
* It **MUST NOT** re-calculate, override, or synthesize pass/fail verdicts already determined by the canonical auditor.

Scientific Verification operates as a standalone commodity tool (in a dedicated repository or isolated static deployment) whose sole responsibility is presenting the evidence serialized in `project_status.json`.

### 2. Provider-Consumer Separation

The boundary between Nexus and external visualizers is strictly contractual:

```text
Abell Nexus Core
  │
  ├── Deterministic Audits (ADR 0008, ADR 0018, ADR 0019, ADR 0022)
  │
  └── Produces Canonical Evidence Contract
          │
          ▼
      project_status.json  (Sole Source of Truth)
          │
          │ Read-Only Contract
          ▼
External Presentation Consumers
  (e.g., scientific-verification-dashboard)
```

1. **Nexus is solely an evidence producer and auditor:** It enforces quality gates and emits `project_status.json` (and the derived `PROJECT_STATUS.md` report).
2. **Consumers are read-only renderers:** External dashboards ingest `project_status.json` over standard HTTP/static fetch, honoring its exact status vocabulary (`PASS`, `FAIL`, `SKIPPED`, `UNVERIFIED`, `N/A`) without altering or second-guessing the aggregation.
3. **Single Canonical Output in Core:** Nexus produces a single `project_status.json` at repository root during audit/CI. Nexus core MUST NOT generate secondary duplicate copies inside frontend public asset trees.

### 3. Decommissioning of In-Tree Verification View

All temporary in-tree verification view components, routes, and contextual JSON files introduced in `frontend/src/main/components/ScientificVerification/` are removed from the Nexus repository. The primary Nexus user interface remains exclusively dedicated to industrial patent intelligence and demand matching.

## Consequences

### Positive
* **Architectural Hygiene:** Nexus core maintains zero coupling to external verification dashboards or ad-hoc researcher interfaces.
* **Single Source of Truth:** No duplicate `project_status.json` files exist in the repository.
* **Commodity Portability:** The external verification dashboard can be developed, tested, and reused across any project that emits an ADR 0022-compliant `project_status.json` contract.
* **Zero UI Epistemic Drift:** Eliminates the risk of React components fabricating passing verdicts or masking unverified states.

### Negative / Trade-offs
* Hosting an external verification dashboard requires deploying a separate static artifact or repository, rather than bundling it inside the existing Nexus SPA bundle.
