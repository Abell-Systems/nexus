# Second product vertical: descriptive subclass explorer (contract)

**Status:** Contract, to be reviewed before any code is written. Nothing is implemented by this document.
**Date:** 2026-10-21
**Checks:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (C2, C3, §9) · [vertical 1 contract](product-vertical-1-contract.md) · [section density](../../backend/src/main/application/whitespace/section_density.py)
**Scope:** An explorer in which the user picks an IPC subclass and sees, for every other active subclass, whether the pair has been seen together in the corpus and with what counts. **Descriptive only: no score, no ranking by merit, no predictive claim.** It is the product's first interactive search; it is not the white-space detector.

## 1. Decision behind it

The user asked for a searchable MVP rather than a report. The options were a descriptive explorer, an exploratory ranking and waiting for the validated detector. The descriptive explorer was chosen: it is usable now and does not relax C2 of the ADR, because no detector, null model, baseline or evaluation is implemented or run. If a ranking is wanted later, it needs its own decision and an ADR change before any code.

## 2. What the user can do

1. Choose an origin (2006 or 2022, the two origins for which the study has versioned counts). Default 2022.
2. Search and choose a subclass by its symbol (e.g. `G06N`) or part of it.
3. See the subclass's summary: documents active up to the origin, section, first year seen.
4. See a table of every other active subclass of the origin with: symbol, documents, **pair seen** (yes / no), **documents with both** up to the origin, **first year seen together**.
5. Filter (seen / not seen / all) and filter by section. Sort by symbol, by documents or by documents with both. **No sort by any derived measure.**
6. Open a pair (the chosen subclass and another) to see the counts behind it by publication year.

## 3. Rules

* An unseen pair is described as «no observada en este corpus y periodo»; it is never called an opportunity, gap, candidate or "promising". The sentence of vertical 1 («Una ausencia observada… no demuestra… una oportunidad tecnológica») is shown wherever unseen pairs are listed.
* Default order of an unseen list is alphabetical by symbol, never by size of the other subclass presented as a ranking. Sorting by documents is user-chosen and labelled with the column name.
* The limits of the corpus (kind `Y` absent in 2000–2009, the 2010 gap, 4 and 7 years of history at the development origins) are shown beside the origin selector, not only on another page.
* A subclass with fewer than 20 documents up to the origin (below *m*_min) is not listed; the page says so. The threshold is the study's, not a tuning of the product.
* Only symbols are shown. No IPC title is shown unless it comes from a versioned, cited source added in its own change.
* No claim of predictive capacity anywhere; the status line of vertical 1 stays on the page.
* The browser filters and sorts what the versioned data states; it computes no metric.
* Source attribution as in vertical 1. Language: Spanish.

## 4. Data

* A new versioned result, `docs/whitespace/oepm-subclass-pairs-results.json`, produced by a script from the corpus with the same unit rules as the study (O4: activity by publication identifier at its earliest date; pairs from single source records). It holds, per origin: the active subclasses with their document counts, and for each seen pair the count up to the origin, the first year seen and the count by year. Unseen pairs are not stored: they are the complement.
* The result carries the corpus identity hashes and the Authority File hash, like the other results. The script reuses `base_rates` and `section_density`; it does not re-implement them. A test requires the totals of the new result to equal those of the section-density result (seen pairs and active subclasses per origin: 134,747 candidate pairs at 2006, 146,381 at 2022 from the active subclasses and seen pairs).
* The file reaches the frontend by `sync_whitespace_frontend_data.py`, with the identity and hash tests of vertical 1. Size is checked at implementation and stated; if the bundle growth is not acceptable, the data is loaded on demand as a static file, still without an endpoint.
* The corpus itself stays out of git; only the derived result is versioned.

## 5. Structure

Same layering as vertical 1: types and fixed texts in `domain`; pure functions (search, filter, sort, pair detail) in `application`; loader in `infrastructure`; components in `components/WhiteSpace`. The explorer is a section of the front page reached by an anchor, or its own anchor-addressed view; no router and no new dependency.

## 6. Acceptance

* Typecheck, lint, build, tests and the documentation gate pass.
* Tests: the result's totals equal the section-density totals; the frontend copy is identical to the original; filters and sorts are correct on a small fixture; unseen pairs are listed with the required sentence; forbidden formulations are absent from the page; keyboard operation of search and table; phone width without horizontal scroll.
* Playwright journey: choose an origin, search a subclass, filter unseen, open a pair.
* The diff adds no endpoint, no score, no ranking and no dependency, and changes no figure of the study.

## 7. Not in this vertical

Any ranking or score of unseen pairs, any use of the development-origin outcomes (what appeared in the following three years) as a quality indicator, and any publication of the page. Those need decisions that are not taken.
