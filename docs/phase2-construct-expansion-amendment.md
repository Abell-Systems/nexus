# Phase 2 Construct Expansion Amendment: `Technology request` only → `Technology request` + `R&D request`

**Status:** Approved (2026-09-14). This is a **methodological amendment record**, kept
separate from `docs/adr/0031-corpus-expansion-contract.md` §2.2 by design, following
the same pattern `docs/phase2-temporal-window-amendment.md` uses for the 2020–2025 →
2024–2025 window change. Approval authorizes the decision this document argues for
(§3–§8); it does not, by itself, apply it.

**Approved, but not yet implemented.** `corpus_expansion_policy_v2.json`, ADR 0031,
`EenPodCandidateMapper`, and `EenPodOfficialHarvester` remain unmodified as of this
writing — this is a deliberate separation of the methodological decision (this commit)
from its implementation (a distinct, separate commit/PR). Applying it (editing ADR
0031 §2.2, versioning a `v3` policy, extending the mapper/harvester, TDD, and
re-running acquisition) is §9's explicit next step, not taken here. The success
criterion in §8 — $N_{\mathrm{power}} \ge 60$ *after* every existing filter and the
independence audit, never a raw or accepted count alone — governs that follow-on work
and is not relaxed by this approval.

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

## 10. Open item, not resolved here

All 47 `Technology request` records accepted in #101b-v2 have `organization_raw =
UNKNOWN` — the official-portal mapper does not currently extract an organization
identity field (the Lombardia mirror mapper path did). This is independent of the
construct-expansion question and would block a meaningful #102 regardless of whether
`R&D request` is authorized. Whoever implements §9's chain should treat this as a
prerequisite to #102, not as something this amendment or a `v3` policy change
resolves on its own.
