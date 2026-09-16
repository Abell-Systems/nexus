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
`experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.json`, and does not reopen #78. It
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

Each of the four rubric fields below takes one of three values: `yes`, `no`, or
`indeterminate`. `indeterminate` is reserved for a field the text genuinely does not
permit a defensible yes/no call on — it is not a synonym for "no" and not a
convenience default for a difficult-but-resolvable case.

| Field | Values | Meaning |
|---|---|---|
| `technical_problem_present` | yes / no / indeterminate | Does the text name a defined technical problem, limitation, or performance gap to be solved? |
| `technology_solution_requested` | yes / no / indeterminate | Is an external technology/material/method/product being solicited (not an existing product being marketed, sold, licensed *out*, or analyzed for business adoption)? |
| `technical_specification_present` | yes / no / indeterminate | Are there concrete operational constraints, parameters, or target metrics? This is §4.1 Demand Inclusion Criterion 2 verbatim ("Identifies specific operational constraints or target technical metrics") — a required inclusion condition, not a descriptive/auxiliary field. |
| `exclusion_criterion_1` | yes / no / indeterminate | Does the text match §4.1 Demand Exclusion Criterion 1, "pure business partnership or marketing requests lacking technical specifications"? |
| `construct_status` | `ELIGIBLE` / `INELIGIBLE` / `UNCERTAIN` | Final determination, mechanically derived from the four fields above by the decision rule below — never set independently of them. |
| `rationale` | free text | Why, referencing the fields above, using only §4.1's own terms (technical problem / solution requested / specification / exclusion criterion). Does not introduce undefined derived concepts (e.g. "patent-relevant", "inverse construct") that §4.1 does not itself use — construct eligibility is evaluated against the demand text alone, not against how well-suited the demand later turns out to be for patent retrieval. |
| `evidence` | quoted fragment(s) | The specific text the determination rests on. For a demand where the frozen corpus record's `title`/`description` conflicts with any other repository document's characterization of the same or a similarly-named record (see "Provenance discrepancies" below), evidence is drawn from the frozen corpus record only. |
| `reviewer` | identifier | Who made this pass. |
| `adjudication` | free text or null | Filled only if Auditor A and B disagree (see roles). |

### Decision rule

```text
IF technical_problem_present == indeterminate
   OR technology_solution_requested == indeterminate
   OR technical_specification_present == indeterminate
   OR exclusion_criterion_1 == indeterminate
      → UNCERTAIN

ELSE IF exclusion_criterion_1 == yes
      → INELIGIBLE
ELSE IF technical_problem_present == no
      → INELIGIBLE
ELSE IF technology_solution_requested == no
      → INELIGIBLE
ELSE IF technical_specification_present == no
      → INELIGIBLE

ELSE
      → ELIGIBLE
```

`construct_status` is a pure function of the four fields — there is no path to
`UNCERTAIN` (or to `ELIGIBLE`/`INELIGIBLE`) that does not go through this rule. A
record is `UNCERTAIN` precisely when at least one rubric field itself could not be
assigned a defensible `yes`/`no` from the text — not when the auditor finds the
*outcome* uncomfortable. `technical_specification_present == no` is a first-class
inclusion failure per §4.1 Criterion 2, on equal footing with the other two positive
requirements — not a descriptive-only field, matching the reading that all three of
§4.1's Demand Inclusion Criteria are conjunctive requirements, not illustrative
guidance.

**Sector fit ("does it belong to one of the six taxonomy categories") is never an
input to this rule.** A demand naming a real technical problem, a real technical
solution, and concrete specifications is `ELIGIBLE` even if no current sector category
covers its domain (e.g. automotive lightweighting materials, LCD thermal performance)
— that outcome feeds #83/#84 path B (taxonomy coverage), not this audit's exclusion
decision.

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
  independent of the underlying product's technical domain (machine
  performance/energy monitoring). Sector-fit does not override construct exclusion.
