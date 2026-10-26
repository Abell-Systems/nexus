# Third product vertical: exploratory unobserved pairs (contract, draft)

**Status:** Contract approved by the review of #177 (merged 2026-10-26). **The view is not implemented**, and the Spanish terms of §3 and §4 remain proposals until approved. Approval of the contract does not authorise exposing the view or running scenarios M1–M7; the gates of §7, §8 and §9 apply. The acceptance scenarios below are new and proposed; none comes from an earlier decision.
**Date:** 2026-10-26
**Checks:** [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) (E1–E8; Proposed in #176, Accepted by the pull request that follows #177) · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (§5.4, §9, C3) · [vertical 1 contract](product-vertical-1-contract.md) · [vertical 2 contract](product-vertical-2-contract.md)
**Scope:** A view in which the user explores pairs of IPC subclasses **not observed together** in the OEPM corpus up to 2025, with the expected count under independence beside each. **Exploratory and not validated: no prediction, no probability, no score, no recommendation.** It does not change the explorer of vertical 2, which stays descriptive.

## 1. Relation to the ADR

ADR 0038 allows this view under rules E1–E8. This contract turns those rules into requirements that can be checked. Where the ADR leaves a reading open, the contract says so in §9 instead of deciding it silently. ADR 0038 is *Accepted* by the pull request that follows #177. Code is written only as this contract describes it, in small pull requests; exposing the view needs the gates of §7, §8 and §9.

## 2. What the user can do

1. Open the view from an anchor of the front page (no router, no new dependency). The corpus period is fixed: documents up to 2025, with the 2010 gap stated.
2. Read the notice of §4 before the list.
3. Search a subclass by symbol, or choose a section. **No list of pairs loads before one of the two is chosen** (decision of the review, §9.3). The initial state explains how to start: choose a subclass or a section; it shows no pair and no count of pairs presented as a result.
4. Filter: section; **type A** (every unobserved pair of two active subclasses) or **type A with expected count ≥ 1** (ADR 0036 type B, *e*_min = 1, fixed).
5. Sort. Default **alphabetical by symbol of the first, then the second subclass**. The user may choose to sort by expected count (descending), by documents of either subclass, or by symbol. The first choice of the expected-count sort shows the notice of §4.
6. Open a pair: the evidence of §5.

The user cannot: change *m*_min or *e*_min, mark pairs as good or bad, export a ranked list, or share a link that carries a sort by expected count as if it were a result (the link keeps the default order).

## 3. Rules

* **Universe.** Active subclasses at 2025 (≥ 20 publication identifiers, O4) and the pairs among them. The pair is *not observed* if no single source record published up to 2025 carries both.
* **Expected count.** Exactly the quantity and formula of ADR 0038 E3, computed offline and read as data. The browser filters and sorts; it computes no metric. Years not observed (2010) are skipped, never zero. Shown with one decimal; the unrounded value stays in the data.
* **Names (Spanish).** Pair type A: «par no observado en este corpus y periodo». Type A with expected ≥ 1: «par no observado con esperado ≥ 1 bajo independencia». Column: «Esperado bajo independencia (coincidencias)». These are the only labels. No other quality or relevance label exists.
* **Fixed values.** *m*_min = 20 and *e*_min = 1 are stated in the limits block beside every list (the text of §4, «Parameters»), as fixed by design and not tuned to the results.
* **Limits beside the list, not on another page:** kind `Y` absent in 2000–2009, the 2010 gap, the 2023 drop of EP translations, and the remaining limits of C3. Whether 2025 is complete is checked at implementation and stated (§9).
* **Rights.** Source attribution and the download date as in vertical 1. The view is served only inside the tailnet.
* Only symbols are shown; no IPC titles (as in vertical 2).
* Language: Spanish.

## 4. Mandatory texts

* **Notice above every list (E6):** «Exploratorio. Sin validar. Ningún orden mostrado aquí es una predicción.» Followed by one sentence that the study has not shown that any ordering predicts anything, with a link to ADR 0036.
* **Notice at the first expected-count sort:** «Orden por esperado bajo independencia: refleja cuántas coincidencias se esperarían si las dos subclases fueran independientes; no mide probabilidad de aparición ni interés.»
* **Parameters (in the limits block beside every list):** «Parámetros fijados por diseño, no ajustados a los resultados: una subclase es activa con al menos 20 identificadores de publicación; el esperado mínimo para el tipo con esperado ≥ 1 es 1.»
* **Absence sentence of vertical 1** wherever unobserved pairs are listed.
* **Study status line** of vertical 1 stays on the page; if the study has a negative or unresolved result, it is shown here too (E7).

### Forbidden formulations (tested negatively)

None of these, nor their translations or obvious variants, may appear in the page text, in labels, or in accessible names, **except inside the exact sentences of the allowlist below**: *oportunidad, hueco prometedor, potencial, atractivo, recomendado, mejor, top, ranking, puntuación, probabilidad, p-valor, significativo, white space* (as a result label), *innovación* as an outcome, and the closed set of money and market words: *euro, €, dólar, $, precio, mercado, ventas, ingresos, rentabilidad, inversión, negocio, comercial*. **Scope of the checks:** the automated test covers exactly the words listed here, detected as **whole terms** (word boundaries, never arbitrary substrings, so a legitimate word that contains a forbidden sequence by accident is not rejected), case-insensitively and without accents, in singular and plural (the symbols € and $ are matched as characters), over the page text, labels, accessible names and data labels, and the expressions «white space» and «top N» in any case. Synonyms and variants that are not in this list are covered only by the human reading of M3, and the contract does not claim otherwise. **Allowlist (negations that delimit what a quantity is not).** The forbidden words may appear only inside these sentences, verbatim: the notice at the first expected-count sort (it says the quantity does not measure probability), the absence sentence of vertical 1 (it denies an opportunity), and the study status line of vertical 1. The list is closed: a sentence is added only by amending this contract, and each allowlisted sentence must be a negation or a limit, never an affirmation. The negative tests (§8) fail on any occurrence of a forbidden word outside those strings, which are read from the same constants the page renders, so the test and the page cannot drift apart. That each allowlisted sentence is a negation is a human check (scenario M3), because a test cannot read meaning.

Also forbidden: a numeric rank column, a position badge, a colour scale that encodes the expected count as better or worse, and any element that shows only the first *N* sorted pairs as a headline.

## 5. Evidence of a pair (E5)

Opening a pair shows: both symbols; documents per subclass up to 2025 and by publication year; documents with both (0 by definition); the expected count and its terms (the per-year contributions); the corpus identity, the SHA-256 of the result and the configuration identifier; the limits of §3; and the activity evidence of each subclass. The activity evidence of each subclass is the **full list** of its publication identifiers with dates, loaded on demand when the evidence is opened (§9.1); this is the literal reading of ADR 0038 E5.

## 6. Data

* A new versioned result produced offline by a script from the corpus, in its own module, reusing the unit rules of the study (O4) but **not importing study detector or baseline code and not named F1, null model or baseline**.
* Per active subclass: documents by year (observed years only), and a separate static file with all its publication identifiers and dates, fetched only when the user opens the evidence. Per unobserved pair: the expected count. Corpus identity hashes and the Authority File hash are recorded, like the other results.
* Size is measured at implementation and stated. The result is loaded on demand as a static file (as the 6.2 MB pairs file), without an endpoint, unless the measurement says otherwise.
* The corpus stays out of git; only the derived result is versioned.
* Invariants tested: the number of active subclasses and the observed pairs agree with the section-density and subclass-pairs results at the years they share; unobserved + observed = pairs among active; every listed pair is absent from the observed set; the formula on a small hand-computed fixture, with a year missing (it must not count as zero) and with a subclass that has no documents in a year.

## 7. Firewall with the study (E7), as requirements

* No file of this vertical imports from, or is imported by, study code; a test fails if a study module path appears in its imports.
* No script or test of this vertical computes precision, AUC-PR, hit rate or any quality of the ordering on any study origin or on outcomes after 2025.
* The access list of the staging view is recorded before anyone is shown the pairs: for each person, whether they may take part in the human review of ADR 0036 §8.11. Anyone who may score does not receive access until the decision is written down.

## 8. Acceptance

**Automated** (necessary, not sufficient): typecheck, lint, build, unit tests of search, filter, sort, the formula and the invariants; the negative tests of the forbidden formulations over the rendered page, the accessible names and the data labels (with the closed allowlist of §4, and a test that the allowlist equals the mandatory constants); keyboard operation; phone width without horizontal scroll; Playwright journey (open the view, see the notice, search a subclass, filter type A with expected ≥ 1, sort by expected count and see the second notice, open a pair); the diff adds no endpoint and no dependency and changes no figure of the study. The documentation gate passes.

**Manual scenarios (proposed, new; to be run and recorded explicitly, they are not satisfied by the automated tests):**

| Id | Scenario | Pass when |
|---|---|---|
| M1 | A person who has not read the ADR opens the view and is asked what the order means | They say it is alphabetical or chosen by them and not a recommendation; no one calls it a ranking of opportunities |
| M2 | Change the sort to the expected count | The notice appears; nothing on screen labels any pair as better; the URL/link keeps the default order |
| M3 | Read every text and label on the view against the forbidden list, by a person, including each allowlisted sentence | No forbidden formulation outside the allowlist, in any state; each allowlisted sentence denies or limits and does not affirm |
| M4 | Open a pair and follow the evidence to the corpus identity | Hashes and terms are visible; the evidence is enough to recompute the expected count by hand for one pair |
| M5 | Initial state (before choosing a subclass or section) and empty states: a filter with no results, a subclass with no unobserved pairs | The text says what was filtered; it does not read as a finding |
| M6 | Desktop and phone width, keyboard only | Everything reachable; the notices are not hidden behind a fold |
| M7 | The access-list record exists before the first outside viewer | The record names the panel decision for each person |

Each scenario is run by a named person, with date, build identifier and result (pass/fail with notes), in a record committed with the change that exposes the view. A failed scenario blocks exposure.

## 9. Points of the review

Measurements below were made on 2026-10-26 from the local corpus (`BIBLIO_2000…2025`, 711,547 records) and from the versioned exposure result. The first is an approximation by source record, not by the O4 publication identifier, and is to be recomputed at implementation.

1. **Activity evidence (E5). Decided in the review: the full list on demand.** The 20-identifier reading is **withdrawn from the contract**: it was not shown to be equivalent to the ADR, and an interface limit must not relax it. The contract states the literal reading (the full list, on demand). Feasibility, measured: 621 subclasses with at least 20 documents, 1,287,829 subclass-document incidences, about **37 MB** in total as identifier-and-date lists, per subclass a median of about 23 KB, a 95th percentile of about 212 KB and a maximum of about 2.5 MB (`A61K`); loaded one subclass at a time, none of this is on the page's critical path. A shorter list would be an explicit change to E5 by ADR amendment, not a choice of the interface. The final figures are recomputed at implementation under O4.
2. **Completeness of 2025. Criterion and rule on failure adopted; threshold approved as an exposure rule, not as proof of absolute completeness.** The existing exposure result compares the corpus with the OEPM inventory by publication key. At 2025 it records 11 absent of 29,238 inventory keys (EP translations 2 of 23,544, kind `Y` 1 of 1,924, other 8 of 3,770; 0.04 % in total). Criterion, **approved as an operative exposure rule** (not as proof of absolute completeness): before exposure, the exposure result for 2025 must show an absent share of at most **1 % in each kind group**; the figures are quoted in the view's limits. **Rule on failure (decided in the review):** with the measurement available and the criterion met in every group, the view may be exposed, stating that the comparison is against the OEPM inventory. With the criterion not met in any group, or the measurement not available, **exposure of vertical 3 is blocked**: the reason is recorded, the reference year is not changed silently (that is an amendment of ADR 0038), and the view is re-evaluated only after the cause is corrected and the comparison recomputed. A warning on the page never substitutes for this gate. The comparison is against the OEPM's own inventory, not an independent count, and says nothing about records the inventory also lacks.
3. **Size of the global list. Decided in the review: adopted.** The number of unobserved pairs is of the order of 10^5 (measured: 192,510 pairs among 621 active subclasses, 43,462 observed, 149,048 not observed; to be recomputed under O4). The view requires a subclass or a section before any list loads (§2), with the clear initial state above. There is no global list that could read as an editorial selection.
4. **Terms. Proposals, not approved.** The Spanish labels of §3 and the notices of §4 stay proposals until approved, together with the forbidden formulations, because a notice can be technically correct and still read as a recommendation. They are reviewed against the visible texts, the accessible names, the empty states and the expected-count sort notice (scenario M3).

## 10. Not in this vertical

Any prediction, probability, composite score or quality indicator of the ordering; any use of outcomes after 2025 or of any study origin; the study's null model; publication beyond the tailnet; the OEPM consultation (P7); and the validation of anything.
