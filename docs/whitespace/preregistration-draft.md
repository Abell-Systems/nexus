# Pre-registration draft: proposals for the open parameters of ADR 0036

**Status:** **Draft for review; nothing here is decided.** Each entry is a proposal with its reason, to be accepted, changed or rejected before the pre-registration is closed. No code, threshold value, null-model implementation or confirmatory evaluation exists, and none is written by this document (ADR 0036, C2).
**Date:** 2026-10-21
**Checks:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) §§5.4, 5.5, 7, 8, 12 (P1, P2, P3, A7, O2)
**Scope:** The parameters that ADR 0036 leaves open, split into what can be fixed now (a design choice that does not depend on any result) and what is chosen on the development origins 2003 and 2006 under a rule that is fixed now. **O2 (the smallest useful AUC-PR difference and the power) depends on a decision of value that is not ours and is not proposed here.**

---

## 1. The principle that orders the proposals

Anything that is a *choice among declared options* **and whose options are comparable on the same evaluation pool** is chosen on the development origins only, by a rule written here before it is applied, and frozen before the confirmatory origins (2013, 2016, 2019, 2022) are evaluated. A parameter whose options change the pool, or only the subset used by one hypothesis, is **not** chosen by AUC-PR: it is fixed here by design, and its other values are sensitivity analyses (§8.6). Anything that is a *design choice* is fixed here, without looking at any result. A proposal never depends on a number computed on a confirmatory origin.

## 2. P1: the family of scores and the null model

| Item | Proposal | Reason |
|---|---|---|
| Score F1 (null-model residual) | The expected number of co-classifications of the pair under the null model of §5.5, computed from documents published up to the origin. A pair never observed is ranked by this expectation, highest first | The only quantity the null model supplies for a pair with zero observations |
| Score F2 (with relatedness) | Defined in full in §2.1: the sum of two ranks over the evaluation pool of the origin, with equal weight and no fitted parameter | A combination without a tuning parameter, so nothing is fitted on the development origins |
| Frozen score | One member of {F1, F2}, chosen on the development origins by the rule of §4 | H1 compares one frozen score with one frozen baseline |
| Null model, reference | Degree-preserving randomisation of the document × subclass incidence within publication-year strata, by the curveball algorithm, **10,000 randomisations per origin** (not 1,000: at an expected count near 1 the Monte Carlo error of 1,000 is about 3 %, too coarse to judge a 5 % criterion), seeds fixed in the freeze record. If the cost is not feasible, the number is reduced only by a recorded deviation that keeps the criterion of the next row evaluable | §5.5 requires degree preservation and year strata; the curveball algorithm preserves both exactly |
| Analytic approximation | Accepted instead of the reference only if, on each development origin, **every** pair whose reference expectation is at least 1 satisfies \|analytic − reference\| ≤ 0.05 × reference + 2 × (Monte Carlo standard error of the reference of that pair). The standard error is the standard deviation of the pair's count over the randomisations divided by the square root of their number. The report gives the maximum violation, if any | Evaluable and reproducible: a real shortfall of the approximation is separated from the variability of the reference, and the 5 % is not relaxed |
| Incidence of a document | The union of the subclasses of its source records at its earliest date (the unit of O4). Sensitivity: the incidence from single source records | Consistent with the activity rule; the known inconsistency of 19 documents is examined by the sensitivity |

### 2.1 Definition of F2 (two independent implementations must give the same ranking)

1. **Pool.** The evaluation pool of the origin (all type A pairs of active subclasses, §8.1). Both ranks are computed over exactly this set.
2. **Components.** F1 is the null-model expected count of the pair; AA is the Adamic–Adar score of the pair on the graph of active subclasses and seen pairs (B4).
3. **Direction.** Both are ranked descending: rank 1 is the highest score.
4. **Ties.** Fractional ranking: a group of tied scores receives the mean of the ranks it occupies. A pair without common neighbours has AA = 0 and shares the last rank with every other such pair; a tie of F1 is treated the same way.
5. **Combination.** F2 = rank(F1) + rank(AA); a lower F2 is better. No weight is fitted or changed.
6. **Order and ties of the final ranking.** Ascending F2; ties are broken by the smaller rank(F1), then by the lexicographic order of the two subclass symbols of the pair (a rule independent of any outcome). The same last rule breaks ties in F1 and in every baseline.
7. **Tie-breaking sensitivity.** On the development origins the AUC-PR is also computed with random tie-breaking (mean of 100 draws with fixed seeds) and reported next to the deterministic one.

**A caution to state with the result.** Under a degree-preserving null the expected count of a pair is close to the product of the two subclass degrees divided by the stratum size, which is what the popularity baseline B1 measures. F1 may therefore add little to B1, and H1b (beyond popularity) may well not be supported. That is an allowed outcome of the study, not a failure of the design.

## 3. P2: thresholds (a proposed change of wording of P2)