- **`INNOGET-2054`** ("Seeking electromagnetic applications to be converted into a
  final product"): the text describes the requesting company's *own* existing magnet
  manufacturing capabilities and solicits commercialization collaborators; whether
  this states an external technical problem to be solved, versus a capability
  advertisement seeking partners, cannot be resolved from the text alone →
  `technical_problem_present=indeterminate` → **UNCERTAIN** (flagged for Auditor B).

## Provenance discrepancies

If, during this audit, a frozen corpus record's actual `title`/`description` is found
to conflict with how the same or a similarly-numbered record is characterized
elsewhere in the repository (e.g. an illustrative example in another document), the
**frozen corpus record is the sole authority for this audit's determination.** The
discrepancy itself is noted in `rationale`/`evidence` as a flag for Auditor B, and, if
substantive, tracked as a separate provenance issue — it is never used as additional
evidence for, or against, construct eligibility. This audit determines eligibility of
what is actually in `dataset_phase2_demand_corpus_n39.json`, not of what any other
document says that record represents.

## Roles

- **Auditor A** performs the full primary pass over all 39 records.
- **Auditor B independently reviews every record marked `INELIGIBLE` or `UNCERTAIN`
  by Auditor A, plus any `ELIGIBLE` record Auditor A flags as borderline** — this is
  full-primary-audit-plus-independent-review-of-all-adverse/uncertain/borderline-cases,
  **not** a second independent full classification of all 39 records. For any
  unflagged `ELIGIBLE` record, the final determination rests on Auditor A alone; that
  is a deliberate scope decision (targeted independent review of every
  non-straightforward case), not a claim of double-classification coverage, and must
  not be described as an "independent audit" of all 39 without this qualification.
- Agreement (`A == B`) resolves the record. Disagreement is adjudicated jointly and the
  `adjudication` field records the resolution and reasoning. This is a corpus-integrity
  audit, not a new inter-rater-reliability endpoint — no kappa statistic is computed
  unless separately decided.

## Closure

Auditor B (Lydia Bares) reviewed all 19 records flagged `needs_auditor_b` (the 13
`INELIGIBLE`, the 2 `UNCERTAIN`, and the 4 borderline-flagged `ELIGIBLE` records) and
confirmed agreement with Auditor A's determination on every one. There is no
disagreement to adjudicate, so no `adjudication` text exists beyond the agreement
itself — per the note under "Roles," this is Auditor B's scoped review of the flagged
records, not an independent full re-classification of all 39.

**Final result: 24 ELIGIBLE, 13 INELIGIBLE, 2 UNCERTAIN.**

`UNCERTAIN` is not `ELIGIBLE`. Per the decision rule, it means construct eligibility
could not be established from the text on at least one required field — it is not a
form of provisional inclusion. The analytic population for Phase 2 going forward is
therefore the **24 `ELIGIBLE` records**, not 26. The 2 `UNCERTAIN` records
(`INNOGET-2054`, `INNOGET-2425`) are excluded from the confirmatory corpus alongside
the 13 `INELIGIBLE` ones, unless a future, separately-decided amendment revisits them.

**N=24 analytic corpus freeze.** Per "What this protocol does not do" below, this
protocol document does not itself produce a reduced corpus — that is now a separate,
traceable derivation: `experiments/wpi-demand-patent-matching/data/dataset_phase2_eligible_corpus_n24_v1.json`
(+ `.sha256` sidecar, `.manifest.json`), the deterministic projection of the frozen
N=39 corpus onto exactly the 24 `ELIGIBLE` `demand_id`s above, in N=39 order, with no
field transformation. Generated by `experiments/wpi-demand-patent-matching/checks/generate_eligible_corpus.py`
and verified by `check_eligible_corpus.py` (both inputs — the N=39 corpus and this
audit — are treated as frozen and checked by sha256, not re-derived). This is the
input #80 (sector taxonomy assignment) resumes on.

## Artifact

`experiments/wpi-demand-patent-matching/data/phase2_demand_construct_eligibility_n39_v1.json` +
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
