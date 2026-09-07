# Phase 2 Demand Corpus Acquisition — Source Feasibility Audit

**Status:** Closed (2026-09-07). Documents the empirical search for a real, Spain-origin,
`Technology request`-construct demand corpus, and why acquisition was closed at
**N=48** against the pre-registered target **N=60**
(`docs/empirical-study-protocol.md` §3.2, "Frozen Demand Sample Size", left unmodified).
The resulting methodological amendment is recorded separately in
`docs/phase2-sample-size-amendment.md`.

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

## Sources accepted

| Source | Construct | Discovered | Spain-verified (`is_target_origin=True`) | New (post-dedup) |
|---|---:|---:|---:|---:|
| InnoGet (`innoget.com/technology-calls`) | Technology call | 412 | 41 | 41 |
| EEN Partnering Opportunities Database, "Technology request" facet (`p:4320`) | Technology request | 110 | 5 | 5 |
| Open Innovation Lombardia (`openinnovation.regione.lombardia.it`) — regional EEN mirror, "Technology request" (`collaboration_type_id=2`) | Technology request | 35 | 3 | 2 (1 duplicate: `TRES20260408022` also present in EEN) |
| **Total** | | | | **48** |

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

## Decision

Acquisition is closed at **N=48**. No eligibility criterion was relaxed, no observation
was fabricated or imputed, and no incompatible demand construct was mixed in to reach
60. See `docs/phase2-sample-size-amendment.md` for the resulting methodological
amendment record (kept separate from the frozen pre-registration in
`docs/empirical-study-protocol.md` §3.2) and
`data/experiments/power_analysis_wilcoxon_n48_sensitivity.json` for the power
sensitivity computation at N=48 under the identical, unmodified frozen design.

Raw per-record screening artifacts (id/URL/country_raw/origin_level per candidate,
before dedup) are retained by the author outside this repository for audit purposes and
are summarized, not reproduced verbatim, above.
