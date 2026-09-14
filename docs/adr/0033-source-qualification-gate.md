# ADR 0033: Source Qualification Gate for Phase-2 Demand Corpus Expansion

**Status:** Proposed
**Date:** 2026-09-14
**Scope:** Defines a documentary qualification gate for candidate primary sources under
ADR 0031 §2.2's `ADMISSIBLE_SOURCE_CANDIDATE` process, and applies it to the first
round of candidates investigated after #102's closure. Authorizes nothing beyond
recording this evaluation — no source is admitted, and no acquisition runs from it.

---

## 1. Context

#102 (`docs/phase2-demand-independence-audit-n76-v3-closure.md`) closed with
$N_{\mathrm{power}} = 0$: applying ADR 0029's unmodified, binding organization-identity
rule to the 76 candidates accepted under `corpus_expansion_policy_v3` found
`organization_raw` null for all 76, verified exhaustively across all 315 raw payloads
(not a sample). This is a source-structure finding, not fixable by further EEN/POD
acquisition: the official portal never publishes a company-name field, for either
authorized construct, under any temporal window.

**A sharper finding, established while scoping this ADR:** re-checking #101b's sealed
`data/experiments/phase2/candidates_mapped.json` shows the two sources this study has
ever acquired from split cleanly and completely on the two axes that matter most:

