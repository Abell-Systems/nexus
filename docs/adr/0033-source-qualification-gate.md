# ADR 0033: Source Qualification Gate for Phase-2 Demand Corpus Expansion

**Status:** Proposed — spike complete (§6), TED provisionally admissible, formal
admission not yet taken.
**Date:** 2026-09-14
**Scope:** Defines a documentary qualification gate for candidate primary sources under
ADR 0031 §2.2's `ADMISSIBLE_SOURCE_CANDIDATE` process, applies it to the first round of
candidates investigated after #102's closure, and records a targeted spike (§6) on the
one live lead (TED Innovation Partnership notices). Authorizes nothing beyond
recording this evaluation — no source is admitted, no policy is versioned, and no
acquisition code or run happens here.

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

## 5. Next step (executed — see §6)

A dedicated spike on TED's Innovation Partnership notice population specifically (not
general procurement) — sizing the construct-eligible volume, sampling notices for
`has_articulated_technical_problem`-style fit, and checking for public-buyer
concentration — following #101c's browser-spike precedent, before any decision to
acquire from it.

## 6. TED Innovation Partnership Spike Findings (2026-09-14)

Executed with a real browser against `ted.europa.eu`'s advanced search
(`Type of procedure = Innovation partnership`, notice type restricted to `Competition`
— the original call-for-tenders notice, i.e. the actual solicitation, as opposed to
`Result`/`Planning`/`Contract modification` notices which report on or precede one).
No scraper/harvester code was written; searches and notice pages were fetched directly
via a real browser session.

### 6.1 Construct fit — confirmed present, but population is heterogeneous

Sampled two notices directly:

- **`452177-2026` (AENA, S.M.E., S.A., Spain, €66,000,000, 9-year IT-services
  contract):** weak construct fit. Title and description are identical
  ("MODERNIZACIÓN DEL ECOSISTEMA OPERACIONAL AENA") — no substantive technical-problem
  narrative in the notice text itself; the actual technical content, if any, lives in
  attached procurement-document PDFs, outside the notice's own structured text. Reads
  as a large-scale IT modernization competition, not an open technical-problem
  solicitation.
- **`462609-2026` (Suomen metsäkeskus / Finnish Forest Centre, Finland):** strong
  construct fit. The notice's own `Description` field states (translated): *"The aim
  of the procurement is to find an innovation partner with whom to develop a system
  ('Monitoring Tool') for data-based forest biodiversity monitoring... combining
  multi-source data, including AI-assisted approaches..."* — a genuinely articulated
  technical problem (biodiversity-monitoring via multi-source data fusion) seeking an
  external partner to co-develop a novel solution, structurally very close to
  `Technology request`/`R&D request`.

**Conclusion:** the Innovation Partnership procedure type is not construct-uniform —
some notices are large procurement competitions with no substantive problem narrative
in-notice, others are exactly the kind of open technical-problem solicitation this
study's construct requires. This is not disqualifying (EEN/POD's raw population was
never construct-uniform either — that is what the eligibility filter is for), but it
means the realized acceptance rate is unknown until a real sample is run through
`has_articulated_technical_problem`-equivalent criteria, and some notices' technical
content may only exist in attached PDF procurement documents the current pipeline
(HTML-only, per ADR 0032 §3's provider-agnostic core) does not parse.

### 6.2 Identity — pass, structurally mandatory

Every notice carries a mandatory, structured `1.1. Buyer / Official name` field
(`AENA, S.M.E., S.A.`; `Suomen metsäkeskus`) — a legal requirement of the EU
procurement directives, not a discretionary field a poster might omit. This is the
axis EEN/POD failed on (§3.1); TED passes it unconditionally by construction.

### 6.3 Date — pass, with one execution wrinkle to handle later

Every notice carries a mandatory `OJ S <issue>/<year> <dd/mm/yyyy>` publication line,
structurally distinct from the deadline field (`Deadline for receipt of requests to
participate`). **Wrinkle, not a disqualifier:** `452177-2026` is itself a "Change
notice" that says "This notice changes the previous version `435752-2026`" — TED
notices can be amended, and an amendment's own publication date is not the original
solicitation's `t_demand`. A future acquisition design must resolve `t_demand` to the
*first* Competition notice in a procedure's version chain, not whichever version is
harvested — a concrete, solvable requirement, not a structural blocker like InnoGet's
(no date field exists at all) or EEN/POD's (no identity field exists at all).

### 6.4 Historical depth — pass, far exceeds any source investigated so far

671 total `Competition`-type Innovation Partnership notices (all countries, all time)
span **2016–2026** (a full decade — the procedure type was introduced by the 2014 EU
procurement directives), confirmed by paging to the oldest results. This is
categorically deeper than InnoGet (no verifiable depth at all), the Lombardia mirror
(#101b: mostly current/live), or the official EEN/POD portal (#101c/#101d: ~2 years).

### 6.5 Population — 671 raw before eligibility filtering, diverse geography

671 `Competition`-type notices, spanning at least Spain, Finland, Germany, France,
Netherlands, Denmark, UK, Poland, Austria, Czechia, Malta, Italy, Luxembourg,
Belgium (observed across two sampled pages). Whether this clears $N \ge 60$ after
eligibility filtering depends entirely on §6.1's unresolved acceptance-rate question —
plausible given EEN/POD's own filtered rates ran 24–43%, but not confirmed.

### 6.6 Independence / duplication risk — plausible, not resolved

Buyer names are diverse across the two sampled pages (no repeats observed in ~30
notices spanning 10+ countries), a positive sign against gross concentration. Not
resolved: whether the *same* recurring public bodies (a national rail operator, a
water utility, a transport ministry) issue multiple Innovation Partnership notices
across the decade — plausible given many are large infrastructure/utility operators
government bodies tend to be repeat procurers. ADR 0029's existing rule handles this
correctly if it happens (one `INDEPENDENT` representative, the rest
`PSEUDOREPLICATE`) — this is a question of how much of the 671 collapses under that
rule, not a new methodological problem.

### 6.7 Verdict

**TED Innovation Partnership `Competition` notices are provisionally admissible** —
they clear identity and date, the two axes that sank EEN/POD and InnoGet respectively,
and clear historical depth and raw volume by a wide margin. Construct fit is real but
not uniform, and the true post-filter, post-independence yield is unknown until a
real acquisition-and-audit cycle is run, exactly like every other source in this
study (InnoGet, EEN/POD) needed. Two concrete execution requirements are already
known before that cycle begins: (1) resolve `t_demand` to a notice's first version in
an amendment chain, and (2) build eligibility criteria that can reject
generic-procurement notices like `452177-2026` while accepting genuine
technical-problem notices like `462609-2026` — likely the same
`has_articulated_technical_problem`/`min_word_count` criteria already in
`corpus_expansion_policy_v3`, applied to the notice `Description` field, need
verifying against a larger sample first.

**This is a GO to open source qualification formally (a new ADR 0031 §2.2 admission,
`corpus_expansion_policy_v4`, a new harvester/mapper) as the next PR — not taken in
this document.**
