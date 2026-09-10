# Phase 2 Sector Assignment — Protocol

**Status:** Proposed. Fixes the assignment artifact contract for #80, before any of
the N=24 eligible demands are classified. Same discipline as
`docs/phase2-demand-construct-eligibility-audit-protocol.md` (#85/#86): contract and
executable check first, observation second, never the other way around.

**Amended (closing #90):** applying D4 analytically to the real N=24 corpus — before
writing any artifact — found demands with no defensible sector candidate under any of
the six categories (not a tie-break case; an absence of coverage). Per
`docs/phase2-sector-coverage-decision.md` (Option B: taxonomy kept unchanged, no
seventh/`OTHER` category), the artifact contract below is extended with a
`no_sector_coverage` list, separate from `assignments`, so this outcome is
representable without adding a value to `sector_code`'s closed six-value domain or
implying a failed classification attempt inside a per-demand `decision_trace`.

Which `demand_id`s land in `no_sector_coverage` is not this artifact's call: it must
match exactly the set `experiments/wpi-demand-patent-matching/config/phase2_sector_coverage_decision_v1.json`
already declares (frozen alongside the decision, `.sha256`-pinned to it). This is
deliberate — hashing only the decision *document* would let a future artifact accept
any partition of N=24 that merely satisfies the shape/membership invariants, without
actually matching the demands #90's decision was about. Pinning the declared ID set
closes that gap.

## Why this exists

`docs/phase2-sector-taxonomy-amendment.md` (#83, merged) closes the category set (D1)
and fixes the assignment algorithm (D2–D7): six sectors, exactly one per demand,
demand-text-only, no CPC/IPC, a strict-order decision procedure (D4), and an
auditability requirement (D6) for any case resolved by tie-break. What it deliberately
does not do (its own "What this amendment does not do") is assign any demand to a
sector, or define the artifact/roles that assignment work produces. This document
closes that remaining gap — the contract only, not the classification itself.

## Input (frozen, hash-pinned)

- `experiments/wpi-demand-patent-matching/data/dataset_phase2_eligible_corpus_n24_v1.json`
  (#88) — the analytic population. **Not** N=39: the 13 `INELIGIBLE` and 2 `UNCERTAIN`
  demands (#84) are out of scope for sector assignment entirely, by construction of the
  input artifact.
- `experiments/wpi-demand-patent-matching/config/phase2_sector_taxonomy_v1.json` (#83,
  frozen alongside this document) — the closed six-sector set.

Both are verified against their own sha256 sidecars before an assignment artifact may
be accepted as valid (see `check_sector_assignments.py` below); neither is re-derived.

## Permitted / forbidden information

Unchanged from the amendment's D3: `title`, `description`, and frozen provenance
metadata are permitted; retrieved patents, similarity/retrieval scores, CPC/IPC
(demand- or patent-side), and any matching-pipeline output are forbidden. Restated
here only as a reminder — D3 remains the normative source.

## Assignment artifact: top-level shape

```text
{
  "dataset_id": "...",
  "assignments": [ ... ],           // one entry per demand WITH a defensible sector
  "no_sector_coverage": [ ... ]     // one entry per demand WITHOUT one (#90/decision)
}
```

`assignments` (demand_id) ∪ `no_sector_coverage` (demand_id) must equal exactly the
N=24 eligible corpus, with no overlap and no duplicates across either list — a demand
is in exactly one of the two.

### `no_sector_coverage` entry shape

```text
{
  "demand_id": "...",
  "rationale": "...",     // why D4 produces no defensible candidate among the six
  "evidence": ["...", "..."],
  "reviewer": "Auditor A"
}
```

No `sector_code`, no `decision_trace`, no `audit` block: this is a documented absence
of a candidate, not an attempted-and-resolved classification, so it does not carry the
fields that presuppose one. `rationale` and `evidence` are still required and
non-empty — the absence of a candidate must be as auditable as a presence of one.

## `assignments` entry shape

One entry per `demand_id` with a defensible sector. Layered, not flattened, to keep
three distinct concerns separable per the amendment's own D4/D6 distinction (a
decision procedure is not the same thing as who reviewed it):

```text
{
  "demand_id": "...",
  "sector_code": "...",              // one of the six closed codes

  "decision_trace": {
    "resolved_at_step": 1,           // 1-5, the first D4 step that resolved exactly one sector
    "primary_technical_object": "...",
    "primary_technical_problem": null,      // populated only if resolved_at_step >= 2
    "application_domain": null,             // populated only if resolved_at_step >= 3
    "candidates_after_step_3": null,        // populated only if resolved_at_step >= 4; the tied sector set
    "joint_reread_result": null,            // populated only if resolved_at_step >= 4
    "title_first_object": null              // populated only if resolved_at_step == 5
  },

  "rationale": "...",                // free-text summary of the decision
  "evidence": ["...", "..."],        // verbatim quotes from title/description

  "assignment": {
    "reviewer": "Auditor A"          // who produced this primary assignment
  },

  "audit": {
    "needs_auditor_b": false,
    "auditor_b_reviewer": null,
    "auditor_b_status": null,        // Auditor B's independently-produced sector_code, when reviewed
    "agreement": null,               // auditor_b_status == sector_code, when reviewed
    "adjudication_required": false,
    "adjudication": null
  }
}
```

`assignment` (who produced the primary call) and `audit` (who reviewed it, and how
disagreement is resolved) are kept as separate objects — they answer different
questions and must not be collapsed into one `reviewer` field, per review of this
document.

### `decision_trace` invariants

`resolved_at_step` is the single source of truth for which trace fields must be
present vs. `null`. An assignment artifact is invalid if a field's presence
contradicts `resolved_at_step`:

| `resolved_at_step` | `primary_technical_problem` | `application_domain` | `candidates_after_step_3` | `joint_reread_result` | `title_first_object` |
|---|---|---|---|---|---|
| 1 | `null` | `null` | `null` | `null` | `null` |
| 2 | set | `null` | `null` | `null` | `null` |
| 3 | set | set | `null` | `null` | `null` |
| 4 | set | set | set (≥2 codes) | set | `null` |
| 5 | set | set | set (≥2 codes) | set | set |

`primary_technical_object` is always required (step 1 is always attempted first).
`evidence` and `rationale` are always required, non-empty, regardless of
`resolved_at_step`.

## Roles

Same pattern as `phase2-demand-construct-eligibility-audit-protocol.md`:

- **Auditor A** performs the full primary pass over all 24 records (`assignment.reviewer`).
- D6 mandates auditability (a recorded rationale trail) for every case resolved via D4
  step 5 (the title-first tie-break) — that obligation is already satisfied by
  `decision_trace` itself and is not, by itself, a second-reviewer requirement.
  **This protocol additionally requires independent Auditor B review of every record
  where `resolved_at_step >= 4`** (step 4's joint re-read included, not just step 5) —
  a stricter, deliberate quality-control decision of this protocol, not a restatement
  of D6's own minimum. Auditor B also reviews **any record Auditor A flags as
  borderline** at a lower step. Unflagged records resolved cleanly at step 1–3 rest on
  Auditor A alone — a deliberate scope decision, not a claim of full
  double-classification.
- Agreement (`sector_code` matches Auditor B's independent call) resolves the record.
  Disagreement is adjudicated jointly; `audit.adjudication` records the resolution and
  reasoning.

## Anti-post-hoc guard

Per the amendment's adequacy rule (D1): the taxonomy is closed and must not be revised
because of the distribution the 24 assignments produce. This protocol adds the
symmetric constraint for the assignment process itself: **the decision procedure (D4)
and this artifact contract are fixed before any of the 24 demands are read against
them.** If applying D4 to the real N=24 corpus surfaces a construct problem (as
happened once already, #84, when applying it to N=39) that blocks assignment, the
correct response is a new, explicitly-scoped finding issue — same pattern as #84 — not
a silent adjustment of D4 or of this contract while classifying.

## Frozen artifact

`experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json` —
`dataset_id: "nexus-phase2-sector-assignments-n24-v1"`, `assignments` +
`no_sector_coverage` covering the N=24 corpus exactly between them, `.sha256`
sidecar, `.manifest.json` recording `demand_count` (len of `assignments`),
`no_sector_coverage_count`, `no_sector_coverage_demand_ids`, per-sector counts,
`derived_from.{eligible_corpus_sha256, taxonomy_config_sha256, coverage_decision_sha256}`
— the third hash pins `phase2_sector_coverage_decision_v1.json` (not the decision
document directly): this artifact is invalid both if that config changes underneath
it, and — independently, checked by `check_sector_assignments.py` itself — if its own
`no_sector_coverage` list's `demand_id`s do not match exactly what that config
declares. Produced and validated in a follow-up PR — not this one.

## Verified by

`experiments/wpi-demand-patent-matching/checks/check_sector_assignments.py` and
`check_sector_coverage_decision.py` (the latter verifies
`phase2_sector_coverage_decision_v1.json` itself against its sidecar, against
`docs/phase2-sector-coverage-decision.md`'s sha256, and that its declared IDs are a
subset of the N=24 eligible corpus).

## What this protocol does not do

- Does not classify any of the 24 demands, and does not decide which demands land in
  `assignments` vs. `no_sector_coverage`. That is the next, separate PR.
- Does not modify `phase2_sector_taxonomy_v1` (#83) or the amendment's D1–D7. The
  `no_sector_coverage` mechanism is deliberately not a seventh `sector_code` value —
  see `docs/phase2-sector-coverage-decision.md`.
- Does not re-derive or modify `dataset_phase2_eligible_corpus_n24_v1.json` (#88).
- Does not touch #79 (Dev/Test split) or ADR 0016's normalization decision. #79 must
  consume `assignments` as the sector-stratifiable population once frozen, not
  re-derive or re-decide coverage during the split.
- Does not observe, and must not be revised based on, any actual sector distribution.