| Source | `organization_raw` populated | Date evidence verifiable |
| :--- | ---: | ---: |
| InnoGet (424 records) | 422 / 424 | 0 / 424 (`unverifiable`, #101c) |
| EEN/POD, Lombardia mirror (400 records, #101b) | 0 / 400 | varies, generally live-only (#101b) |
| EEN/POD, official portal (315 records, #101d) | 0 / 315 | 315 / 315 (that's why it was authorized) |

**No source this study has ever touched has had both identity and date evidence
simultaneously.** This is the bar a new candidate must clear, and it is a bar neither
prior source cleared — so a candidate resembling either in structure is not worth
re-investigating on that axis alone.

## 2. Gate Criteria

A candidate source must be evaluated, in this order, against:

1. **Construct fit:** does the source carry postings matching "a publicly-solicited
   industrial or research technology demand with an articulated technical problem,
   seeking an external technology-provider match" (the construct ADR 0031 §2.2 /
   `docs/phase2-construct-expansion-amendment.md` §5 already operationalizes) —
   or something structurally different (a procurement specification, a funding call, a
   generic partnership listing)?
2. **Identity field:** is the requesting organization's identity present as an
   **observed, explicit field or fact** in the record as acquired — never inferred
   from title/description text (ADR 0029 §3.1, unconditionally binding, not relaxed
   by this ADR)?
3. **Date:** is there a verifiable **publication** date distinct from a deadline,
   crawl date, or last-updated timestamp (Golden Invariant #3, ADR 0032)?
4. **Historical depth:** does the source's population extend back far enough to be
   useful under a defensible temporal window (not necessarily 2020, but not only the
   live present either — #101c/#101b-v2's lesson)?
5. **Volume:** is the population, after a realistic estimate of the acceptance rate
   observed elsewhere in this study (roughly 1–45%, #101b through #101d), plausibly
   sufficient to clear $N \ge 60$ **independent** observations, not just raw records?
6. **Access:** is the source publicly, reproducibly accessible without authentication,
   scraping-hostile bot mitigation, or paywall?
7. **Geography:** is the source's population compatible with ADR 0031 §2.1's `spain` /
   `international_european` strata, or would it require a new stratum definition?
8. **Independence:** setting organization identity aside, is there an early, visible
   risk of concentration (a handful of repeat postings from the same handful of
   requesters) that would erode $N_{\mathrm{power}}$ even if identity is resolvable?

A candidate that fails (1), (2), or (3) outright does not warrant a browser-spike-level
investigation (the #101c/#101d pattern) — those three are structural, not tunable by
acquisition parameters. A candidate passing (1)–(3) provisionally, with (4)–(8) still
open, is a **live lead**, not a qualified source; qualification requires a dedicated
spike (per #101c's precedent) before any acquisition code is written.

## 3. Candidates Investigated

Documentary web research only. No scraper, harvester, or mapper code was written. No
policy file was modified. No harvest was run.

### 3.1 TED (Tenders Electronic Daily) — EU public procurement notices, Pre-Commercial Procurement / Innovation Partnership notices

- **Construct fit — partial, genuinely different population.** TED's general
  procurement notices are specifications for known deliverables, not open technical-
  problem solicitations — a poor construct match. Its narrower **Pre-Commercial
  Procurement (PCP)** and **Innovation Partnership** procedure types are structurally
  closer: a public buyer states an unresolved technical challenge and invites R&D
  proposals. This shifts the requester population from private industrial companies
  toward public bodies (hospitals, municipalities, agencies) commissioning R&D — a
  real representativeness difference from InnoGet/EEN's private-company demands, to be
  stated explicitly if pursued, not smoothed over.
- **Identity field — pass.** "Name, address, country of the buyer (the contracting
  authority)" is a mandatory structured field on every notice, by EU procurement-law
  requirement, not a discretionary field a poster might omit.
- **Date — pass.** Publication date is mandatory and structurally distinct from
  submission-deadline fields.
- **Historical depth — pass.** Bulk open data available 2006–2021 (CSV), with the live
  TED site continuing to the present.
- **Volume — likely pass, unconfirmed for the narrowed PCP/Innovation-Partnership
  subset specifically.** Aggregate TED volume is very large; the PCP/Innovation
  Partnership subset (the only construct-relevant slice) is a much smaller fraction not
  yet sized.
- **Access — pass.** Structured open-data exports and an API exist (third-party
  wrappers found; official TED API also documented publicly), no authentication.
- **Geography — pass.** EU/EEA-wide by construction; Spain-stratum coverage included.
- **Independence — unconfirmed.** Repeat public buyers (large national agencies, for
  instance) issuing many PCP notices could concentrate the pool; not checked yet.

**Verdict: live lead.** Clears the three structural criteria provisionally. Needs a
dedicated spike (real PCP/Innovation Partnership notice sample, construct-fit read
against `has_articulated_technical_problem`, and a volume count for that specific
procedure type) before further consideration — not qualified yet.

### 3.2 InnoGet white-label instances (e.g. `qrdiopeninnovationchallenges.innoget.com`)

Checked as a distinct question from the main `innoget.com` site (already ruled out by
#101c): does a *different* InnoGet-hosted tenant expose date evidence the main site's
template lacks?

- **Construct fit — pass** (same InnoGet challenge construct already validated in
  #101b/#101c).
- **Identity field — pass.** Named requesting organizations shown explicitly (e.g.
  "Kahramaa", "Hassad Food", "Milaha", on the one tenant sampled).
- **Date — fail, same defect as the main site.** Only a submission deadline is shown;
  no publication date field exists on this template either.
- **Historical depth — fail.** Six challenges total on the sampled tenant, all from
  2022, no visible closed/archived challenges despite a "Deadline completed (0)"
  counter implying the mechanism exists but is empty here.
- **Volume — fail** for the same reason.
- **Geography — fail.** Qatar-focused tenant; does not fit either existing stratum.

**Verdict: rejected, same grounds as #101c's InnoGet finding.** The date-evidence
absence is a property of the InnoGet platform template, not a single-tenant quirk —
this generalizes #101c's conclusion rather than reopening it. Other InnoGet-hosted
tenants are not expected to differ and are not worth individually re-checking on this
basis alone.

### 3.3 ACCIÓ Radar (Catalonia's trade/innovation agency curated bulletin)

- **Construct fit — partial.** A curated newsletter mixing technology demands,
  procurement opportunities, funding calls, and generic business-partnership
  listings; only a subset of each issue's items are construct-eligible technology
  demands (roughly 3–4 of ~8+ items per issue sampled).
- **Identity field — partial.** Some items name the requesting organization explicitly
  (`BASF`, `ASFINAG`, `Fluidra Ventures` on the one issue sampled); others describe the
  requester only by sector/country ("Polish educational firm"), with no name at all —
  not a uniform field, a per-item editorial choice.
- **Date — unconfirmed, real ambiguity.** Each issue carries its own stable
  publication date (e.g. "Núm. 042, Dijous, 18 de juliol del 2024"), but individual
  items show only a response deadline, and it is not yet verified whether an item is
  new to its issue (making the issue date a valid proxy for first publication) or
  carried over from an earlier issue (which would make the issue date wrong).
- **Historical depth / volume — unconfirmed**, and likely to disqualify on its own:
  at an observed rate of roughly 3–4 usable items per weekly-ish issue, reaching a
  raw pool even in the low hundreds requires many dozens of issues, before any
  eligibility filtering.
- **A structural risk distinct from the other two candidates: likely non-independence
  from EEN/POD.** ACCIÓ curates opportunities from upstream networks (plausibly
  including EEN itself, given the overlap in company profile and phrasing) rather than
  hosting primary listings. If items overlap with EEN/POD postings, acquiring both
  sources would not add independent population — it would double-count the same
  requesters under two source labels. Not yet checked, but a real risk this candidate
  carries that TED does not.

**Verdict: not a live lead as-is.** Fails or leaves unconfirmed too many criteria,
including one (source non-independence from EEN/POD) that would need resolving before
any of the others matter. Noted for completeness, not pursued further here.

## 4. What this ADR does not do

- **Does not qualify any source.** No candidate here has cleared every criterion in §2;
  TED is the only live lead, and only provisionally.
- **Does not authorize acquisition code, a harvester, a mapper, or a policy version**
  for any candidate.
- **Does not relax ADR 0029 §3.1.** The identity-field criterion in §2 is exactly that
  rule, applied prospectively to new candidates instead of retrospectively to EEN/POD.
- **Does not decide the ADR 0029 / $N \ge 60$ discussion §7 of the calling context
  reserves for a "no qualified source" outcome.** That discussion has not been opened;
  a live lead (TED) still exists.

## 5. Next step, not taken here

A dedicated spike on TED's Pre-Commercial Procurement / Innovation Partnership notice
population specifically (not general procurement) — sizing the construct-eligible
volume, sampling notices for `has_articulated_technical_problem`-style fit, and
checking for public-buyer concentration — following #101c's browser-spike precedent,
before any decision to acquire from it.
