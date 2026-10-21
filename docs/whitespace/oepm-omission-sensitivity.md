# Descriptive sensitivity of the base-rate counts to perturbations of the corpus (ADR 0036, O5.2)

**Status:** Result of `scripts/report_oepm_omission_sensitivity.py` for the scenarios fixed in [ADR 0036, §8.10](../adr/0036-technology-white-space-scientific-scope.md) before any result was seen. Exploratory; it describes how counts move under perturbations of the **observed** corpus. It does not measure the effect of the omitted publications.
**Date:** 2026-10-21
**Checks:** [corpus exposure](oepm-corpus-exposure.md) · [base-rate reproduction](oepm-biblio-lag-base-rates-reproduction.md)
**Scope:** Active subclasses (at least 20 documents), candidate pairs, positives and positive rate at the development origins 2003 and 2006, horizon 3. **No detector, no baseline, no metric.**

Reproduction: `python scripts/report_oepm_omission_sensitivity.py ES_Authority_File_20260930.zip --corpus-dir data/raw/oepm_open` (about 11 minutes). Results: [`oepm-omission-sensitivity-results.json`](oepm-omission-sensitivity-results.json). 247,659 records published up to 2009 are in scope. The unit tests fix the scenario definitions and the reproducibility of the seeds.

---

## 1. Fixed rules (unchanged in every scenario)

Activity rule of the decision O4 (documents counted by identifier, with the union of the subclasses of their earliest date); pairs formed from single source records; threshold 20 documents; horizon 3 years; the base-rate definitions of the [characterization](oepm-biblio-corpus-characterization.md) §7. Only the intervention of each scenario differs.

## 2. S-A, the observed corpus

| Origin | Active subclasses | Candidate pairs | Positives | Positive rate |
|---|---|---|---|---|
| 2003 | 524 | 120,151 | 6,713 | 5.59 % |
| 2006 | 565 | 134,747 | 4,532 | 3.36 % |

The 2006 positives reproduce the 4,532 printed in the characterization (§7.1). The origin 2003 had not been computed before.

## 3. S-B1, one history year removed at a time

By construction this changes which pairs are unseen: a pair seen only in the removed year becomes a candidate. The change in positives is therefore split into the positives whose pair was seen only in that year and the rest. It describes a change of the problem, **not** a coverage loss.

**Origin 2006** (S-A: 4,532 positives, 134,747 candidates)

| Year removed | Active | Candidates | Positives | Seen only in that year | Rest |
|---|---|---|---|---|---|
| 2000 | 559 | 132,788 | 4,821 | 301 | −12 |
| 2001 | 556 | 130,757 | 4,713 | 204 | −23 |
| 2002 | 557 | 131,575 | 4,803 | 296 | −25 |
| 2003 | 559 | 132,999 | 4,897 | 383 | −18 |
| 2004 | 557 | 132,280 | 5,046 | 539 | −25 |
| 2005 | 558 | 133,037 | 5,207 | 700 | −25 |
| 2006 | 561 | 134,041 | 5,086 | 560 | −6 |

**Origin 2003** (S-A: 6,713 positives, 120,151 candidates)

| Year removed | Active | Candidates | Positives | Seen only in that year | Rest |
|---|---|---|---|---|---|
| 2000 | 493 | 106,910 | 7,246 | 846 | −313 |
| 2001 | 499 | 109,176 | 7,049 | 587 | −251 |
| 2002 | 501 | 110,654 | 7,338 | 859 | −234 |
| 2003 | 490 | 106,189 | 7,710 | 1,365 | −368 |

Removing one year raises the positives by 4 % to 15 % (181 to 675 at 2006; 336 to 997 at 2003). Almost all of it is pairs seen only in the removed year; the negative remainder comes from subclasses that fall below the activity threshold. The effect is larger at 2003, whose history is four years.

## 4. S-B2, history shortened to the last three years

| Origin | Active | Candidates | Positives | Positive rate |
|---|---|---|---|---|
| 2003 (years 2001–2003) | 493 | 106,910 | 7,246 | 6.78 % |
| 2006 (years 2004–2006) | 522 | 118,270 | 6,005 | 5.08 % |

At 2006 the positive rate rises from 3.36 % to 5.08 % (+32 % positives) when three years of history are dropped. The 2003 row coincides with removing 2000 in S-B1 because the three-year window of 2003 is exactly the history without 2000.

## 5. S-C, deletion at the known absence rate (200 replications, seeds 1–200)

| Origin | Positives, mean | 2.5th–97.5th percentile | Candidates, mean | Percentiles |
|---|---|---|---|---|
| 2003 | 6,708 | 6,698–6,716 | 120,110 | 119,645–120,165 |
| 2006 | 4,524 | 4,510–4,534 | 134,734 | 134,207–134,769 |

The spread is below 0.5 % of the positives. It is that small because the kinds that are present are almost complete in 2000–2009 (0 to 0.41 % absent), so the simulated loss is tiny.

## 6. How to read it

* The counts move much more with the **length and composition of the history** (S-B, 4 % to 32 %) than with random loss at the known rates of the present kinds (S-C, below 0.5 %). The history of the development origins is short (four and seven years) and that, not random loss, is what the counts are sensitive to.
* S-C **says nothing about the kind-`Y` omission**: no kind-`Y` publication of 2000–2009 is observed, so there is nothing to delete or to resemble. The effect of that omission on the pairs seen at the development origins stays **not identifiable** with these data ([exposure](oepm-corpus-exposure.md)).
* S-B1 and S-B2 change the definition of the problem as well as the coverage; their differences are not an estimate of what coverage loss would do.
* Nothing here changes the corpus, the pool or any decision of the ADR. The sensitivity of the baselines' metrics (O5.3) is run after the baselines exist.
