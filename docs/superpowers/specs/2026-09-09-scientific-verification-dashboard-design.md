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
2. **Separation of Context and Evidence:** Narrative context, research questions, and epistemic boundaries live in versioned `scientific_context.json` alongside the frontend code, preventing pollution of the machine-readable CI audit contract.
3. **Fail-Safe UI:** If `project_status.json` cannot be fetched or fails schema validation, the interface presents a clear `Verification Unavailable` state in neutral gray/amber. It *never* synthesizes an in-memory pass or default green badge.
4. **Static Route Independence:** Routing is controlled via `window.location.hash === "#/scientific-verification"` (with fallback to pathname), ensuring seamless operation on static web hosts (GitHub Pages) without server rewrite rules.

---

## 3. Detailed Component Structure

All files reside in a dedicated, self-contained feature folder: `frontend/src/main/features/scientific-verification/`:

```text
frontend/src/main/features/scientific-verification/
├── types.ts                     # TypeScript definitions for project_status and scientific_context
├── scientific_context.json      # Versioned scientific narrative, milestones, and boundaries
├── useScientificVerification.ts # Hook: fetch, contract validation, error states
├── ScientificVerificationView.tsx # Top-level view container
├── components/
│   ├── VerificationHero.tsx     # Large semaphoric status: VERIFIED / NOT VERIFIED / UNAVAILABLE
│   ├── ProjectContextCard.tsx   # What is Abell Nexus? (Research objective and protocol link)
│   ├── MilestonesProgress.tsx   # Where do we stand? (Current phase and milestone markers)
│   ├── EpistemicBoundaryCard.tsx# Demonstrated vs. Not Yet Demonstrated vs. Next Step
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
- Surfaces audited corpus name, commit hash (clickable link to GitHub commit), and evaluation date.

#### 2. `ProjectContextCard`
- Brief, accessible overview of Abell Nexus: an open-science platform investigating relationships between scientific literature, technological patents, and commercial demands through auditable semantic and lexical matching.
- Direct links to `docs/empirical-study-protocol.md` and repository root.

#### 3. `MilestonesProgress` & `EpistemicBoundaryCard`
- Loaded directly from `scientific_context.json`:
  - **Milestones:**
    - Pilot Benchmark (Sealed corpus) → *Verified*
    - Matching Pipeline (M0/M1) → *Validated*
    - Cryptographic Integrity → *Verified*
    - Temporal Restrictions → *Verified (3 frozen exceptions accepted under protocol)*
    - Industrial Corpus Scaling → *Next Phase*
  - **Epistemic Boundaries (Honest Scientific Delimitation):**
    - **Demonstrated:** Byte-level integrity of pilot corpus, reproducibility of 768-dimensional embeddings, and protocol-compliant prior-art temporal filtering.
    - **Not Yet Demonstrated:** Statistical generalizability across industrial-scale catalogs (>100k records), cross-lingual generalization beyond Spanish OEPM/InnoGet corpora.
    - **Next Scientific Step:** Expansion to Phase-2 candidate pool (N=39) with blind dual annotation and inter-annotator agreement (IAA) verification.

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
  - Content-addressed identifiers
  - Frozen artifact sidecars
  - Reproducible conditions confirmed

#### 5. `EvidenceDrawer`
- Non-modal slide-over drawer triggered by "Ver Evidencia Técnica".
- Surfaces exact raw check records, full SHA-256 digests, JSON artifact paths, and links to relevant ADRs (`ADR 0006`, `ADR 0018`, `ADR 0019`, `ADR 0022`).

---

## 4. Testing Strategy & Epistemic Invariants

Unit and component tests in Vitest will enforce:

1. **Epistemic Honesty:**
   - When evidence status is `PASS`, the UI renders "Integridad del corpus verificada" or "Condiciones reproducibles verificadas". It MUST NOT assert broad unverified claims like "El modelo es universalmente válido".
   - When `temporal_eligibility` has status `SKIPPED`, the UI renders it as an amber warning with explicit accepted exceptions citation (`ADR 0018 / ADR 0019`), never as an unflagged green pass or hidden check.
2. **Fail-Fast & Zero False Positives:**
   - If `project_status.json` returns HTTP 404, empty payload, or schema mismatch, the UI displays `VERIFICACIÓN NO DISPONIBLE`. No default green fallback values (`PASS`, `566`, `80%`) are allowed.
3. **Target Binding Invariant:**
   - If `temporal_policy_binding` is `FAIL`, the UI immediately marks the Protocol pillar as `NO VERIFICADO`.
4. **Boundary Verification:**
   - Assert that both `demonstrated` and `not_yet_demonstrated` sections are rendered in the DOM, guaranteeing that the researcher sees the boundaries of the experiment.

---

## 5. Secondary Artifact (`SCIENTIFIC_VERIFICATION.md`)

In CI, `scripts/audit_project_status.py` will generate a markdown equivalent `SCIENTIFIC_VERIFICATION.md` alongside `PROJECT_STATUS.md`. This markdown document serves as a text-only audit record in the repository, while the web dashboard at `#/scientific-verification` provides the primary interface for Lydia.
