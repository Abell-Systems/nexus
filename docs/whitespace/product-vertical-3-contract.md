# Third product vertical: exploratory unobserved pairs (contract, draft)

**Status:** Draft contract, to be reviewed before any code is written. Nothing is implemented by this document. Every acceptance scenario below is **new and proposed**; none comes from an earlier decision.
**Date:** 2026-10-26
**Checks:** [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) (E1–E8; status Proposed, merged in #176) · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (§5.4, §9, C3) · [vertical 1 contract](product-vertical-1-contract.md) · [vertical 2 contract](product-vertical-2-contract.md)
**Scope:** A view in which the user explores pairs of IPC subclasses **not observed together** in the OEPM corpus up to 2025, with the expected count under independence beside each. **Exploratory and not validated: no prediction, no probability, no score, no recommendation.** It does not change the explorer of vertical 2, which stays descriptive.

## 1. Relation to the ADR

ADR 0038 allows this view under rules E1–E8. This contract turns those rules into requirements that can be checked. Where the ADR leaves a reading open, the contract says so in §9 instead of deciding it silently. ADR 0038 is not yet *Accepted*: no code is written until it is, and until this contract is approved.

## 2. What the user can do

1. Open the view from an anchor of the front page (no router, no new dependency). The corpus period is fixed: documents up to 2025, with the 2010 gap stated.
2. Read the notice of §4 before the list.
3. Search a subclass by symbol, or open the list of all unobserved pairs.
4. Filter: section; **type A** (every unobserved pair of two active subclasses) or **type A with expected count ≥ 1** (ADR 0036 type B, *e*_min = 1, fixed).
5. Sort. Default **alphabetical by symbol of the first, then the second subclass**. The user may choose to sort by expected count (descending), by documents of either subclass, or by symbol. The first choice of the expected-count sort shows the notice of §4.
6. Open a pair: the evidence of §5.

The user cannot: change *m*_min or *e*_min, mark pairs as good or bad, export a ranked list, or share a link that carries a sort by expected count as if it were a result (the link keeps the default order).

## 3. Rules

* **Universe.** Active subclasses at 2025 (≥ 20 publication identifiers, O4) and the pairs among them. The pair is *not observed* if no single source record published up to 2025 carries both.
* **Expected count.** Exactly the quantity and formula of ADR 0038 E3, computed offline and read as data. The browser filters and sorts; it computes no metric. Years not observed (2010) are skipped, never zero. Shown with one decimal; the unrounded value stays in the data.
* **Names (Spanish).** Pair type A: «par no observado en este corpus y periodo». Type A with expected ≥ 1: «par no observado con esperado ≥ 1 bajo independencia». Column: «Esperado bajo independencia (coincidencias)». These are the only labels. No other quality or relevance label exists.
* **Fixed values.** *m*_min = 20 and *e*_min = 1 appear in the notice of §4 as fixed by design, not as tuned.
* **Limits beside the list, not on another page:** kind `Y` absent in 2000–2009, the 2010 gap, the 2023 drop of EP translations, and the remaining limits of C3. Whether 2025 is complete is checked at implementation and stated (§9).
* **Rights.** Source attribution and the download date as in vertical 1. The view is served only inside the tailnet.
* Only symbols are shown; no IPC titles (as in vertical 2).
* Language: Spanish.

## 4. Mandatory texts

* **Notice above every list (E6):** «Exploratorio. Sin validar. Ningún orden mostrado aquí es una predicción.» Followed by one sentence that the study has not shown that any ordering predicts anything, with a link to ADR 0036.
* **Notice at the first expected-count sort:** «Orden por esperado bajo independencia: refleja cuántas coincidencias se esperarían si las dos subclases fueran independientes; no mide probabilidad de aparición ni interés.»
* **Absence sentence of vertical 1** wherever unobserved pairs are listed.
* **Study status line** of vertical 1 stays on the page; if the study has a negative or unresolved result, it is shown here too (E7).

### Forbidden formulations (tested negatively)

None of these, nor their translations or obvious variants, may appear in the page text, in labels, or in accessible names: *oportunidad, hueco prometedor, potencial, atractivo, recomendado, mejor, top, ranking, puntuación, probabilidad, p-valor, significativo, white space* (as a result label), *innovación* as an outcome, any currency or market word. Also forbidden: a numeric rank column, a position badge, a colour scale that encodes the expected count as better or worse, and any element that shows only the first *N* sorted pairs as a headline.

## 5. Evidence of a pair (E5)

Opening a pair shows: both symbols; documents per subclass up to 2025 and by publication year; documents with both (0 by definition); the expected count and its terms (the per-year contributions); the corpus identity, the SHA-256 of the result and the configuration identifier; the limits of §3; and the activity evidence of each subclass. The reading of «documents that make each subclass active» is proposed in §9.

## 6. Data

* A new versioned result produced offline by a script from the corpus, in its own module, reusing the unit rules of the study (O4) but **not importing study detector or baseline code and not named F1, null model or baseline**.
* Per active subclass: documents by year (observed years only) and the identifiers evidence of §9. Per unobserved pair: the expected count. Corpus identity hashes and the Authority File hash are recorded, like the other results.
* Size is measured at implementation and stated. The result is loaded on demand as a static file (as the 6.2 MB pairs file), without an endpoint, unless the measurement says otherwise.
* The corpus stays out of git; only the derived result is versioned.
* Invariants tested: the number of active subclasses and the observed pairs agree with the section-density and subclass-pairs results at the years they share; unobserved + observed = pairs among active; every listed pair is absent from the observed set; the formula on a small hand-computed fixture, with a year missing (it must not count as zero) and with a subclass that has no documents in a year.

## 7. Firewall with the study (E7), as requirements

* No file of this vertical imports from, or is imported by, study code; a test fails if a study module path appears in its imports.
* No script or test of this vertical computes precision, AUC-PR, hit rate or any quality of the ordering on any study origin or on outcomes after 2025.
* The access list of the staging view is recorded before anyone is shown the pairs: for each person, whether they may take part in the human review of ADR 0036 §8.11. Anyone who may score does not receive access until the decision is written down.

## 8. Acceptance

**Automated** (necessary, not sufficient): typecheck, lint, build, unit tests of search, filter, sort, the formula and the invariants; the negative tests of the forbidden formulations over the rendered page, the accessible names and the data labels; keyboard operation; phone width without horizontal scroll; Playwright journey (open the view, see the notice, search a subclass, filter type A with expected ≥ 1, sort by expected count and see the second notice, open a pair); the diff adds no endpoint and no dependency and changes no figure of the study. The documentation gate passes.

**Manual scenarios (proposed, new; to be run and recorded explicitly, they are not satisfied by the automated tests):**

| Id | Scenario | Pass when |
|---|---|---|
| M1 | A person who has not read the ADR opens the view and is asked what the order means | They say it is alphabetical or chosen by them and not a recommendation; no one calls it a ranking of opportunities |
| M2 | Change the sort to the expected count | The notice appears; nothing on screen labels any pair as better; the URL/link keeps the default order |
| M3 | Read every text and label on the view against the forbidden list, by a person | No forbidden formulation, in any state |
| M4 | Open a pair and follow the evidence to the corpus identity | Hashes and terms are visible; the evidence is enough to recompute the expected count by hand for one pair |
| M5 | Empty states: a filter with no results, a subclass with no unobserved pairs | The text says what was filtered; it does not read as a finding |
| M6 | Desktop and phone width, keyboard only | Everything reachable; the notices are not hidden behind a fold |
| M7 | The access-list record exists before the first outside viewer | The record names the panel decision for each person |

Each scenario is run by a named person, with date, build identifier and result (pass/fail with notes), in a record committed with the change that exposes the view. A failed scenario blocks exposure.

## 9. Open points for the review

1. **Activity evidence (E5).** ADR 0038 asks for «the documents (identifiers and dates) that make each subclass active». Proposed reading: the 20 earliest publication identifiers with their dates, which show the activity threshold is met, plus the total count. The alternative, the full list, is large for a subclass with thousands of documents. The reviewer decides.
2. **Completeness of 2025.** Whether the corpus is complete for 2025 is not established by this document; it is measured at implementation. If it is not, the view states it, and the reference year is reconsidered by an ADR change.
3. **Global list size.** The number of unobserved pairs at 2025 is large (the order of 10^5). Whether the list is shown paginated or only after choosing a subclass or a section is decided in review; the proposal is to require a subclass or a section before the list loads, so that no screen of pairs can be read as a headline.
4. **Terms.** The Spanish labels of §3 are proposals.

## 10. Not in this vertical

Any prediction, probability, composite score or quality indicator of the ordering; any use of outcomes after 2025 or of any study origin; the study's null model; publication beyond the tailnet; the OEPM consultation (P7); and the validation of anything.
