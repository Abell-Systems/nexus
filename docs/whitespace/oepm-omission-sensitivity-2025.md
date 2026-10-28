# Descriptive sensitivity of the 2025 unobserved pairs to artificial perturbations of the corpus

**Status:** Result of `scripts/report_oepm_omission_sensitivity_2025.py` (commit `b96e872`; the results file below was produced by exactly that script, with the input hashes recorded in it) under the [protocol](oepm-omission-sensitivity-2025-protocol.md) (with its amendment 1), both committed before the run. Exploratory and descriptive. It does **not** estimate the effect of the real omitted publications and is no evidence of technological opportunity, novelty, patentability or freedom to operate.
**Date:** 2026-10-28
**Results:** [`oepm-omission-sensitivity-2025-results.json`](oepm-omission-sensitivity-2025-results.json). Aggregate only: no pair and no identifier.

## 1. Inputs and reproduction (S-A)

711,888 records read, of which 341 were rejected by the adapter and 711,547 accepted for analysis; 707,985 eligible O4 units (per year in the JSON). All four figures equal the corpus manifest and the script stops if they differ. S-A gives 621 active subclasses, 192,510 pairs and 149,048 unobserved pairs, as required (the stop rule did not trigger); its output was byte-identical to the versioned result (SHA-256 `6a269125…3482f7`).

## 2. S-B1: one publication year removed (25 years; 2010 not eligible)

Removing a year also removes it from the temporal history that E is computed from (stated, not corrected). «New unobservedness» is the share of the pairs observed in S-A, active in both, that are no longer observed. The statistic «share of S-A unobserved pairs that becomes observed» is 0 in every run, as the invariant of amendment 1 requires.

| Year removed | Active | Unobserved | Became unobserved | Share of observed pairs | Spearman E |
|---|---|---|---|---|---|
| 2000 | 620 | 149,060 | 619 | 1.42 % | 0.9998 |
| 2001 | 619 | 148,280 | 418 | 0.96 % | 0.9999 |
| 2002 | 620 | 149,003 | 543 | 1.25 % | 0.9998 |
| 2003 | 619 | 148,576 | 714 | 1.64 % | 0.9999 |
| 2004 | 619 | 148,618 | 764 | 1.76 % | 0.9998 |
| 2005 | 620 | 149,247 | 787 | 1.81 % | 0.9998 |
| 2006 | 620 | 148,958 | 517 | 1.19 % | 0.9999 |
| 2007 | 620 | 149,269 | 820 | 1.89 % | 0.9998 |
| 2008 | 621 | 149,735 | 687 | 1.58 % | 0.9999 |
| 2009 | 620 | 149,007 | 558 | 1.28 % | 0.9999 |
| 2011 | 620 | 148,720 | 260 | 0.60 % | 0.9999 |
| 2012 | 621 | 149,316 | 268 | 0.62 % | 0.9999 |
| 2013 | 621 | 149,304 | 256 | 0.59 % | 0.9999 |
| 2014 | 621 | 149,351 | 303 | 0.70 % | 0.9999 |
| 2015 | 620 | 148,770 | 310 | 0.71 % | 0.9999 |
| 2016 | 619 | 148,197 | 335 | 0.77 % | 0.9999 |
| 2017 | 620 | 149,114 | 665 | 1.53 % | 0.9999 |
| 2018 | 619 | 148,416 | 554 | 1.28 % | 0.9999 |
| 2019 | 618 | 147,864 | 599 | 1.38 % | 0.9999 |
| 2020 | 618 | 147,994 | 729 | 1.68 % | 0.9999 |
| 2021 | 618 | 148,085 | 820 | 1.89 % | 0.9998 |
| 2022 | 619 | 148,567 | 722 | 1.66 % | 0.9999 |
| 2023 | 619 | 148,368 | 517 | 1.19 % | 0.9998 |
| 2024 | 619 | 148,864 | 1,002 | 2.31 % | 0.9992 |
| 2025 | 616 | 146,931 | 868 | 2.00 % | 0.9993 |

