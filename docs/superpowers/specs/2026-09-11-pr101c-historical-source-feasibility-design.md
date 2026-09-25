# PR #101c: Historical Source Acquisition Feasibility Design Specification

**Status:** Closed — Negative Feasibility Finding (see Section 7)
**Date:** 2026-09-11
**Target Milestone:** Milestone #101c
**Binding Architecture:** ADR 0008, ADR 0009, ADR 0025, ADR 0026, ADR 0029, ADR 0030, ADR 0031, ADR 0032
**Predecessor:** Milestone #101b (Closed — Diagnostic Outcome, 10/824 eligible)

---

## 1. Executive Summary & Purpose

Milestone #101b executed the full acquisition pipeline against live sources (InnoGet, EEN/POD via the Open Innovation Lombardia mirror) and closed with a diagnostic finding, not an implementation defect: of 824 raw candidates, only 10 fell inside the `[2020-01-01, 2025-12-31]` temporal window with verifiable `t_demand`. The root cause was identified as a **source-frame failure** — both sources predominantly surface current/live listings, not a historical archive.

**#101c answers one question, and only this question:**

> Which historical, reproducible sources can reconstruct 2020–2025 demands with verifiable `t_demand` and sufficient evidence, such that `corpus_expansion_policy_v1` applies unchanged?

This document reports what was actually verified via direct HTTP requests, Wayback Machine queries, and page inspection — not assumptions. No scraper or harvester code was written. No policy file was modified. No harvest was run.

### Golden Invariant Carried Forward

Per #101b Golden Invariant #3: acquisition/crawl dates, access dates, cache/archive-capture timestamps cannot substitute for `t_demand`. This invariant governs every finding below — an archived page is only useful as a historical source if **the page's own content** carries verifiable original publication evidence, not merely because the archive captured it at some point in the past.

---

## 2. InnoGet — Findings

