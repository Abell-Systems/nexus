# Phase 2 Demand Corpus Acquisition — Source Feasibility Audit

**Status:** Closed (2026-09-07), **corrected twice (2026-09-07)**. Documents the
empirical search for a real, Spain-origin, `Technology request`-construct demand
corpus, and why acquisition was closed at **N=39** against the pre-registered target
**N=60** (`docs/empirical-study-protocol.md` §3.2, "Frozen Demand Sample Size", left
unmodified). The resulting methodological amendment is recorded separately in
`docs/phase2-sample-size-amendment.md`.

> **Correction history:**
> 1. The original closure of this audit (merged as PR #53) reported **N=48**, counting
>    5 EEN-sourced records that pass origin verification (criterion 3 below) but were
>    never checked against criterion 5 (content completeness) before being counted.
>    Corrected to **N=43** (submitted as PR #54): 41 InnoGet + 0 EEN + 2 Lombardia.
> 2. PR #54's review found that N=43 still asserted all 41 InnoGet records as
>    content-complete without actually running them through the real
>    `InnogetHtmlNormalizer`. Doing so (see "Post-closure correction: InnoGet
>    content-completeness" below) found 1 record with no description at all and 3 more
>    under the protocol's literal 25-word threshold. Corrected to **N=39**: 37 InnoGet +
>    0 EEN + 2 Lombardia.
>
> Each prior figure and its sensitivity artifact is retained unmodified in git history
> (PR #53, PR #54) rather than silently overwritten. The table and total under "Sources
> accepted" reflect the current, twice-corrected figures.

This is a **source feasibility record**, not the frozen corpus itself. No demand record
here is part of a sealed dataset; corpus assembly (annotation, Dev/Test split) is a
separate, later step gated on this decision.

## Predefined acceptance criteria

A candidate source counts toward $N$ only if it satisfies **all** of:

1. **Public, reproducible access** — retrievable over plain HTTP without authentication,
   account creation, or defeating a bot-protection challenge (Incapsula/Cloudflare
   challenge pages were treated as a hard "no", not an obstacle to route around).
2. **Compatible demand construct** — the listing represents a company/organization
   publicly requesting a *technology solution to a defined technical problem*
   (InnoGet's "technology call" construct), not a funding-consortium partner search,
   a grant call, or a business/distribution request.
3. **Origin verifiable via the real ADR 0003 pipeline** — classified by
   `DefaultOriginResolver` (`backend/src/main/application/ingestion/origin_resolver.py`)
   against the unmodified, committed `config/policies/data/jurisdiction_policy.json`.
   No heuristic ever substituted for this resolver in a target-origin count.
4. **Deduplicable** — a persistent identifier (own ID, or an EEN `POD Reference`, e.g.
   `TRES20260408022`) so records appearing in more than one source are counted once.
5. **Content-complete** — the record itself (not just its title) carries a substantive
   technical problem description, minimum 25 words, per the pre-existing Demand
   Inclusion Criteria (`docs/empirical-study-protocol.md` §4.1). **This criterion was
   omitted from the original acceptance check** (see the post-closure correction below)
   and is listed here as now-enforced, not as it was originally applied.

## Sources accepted

| Source | Construct | Discovered | Spain-verified (`is_target_origin=True`) | Content-complete (§4.1, empirically checked) | Counted |
|---|---:|---:|---:|---:|---:|
| InnoGet (`innoget.com/technology-calls`) | Technology call | 412 | 41 | 37 — see correction below (1 has no title/description at all; 3 more have genuine but short, 15–24 word descriptions, under the protocol's 25-word minimum) | 37 |
| EEN Partnering Opportunities Database, "Technology request" facet (`p:4320`) | Technology request | 110 | 5 | 0 — see correction below | 0 |
| Open Innovation Lombardia (`openinnovation.regione.lombardia.it`) — regional EEN mirror, "Technology request" (`collaboration_type_id=2`) | Technology request | 35 | 3 | 2 (verified: both have a substantive `Abstract` paragraph, ~40–65 words) | 2 (1 duplicate: `TRES20260408022`, also present in EEN, already counted here) |
| **Total** | | | | | **39** |

Dedup method: exact match on EEN `POD Reference` (e.g. `TRAT20250331004`,
`TRES20260408022`) where present. Lombardia republishes the identical EEN POD scheme,
confirmed by comparing detail-page `POD Reference` / `ID` fields directly — not
inferred from title similarity.

Of the non-target records at both InnoGet and EEN, the large majority classified as
`UNVERIFIED` (143/412 at InnoGet, 50/110 at EEN) were checked individually: they carry
a concrete, non-ambiguous foreign country (e.g. Israel, Kazakhstan, India, Latvia,
Chile) that is simply absent from the 11-jurisdiction `jurisdiction_policy.json`, not a
hidden reserve of Spanish candidates. The genuinely ambiguous residual (region labels
like "European Union"/"EMEA", or missing country) was checked for LEVEL_2/LEVEL_3
signal (organization identity) and found unrecoverable: InnoGet publishes these listings
as "Anonymous Organization", exposing no `organization_location_raw` or verifiable
organization name. `jurisdiction_policy.json` was **not** modified to chase this —
expanding it would not have added any Spain-origin candidate (no unverified record's
country resembles Spain) and touching a production, hashed policy artifact to serve a
discovery script would itself have been a methodological error.

## Sources evaluated and rejected

| Source | Reason for rejection |
|---|---|
| EEN "Research & Development Request" facet (`p:4355`) | Construct mismatch. Sampled listings are funding-consortium partner searches (e.g. "Industrial partner sought in France or Sweden for Franco-German or Swedish-German call in R&D bilateral [programme]"), not requests for a technology solution. |
| CDTI (`cdti.es`) | Behind an Incapsula bot-challenge (no bypass attempted); independently, CDTI is a public R&D funding/loan agency, not a demand marketplace — construct mismatch even if accessible. |
| Eureka Network (`eurekanetwork.org`) | No public technology-request database; only funding "programmes and calls" — construct mismatch. |
| Open Innovation Puglia (`openinnovation.regione.puglia.it`) | Site live but "Work in Progress" — no navigable listing content. |
| Open Innovation Campania (`openinnovation.regione.campania.it`) | Different underlying platform (own "sfide"/challenge showcase), no EEN POD reference scheme, construct not independently verified. |
| EEN-Hessen (`een-hessen.de`) | Descriptive service page only; not a queryable listing database. |
| SUSCHEM SPAIN (`suschem-spain.innogetcloud.com`) | Same vendor platform as InnoGet (InnogetCloud, construct would have matched), but the listing requires member login — fails the public-access criterion. No account created. |
| Catalonia Open Challenges / ACCIÓ (`openchallenges.accio.gencat.cat` → b2match marketplace) | The actual opportunity marketplace is a b2match event instance; no listing is visible without an account — fails the public-access criterion. No account created. |

Eight additional candidates evaluated beyond InnoGet/EEN/Lombardia; **zero** yielded
usable new records. This is recorded as the observed acquisition ceiling under the
evaluated public sources and the stated acceptance criteria — not a claim about the
total worldwide population of Spanish technology demands, and not, by itself, evidence
of insufficient search effort.

## Post-closure correction: EEN content-completeness (2026-09-07)

While scoping the follow-on corpus-freeze work (intended PR #54), the 5 EEN-sourced
records were re-examined for the Demand Inclusion Criteria required by
`docs/empirical-study-protocol.md` §4.1 ("Contains a substantive technical problem
description (minimum 25 words)") — a check the original feasibility audit never
performed, because it only verified *origin* (criterion 3), not *content completeness*.

Findings, checked directly (plain HTTP fetch, cross-checked with a rendered browser for
two of them):

* All 5 EEN detail pages carry **zero** free-text description — no `<p>` element with
  more than a handful of words in the page body, in either the raw HTML or the fully
  JS-rendered DOM. Only a title (8–18 words, itself below the 25-word threshold and not
  an "expanded technological problem statement" in the protocol's sense), a structured
  metadata block (country, partnership type, validity dates, POD reference), and a
  gated "Express interest" contact-form link are present.
* No PDF attachment or other linked document carrying technical content was found on
  any of the 5 pages.
* One of the 5 (`TRES20260408022`) does have a substantive description — but only via
  the Open Innovation Lombardia mirror (`.../1073/startup-spagnola-...`, confirmed
  ~65-word `Abstract` paragraph), which is the same record already counted under
  Lombardia, not an independent EEN contribution.
* The remaining 4 POD references (`TRES20250709018`, `TRES20260522011`,
  `TRES20250625001`, `TRES20251113019`) were checked against Lombardia's own catalog by
  direct substring search across its fetched pages and found absent. Lombardia's total
  catalog across all profile types is empirically capped at ~389 records — a small
  fraction of EEN's full historical POD universe — so non-presence there is the
  unsurprising, expected outcome, not evidence of a broken search.

**Conclusion:** 0 of the 5 EEN-sourced records independently satisfy the content-
completeness criterion. They are removed from the counted total. Lombardia's 2 records
were independently re-verified to have substantive `Abstract` text and remain counted.

## Post-closure correction: InnoGet content-completeness (2026-09-07)

PR #54, which corrected EEN, still asserted all 41 InnoGet Spain-verified records as
content-complete on the grounds that the platform structurally includes a description
field — a property of the platform, not a verified property of each of the 41
observations. Code review on PR #54 correctly flagged this as unproven. The real,
already-tested production pipeline was run against all 41 to settle it directly:

```text
InnoGetExtractor -> DefaultOriginResolver -> InnogetHtmlNormalizer
(backend/src/main/application/ingestion/{extractors,normalizers}/, origin_resolver.py)
```

fetching each of the 41 live pages and calling `normalize_results()` exactly as the
corpus-freeze step will. Findings:

* **1 record** (`INNOGET-1864`, "seeking-chemical-plastic-waste-recycling") returns
  `disposition=EXCLUDED_MISSING_TEXT` — no title or description extractable at all.
* **`InnogetHtmlNormalizer`'s own completeness check only verifies non-emptiness of
  title/description, not the protocol's literal 25-word minimum** — a real gap between
  `docs/empirical-study-protocol.md` §4.1 and the implemented validator, noted here as
  an open item, not fixed in this correction (fixing the normalizer is a separate,
  narrowly-scoped change with its own test coverage, not bundled into a sample-size
  correction).
* Applying the protocol's literal ≥25-word rule directly to the 40 records the
  normalizer did mark `INCLUDED`: **3 more fail it** — `INNOGET-1701` (24 words),
  `INNOGET-1725` (17 words), `INNOGET-1741` (15 words). All three have genuine,
  on-topic technical text (verified by reading the extracted `description` directly,
  e.g. "*We are looking for sensitive, fast, and non-expensive analytical procedures
  for Brettanomyces identification and quantification in wines.*" — 17 words); they are
  excluded strictly because the pre-registered criterion sets a bright-line word count,
  not because the content is deficient in substance. No exception was made for them.

**Conclusion:** 37 of the 41 InnoGet Spain-verified records independently satisfy the
content-completeness criterion. 4 do not and are removed from the counted total.

**Corrected total: 37 (InnoGet) + 0 (EEN) + 2 (Lombardia) = 39.**

## Decision

Acquisition is closed at **N=39**. No eligibility criterion was relaxed, no observation
was fabricated or imputed, and no incompatible demand construct was mixed in to reach
60 — and, per both corrections above, no record missing a substantive, ≥25-word
description was counted either, InnoGet included. See
`docs/phase2-sample-size-amendment.md` for the resulting methodological amendment
record (kept separate from the frozen pre-registration in
`docs/empirical-study-protocol.md` §3.2) and
`data/experiments/power_analysis_wilcoxon_n39_sensitivity.json` for the power
sensitivity computation at N=39 under the identical, unmodified frozen design.

Raw per-record screening artifacts (id/URL/country_raw/origin_level per candidate,
before dedup) are retained by the author outside this repository for audit purposes and
are summarized, not reproduced verbatim, above.
