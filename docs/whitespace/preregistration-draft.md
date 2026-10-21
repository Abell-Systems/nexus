# Pre-registration draft: proposals for the open parameters of ADR 0036

**Status:** **Draft for review; nothing here is decided.** Each entry is a proposal with its reason, to be accepted, changed or rejected before the pre-registration is closed. No code, threshold value, null-model implementation or confirmatory evaluation exists, and none is written by this document (ADR 0036, C2).
**Date:** 2026-10-21
**Checks:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) §§5.4, 5.5, 7, 8, 12 (P1, P2, P3, A7, O2)
**Scope:** The parameters that ADR 0036 leaves open, split into what can be fixed now (a design choice that does not depend on any result) and what is chosen on the development origins 2003 and 2006 under a rule that is fixed now. **O2 (the smallest useful AUC-PR difference and the power) depends on a decision of value that is not ours and is not proposed here.**

---

## 1. The principle that orders the proposals

Anything that is a *choice among declared options* is chosen on the development origins only, by a rule written here before it is applied, and frozen before the confirmatory origins (2013, 2016, 2019, 2022) are evaluated. Anything that is a *design choice* is fixed here, without looking at any result. A proposal never depends on a number computed on a confirmatory origin.

## 2. P1: the family of scores and the null model

| Item | Proposal | Reason |
|---|---|---|
| Score F1 (null-model residual) | The expected number of co-classifications of the pair under the null model of §5.5, computed from documents published up to the origin. A pair never observed is ranked by this expectation, highest first | The only quantity the null model supplies for a pair with zero observations |
| Score F2 (with relatedness) | The sum of the rank of F1 and the rank of the Adamic–Adar score of the pair on the co-classification graph (the baseline B4), with equal weight and no fitted parameter | A combination without a tuning parameter, so nothing is fitted on the development origins |
| Frozen score | One member of {F1, F2}, chosen on the development origins by the rule of §4 | H1 compares one frozen score with one frozen baseline |
| Null model, reference | Degree-preserving randomisation of the document × subclass incidence within publication-year strata, by the curveball algorithm, 1,000 randomisations per origin, seeds fixed in the freeze record | §5.5 requires degree preservation and year strata; the curveball algorithm preserves both exactly |
| Analytic approximation | Used instead of the reference only if, on the development origins, for every pair with an expected count of at least the smallest *e*_min of the grid, the relative difference from the reference is at most 5 % | A pre-declared acceptance criterion for the cost-saving option that P1 requires to be compared |
| Incidence of a document | The union of the subclasses of its source records at its earliest date (the unit of O4). Sensitivity: the incidence from single source records | Consistent with the activity rule; the known inconsistency of 19 documents is examined by the sensitivity |

**A caution to state with the result.** Under a degree-preserving null the expected count of a pair is close to the product of the two subclass degrees divided by the stratum size, which is what the popularity baseline B1 measures. F1 may therefore add little to B1, and H1b (beyond popularity) may well not be supported. That is an allowed outcome of the study, not a failure of the design.

## 3. P2: thresholds

| Item | Proposal | Reason |
|---|---|---|
| *m*_min (documents for a subclass to be active) | {10, 20, 50}, as in P2 | Already declared |
| *e*_min (expected count for type B) | {1, 2, 5} | An expected count of one is the smallest value at which "no co-classification observed" is, under the null, less likely than one observation; the grid then doubles and more than doubles |
| Horizon | 3 (sensitivity 2 and 5), as in §6.4 | Already declared |

## 4. Rule for the choices made on the development origins

For each combination of the frozen-score member (F1 or F2), *m*_min and *e*_min: the AUC-PR of the score on each development origin, averaged over 2003 and 2006. The combination with the highest average is frozen; ties are resolved in favour of the larger *m*_min, then the larger *e*_min, then F1. The strongest baseline is selected by the rule of §8.4. **Caution:** two development origins with histories of four and seven years are a thin basis for a choice, and the omissions of the corpus (C3, O5) fall on them; the report states this with the choice.

## 5. P3: inference and human review

| Item | Proposal | Reason |
|---|---|---|
| Resamples *B* | 2,000 (a multiple of 40, as §8.5 requires) | Gives a stable 2.5 % tail (50 resamples) at a cost that is acceptable |
| Seeds | Fixed in the freeze record, one per origin | Reproducibility |
| Interval | The percentile interval of §8.5 | Already declared |
| Human review: items | At the confirmatory origins 2016 and 2022: the 40 highest-ranked pairs of the frozen score, and 40 control pairs drawn from the pool at random within the popularity decile of each reviewed pair | Controls matched on popularity avoid crediting the review with what popularity explains |
| Human review: reviewers | Three domain experts per item, independent, who see neither the method, nor the rank, nor the score, nor which items are controls; items are assigned by IPC section of the pair | §8.7 requires blinding |
| Human review: scale | Two separate ratings from 1 to 5: plausibility of the combination, and interest | §8.7: plausibility and interest, not truth |
| Human review: reporting | Mean ratings of candidates against controls, and the agreement among reviewers (Krippendorff's alpha) | Shows whether reviewers can tell the two apart and whether they agree |
| Use of the review | None for the ranking, the thresholds or any decision of H1 to H3; it cannot validate the ranking | §8.7 |

## 6. A7: what is frozen, and when

* **Frozen before any confirmatory origin is evaluated:** the member of {F1, F2}, *m*_min, *e*_min, the strongest baseline (and, for 2013, the strongest of B0, B1, B3, B4, §8.2), *B*, the seeds, the baselines' exact definitions (§7), the commit of the code that produces the results and the SHA-256 of the corpus files and of every versioned result it uses.
* **A freeze record** (a versioned document) carries all of the above. A confirmatory origin is evaluated once under that record; any change after the freeze is recorded as a deviation, and the original result is not replaced.

## 7. Exact definitions of the baselines (§8.2 gives the idea; these are the details)

* **B1, popularity:** the product of the document counts of the two subclasses up to the origin (documents counted as in O4).
* **B3, trend:** for each subclass, *g* = (documents in the origin year + 1) / (mean documents of the two previous observed years + 1); the score of a pair is *g*_i × *g*_j. Years without observations (2010) are skipped, not zero.
* **B4, Adamic–Adar:** on the graph whose nodes are the active subclasses and whose edges are the seen pairs, the sum over common neighbours *k* of 1 / ln(degree of *k*); a common neighbour of degree 1 cannot occur.
* **B2 and B0:** as in §8.2.

## 8. What stays open, and why

* **O2:** the smallest useful AUC-PR difference, and the power analysis that depends on it. It needs a decision of value from Abell. A plan for the power analysis can be fixed without the value: estimate the variability of the paired difference by the subclass bootstrap on the development origins, and report the smallest difference detectable at the 2.5 % tail for each candidate value.
* **O3:** the 86 records with undefined entities; it does not condition the design.
* **O5.3:** the sensitivity of the metrics, run after the baselines exist.

## 9. Order of work if these proposals are accepted

1. Accept, change or reject each proposal; amend ADR 0036 (P1–P3, A7) with the decisions.
2. Fix O2 with Abell, and the power plan.
3. Write the freeze-record template and the contract of the first code (baselines B0–B4 and the null model), then tests, then code on the development origins only.
4. Select the frozen configuration by the rule of §4, write the freeze record, and only then evaluate the confirmatory origins.
