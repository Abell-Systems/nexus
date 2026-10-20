# Reproduction of sections 4.2 and 7 of the OEPM bibliographic corpus characterization

**Status:** Result of `scripts/reproduce_oepm_biblio_lag_base_rates.py`. Descriptive and exploratory; no detector, no performance figure.
**Date:** 2026-10-20
**Checks:** [corpus characterization](oepm-biblio-corpus-characterization.md) §4.2, §7, §7.1, §7.2 · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) condition C1
**Scope:** Whether the lag and base-rate figures printed in the characterization can be computed from the repository's adapter, with explicit definitions. **Documentary and analysis code only; the ADR is not changed.**

---

## 1. What was run

* Source: the 26 hashed files of the [first reproduction](oepm-biblio-reproduction.md) through `OepmBiblioSource` (hashes verified before reading): 711,547 records read.
* Code: `application/whitespace/analysis_records.py` (derived values), `publication_lag.py`, `base_rates.py`, `figure_comparison.py`; unit tests in `test_lag_and_base_rates.py`.
* The printed figures are in `config/whitespace/oepm_biblio_lag_base_rates_published.json`, transcribed from the characterization. They are **never an input of the computation**; they are only compared with the result, rounded to the precision they were printed with.
* Reproduced figures, including those that were never printed: [`oepm-biblio-lag-base-rates-results.json`](oepm-biblio-lag-base-rates-results.json). About 2.5 minutes on one process.

```text
python scripts/reproduce_oepm_biblio_lag_base_rates.py --data-dir data/raw/oepm_open [--write-results FILE]
```

Exit code 0: all published figures reproduced; 1: differences listed; 2: source not verified.

## 2. Definitions used

| Term | Definition in the code |
|---|---|
| Filing year `fy` | Year of the earliest **readable** date among all priority dates and the application date. A priority claim whose date is unreadable (3 records) is ignored, so the year comes from the other readable dates; this is a rule of this analysis, not of the source. No record ended without a filing year. |
| Lag | Publication year − `fy`. Groups: EP translations (`T*`) and national (every other kind). Publications from 2012. No lag is negative. |
| Percentiles | Nearest-rank (an observed integer); median is the nearest-rank 50th percentile. Mean rounded to two decimals. |
| Cohort curve | Share of `T*` records with `fy` 2003–2010 (152,847, all publication years) whose lag is ≤ *L*. Completeness of a cohort at the end of 2025 is read at *L* = 2025 − cohort year: an **extrapolation** from older cohorts that assumes a stable lag distribution. |
| Active subclass at origin *t* | At least 20 distinct documents (distinct identifiers) first published in or before *t*, each counted with the subclasses of its earliest publication. The threshold 20 is the characterization's, not a scientific choice (ADR 0036 P2). |
| Seen pair, candidate, positive | As in the characterization §7; computed over **every** record, repeats included. All IPC entries count (P5 primary). |
| Filing diagnostic (§7.1) | For each positive, the earliest `fy` among the records published in *t*+1…*t*+3 that make it a positive. "Filed by the origin": that earliest `fy` ≤ *t*. Not printed, stricter reading: the **latest** `fy` ≤ *t* (every contributing record filed by then). |
| Hidden-year estimate | Pairs, both subclasses active, seen up to *t* only in the hidden year and classified together again in *t*+1…*t*+3. A counterfactual for a year of ordinary volume; it does not recover 2010. |
| Filing-year outcome (§7.2) | National candidates whose earliest `fy` over all their records falls in *t*+1…*t*+3, computed only when *t*+3 ≤ 2022. |

## 3. Result

```text
All published figures reproduced
```

That is every printed figure of §4.2, of the base-rate table (2012–2022), of §7.1 (2006, 2013, 2016, 2019, 2022), of the effect of the gap (2013, 2016, 2019) and of §7.2.

**This agreement was reached after one correction, and it must be read with that in mind (§4).** It shows that the printed definitions admit an implementation that gives the printed numbers, not that the exploratory analysis was independently validated.

## 4. How the agreement was reached

The first run, with my first reading of the definitions, differed in **7 figures**, all at origin 2013 and by one unit (candidate pairs 144,361 against 144,360, positives 2,097 against 2,096, the same pair in the national subcorpus and in the filing diagnostic). Nothing else differed. I investigated instead of accepting or ignoring it:

1. Counting "distinct documents" by (identifier, publication date) instead of by identifier was one wrong reading and was replaced by the literal one (distinct identifier). This alone did not remove the difference.
2. The pair step had dropped records that repeat an identifier and a publication date. **Those repeats are not always identical**: of 3,371 repeated (identifier, date) keys, 19 differ in their IPC subclasses, 29 in the IPC entries, 83 in the applicants, 7 in the title and 1 in the priority dates. One pair is classified together only in one copy. Keeping every record removed the difference.
3. The old exploratory data (the throw-away parser's output) were used only to find which reading was at fault; no figure was altered by hand. The published numbers guided the choice between two readings of an ambiguous definition, which is a limit on independence.

## 5. Results that were not printed

* **Strict reading of §7.1.** Requiring every contributing record to be filed by the origin, positives already filed are 94.7 % (2006), 81.9 % (2013), 87.3 % (2016), 87.9 % (2019), 87.0 % (2022), against 95.9 %, 84.2 %, 89.2 %, 90.1 %, 89.4 % under the printed reading. The conclusion (most positives of the publication axis are filings that predate the origin) holds under both; the "84–90 %" of ADR 0036 §6.2 is the permissive reading.
* **Lag with exact repeats removed.** Mean 6.88 / 1.22, median 6 / 1, 90th percentile 11 / 3: the same to the printed precision.
* **Hidden year, per year**: see the results file. Shares of the positives: 3.7–6.1 % (2013), 2.5–4.5 % (2016), 1.7–3.8 % (2019), consistent with "roughly 2 % to 6 %".
* **Completeness**: 92.7 % (2013 cohort), 77.6 % (2016), 49.0 % (2019), 7.5 % (2022), printed as 93, 78, 49, 8. The 2022 value rounds at the boundary (7.5 → 8) and should be quoted as 7.5 %.

## 6. What this changes for ADR 0036 (no change is made here)

* **P4 wording.** The ADR says that "exact repeats of the analytical unit (same identifier and publication date)" are removed. Same identifier and date do **not** imply identical content (§4.2), so a rule is needed for which copy to keep or whether to take their union. The analysis here uses the union for pairs, which is what the printed figures require.
* **"Distinct document"** in the activity threshold means distinct identifier here. The ADR does not define it; it should.
* **C1.** The figures of §4.2 and §7 and the numbers the ADR cites from them are now computed from the repository. Whether C1 is met, and whether any decision that cites them is reopened, is for the review of this report, not for the script finishing. Nothing in it contradicts A3, A5, A6 or P10 as written; the strict reading of §7.1 lowers the range of A5 from 84–90 % to 82–88 % on the strict side.
* **O1** (baseline B2 at origin 2013) stays open: this work does not touch it.

## 7. Limitations

* One implementation by one author; the comparison with the exploratory parser is not independent (§4).
* The 341 rejected records (86 for undefined entities) are not in any figure; the 17 records with invalid UTF-8 and the 3 with an unreadable priority date are, with the rules above.
* No family identifier: documents are counted as publications of different identifiers.
* The thresholds are exploratory (P2); reproducing a count does not justify its threshold.
