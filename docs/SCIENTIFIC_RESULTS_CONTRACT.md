# Scientific Results Contract — Design (Phase 2)

**Status:** Design only — not implemented, not an ADR.
**Scope:** Defines the minimum structured contract Nexus would need to publish for the
`nexus-status` dashboard's Landscape / Opportunities / Candidates / Evidence views to show
real data. No code changes accompany this document. `project_status.json` is unmodified.

This document is the deliverable requested for Phase 2 of the UX/UI plan, produced after
inspecting the actual backend domain models, ADK pipeline, and ADRs 0001–0024 rather than
assuming the plan's vocabulary already exists in the codebase.

**Terminology note:** [ADR 0025](adr/0025-scientific-results-publication-and-track-semantics.md)
(Accepted) is the normative source for track naming and now names the two tracks this
document describes `discovery` (Head A) and `verification` (Head B) — this document has
been updated to match. Where the two disagree in the future, ADR 0025 governs; this
document is design rationale, not the contract itself.

---

## 1. Purpose

`project_status.json` answers *"is the system that produces Nexus's results itself under
quality control?"* — it is CI/audit evidence (tests, coverage, lint, architecture, docs,
dataset-integrity checks), scored PASS/FAIL/UNVERIFIED/SKIPPED/N/A per dimension.

A **scientific-results contract** would answer a different question: *"what did Nexus
actually observe, propose, and verify?"* — the empirical outputs of the pipeline itself:
technology clusters, white-space opportunities, candidate inventions, and the adversarial
prior-art evidence for or against them.

These are orthogonal. `project_status.json` can be entirely PASS while zero scientific
results have ever been produced (the dataset-integrity checks it runs validate corpus
*identity*, not the *presence or quality* of discovery results). Conversely, Nexus could
produce a rich set of candidates while its test suite is red. Conflating the two contracts
would make it impossible to distinguish "the audit machinery is healthy" from "the science
is real," which is exactly the confusion the original UX plan's §5 (Scientific vs
Engineering views) is trying to prevent one level up in the UI — the same separation has to
exist one level down, in the data.

## 2. Boundary

```text
project_status.json
    = system / verification / engineering status
    (owner: scripts/audit_project_status.py, ADR 0022)

scientific-results contract  [proposed, not yet built]
    = empirical outputs produced by Nexus
    (owner: TBD — see §7)
```

No compelling reason was found in ADR 0001–0024 to merge these. ADR 0022 defines
`project_status.json`'s dimensions exhaustively as audit/quality gates; none of them carry
result payloads today, and none should — a `FAIL` on `backend_testing` must never become
ambiguous with a `FAIL`-shaped adversarial verdict on a candidate invention. They should
remain two sibling, independently-fetchable, independently-versioned JSON artifacts at the
repository root, following the exact publication pattern ADR 0023 §4 already established for
`project_status.json` (git-tracked at repo root, atomic regeneration, plain HTTPS/static
fetch, no server-side coupling).

**Constraint this boundary must respect (ADR 0023 / ADR 0024, both Accepted):**
`nexus-status/frontend` must never import from `frontend/` or `backend/`, and must never call
a live backend endpoint (`/api/landscape`, `/api/analyze`, etc.) — it is a static-artifact
consumer only, enforced in CI by `scripts/check_architecture.py`. Whatever produces the
scientific-results contract must therefore be a **frozen, versioned, published file**, not a
live API the dashboard queries — mirroring exactly how `project_status.json` itself is
produced and consumed.

## 3. What Nexus already produces today

Two structurally different subsystems exist, and ADR 0017 (*Dual-Track Architecture*,
Status: Proposed) already names and classifies them. This classification is the single most
important input to this design and is carried through §3–§7 below.

