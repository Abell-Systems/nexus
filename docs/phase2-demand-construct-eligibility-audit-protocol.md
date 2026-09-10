# Phase 2 Demand Construct Eligibility Audit — Protocol

**Status:** Proposed. Resolves #84 by hypothesis A: turning "is this demand a technology
solicitation under §4.1?" into a reproducible, per-record, closed audit — independent
of `phase2_sector_taxonomy_v1` (#83).

## Why this exists

#80 (sector assignment) found 24/39 demands with no defensible fit in the six frozen
sector categories. Reading those 24 individually found many read as exactly the class
`empirical-study-protocol.md` §4.1 excludes: "pure business partnership or marketing
requests lacking technical specifications." The acquisition audit
(`docs/phase2-demand-acquisition-audit.md`, closed) verified "compatible demand
construct" at the **source/platform level** (InnoGet as a whole qualifies), never at
the per-record level — the same shortcut that same audit already self-corrected for a
different criterion (content-completeness, 48→43→39).

This document does not modify `phase2_sector_taxonomy_v1`, does not touch
`data/evaluation/dataset_phase2_demand_corpus_n39.json`, and does not reopen #78. It
defines the rubric and produces an audit artifact that determines, per record, whether
each of the 39 demands satisfies §4.1's construct — a question logically prior to, and
independent of, which sector it would be assigned.

## Explicit separation from sector fit

**Sector-fit ("does this demand match one of the six categories") is not evidence of
construct eligibility, and construct ineligibility is not inferred from sector-fit
failure.** A demand can be a legitimate technology solicitation that the current
taxonomy simply doesn't cover (a taxonomy-coverage question, #83/#84 path B) — that is
not grounds to mark it construct-ineligible here. Conversely, a demand can superficially
resemble a named sector while being, on inspection, a pure market-research or marketing
brief. The two questions are evaluated independently, using only §4.1's own criteria.

## Rubric

For each demand, using only `title` + `description` (the same permitted-information
scope as #83's D3 — no CPC, no retrieval results, no experimental output):

| Field | Values | Meaning |
|---|---|---|
| `technical_problem_present` | yes / no | Does the text name a defined technical problem, limitation, or performance gap to be solved? |
| `technology_solution_requested` | yes / no | Is an external technology/material/method/product being solicited (not an existing product being marketed, sold, licensed *out*, or analyzed for business adoption)? |
| `technical_specification_present` | yes / no | Are there concrete operational constraints, parameters, or target metrics (§4.1 inclusion criterion 2)? |
| `exclusion_criterion_1` | yes / no | Does the text match §4.1's "pure business partnership or marketing requests lacking technical specifications"? |
| `construct_status` | `ELIGIBLE` / `INELIGIBLE` / `UNCERTAIN` | Final determination, per the decision rule below. |
| `rationale` | free text | Why, referencing the fields above. |
| `evidence` | quoted fragment(s) | The specific text the determination rests on. |
| `reviewer` | identifier | Who made this pass. |
| `adjudication` | free text or null | Filled only if Auditor A and B disagree (see roles). |

### Decision rule

```text
IF exclusion_criterion_1 == yes
      → INELIGIBLE
ELSE IF technical_problem_present == no
      → INELIGIBLE
ELSE IF technology_solution_requested == no
      → INELIGIBLE
ELSE
      → ELIGIBLE
```

`UNCERTAIN` is used only when the text genuinely does not permit a defensible
determination under the above — not as a default for difficult-but-resolvable cases.

**Sector fit ("does it belong to one of the six taxonomy categories") is never an
input to this rule.** A demand naming a real technical problem and requesting a real
technical solution is `ELIGIBLE` even if no current sector category covers its domain
(e.g. automotive lightweighting materials, LCD thermal performance) — that outcome
feeds #83/#84 path B (taxonomy coverage), not this audit's exclusion decision.

### Worked calibration examples

- **`INNOGET-1625`** ("method to remove sodium and trapped water from residual fuel
  oil"): names contaminants to remove and the commercial blending constraint →
  `technical_problem_present=yes`, `technology_solution_requested=yes`,
  `technical_specification_present=yes`, `exclusion_criterion_1=no` → **ELIGIBLE**.
  (Also has no fit in `phase2_sector_taxonomy_v1` — a taxonomy-coverage case, not an
  eligibility failure.)
- **`INNOGET-2297`** ("Designing the Future Marketing Campaign for Connect IQ"): the
  demand *is* a request to design a marketing campaign, not a technology → matches
  §4.1 exclusion text verbatim → `exclusion_criterion_1=yes` → **INELIGIBLE**,
  regardless of the fact that "Connect IQ" (machine performance/energy monitoring)
  would otherwise map cleanly to `INDUSTRIAL_MACHINERY_IOT`. Sector-fit does not
  override construct exclusion.
- **`INNOGET-2054`** ("Seeking electromagnetic applications to be converted into a
  final product"): the text describes the requesting company's *own* existing magnet
  manufacturing capabilities and solicits commercialization collaborators, without
  stating a technical problem to be solved → `technical_problem_present=no` →
  **UNCERTAIN** (reads as a capability/partnership listing, not clearly the exclusion
  class either — flagged for Auditor B).

## Roles

- **Auditor A** performs the full pass over all 39 records.
- **Auditor B** independently reviews every record marked `INELIGIBLE` or `UNCERTAIN`
  by Auditor A, plus any record Auditor A flags as difficult even where resolved
  `ELIGIBLE`.
- Agreement (`A == B`) resolves the record. Disagreement is adjudicated jointly and the
  `adjudication` field records the resolution and reasoning. This is a corpus-integrity
  audit, not a new inter-rater-reliability endpoint — no kappa statistic is computed
  unless separately decided.

## Artifact

`data/evaluation/phase2_demand_construct_eligibility_n39_v1.json` +
`.sha256` sidecar, covering all 39 `demand_id`s from the frozen
`dataset_phase2_demand_corpus_n39.json`, one entry each, produced against this rubric.

## What this protocol does not do

- Does not modify `phase2_sector_taxonomy_v1` (#83).
- Does not modify `dataset_phase2_demand_corpus_n39.json` or produce a derived,
  reduced corpus. If the completed, adjudicated audit finds INELIGIBLE records, a
  separate step (after #84's decision) would produce a distinct, traceable analytic
  corpus derived from N=39 — not an edit to the original acquisition artifact.
- Does not resolve #84's A/B/C decision unilaterally. Auditor A's pass here is one
  input; Auditor B review of the flagged records is required before #84 closes.
- Does not reopen #78 or #80.
