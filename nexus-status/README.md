# Nexus Status Workspace (Scientific Verification)

This workspace contains the independent frontend application for **Nexus Scientific Verification**, providing transparent, human-auditable and researcher-friendly insights into the empirical health and reproducibility of Abell Nexus.

## Architectural Governance

Under **[ADR 0024](../../docs/adr/0024-scientific-verification-workspace.md)** and **[ADR 0023](../../docs/adr/0023-scientific-verification-as-external-consumer.md)**:

1. **Independent Monorepo Workspace:** This application is strictly decoupled from the primary patent intelligence application in `frontend/`.
2. **Zero Cross-Imports:** Code in this workspace MUST NEVER import from `frontend/` or `backend/`. Code in `frontend/` MUST NEVER import from `nexus-status/`.
3. **Sole Source of Truth:** This application is a read-only consumer of the canonical contract `project_status.json` (governed by **[ADR 0022](../../docs/adr/0022-project-status-contract.md)**). It NEVER re-aggregates or overrides status verdicts.
4. **Autonomous Deployment:** This application is configured to build and deploy as a standalone static site (e.g. GitHub Pages) independently of Nexus product releases.

## Directory Layout

```text
nexus-status/
├── README.md               # This document
└── frontend/               # Standalone React/TypeScript SPA
    ├── package.json        # Independent dependencies and build scripts
    ├── tsconfig.json       # Independent TypeScript configuration
    ├── vite.config.ts      # Standalone Vite bundler configuration
    ├── src/
    │   ├── domain/         # Scientific verification models, status contracts & types
    │   ├── application/    # Read-only contract orchestration and state hooks
    │   ├── infrastructure/ # Contract fetcher and schema validation
    │   └── ui/             # Presentation views, metrics and evidence drawers
    └── test/               # Unit and epistemic invariant test suites
```
