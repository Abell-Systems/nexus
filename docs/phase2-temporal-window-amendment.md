# Phase 2 Temporal Window Amendment: 2020–2025 (pre-registered) → 2024–2025 (proposed)

**Status:** Proposed. This is a **methodological amendment record**, kept separate from
`docs/adr/0031-corpus-expansion-contract.md` §2.3 by design: ADR 0031's frozen
pre-registered window (`2020-01-01` to `2025-12-31`) is not rewritten here as if it had
always said 2024. This document records a decision made *after* pre-registration and
after two empirical feasibility findings (#101b, #101c), following the same pattern
`docs/phase2-sample-size-amendment.md` uses for the N=60→39 gap and
`docs/phase2-sector-taxonomy-amendment.md` uses for closing the `sector` attribute.

**Nothing in this amendment has been applied yet.** `corpus_expansion_policy_v1.json`,
ADR 0031, and the #101b design spec are unmodified as of this writing. Applying it
(editing the policy, updating ADR 0031, re-running acquisition) is a separate,
explicit next step, listed in §6 below — not taken here.

---

## 1. What was pre-registered

`docs/adr/0031-corpus-expansion-contract.md` §2.3:

> **Permitted Window:** `2020-01-01` to `2025-12-31` inclusive.
> **Exclusion of 2026:** Solicitations published in 2026 are excluded to decouple
> benchmark construction from unresolved, actively evolving industrial contexts.

Carried through unchanged into `corpus_expansion_policy_v1.json`
(`temporal_window.min_publication_date = "2020-01-01"`,
`temporal_window.max_publication_date = "2025-12-31"`) and into #101b's design spec and
`validate_demand_candidate`.

## 2. What #101b found (live-source acquisition)

Milestone #101b executed the full acquisition pipeline (harvest → map → validate →
audit) against live sources under the unmodified 2020–2025 window: **824 raw
candidates, 10 eligible, 814 rejected**, audit PASSED on all cryptographic, partition,
and field invariants. Two genuine extraction bugs were found and fixed with regression
tests along the way (a harvester/mapper `demand_id` collision, and a missing
Abstract-as-technical-problem extraction rule for EEN/POD `Technology
request`/`R&D request`) — neither changed eligibility criteria. `#101b`'s own
conclusion: the shortfall is a **source-frame failure** (both sources predominantly
surface current/live listings, not a historical archive), not an implementation
defect. Full detail: `docs/superpowers/specs/2026-09-11-pr101b-corpus-expansion-acquisition-design.md`
§8.

## 3. What #101c found (historical-source feasibility)

Milestone #101c investigated whether a reproducible historical source exists for
2020–2025, without modifying the policy or running any harvest:

- **InnoGet: dropped, live or archived.** Verified via the Wayback Machine CDX API
  (real 2020–2021 snapshot coverage exists) and by fetching a full 2021-09-22 archived
  detail page directly: it carries **no publication-date evidence of any kind**,
  structurally identical to the current live site — only a `Deadline` field. No
  feed/sitemap/API alternative exists. Using an archive capture date as a `t_demand`
  proxy would itself violate ADR 0032 Golden Invariant #3 (crawl/capture dates cannot
  substitute for publication date).