* **Head A — generative/product-demo** (`application/landscape/`,
  `application/synthesis/`, `infrastructure/analysis_pipeline.py`, ADK agents, exposed via
  live `GET /api/landscape` and `POST /api/analyze`): produces `PatentCluster`,
  `InventionCandidate`, `AdversarialVerdict`, `ScoreCard` per user query, in real time, via
  Gemini. ADR 0017 §2.3 is explicit: *"Head A ... is classified as synthesis/UX/product-demo
  ... It does not feed metrics, ablations, or efficacy claims. This classification is
  architectural, not provisional."* Its white-space scoring formula
  (`compute_white_space_metrics`) is deterministic arithmetic, but the candidate title,
  description, novelty claim, adversarial verdict rationale, and scorecard numbers are
  LLM-generated per request — not reproducible, not policy-sealed, not dataset-versioned.
* **Head B — deterministic/Lab** (`application/matching/`, `application/evaluation/`,
  `domain/models/matching.py`, `domain/models/evaluation.py`): produces `MatchAssessment`
  (demand↔patent relevance, with `features`, `rationale`, `policy_id`/`policy_version`/
  `policy_sha256`, `fusion_transform_id`) and `EvaluationRunReport` (sealed, dataset- and
  policy-versioned, statistically tested). This is the track ADR 0006/0007/0011/0012 govern
  as scientifically auditable — the same evidentiary machinery `project_status.json`'s
  `scientific_integrity` dimension checks the integrity of.

Neither head currently produces the vocabulary the UX plan assumes wholesale:

| UX concept | Closest existing thing | Where |
|---|---|---|
| Landscape / technology cluster | `PatentCluster` (Head A) | `domain/models/runtime_schemas.py` |
| Opportunity / white-space | `PatentCluster.is_white_space` + `quadrant` (computed, but `quadrant`/`density`/`recency`/`citation_traction`/`demand_intensity` are computed then discarded — not on the returned model) | `application/landscape/metrics.py` |
| | `OpportunityScore` / `OpportunityHypothesis` — fully modeled, **zero producers**, referenced only by their own unit test | `domain/models/opportunity.py` |
| Candidate invention | `InventionCandidate` (Head A, LLM-generated) | `domain/models/runtime_schemas.py` |
| Adversarial verification | `AdversarialVerdict` (Head A, LLM-generated) | `domain/models/runtime_schemas.py` |
| Evidence / cited prior art | `AdversarialVerdict.cited_patents` (bare `publication_id` strings, no resolved metadata); `ScoreCard.supporting_evidence` (ADR 0017: *"mandatory UX citations, not relevance grades"*) | `domain/models/runtime_schemas.py` |
| Demand↔patent evidence (Lab-grade) | `MatchAssessment` (Head B, deterministic, policy-sealed) | `domain/models/matching.py` |
| Provenance primitive | `FieldObservation` (source authority, URI, retrieval timestamp, SHA-256, verification status) — used throughout Head B, **not attached to any Head A entity** | `domain/models/evidence.py` |
| Execution/run identity | `job_id` (Head A, `uuid4().hex`, **in-memory only** — ADR 0017 §7 lists container-restart durability as future/Pilotable, i.e. not true today) vs `run_id`/`EvaluationExecutionContext` (Head B, sealed, dataset+policy+engine-hash versioned) | `infrastructure/storage/job_store.py`, `domain/models/evaluation.py` |

## 4. Proposed data model

Field classification: **Existing** (already produced, unchanged), **Derivable**
(deterministically computable from data Nexus already has, no new judgment introduced),
**New** (requires a pipeline/backend change).

