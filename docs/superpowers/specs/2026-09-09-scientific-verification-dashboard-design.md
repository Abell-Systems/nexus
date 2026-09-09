# Design Spec: Scientific Verification Dashboard for Non-Technical Researchers

**Date:** 2026-09-09  
**Status:** Approved in Brainstorming — Ready for Planning  
**Target Audience:** Non-technical scientific researchers (e.g. Lydia), peer reviewers, external auditors  
**Delivery Mechanism:** Static SPA on GitHub Pages (`#/scientific-verification`) within `frontend/`  

---

## 1. Goal and Vision

Enable a non-technical researcher to navigate to `#/scientific-verification` from GitHub and immediately understand:
1. **What is Abell Nexus?** (The research goal and scientific domain).
2. **Where do we stand?** (Current state of development, milestones, and datasets).
3. **What is verified?** (Objective evidence across Data Integrity, Protocol, and Reproducibility).
4. **Epistemic Boundaries:** Explicit distinction between what has been empirically demonstrated vs. what the pilot does *not* permit concluding, alongside the next scientific step.
5. **Human Conclusion & Evidence Trail:** Clear, plain-language conclusion backed by direct links to underlying artifacts (manifests, sidecars, and ADRs) in an on-demand drawer.

Crucially:
- **Zero terminal commands, zero JSON inspection, zero Python execution required from the researcher.**
- **Zero server infrastructure:** No FastAPI, VPS, or database runtime required. The frontend remains a static SPA deployed on GitHub Pages that fetches `project_status.json`.
- **Strict Epistemic Restraint:** The UI must never claim more than the verified evidence warrants (e.g., verifying dataset checksums proves corpus integrity, *never* method validity or universal efficacy).

---

## 2. Architecture & Data Flow

```text
       ┌─────────────────────────────────────────────────────────────┐
       │                   CI WORKFLOW EXECUTION                     │
       │ pytest · ruff · mypy · check_architecture · dataset_audit   │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    project_status.json    │  (Objective Evidence Contract)
                        └─────────────┬─────────────┘
                                      │
                                      ▼  fetch('./project_status.json')
┌──────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND SCIENTIFIC OBSERVED RUNTIME (GitHub Pages / SPA)                    │
│                                                                              │
│    ┌───────────────────────────┐      ┌───────────────────────────────┐      │
│    │    project_status.json    │      │    scientific_context.json    │      │
│    │ (hashes, checks, metrics) │      │ (milestones, narrative, scope)│      │
│    └─────────────┬─────────────┘      └───────────────┬───────────────┘      │
│                  │                                    │                      │
│                  └─────────────────┬──────────────────┘                      │
│                                    ▼                                         │
│                      useScientificVerification()                             │
│                      (Strict Contract Validation)                            │
│                                    │                                         │
│                                    ▼                                         │
│                      ScientificVerificationView                              │
│                                    │                                         │
│       ┌────────────────────────────┼────────────────────────────┐            │
│       ▼                            ▼                            ▼            │
│  [Hero & Global Verdict]    [Project Context & Goals]   [Roadmap & Boundaries│
│                                                                              │
│       ┌────────────────────────────┴────────────────────────────┐            │
│       ▼                                                         ▼            │
│  [3 Pillars: Integrity / Protocol / Reproducibility]     [Evidence Drawer]   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Invariants:
1. **Single Source of Truth for Evidence:** `project_status.json` provides all verified checks, metrics, statuses, commit SHA, and timestamps. The frontend does not calculate or guess check outcomes.
2. **Separation of Semantic Context and Objective Evidence:** `scientific_context.json` is strictly for semantic and epistemological framing (*what the project means, what research questions it investigates, what has been demonstrated vs. what has not*), manually versioned in git. It does NOT track live verification states (no duplicate state machine). Milestone descriptions live here, but their verification status is derived dynamically from `project_status.json`.
3. **Fail-Safe UI:** If `project_status.json` cannot be fetched or fails schema validation, the interface presents a clear `Verification Unavailable` state in neutral gray/amber. It *never* synthesizes an in-memory pass or default green badge.
4. **Point-in-Time Provenance & Anti-Staleness:** Verification is never presented as an eternal, timeless property of Nexus. The dashboard must prominently display the exact evaluated commit SHA, the target dataset ID, and the evaluation timestamp: *"Esta versión de este corpus fue verificada bajo estas condiciones en esta fecha"*.
5. **Static Route Independence:** Routing is controlled via `window.location.hash === "#/scientific-verification"` (with fallback to pathname), ensuring seamless operation on static web hosts (GitHub Pages) without server rewrite rules.

---

## 3. Detailed Component Structure

All files reside in a dedicated, self-contained feature folder: `frontend/src/main/features/scientific-verification/`:

```text
frontend/src/main/features/scientific-verification/
├── types.ts                     # TypeScript definitions for project_status and scientific_context
├── scientific_context.json      # Versioned scientific narrative, research questions, and boundaries
├── useScientificVerification.ts # Hook: fetch, contract validation, error states
├── ScientificVerificationView.tsx # Top-level view container
├── components/
│   ├── VerificationHero.tsx     # Large semaphoric status + Point-in-time Provenance box
│   ├── ProjectContextCard.tsx   # What is Abell Nexus? (Research objective and protocol link)
│   ├── MilestonesProgress.tsx   # Where do we stand? (Milestones linked to live check statuses)
│   ├── EpistemicBoundaryCard.tsx# Demonstrated vs. Not Yet Demonstrated vs. Next Scientific Step
│   ├── VerificationPillars.tsx  # 3 Pillars: Data Integrity, Protocol, Reproducibility
│   ├── ScientificConclusion.tsx # Plain-language takeaway + "View Evidence" trigger
│   └── EvidenceDrawer.tsx       # Slide-over panel with cryptographic hashes and ADR links
└── __tests__/
    ├── useScientificVerification.test.ts # Hook loading, network failures, corrupt payloads
    └── ScientificVerificationView.test.tsx # Epistemic render tests and boundary verification