- **EEN/POD official portal (een.ec.europa.eu, superseding the Lombardia live mirror
  used in #101b): reproducible, but population-limited.** A Playwright browser spike
  confirmed the construct facet (`?f[0]=p:{profile_type_id}`) is real and
  deterministically reproducible (fresh navigation, no session state, same result
  twice). Paginating to the last page for each eligible construct found:
  - `Technology request` (`p:4320`): **108 total results**, oldest `TRCH20240917026`
    (2024-09-17).
  - `R&D request` (`p:4355`): **207 total results**, oldest `DRTR20240925006`
    (2024-09-25) — not currently an authorized construct under ADR 0031 §2.2; noted
    here as population context only, not proposed for authorization by this document.

  Both populations bottom out around **September 2024**. This is a hard ceiling on the
  source's own population, not a query-contract or reproducibility problem.

Full detail, including the static-analysis correction the browser spike caught (an
earlier hypothesized date-interval filter turned out to belong to an unrelated,
generically-indexed search form):
`docs/superpowers/specs/2026-09-11-pr101c-historical-source-feasibility-design.md` §7.

## 4. What this amendment proposes

Narrow the permitted temporal window in ADR 0031 §2.3 and
`corpus_expansion_policy_v1.json` from:

```text
min_publication_date: 2020-01-01
max_publication_date: 2025-12-31
```

to:

```text
min_publication_date: 2024-01-01
max_publication_date: 2025-12-31
```

Nothing else in the contract changes: authorized sources and constructs (§2.2),
content-completeness threshold (§2.6), independence/anti-concentration rules (§2.4),
the pre-specified exclusion taxonomy (§2.5), and the prohibition on outcome-dependent
selection (§2.7) are all carried forward unmodified. This is a narrower observation
window on an otherwise identical contract, not a relaxation of eligibility criteria.

## 5. What was not done to reach this proposal

- The window was not widened, split, or otherwise adjusted to fit a number already
  observed — the only two data points available (~2023-04 unfiltered floor, ~2024-09
  construct-filtered floor) both independently point to the same conclusion, and 2024
  is the more conservative (later, safer) of the two floors.
- Construct authorization was not expanded to include `R&D request` to inflate the
  addressable EEN/POD population, even though its 207 raw results would help — that is
  a distinct §2.2 decision this document does not make.
- InnoGet was not kept in as a nominal source to pad source count — it remains
  technically listed in `corpus_expansion_policy_v1.json.sources`, but per §3 above it
  will always fail `UNVERIFIABLE_PUBLICATION_DATE` regardless of window; whether to
  formally remove it from `sources` is an open question for whoever applies this
  amendment (§6), not decided here.
- Content-completeness, independence, and anti-concentration rules were not loosened.
- `corpus_expansion_policy_v1.json` was not edited.
- #102 was not run against the 10 candidates from #101b's diagnostic run — running it
  now would audit independence on a corpus this amendment is explicitly about to
  supersede.

## 6. Consequence for interpretation, and next steps if approved

**Scope change, stated plainly:** the corpus moves from a 6-year historical
retrospective sample (2020–2025) to a ~2-year near-contemporary one (2024–2025). Any
discussion of RQ3 (temporal/jurisdictional eligibility) or of the demand corpus's
representativeness should account for this narrower span explicitly, not silently.

**This does not yet establish that N_power ≥ 60 is achievable even under 2024–2025.**
The 108 raw `Technology request` records found in #101c's pagination walk are an
*upper bound on population*, not a forecast of eligible count — #101b already
demonstrated that raw counts shrink sharply once content-completeness, independence,
and the other §2.5 exclusion criteria are actually applied (824 raw → 10 eligible under
the old window). With InnoGet now excluded outright (a source that contributed roughly
half of #101b's raw volume), the addressable population is smaller in absolute terms
even before any filtering. Whether 108 raw EEN/POD records clear 60 independent,
content-complete, construct-compatible observations is an empirical question for a
re-run of #101b, not something this document can answer analytically.

**If this amendment is approved, the chain is:**
1. Edit ADR 0031 §2.3 (temporal window) to reflect this amendment; record the amendment
   reference in the ADR per repository convention.
2. Version `corpus_expansion_policy_v1.json` accordingly (new `temporal_window` bounds;
   consider whether the frozen-artifact convention used elsewhere in this repo warrants
   a new `corpus_expansion_policy_v2` rather than an in-place edit, given no corpus has
   yet been frozen against v1).
3. Re-run #101b's acquisition pipeline (harvest → map → validate → audit) against the
   amended window — EEN/POD only, `Technology request` construct only, per §3's
   findings.
4. Only once that run produces a sealed, audited candidate pool does #102 (independence
   audit) proceed.

None of steps 1–4 are taken by this document.