### `Execution`
| field | class | note |
|---|---|---|
| `execution_id` | New | Head A's `job_id` is not durable; needs persistence to be citable evidence |
| `track` | New | must be `"discovery"` (Head A) or `"verification"` (Head B) — mandatory per ADR 0025 §1 (supersedes this document's earlier "synthesis"/"deterministic" naming) |
| `domain`, `query` | Existing | `AnalyzeRequest` |
| `created_at` | Existing | job store timestamp |
| `dataset_id`, `dataset_version` | Existing for Head B (`EvaluationRunReport`); New for Head A (no dataset stamped per job today) |
| `engine_commit`, `policy_id`/`policy_version`/`policy_sha256` | Existing for Head B; New for Head A |

### `Landscape`
| field | class | note |
|---|---|---|
| `query`, `domain` | Existing | `ResearchOutput` |
| `clusters: TechnologyCluster[]` | Existing | `ResearchOutput.clusters` |

### `TechnologyCluster`
| field | class | note |
|---|---|---|
| `cluster_id`, `label`, `representative_patents`, `patent_count`, `white_space_score`, `is_white_space` | Existing | `PatentCluster` |
| `density`, `recency`, `citation_traction`, `citation_coverage`, `demand_intensity`, `quadrant` | Derivable | already computed by `compute_white_space_metrics`, just not currently kept on the returned model |

### `Opportunity`
| field | class | note |
|---|---|---|
| `opportunity_id` | Derivable | = a white-space (`is_white_space=True`) cluster's `cluster_id`, no new concept needed |
| `cluster_id`, `white_space_score`, `quadrant` | Derivable | see `TechnologyCluster` |
| `rationale` | New | not currently generated for a cluster as such (only per-candidate rationale exists downstream) |
| `target_demand_ids` | Derivable | derivable from the demand grouping already computed inside `cluster_patents` but not surfaced |

*(`OpportunityHypothesis`/`OpportunityScore` in `domain/models/opportunity.py` model a
similar-but-not-identical shape and have no producer — adopting them wholesale vs. deriving
`Opportunity` from `PatentCluster` is an open question, see §7.)*

### `CandidateInvention`
| field | class | note |
|---|---|---|
| `candidate_id`, `cluster_id`, `title`, `description`, `claimed_novelty` | Existing | `InventionCandidate` — **LLM-generated text, must be labeled as model output** |
| `verification_status` | Existing | derived 1:1 from `AdversarialVerdict.verdict` (`survives`/`rejected`), already reconciled by `reconcile_candidate_verdicts` |
| `execution_id` | New | needs the durable `Execution` above to cite |

### `EvidenceItem`
| field | class | note |
|---|---|---|
| `citation` (publication_id) | Existing | `AdversarialVerdict.cited_patents[i]` / `ScoreCard.supporting_evidence[i]` |
| `title`, `abstract`, `publication_date`, `assignees` | Derivable | resolvable via existing `patents_datasource.search_patents` / `PatentRecord`, not currently joined back onto the citation |
| `role` (supports / challenges) | Existing | implicit in which list (`cited_patents` vs `supporting_evidence`) the citation came from |

### `AdversarialVerificationResult`
| field | class | note |
|---|---|---|
| `candidate_id`, `verdict`, `rationale`, `cited_patents` | Existing | `AdversarialVerdict` |
| `scorecard: {novelty, prior_art_risk, differentiation, evidence, supporting_evidence}` | Existing | `ScoreCard` — ADR 0017: *"mandatory UX citations, not relevance grades"*, must carry that disclaimer wherever rendered |

### `Provenance`
| field | class | note |
|---|---|---|
| shape | Existing | `FieldObservation` already defines exactly this primitive (`source_authority`, `source_uri`, `retrieval_timestamp`, `raw_payload_sha256`, `verification_status`) |
| attachment to Head A entities | New | no `CandidateInvention`/`AdversarialVerdict`/`ScoreCard` today carries a `FieldObservation` — they carry only ambient job-store metadata |

## 5. Scientific integrity invariants

1. **Track label is mandatory and immutable per record.** Every `Execution`, and therefore
   everything hanging off it, is stamped `track: "discovery" | "verification"` and the
   dashboard must render that distinction as prominently as `overall_status` is rendered
   today — collapsing Head A output into an undifferentiated "scientific result" would
   contradict ADR 0017 §2.3 directly.
2. **Every `CandidateInvention` and `AdversarialVerificationResult` must carry `execution_id`.**
   No candidate or verdict may be displayed without the run that produced it — mirrors
   `MatchAssessment.policy_sha256`/`fusion_transform_id` being mandatory, no-default fields
   in the existing Head B model (ADR 0016 §4 / ADR 0017 §4).
3. **Every evidence-backed claim references its evidence by citable id**, not by prose.
   `AdversarialVerdict.cited_patents` and `ScoreCard.supporting_evidence` already satisfy
   this at the identifier level; the contract must not collapse them into a rendered string.
4. **Cited prior art must resolve to an identifiable record.** A `publication_id` that
   cannot be resolved to a `PatentRecord`/`PatentDocument` is surfaced as an unresolved
   citation, never silently dropped or silently treated as absent evidence.
5. **Absence of evidence ≠ negative evidence.** A candidate with no `cited_patents` is
   "not yet challenged," not "clean of prior art" — the contract needs an explicit
   `challenge_status` distinct from an empty citation list.
6. **Results are dataset/execution-scoped, never global.** No aggregate ("N opportunities
   detected") may be computed across executions unless every contributing execution shares
   the same `track`, `dataset_id`, and `policy_version` — otherwise a hero-page KPI would
   silently mix incomparable runs, exactly the kind of engineering-dashboard fabrication
   §4.1 of the original plan already forbade.
7. **The frontend never recalculates a score.** `white_space_score`, `novelty`,
   `prior_art_risk`, etc. are rendered as received; any derived display value (e.g. a
   percentile) must be precomputed server-side and shipped as its own field, not computed
   client-side from raw scores.
8. **The frontend never manufactures evidence, and PILOT-status output is never presented
   as an efficacy claim** (ADR 0017 §5.8) — Head A output must carry Nexus's existing
   recall-aid / non-patentability disclaimer (ADR 0017 §5.5–5.6) verbatim, not a dashboard
   paraphrase.

## 6. Example payload

**This is a shape example only — no field values are real Nexus output.** Numbers, ids and
text below are illustrative placeholders, not observed results.

```json
{
  "schema_version": "0.1.0-draft",
  "generated_at": "2026-09-09T12:00:00Z",
  "executions": [
    {
      "execution_id": "exec-example-0001",
      "track": "discovery",
      "domain": "solid_state_battery",
      "query": "example query text",
      "created_at": "2026-09-09T11:40:00Z",
      "dataset_id": "example-dataset-id",
      "dataset_version": "0.0.0-example"
    }
  ],
  "landscape": {
    "execution_id": "exec-example-0001",
    "clusters": [
      {
        "cluster_id": "H01M",
        "label": "Solid State Battery - H01M",
        "patent_count": 12,
        "white_space_score": 0.0,
        "is_white_space": false,
        "quadrant": "Quadrant III (Dormant / Speculative)"
      }
    ]
  },
  "opportunities": [
    {
      "opportunity_id": "H01M",
      "cluster_id": "H01M",
      "white_space_score": 0.0,
      "quadrant": "Quadrant III (Dormant / Speculative)",
      "rationale": "example rationale placeholder"
    }
  ],
  "candidates": [
    {
      "candidate_id": "example-candidate-0001",
      "execution_id": "exec-example-0001",
      "cluster_id": "H01M",
      "title": "example candidate title",
      "description": "example candidate description",
      "verification_status": "survives"
    }
  ],
  "verifications": [
    {
      "candidate_id": "example-candidate-0001",
      "verdict": "survives",
      "rationale": "example rationale placeholder",
      "cited_patents": ["EXAMPLE-PATENT-0001"],
      "scorecard": {
        "novelty": 0.0,
        "prior_art_risk": 0.0,
        "differentiation": 0.0,
        "evidence": 0.0
      }
    }
  ],
  "evidence": [
    {
      "citation": "EXAMPLE-PATENT-0001",
      "role": "challenges",
      "title": "example patent title",
      "publication_date": "2020-01-01"
    }
  ]
}
```

## 7. Frontend consumption

```text
scientific_results.json  (proposed sibling of project_status.json, same publication pattern)
   ↓  fetch (static, same as useProjectStatus)
domain/scientificResults.ts  (new parser, same shape as domain/status.ts:
                               validate, freeze, reject unknown-track records —
                               no recalculation, ADR 0023 rule applied identically)
   ↓
Landscape / Opportunities / Candidates / Evidence views
   (each record's `track` badge rendered with the same prominence as
    StatusBadge today; a "discovery" record always shows the ADR 0017
    disclaimer inline, never only in a tooltip)
```

The frontend remains exactly what ADR 0023/0024 already require: a read-only, non-importing,
non-recalculating consumer. No new violation of those ADRs is introduced by adding a second
sibling contract file, provided it is published the same way (`scripts/`, repo-root,
git-tracked, atomic with its own regeneration step) rather than fetched live from the
backend.

## 8. Migration / implementation sequence

Smallest-first, each step independently shippable:

1. **Plumb the already-computed cluster metrics onto `PatentCluster`.** Zero new logic —
   `compute_white_space_metrics` already returns `density`/`recency`/`citation_traction`/
   `demand_intensity`/`quadrant`; they're discarded in `clustering.py` before constructing
   `PatentCluster`. This alone would make a real, honest `Landscape` view possible from
   Head A, still labeled `track: "discovery"`.
2. **Add a durable `Execution` record.** Persist what `job_id`/`AnalyzeRequest` already
   carry (domain, query, timestamp) past process restart — the smallest version of the
   "container restart is not data loss" requirement ADR 0017 §7 already lists as a Pilotable
   goal for the unrelated Matching Store work; here it only needs to cover Head A jobs.
3. **Write a `scripts/publish_scientific_results.py`-style step** that snapshots a
   *specific, chosen* set of completed executions into `scientific_results.json` at repo
   root, mirroring `scripts/audit_project_status.py`'s publication discipline exactly
   (atomic, git-tracked, single canonical file). This is the first point real data reaches
   `nexus-status`.
4. **Resolve `cited_patents` ids to `PatentRecord` metadata** at publish time (not
   render time) so `EvidenceItem` ships titles/dates instead of bare ids.
5. **Attach `FieldObservation`-shaped provenance** to published candidates/verdicts —
   already-defined shape, just not wired to Head A entities yet.

Steps 1–3 alone are enough to replace the `NotAvailableView` stub on Landscape with real
data, still correctly labeled `track: "discovery"` and carrying the ADR 0017 disclaimer.
Opportunities/Candidates/Evidence follow the same script incrementally.

---

## Open architectural decision — requires human approval before step 1

**Which track should populate `Opportunities`/`Candidates`/`Evidence` on a page titled
"Scientific Verification"?**

* **Head A (synthesis/demo)** is real, running, and structurally closest to the UX plan's
  vocabulary (clusters, candidates, adversarial verdicts already exist in code). But ADR
  0017 §2.3 explicitly classifies it as *not* scientific evidence ("does not feed metrics,
  ablations, or efficacy claims"), and §5.8 forbids presenting PILOT-status output as an
  efficacy claim anywhere in UI. Shipping it into a *Scientific Verification* dashboard —
  even with a disclaimer — puts Head A output in a UI whose entire premise (per the
  original brief) is "why should I believe it?", which is in tension with a track ADR 0017
  says was never meant to carry evidentiary weight.
* **Head B (deterministic/Lab)** is the track the rest of `project_status.json`'s
  `scientific_integrity` dimension actually audits, and is genuinely reproducible/sealed —
  but it doesn't produce "opportunities" or "candidate inventions" today, only demand↔patent
  `MatchAssessment` evidence. Building Landscape/Opportunities/Candidates from it means
  designing new concepts on top of an existing, scientifically legitimate substrate, not
  wiring up what already runs.

This document does not decide between them. §8 above is written so that steps 1–3 are
useful regardless of the answer, but step 3's *"specific, chosen set of executions"* and
every disclaimer described in §5/§6 depend on which answer is chosen. Recommend resolving
this — and formalizing it as an ADR, given ADR 0017 is itself still `Proposed`, not
`Accepted` — before any implementation begins.
