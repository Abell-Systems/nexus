# ADR 0026: Experiment/Domain Boundary

**Status:** Accepted

**Scope:** `backend/src/main` (all layers), `backend/test`, `experiments/`

## Context

PR #86 (and the Phase 2 construct-eligibility audit work leading up to it)
embedded scientific-run facts — N=39, the 24/13/2 ELIGIBLE/INELIGIBLE/UNCERTAIN
split, Auditor A/B decisions — directly into `backend/` production code,
`backend/test/unit`, and `data/evaluation/` file names. This mixed three
distinct concerns:

- **Domain science**: what does "construct eligible" mean per protocol §4.1?
- **Experimental run**: what corpus, annotations, and audits constitute *this*
  study?
- **Infrastructure**: how are artifacts persisted, versioned, hashed,
  reproduced?

Continuing this pattern into future scientific work (e.g. sector taxonomy
assignment, Dev/Test split design) would hardcode one paper's specific
taxonomy, IDs, and counts into Nexus itself — a future study at a different N
would require rewriting Nexus rather than reconfiguring it.

This is a direct extension of ADR 0006's existing boundary (which already
forbids `domain`/`application` from resolving `data/evaluation/`-relative
paths) and ADR 0017's Lab/Product separation — neither addressed the
distinction between generic evaluation *mechanism* (Nexus) and one
experiment's *instantiation and observations* (this paper).

## Decision

**Nexus implements generic evaluation mechanisms; `experiments/` records how
those mechanisms were instantiated and what a specific scientific run
observed.**

The absence of an `experiments/` reference from backend source and backend
tests is an architectural invariant, not a claim that experiments are
independent of Nexus. Experiments necessarily *use* Nexus; the dependency is
one-way:

```
experiments/ (config, data, checks) --uses--> Nexus (domain/application/infrastructure)
```

Never the reverse.

### Litmus test

Would this `backend/test/unit` test still make sense and be executable if the
relevant `experiments/<paper>/` directory were deleted? If not, it belongs in
that experiment's `checks/`, not in `backend/test/unit`. Likewise: if changing
a paper's taxonomy or sample requires changing `backend/src/main`, domain
knowledge has leaked and must be extracted to configuration/data.

### Directory contract

```
experiments/
├── shared/                     # fixtures genuinely reused across multiple
│                                # experiments — not a dumping ground
└── <paper-slug>/
    ├── protocol/                # a reference (path + content hash) to the
    │                             # canonical protocol doc under docs/ — never
    │                             # a copy
    ├── config/                  # frozen taxonomies, rule tables — data, not
    │                             # executable Python constants
    ├── data/                    # frozen corpora, derived artifacts,
    │                             # manifests, sha256 sidecars
    └── checks/                  # manifest-conformance validation scripts —
                                  # never hardcode expected counts; read them
                                  # from the frozen manifest
```

Root-level, sibling to `backend/` and `frontend/`, outside both apps'
`src/main`. This ADR does not amend CLAUDE.md's 3-tier rule for product code.

### Layer allocation (worked precedent: PR #86's construct-eligibility audit)

| Layer | Owns | This precedent |
|---|---|---|
| `backend/src/main/domain` | Structural types only, no known values | `ConstructEligibilityRubric`, `RubricValue`, `ConstructEligibilityStatus` (`domain/models/annotation.py`) |
| `backend/src/main/application` | Generic mechanism | `derive_construct_status()` (`application/annotation/construct_eligibility.py`) — protocol §4.1's decision rule, a pure function of any rubric |
| `backend/test/unit` | Generic invariants only, proven against synthetic/arbitrary fixtures | `test_construct_eligibility.py` — exhaustive over all rubric-value combinations, no real demand IDs, no `39`/`24`/`13`/`2` |
| `experiments/wpi-demand-patent-matching/data/` | This run's frozen evidence | `phase2_demand_construct_eligibility_n39_v1.json` + manifest + sha256 |
| `experiments/wpi-demand-patent-matching/checks/` | Manifest-conformance validation of that evidence, using the generic mechanism | `check_construct_eligibility.py` |

### Enforcement

One automated guard, `backend/test/unit/architecture/test_adr_0026_invariants.py`:
scans `backend/src` and `backend/test` for any path-segment/import reference
to `experiments` (e.g. `from experiments...`, `Path("experiments/...")`,
string literals containing `experiments/` as a path prefix) and fails on any
match. This is a reference-boundary check, not a prose linter — a comment
containing the word "experiments" in running text does not trip it.
`experiments/shared/` is exempt from the path-string check — it holds
reusable fixture data (e.g. the ES Pilot-16 pilot benchmark), not
paper-specific scientific evidence, so integration tests may legitimately
reference it (see backend/test/unit/infrastructure/annotation/test_blind_export.py)
without violating the boundary this ADR protects.

No magic-number linter is built. `39`/`24`/`13` are scientific observations,
not architectural violations, and a literal-scanning guard would be brittle
and would conflate the two. The manifest-conformance pattern in
`checks/check_construct_eligibility.py` is the intended replacement.

The reverse direction — experiment code must use only Nexus's public generic
mechanisms, never reach into internal implementation paths — is left to code
review, not automated by this ADR.

## Consequences

- PR #86 is not reverted or reopened. Its scientific conclusion (24 ELIGIBLE /
  13 INELIGIBLE / 2 UNCERTAIN) stands unchanged; only artifact location and
  test placement moved.
- Future scientific work (sector taxonomy assignment, Dev/Test split, and
  beyond) follows this same layer allocation from the start: generic
  mechanism in `backend/`, concrete taxonomy/policy/results in
  `experiments/<paper-slug>/`.
- A future paper introduces a new `experiments/<paper-slug>/` directory and
  reuses `experiments/shared/` fixtures where genuinely applicable, without
  touching `backend/src/main`.