### 2.1 robots.txt
`https://www.innoget.com/robots.txt` does **not** disallow `/technology-calls` (the path used in #101b). Several adjacent paths (`/technology-requests/`, `/demandas-tecnologicas/`) are disallowed, but our path is clear.

### 2.2 Wayback Machine coverage
Queried the CDX API directly:
```
http://web.archive.org/cdx/search/cdx?url=innoget.com/technology-calls*&from=2020&to=2025&output=json&collapse=urlkey
```
Result: **real coverage exists**. Confirmed snapshots with HTTP 200 and substantial page bodies (18–22 KB) across 2020–2021 for both listing pages and individual technology-call detail pages (e.g. `technology-calls/1033`, captured 2021-09-22, 21,854 bytes). Many other snapshots return 302 (redirect stubs, ~450–600 bytes — not usable).

### 2.3 Does an archived page carry a real publication date?
Fetched a full 2021-09-22 archived detail page (`technology-calls/1033`) and inspected it directly (not the current live template — an actually different, older snapshot). Result: **no publication-date evidence of any kind**. The only date-shaped field present is `Deadline : 2022-06-23` / `Deadline completed`, structurally identical to what #101b found on the current live site. This is not a template regression fixed later — the absence is structural and historical.

**Conclusion: Wayback access does not solve the InnoGet problem.** The page has never (at least not in 2020–2021, nor today) exposed an explicit publication timestamp. Falling back to "date of first Wayback capture" as a proxy for `t_demand` would be exactly the crawl/capture-date substitution Golden Invariant #3 forbids — the capture date reflects when Wayback's crawler happened to visit, not when InnoGet published the listing, and (per the design's own logic) a capture that is close to the true publication date is not distinguishable from one that is not, with no verifiable bound either way.

### 2.4 Feeds / sitemap / API
Probed `sitemap.xml`, `sitemap_index.xml`, `feed`, `rss.xml`, `technology-calls/feed`, `api` — **all return 404**. No alternative structured access point found.

### 2.5 InnoGet verdict
**Not feasible as a historical source**, live or archived. The absence of publication-date evidence is a structural property of the source itself, not an artifact of scraping the current live template. No avenue investigated (archive, feed, API) resolves it.

---

## 3. EEN/POD — Official Portal (een.ec.europa.eu)

This supersedes reliance on the Open Innovation Lombardia mirror used in #101b, which only ever surfaced current/future listings.

### 3.1 robots.txt
`https://een.ec.europa.eu/robots.txt` does **not** disallow `/partnering-opportunities`. Standard Drupal admin/search/user paths are disallowed; the listing path is clear.

### 3.2 POD reference format confirmed at the authoritative source
Fetched `https://een.ec.europa.eu/partnering-opportunities` directly. Confirmed live reference codes in the expected shape (`TOES20260911035`, `BODE20260911029`, etc. — prefix + country + `YYYYMMDD` + sequence), matching exactly the format `_POD_DATE_RE` in `een_pod_mapper.py` already parses. This confirms the POD reference **is** the authoritative `t_demand` evidence at the source of truth, not a Lombardia-mirror-specific artifact.

### 3.3 Search/filter interface
Inspected the search form markup directly (`/partnering-opportunities`, form `action="/partnering-opportunities"`). Confirmed present:
- `node_partnering_opportunities_profile_type[]` — numeric term IDs for all five constructs: Business Offer (4330), Business request (4294), Research & Development Request (4355), Technology offer (4309), **Technology request (4320)**.
- A `dr` (date range) radio control with values `at` (any time, default), `lw`, `lm`, `ly`, and `di` (date interval — implies free "after/before" bounds).
- Keyword search, country/partner-type/development-stage facets.

**Open item:** the `di` (date interval) control's actual min/max query parameters are rendered client-side (a JS datepicker widget) and were not recoverable from static HTML. This needs a browser-based inspection pass (not static `curl`) before #101c implementation can rely on it.

### 3.4 Depth of browsable history — the decisive finding
Tested pagination directly against the live portal (unfiltered default browse, sorted newest-first):
- Pages up to **599** return real listings.
- Page 599 (`Showing results 5990 to 5999`) — oldest reference found: **`BOPL20230421007`** (2023-04-21); all other items on that page are 2024-09.
- Page 600 onward (`Showing results 6000 to 5999`) returns an empty/garbled result — the browsable index **caps at 6000 total items**.
- Applying the `profile_type[]=4320` (Technology request) parameter via direct URL did **not** visibly restrict results (mixed BO/BR/TO/TR references still appeared) — the exact facet query contract was not correctly reverse-engineered from static requests and needs confirmation via browser network inspection.

**This is the critical constraint:** the default browsable index — even on the authoritative portal — reaches back only to approximately **2023-04**, not 2020. The 6000-item cap behaves like a fixed result-window limit (common in Elasticsearch/Solr-backed search with a bounded `from+size`), not a true historical depth limit — meaning a correctly-applied date-interval filter (narrowing the matching set before the window cap is hit) **might** unlock 2020–2022 data that a full unfiltered browse cannot reach. This is a testable, not yet confirmed, hypothesis.

### 3.5 EEN/POD verdict
**Provisionally the more promising lead**, but not yet demonstrated sufficient:
- Confirmed: authoritative, correct POD reference format; construct-type facet exists; ~6,000-item browsable pool (an order of magnitude larger than the Lombardia mirror's few hundred).
- Not yet confirmed: whether the `di` date-interval filter genuinely reaches 2020–2022 (the historical bound needed), or whether the underlying index itself simply doesn't retain listings older than ~2023 regardless of filter — these produce identical symptoms from outside and can only be distinguished by successfully executing a bounded date-interval query.
- The `profile_type` facet's correct query contract also needs confirmation (my direct-URL attempt did not filter as expected).

---

## 4. Scoring Table

| Criterion | InnoGet (live or Wayback) | EEN/POD official portal |
| :--- | :--- | :--- |
| Temporal coverage 2020–2025 | **No** — no publication-date evidence in any era investigated | **Unconfirmed** — default browse reaches only to ~2023-04; date-interval filter untested |
| Stable identifiers | Yes (`INNOGET-{id}` from URL) | Yes (POD reference, authoritative format confirmed) |
| `t_demand` evidence quality | **None** — structural absence, confirmed on 2021 and current snapshots alike | High — POD reference encodes date directly, confirmed at source |
| Text completeness (technical problem + description) | Good on live pages (per #101b mapper) | Good — confirmed "Abstract" content present; same extraction rule from #101b applies |
| Construct labeling | N/A (single construct: Technology call) | Confirmed 5-way facet exists (`profile_type`); exact URL contract TBD |
| Reproducibility | Wayback CDX API is deterministic and third-party-verifiable | Live portal search is deterministic per query, but the exact date-filter contract must be nailed down and documented before it can be called reproducible |
| Public accessibility | robots.txt permits; no auth | robots.txt permits; no auth |
| Operational cost/risk | Low (static Wayback fetches) | Low (static HTTP), pending date-filter confirmation |

---

## 5. Recommendation

**InnoGet: drop as a source**, live or archived. This is a firm conclusion, not a hedge — the absence of publication-date evidence was verified directly on both a current page and a 2021 archived snapshot, with no feed/API/sitemap alternative found. No further InnoGet investigation is warranted under the current contract.

**EEN/POD official portal: pursue, but not yet cleared.** The reference format and construct facet are confirmed authoritative and match the existing #101b mapper's expectations. The single open question that determines feasibility is narrow and testable: **does the `dr=di` date-interval filter (or an equivalent correctly-constructed query) return genuine 2020–2022 listings, or does the underlying index simply not retain data that old?** This requires one focused technical spike — likely browser-based (to observe the JS-issued request when the date-interval widget is used) rather than further static `curl` probing — before any acquisition design or harvester work begins.

**No source currently clears the bar for a full 2020–2025 historical corpus.** This is a #101c-level finding, not a reason to reopen or relax #101b. `corpus_expansion_policy_v1` remains untouched. No harvest should begin until the EEN/POD date-interval question above is resolved one way or the other; if it resolves negative (index doesn't retain pre-2023 data), #101c should also consider whether a partial window (e.g. 2023–2025 only) combined with InnoGet's exclusion changes the achievable `N_power`, and whether that requires renegotiating the temporal window itself at the #101a contract level — a decision explicitly out of scope for this document.

---

## 6. Explicitly Out of Scope for This Document

- Any scraper, harvester, or mapper code.
- Any modification to `corpus_expansion_policy_v1`.
- Running a harvest against either source.
- ~~Resolving the EEN/POD date-interval query contract~~ — resolved in Section 7 below.

---

## 7. Browser Spike Findings (2026-09-11)

Executed with a real browser (Playwright) against `https://een.ec.europa.eu/partnering-opportunities` to resolve the single open question from Section 3: does the hypothesized date-interval filter reach 2020–2022 listings?

### 7.1 Correction: the `dr`/date-interval control is not part of the partnering-opportunities filter

Inspecting the live DOM found **two separate forms** on the page:
1. `form[action="https://een.ec.europa.eu/search"]` (`method=get`) — a **generic sitewide search** box, with the `dr` (date-range: `at`/`lw`/`lm`/`ly`/`di`) radio control and a `clm[min]`/`clm[max]` field that Section 3.3's static inspection found. This form is unrelated to the partnering-opportunities listing.
2. `#oe-list-pages-facets-form` (`method=post`, id confirms an OpenEuropa "List Pages" facets widget) — the **actual** partnering-opportunities filter (Type of profile, Type of partner, Technology keywords, Target countries, etc.). Enumerating all ~1,068 form field names in this form found **no date field of any kind**.

So Section 3.3's premise was a misattribution: the date-interval control belongs to a different, generic search endpoint, not the partnering-opportunities facets. Confirmed by testing the generic search form directly: submitting `dr=di` with explicit bounds returned the validation error *"The submitted value 2020-01-01 in the Last update element is not allowed"* — revealing that even this unrelated control filters by **page last-update/index date, not a publication date**, and a direct keyword query against it (`s=technology+request`) returned **0 results**, confirming it indexes a different, generic content pool, not the structured partnering-opportunities dataset. This avenue is dead on two independent grounds (wrong field semantics per Golden Invariant #3, and wrong content index).

### 7.2 The real facet query contract, and the decisive temporal finding

The facets form actually submits as `?f[0]=p:{profile_type_id}` (not `node_partnering_opportunities_profile_type[]={id}` as Section 3.4 guessed from static HTML — this explains why that earlier direct-URL attempt silently failed to filter). Confirmed working: submitting the form with "Technology request" (id `4320`) selected navigated to `?f%5B0%5D=p%3A4320` and returned exclusively `TR*` references. **Reproduced independently** by re-navigating directly to that URL in a fresh page load (no session/form state carried over) — deterministic and third-party-reproducible.

With the filter *confirmed working*, pagination was walked to the last page for each of the two eligible constructs:

- **Technology request** (`p:4320`): **108 total results**. Last page (page 10, "Showing results 100 to 108") oldest reference: `TRCH20240917026` — **2024-09-17**.
- **R&D request** (`p:4355`): **207 total results**. Last page (page 20, "Showing results 200 to 207") oldest reference: `DRTR20240925006` — **2024-09-25**. (Note: R&D request references use a `DR` prefix on this portal, not the `RD` prefix seen on the Lombardia mirror in #101b — a naming difference to account for if this source is used, not a data-quality issue.)

Both eligible constructs terminate at **~September 2024**, not 2020. This is shallower than even the unfiltered browse's ~2023-04 floor (Section 3.4) — the population of Technology-request/R&D-request listings on this portal simply does not extend back to 2020–2022; it isn't a query/filter-mechanics problem, it's an absence of population. The POD Reference field remained present and correctly formatted on every record inspected across all pages.

### 7.3 Stop condition reached

**FILTER WORKS + NO 2020–2022 RECORDS EXIST.** The construct facet is real, reproducible, and correctly scoped (unlike the false lead in Section 3.3/3.4). But the underlying index — for both constructs that matter to this corpus — genuinely does not retain listings older than ~September 2024. This is not a reproducibility failure and not a query-contract failure; it is a hard population ceiling on the official EEN/POD portal itself.

### 7.4 Updated Recommendation

Section 5's "pursue EEN/POD official portal" is **superseded**: the reachable window is approximately **September 2024 – present**, not 2020–2025. Combined with Section 5's InnoGet conclusion (drop entirely), **no source investigated in #101c can reconstruct the 2020–2025 window**. Per Section 5's own contingency, this pushes the decision to the #101a contract level: either the temporal window must be renegotiated (e.g. a partial window such as 2024–2025) at #101a, or a third source class not yet investigated (outside EEN/POD and InnoGet) must be found. Both are out of scope for this document and require a separate decision, not a #101c or #101b extension.
