# Phase 2 Construct Expansion Amendment: `Technology request` only → `Technology request` + `R&D request`

**Status:** Approved (2026-09-14). This is a **methodological amendment record**, kept
separate from `docs/adr/0031-corpus-expansion-contract.md` §2.2 by design, following
the same pattern `docs/phase2-temporal-window-amendment.md` uses for the 2020–2025 →
2024–2025 window change. Approval authorizes the decision this document argues for
(§3–§8); it does not, by itself, apply it.

**Implemented and re-acquired (2026-09-14).** ADR 0031 §2.2 amended,
`corpus_expansion_policy_v3` versioned, `EenPodOfficialHarvester` extended to crawl
both construct facets, `EenPodCandidateMapper` extended for the R&D request reference
prefix, TDD added, acquisition re-run live. Full outcome: §10 below.

---

## 1. Evidence from #101b / #101c / #101b-v2

- **#101b** (live acquisition under the original 2020–2025 window, InnoGet +
  Lombardia mirror): 824 raw → 10 eligible. Root cause diagnosed as a source-frame
  failure, not an implementation defect.
- **#101c** (historical-source feasibility, no harvest run): confirmed the official
  `een.ec.europa.eu` portal's `Technology request` facet (`p:4320`) reproducibly
  returns exactly **108** total raw records, oldest `TRCH20240917026` (2024-09-17).
  The same investigation found the `R&D request` facet (`p:4355`) reproducibly
  returns **207** total raw records, oldest `DRTR20240925006` (2024-09-25) — noted at
  the time only as population context, explicitly not proposed for authorization by
  that document.
- **#101b-v2** (live acquisition under the amended 2024–2025 window,
  `Technology request` only, official portal only): 108 raw → 47 accepted, 0 mapping
  errors, audit PASSED. **`N_power ≤ 47 < 60`**, and independence status can only
  shrink that count further — the amendment closed with a "stop, don't manipulate
  criteria" gate result. Full detail: `docs/phase2-temporal-window-amendment.md` §7.

## 2. Why `Technology request` alone cannot reach N≥60