The wording of P2 says that the thresholds are chosen on the development origins. For two of them that cannot be done by AUC-PR:

* ***e*_min** defines which pool pairs are of type B, the subset that H2 examines (§5.4, §7). The evaluation pool of H1 is the set of type A pairs (§8.1), so changing *e*_min changes neither the pool nor the ranking of a score and cannot change its AUC-PR: a selection by AUC-PR would pick a value on no evidence, through the tie rule.
* ***m*_min** changes the set of active subclasses, hence the pool, its size and its positive rate; the AUC-PR of different values is computed on different problems and is not comparable.

| Item | Proposal | Reason |
|---|---|---|
| *m*_min, primary | **20**, fixed by design | The middle of the declared options; the value used in the descriptive counts is kept so that the study and the descriptive results refer to the same subclasses. It has no scientific justification of its own, and the draft does not claim one |
| *m*_min, sensitivity | 10 and 50, reported next to the primary result (§8.6) | Shows how far the conclusion depends on the threshold, without choosing on results |
| *e*_min, primary | **1**, fixed by design | The smallest value of the proposed grid {1, 2, 5}, so the subset of type B pairs is the widest of the three; 2 and 5 narrow it as sensitivities. No probabilistic meaning is attached to the value: the distribution of the count under the null model is not estimated here, and the draft does not claim that an absence at an expected count of one is unlikely |
| *e*_min, sensitivity | 2 and 5, reported for H2 next to the primary result (§8.6) | The H2 conclusion is stated only where it survives |
| Horizon | 3 (sensitivity 2 and 5), as in §6.4 | Already declared |

H2 is therefore evaluated at one declared *e*_min with the other two as sensitivities, and no value is selected after seeing results.

## 4. Rule for the one choice made on the development origins

The comparable choices are the frozen-score member (F1 or F2) and the strongest baseline, both evaluated on the **same pool** (*m*_min = 20): the average, over 2003 and 2006, of the AUC-PR on the pool of each origin. The higher average is frozen; a tie is resolved in favour of F1. The strongest baseline is selected by the rule of §8.4. **Caution:** two development origins with histories of four and seven years are a thin basis for a choice, and the omissions of the corpus (C3, O5) fall on them; the report states this with the choice.

## 5. P3: inference and human review

| Item | Proposal | Reason |
|---|---|---|
| Resamples *B* | 2,000 (a multiple of 40, as §8.5 requires) | Gives a stable 2.5 % tail (50 resamples) at an acceptable cost |
| Seeds | Fixed in the freeze record, one per origin | Reproducibility |
| Interval | The percentile interval of §8.5 | Already declared |

### 5.1 Human review

* **Items.** At each of the confirmatory origins **2016 and 2022**, separately: the **40 highest-ranked pairs** of the frozen score (the candidates) and **40 controls**, one per candidate, drawn at random (fixed seed) from the evaluation pool within the same decile of the popularity score B1 as that candidate, excluding the 40 candidates. Controls are drawn without regard to any outcome. If a decile holds fewer eligible pairs than needed, the nearest decile with enough eligible pairs is used, and every such substitution is recorded. 80 items per origin, 160 in all.
* **Panel and assignment.** A panel of at least six domain experts; three independent raters per item. Items are grouped by the IPC section of the pair (the section of its first subclass in alphabetical order), and within each section candidates and controls are distributed over raters in a balanced rotation, so that each rater sees equal numbers of both and a rater's or a section's leniency cannot be mistaken for a difference between candidates and controls.
* **Blinding.** Raters see neither the method, the rank, the score, the origin of the items nor which are controls; the order is random with a fixed seed.
* **Scales.** Two separate ratings from 1 to 5: plausibility of the combination and interest. They are analysed and reported separately.
* **Analysis, within each origin.** For each matched pair (candidate, control), the difference of the mean rating of the three raters; the mean of these differences with a bootstrap percentile interval over matched pairs (*B* = 2,000); the descriptive means of candidates and of controls. The matching is respected; the two origins are reported separately and not combined.
* **Reliability.** Krippendorff's alpha, ordinal variant, computed separately for plausibility and for interest. Items with fewer than two ratings are left out of alpha (all available ratings are used for the means); the number left out is reported. There is no threshold of agreement that decides anything: alpha describes how consistently the panel rates and is never presented as evidence that the ranking works.
* **Use.** None for the ranking, the thresholds or any decision about H1 to H3; the review judges plausibility and interest, not truth, and cannot validate the ranking (§8.7).

## 6. A7: what is frozen, and when

* **Frozen before any confirmatory origin is evaluated:** the member of {F1, F2}, the primary *m*_min and *e*_min (fixed in §3), the strongest baseline (and, for 2013, the strongest of B0, B1, B3, B4, §8.2), *B*, the seeds, the baselines' exact definitions (§7), the commit of the code that produces the results and the SHA-256 of the corpus files and of every versioned result it uses.
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
