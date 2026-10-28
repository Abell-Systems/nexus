# First article: descriptive and exploratory outline (working draft)

**Status:** Working outline, not an approval and not a result. It fixes the scope of the first publication as decided on 2026-10-28 (descriptive and exploratory; prediction in a later phase with its own protocol). It validates no hypothesis, authorises no exposure of candidates and does not resolve D4, E5 or E7. Nothing here changes code, an ADR or a contract.
**Date:** 2026-10-28
**Builds on:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) · [vertical 3 acceptance status](vertical-3-acceptance-status.md) · [reading notes](state-of-the-art-reading-draft.md) (unverified against the original PDFs)

## 1. Question and scope

> **Q-D.** In the OEPM bibliographic corpus 2000–2025 (2010 absent), which pairs of IPC subclasses are never classified together on one document, and how many co-classifications would be expected for each under an independence model?

It is a question about the corpus, not about technology. ADR 0036 §2 (predicting first co-classification) is **not** part of this article.

Universe: documents published by the OEPM (ADR 0036 §3). The article draws no conclusion about Spanish applicants, world technology, unpublished filings, demand or markets.

## 2. Claims the article may make

1. The corpus, its gaps (2010 missing, publication lag, 72.0 % EP translations) and how they shape the observed set of pairs.
2. A reproducible count: 621 active subclasses (≥ 20 documents in 2025), 192,510 pairs, 149,048 unobserved pairs (`oepm-unobserved-pairs-results.json`).
3. For each unobserved pair, the expected co-classifications under independence within publication years, E = Σ_y n_i(y)·n_j(y)/N(y) (ADR 0038 E3), and the distribution of E across pairs.
4. Sensitivity of those counts to omissions and to the choices in the configuration (`oepm-omission-sensitivity.md`, minimum documents, E_min).

## 3. Claims the article must not make

- That an unobserved pair is novel, an opportunity, patentable, free to operate or valuable.
- That a high E means a pair "should" exist; E is a consequence of the model's assumptions, not a forecast.
- Anything about pairs outside the corpus window or outside OEPM publications.
- Any ranking of candidates for decision-making (ADR 0036, explorer contract: no ranking).

## 4. Proposed structure

| § | Content | Source in repo |
|---|---|---|
| 1 | Introduction: combinatorial view of invention, why describe before predicting | reading notes |
| 2 | Data: OEPM BIBLIO 2000–2025, SHA-256 of each file, the 2010 gap, lag | `oepm-biblio-corpus-characterization.md`, results `corpus.files` |
| 3 | Definitions: active subclass, pair, unobserved, O4 unit, configuration id `456858bd…83bd8` | contract, `configuration` in results |
| 4 | Null model: independence within years; assumptions and where they fail (no co-occurrence structure, size effects, single-code documents) | ADR 0038 E3 |
| 5 | Results: counts, distribution of E, unobserved pairs by section | results JSON |
| 6 | Robustness: omission sensitivity, parameter choices, completeness gate of 2025 | `oepm-omission-sensitivity.md`, `oepm-corpus-exposure.md` |
| 7 | Limits and non-claims (§3 above, verbatim) | ADR 0036 §3, §6 |
| 8 | Reproducibility: code, configuration id, hashes, one command per table | acceptance status §2 |

## 5. Open points before drafting results

| Point | State |
|---|---|
| Comparison with a second null model (e.g. degree-preserving bipartite, as in the literature read) | Undecided; without it the article describes one model only. |
| Unit of analysis (documents vs. families) | Defined as O4 in the contract; the justification must be written down. |
| Citing the literature | Every [S] in the reading notes is "to be checked against the original before citing"; none may be cited as is. |
| OEPM licence for publication of derived counts and any identifier lists | **D4, no responsible person yet.** No identifier lists are generated or published until it is resolved. |
| Whether tables list individual candidate pairs | Tied to E7 (deferred). Default: aggregate tables only. |
| Authorship, venue, Lydia's role | Not decided here. |

## 6. Next steps

1. Review this outline; decide the second null model and the aggregate-only default.
2. Verify the cited papers against the original PDFs.
3. Draft §2–§4 (no results), then §5–§6 from the committed results files.