`Technology request`'s entire population on the one authorized source is 108 raw
records (a hard ceiling confirmed by two independent walks: #101c's pagination spike
and #101b-v2's actual harvest, which returned exactly 108). Even at a hypothetical
100% acceptance rate, the ceiling is 108; at the acceptance rate #101b-v2 actually
observed (43.5%), the realistic yield is well under 60 before independence dedup even
applies. No temporal-window adjustment changes this — the population, not the window,
is now the binding constraint. This is the central finding this amendment responds to.

## 3. What `R&D request` is

`R&D request` (`profile_type_id = 4355` on the official EEN/POD portal;
`node_partnering_opportunities_profile_type` term `4355`) is one of the five EEN/POD
partnering-opportunity construct types (alongside Business Offer, Business request,
Technology offer, and Technology request). Per the EEN/POD portal's own taxonomy, it
represents an organization (typically a research group, university, or R&D-active
company) publicly seeking a partner to collaborate on solving a defined technical or
scientific problem — structurally the same "party publicly articulates an unmet
technical need and seeks an external partner" shape as `Technology request`, differing
mainly in whether the seeking party frames itself as pursuing near-term technology
transfer (`Technology request`) or a joint R&D/research collaboration (`R&D request`).

## 4. Evidence that R&D request abstracts articulate technical problems

This is not new evidence — it was already established in #101b, before this amendment
was conceived. `EenPodCandidateMapper._CONSTRUCTS_WITH_TECHNICAL_ABSTRACT` already
includes `"R&D request"` alongside `"Technology request"`, and the corresponding
extraction rule (`experiments/phase2/harvesters` / mapper `Abstract`-as-technical-
problem path) was written and regression-tested in #101b specifically because both
constructs' `Abstract` sections were manually sampled and found to articulate the
technical need directly (verified against a `Business offer` negative control, which
does not). `docs/superpowers/specs/2026-09-11-pr101c-historical-source-feasibility-design.md`
§7.2 also confirms the `Abstract`/description content is present and well-formed on
the official portal for `R&D request` records (the `DR*`-prefixed ones sampled during
the pagination walk), not just on the Lombardia mirror.

## 5. Scientific justification for a shared superordinate construct

`Technology request` and `R&D request` both instantiate the same underlying
theoretical construct this study actually measures: **a publicly-solicited industrial
or research technology demand with an articulated technical problem, seeking an
external technology-provider match** — which is precisely what
`has_articulated_technical_problem` / `technical_problem_evidence_text` in
`DemandCandidateContractRecord` already operationalizes, construct-agnostically. The
policy's `permitted_constructs` field exists to gate which EEN/POD *document types*
are trusted to carry this construct, not to define the construct itself. `Business
offer` and `Business request` are excluded because they solicit commercial/market
partnerships, not technical problems (confirmed by #101b's negative-control sampling in
§4 above) — the same logic that admits `Technology request` extends to `R&D request`
on its own evidentiary merits, not by analogy alone.

**What would falsify this:** if `R&D request` abstracts, once acquired, systematically
failed `NO_TECHNICAL_PROBLEM` or `CONTENT_TOO_SHORT` under the existing unmodified
validator — i.e. if the construct admits records that don't actually carry the
technical-problem construct this study measures. This is an empirical check the
re-acquisition run itself performs (§8's success criterion), not something assumed by
this document.

## 6. What stays unchanged

- Temporal window (`2024-01-01`–`2025-12-31`, from `corpus_expansion_policy_v2`).
- Source authorization: EEN/POD official portal only. InnoGet remains dropped
  (structurally `t_demand`-unverifiable, per #101c — independent of construct).
- Content-completeness threshold (`min_word_count = 25`), technical-problem
  requirement, confidentiality rule, geographic strata, public-access requirement.
- Organization independence rule (ADR 0029) and UNKNOWN quarantine (ADR 0030) —
  unmodified and applied identically to `R&D request` records.
- The prohibition on outcome-dependent selection (ADR 0031 §2.7) — `R&D request` is
  not being added because early records "look good"; it is being proposed because its
  population (207 raw, per #101c) and its technical-problem-bearing structure (§4) are
  independent of any observed acceptance or matching outcome.
- Sector concentration monitoring thresholds.

## 7. Consequences for representativeness

Adding `R&D request` shifts the demand corpus's composition toward research-partner
solicitations alongside near-term technology-transfer solicitations. This is a
**broadening of construct scope**, not a narrowing or a convenience selection: both
constructs already share the same operationalized technical-problem construct (§5),
and the policy's rejection criteria apply identically to both. Any discussion of RQ3
or of corpus representativeness should state explicitly, from this point forward, that
the demand corpus spans two EEN/POD construct types, not one — future analysis should
report the `Technology request` / `R&D request` split (as it already reports the
`spain` / `international_european` stratum split) rather than treating the corpus as
construct-homogeneous.

## 8. Success criterion

**Success is $N_{\mathrm{power}} = N_{\mathrm{eligible,\ independent}} \ge 60$,
measured after every existing criterion is applied unchanged** — temporal window,
content-completeness, technical-problem requirement, confidentiality, public access,
and organization independence/UNKNOWN-quarantine — not simply a larger raw or accepted
count. Concretely:

1. Re-run acquisition (harvest → map → validate → audit) with both constructs
   authorized under a versioned `corpus_expansion_policy_v3`.
2. Report accepted count per construct and combined (never combined-only).
3. Resolve `organization_raw` for the full accepted pool (a real, separate gap:
   #101b-v2's 47 accepted `Technology request` records all came back
   `organization_raw = UNKNOWN` from the official-portal mapper — this must be closed
   before independence status can be computed meaningfully; see §10.)
4. Only once `organization_raw` is resolved does #102's independence audit produce a
   real $N_{\mathrm{power}}$. If accepted count alone is already `< 60` (as it was for
   `Technology request` alone), stop there without needing to resolve `organization_raw`
   first — the same conservative short-circuit #101b-v2 used.
5. Gate, same as before: **`N_power ≥ 60` → #102 proceeds. `N_power < 60` → stop,
   analyze the deficit, do not relax criteria to close the gap.**

## 9. What this amendment explicitly does not do

> **Executed — see §11 for the outcome.** The chain below was carried out as written,
> with one correction found during execution: §9 item 3's "`DR`" reference prefix
> (from #101c §7.2's single manually-read sample) turned out not to match any of the
> 207 `R&D request` records actually harvested; the real prefix, confirmed on all of
> them, is `RDR`. `DR` is kept as an accepted alternative in code in case #101c's
> reading reflects a genuine second variant never encountered in this run — see §11.

- **No opportunistic inclusion.** Records are not being added because they perform
  better in matching, produce more favorable metrics, or "look easier" — the case for
  `R&D request` rests entirely on §3–§5's construct-identity argument and #101c's
  pre-existing population evidence, all established before this document was written
  and independent of any acceptance-rate outcome.
- **No relaxation of any existing criterion** (§6).
- **No code or policy change.** `corpus_expansion_policy_v2.json` is not edited;
  `EenPodCandidateMapper` and `EenPodOfficialHarvester` are not modified. If approved,
  the chain is:
  1. Amend ADR 0031 §2.2 to authorize `R&D request` as a second permitted
     `een_pod` construct, recording this amendment per repository convention.
  2. Version `corpus_expansion_policy_v3.json` (new `permitted_constructs` entry for
     `een_pod`; every other field carried forward unmodified from `v2`, including the
     `2024-01-01`/`2025-12-31` temporal window — `v2` is not edited in place).
  3. Extend `EenPodOfficialHarvester` to also crawl `?f[0]=p:4355`, and extend
     `EenPodCandidateMapper`'s `_POD_DATE_RE`/`construct_map` to recognize the official
     portal's `DR` reference prefix for `R&D request` (distinct from the `RD` prefix
     seen on the Lombardia mirror in #101b — a naming difference already flagged in
     #101c §7.2, not yet resolved in code).
  4. TDD the construct addition: `R&D request` records accepted, non-`een_pod`
     constructs still rejected, `DR`-prefixed and `RD`-prefixed references both parse
     correctly, and every existing test for `Technology request`-only behavior still
     passes unmodified.
  5. Re-run acquisition against `v3`, run #101b-v2's same audit, report `N_power` per
     §8, and apply the same gate.
- **No decision on a third source class.** That remains a distinct, separate option
  this document does not evaluate.

## 10. Open item flagged before execution

All 47 `Technology request` records accepted in #101b-v2 have `organization_raw =
UNKNOWN` — the official-portal mapper does not currently extract an organization
identity field (the Lombardia mirror mapper path did). This is independent of the
construct-expansion question and would need addressing before a meaningful #102,
whether or not `R&D request` is authorized. §11 reports what was actually found once
acquisition ran.

## 11. Outcome (2026-09-14)

Re-ran the acquisition pipeline (harvest → map → validate → audit) against
`corpus_expansion_policy_v3`, both `een_pod` construct facets.

**Correction found during harvest:** the official portal's actual `R&D request`
reference prefix is **`RDR`** (3 letters), confirmed consistently on all 207 raw
`R&D request` records harvested — not `DR` as #101c §7.2's single manually-read
sample suggested. The initial harvest run (with only `DR` supported) crashed with a
`PayloadCollisionError`: two distinct records, neither matching any known prefix,
fell back to a URL-slug-derived synthetic id that happened to collide after
truncation. Fixed by (1) adding `RDR` as the primary `R&D request` prefix (`DR` kept
as a secondary alternative, unconfirmed but harmless), (2) anchoring the reference
regex to a token boundary (`\b`) to stop a latent cross-match bug the `DR` addition
exposed against unrelated `RD`-prefixed strings (caught by
`test_een_pod_mapper_trusts_lead_field_over_unrelated_sidebar_reference`, whose
fixture had to be corrected — it had accidentally become a coincidentally
well-formed `RDR` reference), and (3) making the synthetic-id fallback
collision-proof with a full-URL hash suffix instead of a bare truncated slug.

| Stage | Count |
| :--- | ---: |
| Raw harvested | 315 (108 `Technology request` + 207 `R&D request`, both matching #101c's/#101b-v2's population exactly) |
| Mapping errors | 0 |
| **Accepted** | **76** (47 `Technology request` + 29 `R&D request`) |
| Rejected | 239 (238 `OUT_OF_TEMPORAL_WINDOW`, 1 `CONTENT_TOO_SHORT`) |

Accepted breakdown: 12 published in 2024, 64 in 2025; 70 `international_european` / 6
`spain`. Audit (`experiments.phase2.audit` against `corpus_expansion_policy_v3`):
**PASSED**. Sealed artifacts in `data/experiments/phase2_v3/`; raw payloads in
`data/raw/phase2_candidates_v3/` (kept separate from `v2`'s raw dir).

**Gate:** accepted count **76 ≥ 60** — unlike #101b-v2's 47, this does *not*
short-circuit to "stop": §8 requires $N_{\mathrm{power}}$ measured *after*
independence, and dedup can only shrink 76, so whether the real $N_{\mathrm{power}}$
clears 60 is not yet decided. **Per the gate, #102 (independence audit) is the next
step** — not yet run by this document.

**§10's flagged gap, now confirmed as a genuine source characteristic, not a mapper
bug:** the official portal's detail page structure exposes only `Company's Country`,
never an organization/company name field, for any record inspected. Some records'
free-text description *does* name the requesting organization explicitly (e.g. "Green
Tribology Solutions (GTS) develops..."); others only say "The company..." / "A German
SME..." with no recoverable name. This means organization identity, where resolvable
at all, must come from close reading of free text — the same manual-annotation
methodology already used for `sector_assignments_n24_v1.json` — not from a structured
field a mapper fix could populate. This is #102's actual job, not a prerequisite
blocking it; #102 should expect a non-trivial `UNKNOWN` share on genuine grounds (some
organizations truly aren't named on the page), which — per ADR 0031 §2.4/§2.9 and
`unknown_handling.counts_towards_independent_target = false` — do not count toward
$N_{\mathrm{power}}$ regardless of how #102 is run.
