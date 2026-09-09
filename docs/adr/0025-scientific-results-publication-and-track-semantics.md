# ADR 0025: Scientific Results Publication and Track Semantics

**Status:** Proposed
**Date:** 2026-09-09
**Scope:** `scientific_results.json` (new, proposed), `nexus-status/frontend`, `application/landscape/`, `application/synthesis/`, `application/matching/`, `application/evaluation/`

## Context

[ADR 0017](0017-dual-track-architecture.md) established that Nexus has two execution
contexts sharing a common deterministic core — informally "Head A" (generative: landscape
white-space heuristic + ADK inventor/adversarial/governor loop, exposed via
`GET /api/landscape` and `POST /api/analyze`) and "Head B" (deterministic: `UC1` matching
pipeline + sealed evaluation harness, exercised via `scripts/` and `application/evaluation/`).
ADR 0017 is explicit that Head A "does not feed metrics, ablations, or efficacy claims" and
that this classification is "architectural, not provisional."

[`docs/SCIENTIFIC_RESULTS_CONTRACT.md`](../SCIENTIFIC_RESULTS_CONTRACT.md) (Phase 2 of the
`nexus-status` UX redesign) inspected the actual domain models and pipelines behind both
heads and confirmed: Head A already produces real, running output (`PatentCluster`,
`InventionCandidate`, `AdversarialVerdict`, `ScoreCard`) that maps closely onto the UX
vocabulary of "landscape / opportunities / candidates / evidence"; Head B produces
scientifically rigorous, policy-sealed `MatchAssessment` and `EvaluationRunReport` evidence,
but does not produce "opportunity" or "candidate invention" as UX concepts. That document
left one question explicitly unresolved: **which track, if either, may populate a dashboard
whose stated purpose is "why should I believe it?"**

This ADR resolves that question. It does not re-litigate ADR 0017's dual-track architecture;
it extends it with the publication and epistemic-labeling rules a scientific-results
consumer needs, and formalizes them before any implementation begins — the repository's own
`contract → test → code` discipline (ADR 0021) applied one level up, to a data contract
about to be handed to a UI.

## Decision

### 1. Track semantics are named, not merged

Every published scientific-result record carries an explicit, mandatory `track` field with
exactly two values:

* `discovery` — Head A output (landscape clustering, white-space scoring, candidate
  invention synthesis, adversarial challenge). Real-time, LLM-involved, quota-bound,
  reproducible only in the sense that the deterministic parts of it (the white-space
  formula) are; the candidate/verdict/scorecard text is not.
* `verification` — Head B output (`MatchAssessment`, `EvaluationRunReport`). Deterministic,
  policy-sealed, dataset-versioned, statistically tested.

`discovery` and `verification` are never presented as interchangeable, never merged into an
undifferentiated "result," and never silently defaulted — a record without a `track` is
invalid and must be rejected by the publisher and by the frontend parser alike, the same way
`domain/status.ts` already rejects a `project_status.json` record with an invalid
`StatusValue` (ADR 0022).

### 2. What the dashboard may and may not claim, per track

| Track | Permitted framing | Forbidden framing |
|---|---|---|
| `discovery` | "Nexus generated/discovered this candidate from this landscape." | "Nexus demonstrates this invention is valid/effective." "This candidate is scientifically verified." Any patentability, freedom-to-operate, or efficacy claim (already forbidden system-wide by ADR 0017 §5.5–5.6, restated here as it applies specifically to the scientific-results contract). |
| `verification` | "Nexus evaluated this matching/evidence under this deterministic policy [`policy_id`/`policy_version`/`policy_sha256`]." | Presenting a `verification` metric as if it graded a `discovery` candidate it was not computed against. |

A `discovery` record is never rendered without its track badge and the ADR 0017 recall-aid
disclaimer inline (not only in a tooltip or a separate "limitations" page) — this restates
`SCIENTIFIC_RESULTS_CONTRACT.md` §5 invariant 8 as a binding rule, not a suggestion.

### 3. Information architecture assignment

* **Landscape** → `discovery`. Technology clusters and white-space scoring are Head A's
  domain; no Head B equivalent exists or is proposed.
* **Opportunities / Candidate Inventions** → `discovery`, unambiguously labeled as such.
  Head A is not retired or hidden on account of ADR 0017's limitation — it remains the only
  subsystem that makes Nexus interesting as a *technology discovery* system, and is
  presented as exactly that: discovery output, not verified science.
* **Evidence / Verification** → `verification`, populated only where genuine Head B evidence
  exists for the entity being viewed. Where no `verification`-track evidence exists yet for
  a given candidate or opportunity, the view says so explicitly (an honest empty state, per
  the existing `NotAvailableView` pattern already shipped in `nexus-status`) rather than
  substituting `discovery`-track content to fill the gap.
