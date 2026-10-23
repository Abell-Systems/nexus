# Gap review: the descriptive white-space MVP against its contracts

**Date:** 2026-10-23
**Checks:** [vertical 1 contract](product-vertical-1-contract.md) · [vertical 2 contract](product-vertical-2-contract.md) · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) · [architecture audit](architecture-audit.md)
**Scope:** What is built, what is verified, what is missing, and which missing work is product and which is research. **No code was changed.** The product shows what the study has measured; showing results is not validating the method.

## 1. What was run for this review (2026-10-23, `main` at the merge of #166)

| Check | Result |
|---|---|
| `tsc --noEmit`, `oxlint` (frontend) | pass |
| `vitest run` (frontend) | 62 passed, 1 skipped (`matchesJourney.integration`) |
| Playwright `whiteSpaceHome.spec.ts` (5 journeys, local server) | 5 passed |
| Backend tests selected by `-k "whitespace or section_density or subclass_pairs or base_rates or biblio"` | 105 passed |
| CI of the merged PRs | green at each merge |

Not run: a human visual review at desktop and phone width; the other e2e file (`matchesJourney.spec.ts`).

## 2. Vertical 1 (front page) against its contract

| Contract item | State | Evidence |
|---|---|---|
| Six parts in order: overview, coverage, section map, what moves the counts, traceability, status | **Built** (plus the explorer of vertical 2 between the map and the sensitivity) | `WhiteSpacePage.tsx`, `components/WhiteSpace/*` |
| One colour scale for both maps | Built and tested | `shouldDrawBothMapsOnOneColourScale…` |
| Mandatory texts: attribution, "an absence is not an opportunity", the unavailable status | Built and tested | `TEXT` in `domain/whitespace.ts`, `shouldStateTheAttribution…` |
| Forbidden formulations absent | Tested | `shouldNeverUseFormulationsThat…` |
| Data copies identical to the versioned results; hashes recorded | Tested | `whitespaceData.test.ts` |
| Traceability panel: result, SHA-256, corpus identity, Authority File, pull request | Built and tested | `TraceabilitySection.tsx` |
| Landmarks, one main heading, anchors, text alternatives, data table for the chart | Tested | `WhiteSpacePage.test.tsx` |
| Phone width without horizontal scroll | Tested in Playwright | `shouldKeepAnchors…Phone` |
| Matcher stays reachable at its own address | Tested in Playwright | `shouldKeepTheMatcherReachable…` |
| Visual review at desktop and phone width | **Not evidenced** (no record of a human review) | |
| Source attribution with the date of the last update (the OEPM reuse conditions ask to state it when the document gives it; see gate 5) | **Gap**: the page shows the attribution and the no-sponsorship line; a search of the page texts found no update or download date. The download date of the corpus is 2026-10-20 (characterization, section 1) | |

## 3. Vertical 2 (subclass explorer) against its contract

| Contract item | State | Evidence |
|---|---|---|
| Origin 2006 or 2022, default 2022; search by symbol; summary; table of every other active subclass with pair seen, documents with both, first year | **Built** | `SubclassExplorerSection.tsx`, `subclassExplorer.ts` |
| Filters (seen / not seen / all) and section filter; sort by symbol, documents, documents with both; **no sort by a derived measure** | Built and tested | `shouldFilterBy…`, `shouldFilterUnseen…` |
| Unseen pair described as "no observada en este corpus y periodo"; never zero or a year; the absence sentence shown | Tested | `shouldShowNoObservadaNeverZeroOrAYear…` |
| Pair detail with counts by year | Tested | `shouldOpenAPairWith…` |
| Limits of the corpus beside the origin selector | Tested | `shouldLoadTheStaticFileOnDemandAndStateTheLimits…` |
| Result not bundled; loaded on demand (the file is 6.2 MB) | Built and tested; the contract left this open until the size was known | `shouldServeThePairsResult…` |
| Keyboard operation, focus on the pair detail, phone width | Tested | unit tests and e2e |
| Invariants of the versioned result against the section density (565 / 612 active, 24,583 / 40,585 observed, 159,330 / 186,966 universe) | Tested in the backend | `scripts/report_oepm_subclass_pairs.py`, `check_against_density` |
| IPC titles | **Not shown, by design**; a titled version needs a versioned, cited source added in its own change | contract section 3 |
| Origins other than 2006 and 2022 | **Not available**, by design (the study has versioned counts only for these two) | |