Share of observed pairs that become unobserved: 0.59 % to 2.31 % across years. Spearman of E over the pairs unobserved in both: min 0.9992, median 0.9999, max 0.9999.

## 3. S-C: 10 % of the O4 units removed, stratified by year (k_y = ⌊0.10·n_y⌋)

Five draws of one artificial mechanism, not five independent observations of the real world; no interval is computed.

| Seed | Units removed | Active | Unobserved | Became unobserved | Share of observed pairs | Spearman E |
|---|---|---|---|---|---|---|
| 20261101 | 70,789 | 616 | 147,496 | 1,420 | 3.28 % | 0.9999 |
| 20261102 | 70,789 | 618 | 148,629 | 1,364 | 3.14 % | 0.9999 |
| 20261103 | 70,789 | 615 | 146,888 | 1,412 | 3.26 % | 0.9999 |
| 20261104 | 70,789 | 620 | 149,883 | 1,423 | 3.28 % | 0.9998 |
| 20261105 | 70,789 | 617 | 148,043 | 1,379 | 3.18 % | 0.9999 |

Share: 3.14 % to 3.28 %. Spearman: min 0.9998, median 0.9999, max 0.9999. Rerunning the first seed gave identical output.

## 4. S-D: activity threshold

| Threshold | Active | Unobserved | Common active with S-A | Dropped from U_A (subclass inactive) | Entering (new subclasses) | Status changes in the common universe | Spearman E |
|---|---|---|---|---|---|---|---|
| 10 | 636 | 158,293 | 621 | 0 | 9,245 | 0 | 1.0000 |
| 40 | 603 | 138,463 | 603 | 10,585 | 0 | 0 | 1.0000 |

Changing the threshold changes the **population** of pairs (15 subclasses enter at 10; 18 leave at 40) and, within the pairs both configurations contain, neither the observed status nor the order of E: the Spearman is 1.0 because E depends on the subclass counts per year and not on the threshold. It says nothing about which threshold is right.

## 5. Reading

- The set of unobserved pairs is **not** stable under removal. Of the 43,462 pairs observed in S-A, between 0.59 % and 2.31 % (256 to 1,002 pairs) become unobserved when one year is removed, and 3.14 % to 3.28 % (1,364 to 1,423) when 10 % of the units are removed. The counts of unobserved pairs are a property of this corpus as observed, as the outline's non-claims already say.
- **Universe changes with the threshold (S-D).** At thresholds 10, 20 and 40 there are 636, 621 and 603 active subclasses and 158,293, 149,048 and 138,463 unobserved pairs. The Spearman of 1.0 in S-D is computed only on pairs both configurations contain; it does not mean the global result is invariant, because the set of pairs itself changes by about 10,000 either way. It says nothing about which threshold is right.
- **Rank correlation of E is secondary.** It is computed only over the pairs unobserved in both scenarios (Spearman ≥ 0.9992). It does not measure the stability of the full set of unobserved pairs, and it does not show that the absences are robust. That E barely reorders is expected, because E is a function of subclass frequencies per year, which move little.

Descriptive conclusion this report supports: the number of unobserved pairs depends on the observed coverage and on the activity threshold, while the order of E among pairs that stay unobserved in both scenarios barely changes under these perturbations. Nothing here estimates the effect of the real omitted publications or says anything about novelty, opportunity or value.

## 6. Deviations from the protocol

- Amendment 1 (committed before the run) replaced the zero-by-construction statistic of §3 item 2 by «new unobservedness» and kept the former as an invariant (0 in all 32 runs).
- Amendment 2 (labelling only): the first run called 711,547 «source records»; the corpus manifest separates 711,888 read, 341 rejected and 711,547 accepted. The script was corrected and rerun; the scenario numbers did not depend on the label.
- «Entering» pairs of S-D at threshold 10 are not a field of the JSON; they are derived here as `unobserved − common_unobserved_pairs_of_S_A − became_unobserved`.
- S-B1 and S-C Spearman summaries are min, median and max, as fixed; per-year and per-seed values are in the JSON.