* **A single candidate detail view may show both tracks side by side** if and only if an
  explicit, traceable relationship exists between the `discovery` candidate and a
  `verification` record (e.g. a `MatchAssessment` computed against the same cited
  publication). The two tracks are never blended into one score or one verdict — each keeps
  its own badge, provenance, and disclaimer even when shown together.

### 4. Publication mechanism

`scientific_results.json` is a new, independent, git-tracked artifact at the repository
root, published by the same discipline ADR 0022/0023 already established for
`project_status.json`:

* Produced by a dedicated publication step (proposed: `scripts/publish_scientific_results.py`),
  never written directly by `application/landscape/` or `application/synthesis/` code, and
  never by `nexus-status/frontend`.
* Consumed exclusively as a static, read-only fetch — `nexus-status/frontend` must not call
  `/api/landscape` or `/api/analyze` live, per the existing ADR 0023/0024 boundary
  (no cross-imports, no live backend coupling, enforced by `scripts/check_architecture.py`).
* `project_status.json` is not extended to carry this data (ADR 0022 scopes it to audit
  dimensions only); the two files remain siblings, independently regenerated, independently
  versioned.
* Every published record is scoped to a specific, chosen `execution_id`; no dashboard
  aggregate may combine records across executions unless they share `track`, `dataset_id`
  (or its `discovery`-track equivalent once execution persistence exists), and
  `policy_version` — restates `SCIENTIFIC_RESULTS_CONTRACT.md` §5 invariant 6.

### 5. Sequencing

This ADR is a prerequisite, not a parallel track:

```text
ADR 0025 (this document)
    ↓
tests for the publisher and the contract parser
    ↓
publisher implementation (SCIENTIFIC_RESULTS_CONTRACT.md §8, steps 1–3)
    ↓
first real scientific_results.json snapshot
    ↓
nexus-status Landscape / Opportunities / Candidates / Evidence views
```

No `discovery` or `verification` UI is implemented in `nexus-status` before this ADR is
Accepted. `SCIENTIFIC_RESULTS_CONTRACT.md` §8 steps 1–3 (stop discarding computed cluster
metrics → persist executions → publish a snapshot) remain the correct, smallest first
implementation once this ADR lands.

**Placeholder scaffolding is not implementation.** `nexus-status` may ship the
`Landscape`/`Opportunities`/`Candidates`/`Evidence` navigation entries ahead of this ADR's
acceptance — as it does today — provided every one of them renders an explicit, unambiguous
"not yet available" state and no `track`-labeled record. Such scaffolding is UI navigation
only; it does not constitute, and must not be described in review or documentation as,
implementation of either track. The gate this ADR imposes is on rendering real `discovery`
or `verification` data, not on the existence of the nav items or empty-state components
themselves.

## Consequences

### Positive

* Head A keeps its role and its value as a discovery engine instead of being suppressed or
  quietly reinterpreted as evidence it was never designed to be.
* The dashboard can show real output far sooner than waiting for Head B to grow an
  "opportunity"/"candidate" vocabulary of its own — without misrepresenting what that output
  is.
* The `track` field makes the discovery/verification distinction machine-checkable, not just
  a documentation convention — a malformed or missing `track` is a contract violation the
  parser rejects, the same epistemic-restraint pattern ADR 0022/0023 already apply to
  `overall_status`.
* `scientific_results.json` inherits a publication discipline that already works
  (`project_status.json`), rather than inventing a new one.

### Negative / trade-offs

* Two tracks must be maintained and clearly badged in the UI indefinitely — added rendering
  and copy-review discipline (every `discovery` surface needs the disclaimer kept current).
* Head A's lack of durable execution records (ADR 0017 §7) must be fixed before
  `discovery`-track publication can cite a stable `execution_id` — tracked as
  `SCIENTIFIC_RESULTS_CONTRACT.md` §8 step 2, not solved by this ADR itself.
* A candidate view that wants to show both tracks together depends on a traceable
  `discovery`↔`verification` link that does not exist yet in either domain model; until it
  does, combined views are simply unavailable, not fabricated.

## Enforcement

A change is non-compliant with this ADR if it:

1. Publishes a `scientific_results.json` record without a `track` field, or with a value
   other than `discovery` or `verification`.
2. Renders `discovery`-track content without its track badge and the ADR 0017 recall-aid
   disclaimer inline.
3. Presents a `discovery`-track candidate, cluster, or verdict using patentability,
   freedom-to-operate, or efficacy language (ADR 0017 §5.5–5.6, restated in §2 above).
4. Aggregates or averages records across executions, tracks, dataset versions, or policy
   versions without all of them matching.
5. Has `nexus-status/frontend` call a live backend endpoint, or import from `frontend/` or
   `backend/`, to obtain scientific-results data (ADR 0023/0024, restated here as it applies
   to this new contract specifically).
6. Extends `project_status.json`'s schema to carry scientific-result payloads instead of
   publishing them to the sibling `scientific_results.json` artifact.
7. Ships any `nexus-status` Landscape/Opportunities/Candidates/Evidence UI before this ADR's
   status is `Accepted`.
