# Phase 2 Sector Taxonomy Coverage Decision — closing #90

**Status:** Decided. Resolves #90 (finding: `phase2_sector_taxonomy_v1` has no
defensible candidate, under D4, for 11 of the 24 demands in the frozen
`dataset_phase2_eligible_corpus_n24_v1.json`).

## Decision

**The six-category taxonomy is kept unchanged. No seventh category is added.**

Checked against `docs/empirical-study-protocol.md` end to end (#90 §3): every domain
name the protocol mentions anywhere (§4.1's `sector` definition, RQ4's example list)
is already captured by `phase2_sector_taxonomy_v1`'s six categories. There is no
pre-registered domain name left over to justify an additional category. Naming one now
would necessarily be derived from having observed these 11 real demands — the exact
post-hoc contamination `docs/phase2-sector-taxonomy-amendment.md`'s D1 adequacy rule
forbids ("the taxonomy's adequacy is judged solely by its correspondence to the
pre-registered domain ... never by the distribution observed"). Amending the taxonomy
is therefore not an available option under the current protocol, not merely a
disfavored one.

An `OTHER`/residual category is also rejected, for the reason D1 already gave: it
would immediately raise the same question one level down — what construct `OTHER`
represents and what rule assigns it — without answering it.

## What "no sector coverage" means

> The six-sector taxonomy is kept without expansion. Eligible demands for which D4
> produces no defensible sector are not assigned a sector, and are not included in
> analyses requiring sector stratification. They remain in the N=24 corpus and are
> **not** treated as `INELIGIBLE` or `UNCERTAIN` with respect to the demand construct
> (`docs/phase2-demand-construct-eligibility-audit-protocol.md`, #84/#85/#86) — that
> question is closed and is not reopened here.

Concretely:

- **Corpus membership is unaffected.** All 24 demands in
  `dataset_phase2_eligible_corpus_n24_v1.json` remain exactly as frozen by #88. This
  decision does not remove, add, or modify any demand record.
- **Sector-stratified analysis population is redefined, explicitly, here — not
  inferred later by a script.** The population eligible for sector-stratified
  analysis (feeding #79's Dev/Test split and RQ4's domain-heterogeneity analysis) is
  the subset of N=24 with a defensible sector under D4. The 11 without coverage are
  excluded from that specific population, not from the corpus generally.
- **The reason for the 11's exclusion from sector-stratified analysis must be
  reported as instrument coverage, not demand quality.** Any read-out of this
  (paper, dashboard, downstream doc) must state plainly: coverage was left short by
  the taxonomy instrument, not by an inelegibility or defect in these 11 demands. Each
  is a legitimate, construct-eligible technology solicitation (#85/#86); the taxonomy
  pre-registered in §4.1/RQ4 simply does not name its domain.

## Artifact-contract consequence (#89)

`docs/phase2-sector-assignment-protocol.md`'s artifact contract is amended, minimally,
to represent this without touching `sector_code`'s closed six-value domain (see that
document's own changelog note for the exact mechanism): the sector-assignment
artifact's per-demand entries cover only the demands with sector coverage; the 11
without coverage are recorded once, at the artifact's top level, by `demand_id` and a
pointer to this decision — never as a seventh `sector_code` value, and never inside a
per-demand entry that would otherwise imply an attempted-but-failed classification
judgment.

## Traceability

- `phase2_sector_taxonomy_v1` (#83): **unchanged**, `docs/phase2-sector-taxonomy-amendment.md` untouched.
- `dataset_phase2_eligible_corpus_n24_v1.json` (#88): **unchanged**.
- `docs/phase2-sector-assignment-protocol.md` (#89): amended per "Artifact-contract
  consequence" above; the D4 decision procedure and per-entry `decision_trace` shape
  for demands that *do* have coverage are otherwise unchanged.
- This decision does not itself classify any demand. #80's classification PR resumes
  against this decision plus #89's (amended) contract.
- This decision does not touch #79. #79's stratification design must consume the
  13-demand sector-coverable population as its stratification input once #80 freezes
  it — not re-derive or re-decide coverage during the split.

Closes #90.