```

### Component Details

#### 1. `VerificationHero`
- Displays global verdict prominently:
  - `VERIFICADO` (green) if `overall_status == PASS` and required scientific checks passed.
  - `NO VERIFICADO` (red) if any required check failed.
  - `VERIFICACIÓN NO DISPONIBLE` (amber/gray) if data is missing, loading, or unverified.
- **Provenance Statement**: Prominently anchors the assessment to its exact point-in-time evidence:
  > *"Evaluación realizada sobre el dataset `{dataset_id}` en el commit `{commit_sha}` el `{evaluated_at}`."*
  (Commit SHA links directly to GitHub commit).

#### 2. `ProjectContextCard`
- Accessible overview of Abell Nexus: an open-science platform investigating relationships between scientific literature, technological patents, and commercial demands through auditable semantic and lexical matching.
- Direct links to `docs/empirical-study-protocol.md` and repository root.

#### 3. `MilestonesProgress` & `EpistemicBoundaryCard`
- Content rendered purely from versioned `scientific_context.json` (no hardcoded corpus counts, phase names, or domain constants in the component):
  - **Milestones:** Research trajectory steps, whose status badges (e.g. verified / pending) are wired directly to `project_status.json` dimensions, preventing stale status claims in the narrative file.
  - **Epistemic Boundaries (Honest Scientific Delimitation):**
    - **Demostrado con evidencia objetiva:** Integridad byte-a-byte del corpus auditado, reproducibilidad de embeddings de representación semántica, y cumplimiento estricto de las restricciones temporales del protocolo.
    - **No demostrado aún:** Generalización estadística sobre catálogos industriales a gran escala, validez transfronteriza fuera de jurisdicciones auditadas.
    - **Siguiente paso científico:** Declarado dinámicamente desde `scientific_context.json` (p. ej. expansión a pool de anotación ciega con cálculo de acuerdo entre anotadores IAA).

#### 4. `VerificationPillars` (The 3 Pillars)
- **Data Integrity:**
  - Dataset byte identity (`dataset_sha_sidecar`, `dataset_sha_manifest`)
  - Completeness (`manifest_counts`)
  - Identity integrity (`no_duplicate_demand_ids`, `no_duplicate_patent_ids`)
  - Referential integrity (`annotations_reference_known_ids`)
  - Embedding binding (`embeddings_dataset_sha`, `embeddings_dimension`)
- **Protocol:**
  - Cryptographic policy binding (`temporal_policy_binding`)
  - Temporal prior-art compliance (`temporal_eligibility`)
  - Explicit notification of accepted exceptions (displaying reason and governance citations like `ADR-0018/ADR-0019`, never disguised as an unconditioned pass).
- **Reproducibility:**
  - Identificación criptográfica de artefactos
  - Trazabilidad reproducible de los artefactos confirmada (no afirma "100% reproducible" sin réplica experimental independiente).

#### 5. `EvidenceDrawer`
- Non-modal slide-over drawer triggered by "Ver Evidencia Técnica".
- Surfaces exact raw check records, full SHA-256 digests, JSON artifact paths, and links to relevant ADRs (`ADR 0006`, `ADR 0018`, `ADR 0019`, `ADR 0022`).

---

## 4. Testing Strategy & Epistemic Invariants

Unit and component tests in Vitest will enforce:

1. **Epistemic Honesty:**
   - When evidence status is `PASS`, the UI renders "Integridad del corpus verificada" or "Trazabilidad reproducible confirmada". It MUST NOT assert unverified global claims like "El modelo es universalmente válido" o "100% reproducible".
   - When `temporal_eligibility` has status `SKIPPED`, the UI renders it as an informative warning with explicit accepted exceptions citation (`ADR 0018 / ADR 0019`), never as an unflagged green pass or hidden check.
2. **Fail-Fast & Zero False Positives:**
   - If `project_status.json` returns HTTP 404, empty payload, or schema mismatch, the UI displays `VERIFICACIÓN NO DISPONIBLE`. No default green fallback values (`PASS`, `566`, `80%`) are allowed.
3. **Target Binding Invariant:**
   - If `temporal_policy_binding` is `FAIL`, the UI immediately marks the Protocol pillar as `NO VERIFICADO`.
4. **Boundary & Provenance Verification:**
   - Assert that both `demonstrated` and `not_yet_demonstrated` sections from `scientific_context.json` are rendered in the DOM.
   - Assert that the commit SHA, dataset ID, and timestamp provenance statement is displayed in the hero section.

---

## 5. Secondary Artifact (`SCIENTIFIC_VERIFICATION.md`)

In CI, `scripts/audit_project_status.py` will generate a markdown equivalent `SCIENTIFIC_VERIFICATION.md` alongside `PROJECT_STATUS.md`. This markdown document serves as a text-only audit record in the repository, while the web dashboard at `#/scientific-verification` provides the primary interface for Lydia.