## 4. What does not exist, and is research, not product

ADR 0036 is *Accepted* as a **framework**; the study is **not ready to run** (its section 12.4).

| Open item | Where | Consequence |
|---|---|---|
| O2: smallest AUC-PR difference regarded as useful, and the power analysis that depends on it | ADR 0036 §10, §12.3 | Needed before the confirmatory origins are evaluated |
| O3: recovery of the 86 records with undefined entities (needs the official DTD) | ADR 0036 §12.3 | They stay rejected |
| Two viability conditions of §8.11 not yet confirmed | ADR 0036 §12.4 | The pre-registration is not closed |
| P7: consultation with the OEPM (2010 gap, 2023 drop, repeated identifiers, access, reuse conditions) | ADR 0036 §10.2 | The message is drafted and reviewed, **not sent** |
| Pre-registration closed with a freeze record (A7) | ADR 0036 §8.11 | No confirmatory origin may be evaluated before it |
| Detector: null model, baselines, ranking of unseen pairs; temporal evaluation; expert review | ADR 0036 §8, C2 | **Nothing is implemented, by rule (C2).** No predictive claim, ranking or "white-space" list can be shown |

## 5. Gaps that are product or infrastructure

1. **Deployment of the page is not evidenced in the repository.** `docs/deploy.md` covers the matcher container; the `deploy-nexus-status` workflow builds a different SPA (`nexus-status/frontend`). Where and for whom the white-space page is served, and under which access control, is **not verified here**.
2. **OEPM reuse conditions in the product:** the update-date gap of section 2 above; also whether the "no desnaturalizar" condition is met is not assessed (gate 5 §3 leaves it open).
3. **The corpus is not in git, by rule** (account-protected download). A fresh clone cannot regenerate the results; it can verify the versioned ones against the hashes. This is a stated property, not a defect, but a reviewer must be told.
4. **Shared infrastructure.** ADR 0036 P8 requires the retrieval corpus of the matcher and the bibliographic corpus of the study to stay separate and reconciled before any shared infrastructure. ADR 0037 (Proposed) puts both corpora in one database technology with separate schemas (`operational_v1`, `biblio_v1`). They are compatible only if "separate schemas, separate manifests" counts as separate; **that reading needs an explicit decision** before ADR 0037 is accepted. #112 and #113 are still open.
5. **The explorer ships a 6.2 MB static file** loaded on demand. Acceptable at this size; revisit if more origins are added.

## 6. Tasks, ordered (product separate from research)

Product (small, independent):
1. State the corpus download date (2026-10-20) and the OEPM attribution conditions on the page and in the traceability panel, with a test.
2. Record a human visual review at desktop and phone width.
3. Verify and document where the page is deployed and who can reach it.

Research (each needs a decision first):
4. Send, or decide not to send, the OEPM consultation (P7).
5. Decide O2 (the smallest useful difference): it is a decision of value for the users of a ranking, not a technical one.
6. Close the pre-registration and the freeze record (A7); only then implement baselines and the null model, in that order, with tests of contract.
7. Evaluate on the development origins; then the confirmatory origins once, with negative results reported.
8. Expert review of candidates and matched controls, as the protocol defines it.

Governance:
9. Decide the P8 reading against ADR 0037 before accepting it.

No calendar is given: none of these has been measured, and 4 to 8 depend on decisions and on reviewer availability.

## 7. Not verified

* Whether the deployed environment, if any, serves the current build.
* The contents of the 26 corpus files (this review used the versioned results, not the corpus).
* The backend tests outside the selection above.
* Any claim of ADR 0036 beyond its status and open items.
