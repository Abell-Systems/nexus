# OEPM OpenData bibliographic corpus 2000–2025: characterization

**Status:** Descriptive audit, exploratory. Not a pre-registered analysis.
**Date:** 2026-10-20
**Used by:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md)
**Scope:** What the corpus contains, where it is incomplete, and which descriptive counts were taken from it. **Documentary only.** No ingestion code, adapter or data is added to the repository by this document.

Every number below was computed after the data had been downloaded and inspected. None of it is a hypothesis test, and none of it says anything about whether a detector works.

---

## 1. Provenance

| Item | Value |
|---|---|
| Publisher | Oficina Española de Patentes y Marcas (OEPM), OpenData programme |
| Dataset | "Datos bibliográficos" of the patent and utility-model catalogue |
| Page | `https://sede.oepm.gob.es/eSede/datos/es/catalogo/catalogo-patentes-y-modelos-de-utilidad/bibliograficos/` |
| Access | Requires a registered OEPM account. A direct HTTP request for a file is answered with HTTP 200 and an HTML "no permission" body; the file is delivered only when the download link is clicked in a logged-in browser session (the page records an audit entry on click) |
| Licence | The catalogue states that the data are reusable free of charge under Ley 37/2007 and RD 1495/2011. The conditions of the OEPM legal notice have not been reviewed by counsel |
| Downloaded | 2026-10-20, with `scripts/download_oepm_opendata.py` (not part of this PR) |
| Files | `BIBLIO_2000.zip` … `BIBLIO_2025.zip` (26 files). Earlier years (1987–1999) and the 2026 daily and monthly files were not downloaded |
| Location | `data/raw/oepm_open/`, kept out of git |
| Format | ST36 XML (`es-patent-document-v1-2.dtd`) inside three levels of nested ZIP (file → month → day) |

The 26 files are identified by the hashes in §8. The CPC classification data are a different OEPM dataset (`CPC_YYYY.zip`) and were **not** downloaded.

## 2. What a record contains

One XML document per publication. Fields present and used here: country, document number, kind code, publication date, application date, earliest priority date (when a priority claim exists), applicants, inventors, title, IPC classifications with the IPC version indicator.

Fields **absent**: abstract and description (the XML carries empty `<description>` and `<claims>` elements), CPC codes, citations, patent family identifier.

## 3. Counts

### 3.1 Totals

| Quantity | Value |
|---|---|
| Records read | 711,547 |
| Distinct `doc_id` (country + number + kind) | 707,985 |
| Distinct (`doc_id`, publication date) | 708,176 |
| Records unparseable after stripping control characters | 341 (0.05 %), all in files 2000–2009, 2014 and 2016 |
| Records with no IPC classification | 2,749 |
| Records kept with an unreadable optional date (see G7) | 3 |
| Distinct IPC subclasses (4 characters) | 660 |

`doc_id` repeats 3,562 times: 3,371 are exact repeats (same identifier and publication date, 2,127 of them kind `T3`) and 185 identifiers appear with more than one publication date. The cause of the repeats was not investigated.

### 3.2 Document types

| Group | Kinds | Records | Share |
|---|---|---|---|
| EP translations validated in Spain | `T*` | 511,992 | 72.0 % |
| National patents | `A*`, `B*`, `R*` | 105,065 | 14.8 % |
| National utility models | `U*`, `Y*` | 94,490 | 13.3 % |

The `T*` share varies by publication year between 54 % and 81 %.

### 3.3 Publication-year table

2010 has no record. The first record of 2011 is dated 2011-01-10.

| Publication year | Records | EP translations (`T*`) | National | Distinct publication dates |
|---|---|---|---|---|
| 2000 | 19,202 | 11,925 | 7,277 | 24 |
| 2001 | 17,010 | 9,156 | 7,854 | 24 |
| 2002 | 20,661 | 14,207 | 6,454 | 24 |
| 2003 | 23,916 | 16,416 | 7,500 | 24 |
| 2004 | 29,961 | 22,673 | 7,288 | 24 |
| 2005 | 29,413 | 21,755 | 7,658 | 24 |
| 2006 | 24,484 | 17,132 | 7,352 | 24 |
| 2007 | 29,131 | 21,972 | 7,159 | 24 |
| 2008 | 27,396 | 19,926 | 7,470 | 24 |
| 2009 | 26,485 | 18,753 | 7,732 | 173 |
| **2010** | **0** | **0** | **0** | **0** |
| 2011 | 28,630 | 18,404 | 10,226 | 236 |
| 2012 | 30,683 | 19,945 | 10,738 | 246 |
| 2013 | 32,262 | 19,565 | 12,697 | 235 |
| 2014 | 30,805 | 18,958 | 11,847 | 247 |
| 2015 | 28,555 | 18,493 | 10,062 | 247 |
| 2016 | 26,954 | 17,656 | 9,298 | 246 |
| 2017 | 36,940 | 29,027 | 7,913 | 241 |
| 2018 | 28,949 | 23,228 | 5,721 | 226 |
| 2019 | 27,609 | 21,573 | 6,036 | 246 |
| 2020 | 34,817 | 27,692 | 7,125 | 248 |
| 2021 | 41,189 | 32,470 | 8,719 | 248 |
| 2022 | 31,583 | 24,965 | 6,618 | 247 |
| 2023 | 21,290 | 14,846 | 6,444 | 244 |
| 2024 | 34,393 | 27,712 | 6,681 | 249 |
| 2025 | 29,229 | 23,543 | 5,686 | 248 |

## 4. Dates

### 4.1 Application and priority dates

* The application date is present in every record read and is never later than the publication date.
* A priority date (earliest `priority-claim` date) is present in 66.1 % of records and **absent in 33.9 %** (240,916). The absence is not uniform:

  | Group | Records without a priority claim |
  |---|---|
  | EP translations (`T*`) | 11.6 % |
  | National patents | 87.0 % |
  | National utility models | 95.6 % |

  The pattern is what one expects if records without a claim are first filings, in which case the application date would be the priority date. That reading is a **hypothesis consistent with the counts**; it has not been verified against the documents.

### 4.2 Publication lag

Lag is the publication year minus the year of the earliest of priority and application date (`py − fy`), over records published in 2012 or later.

| Group | Mean | Median | 90th percentile |
|---|---|---|---|
| EP translations (`T*`) | 6.9 years | 6 | 11 |
| National | 1.2 years | 1 | 3 |

For `T*` documents in filing-year cohorts 2003–2010, the cumulative share published within *L* years of filing is: 3 y 7.5 %, 5 y 37 %, 7 y 60 %, 9 y 78 %, 11 y 89 %, 13 y 95 %. Applied to observation up to the end of 2025, this implies that a `T*` cohort filed in 2013 is about 93 % complete, 2016 about 78 %, 2019 about 49 %, 2022 about 8 %. These are extrapolations from older cohorts and assume the lag distribution is stable.

### 4.3 Resolution of publication dates

From 2000 to 2008 the corpus contains **24 distinct publication dates per year** (the 1st and 16th of each month, ending on 16 December). Daily publication dates appear during 2009 (173 distinct dates) and are the rule from 2011. Analyses at year granularity are unaffected; finer ones are not comparable across the two regimes.

### 4.4 File year is not publication year

Files are labelled by the year of their *file date*, not of the publication dates they contain. For example `BIBLIO_2011.zip` holds publications from 2011-01-14 to 2012-01-12 and `BIBLIO_2023.zip` reaches 2024-03-14 (one record). Analyses must group by the publication date of the record and never by the file name.

## 5. Classification

* Every record but 2,749 carries at least one IPC classification. The mean number of distinct IPC subclasses per record is 1.81, and **48.7 % of records have two or more distinct subclasses**; only those records can form a pair, so about half of the corpus contributes nothing to a co-classification analysis.
* The version indicator of the first IPC entry of the records with an IPC takes **45 distinct raw values**: 43 in `YYYY.MM` form, one empty value and one that is not a date (`3.11`) (corrected on 2026-10-20, see §11). 91.6 % of those records carry `2006.01`. Whether this means that stored classifications are the ones assigned at publication, rather than retroactively updated, has **not been verified** (ADR 0036, P5).
* The classification level and the "inventive / additional" value are present in the XML. **They were not used** in the counts of this document: all IPC entries of a record were taken together. Whether secondary or additional-information entries should count is an open decision (ADR 0036, P5).
* No CPC data are in this dataset.

## 6. Gaps and anomalies

| # | Observation | Status |
|---|---|---|
| G1 | **No record has a publication date in 2010**, and none before 2011-01-10 in 2011. `BIBLIO_2010.zip` contains a single monthly archive named `BIBLIO_201012.zip`, but its 381 records are dated 2011-01-10 to 2011-01-13. | Source gap. Cause unknown; the OEPM has not been asked. |
| G2 | **EP translations in 2023**: 14,846, against 24,965 (2022) and 27,712 (2024), while national kinds are stable (6,444 against 6,618 and 6,681). All twelve months and 244 publication dates are present. | Unexplained. A real fluctuation and an incomplete source are both possible. |
| G3 | 2018 has 226 distinct publication dates against 241–249 in neighbouring years. | Noted, not investigated. |
| G4 | 341 records (0.05 %) could not be parsed (invalid characters), concentrated in 2004–2009. | Excluded and counted. |
| G5 | Repeated identifiers (§3.1). | Not investigated. |
| G6 | 2000–2008 records are assigned to one of 24 dates per year (§4.3). | Structural. |
| G7 | Three records state a priority date that is not a valid date: `ES2283462` kind `T3` (published 2007-11-01, `00000000`) and `ES2394445` kinds `A1` and `B1` (published 2013-01-31 and 2013-08-20, `101108`). They count as having a priority claim; the unreadable date is kept as a raw value and is not used. | Found by the adapter (2026-10-20); the exploratory parser had kept the strings. |

## 7. Descriptive base rates used for feasibility

These counts exist only to show how many cases the data contain. They are **not** performance figures and involve no detector.

**Definitions used.** A *seen pair* at origin *t* is a pair of IPC subclasses classified together on at least one record published in or before year *t*. An *active subclass* at *t* has at least 20 distinct documents published in or before *t*. A *candidate pair* is a pair of active subclasses that is not a seen pair. A *positive* is a candidate pair that is classified together on at least one record published in the years *t*+1 to *t*+3. The threshold of 20 was chosen for this count only and carries no scientific justification (see ADR 0036, P2).

| Origin *t* | Active subclasses | Candidate pairs | Positives within 3 years | Positive rate |
|---|---|---|---|---|
| 2012 | 592 | 143,894 | 2,060 | 1.43 % |
| 2013 | 594 | 144,360 | 2,096 | 1.45 % |
| 2014 | 597 | 145,416 | 2,626 | 1.81 % |
| 2015 | 599 | 145,903 | 2,907 | 1.99 % |
| 2016 | 600 | 145,749 | 3,159 | 2.17 % |
| 2017 | 603 | 146,285 | 3,045 | 2.08 % |
| 2018 | 606 | 147,070 | 3,255 | 2.21 % |
| 2019 | 606 | 146,076 | 3,237 | 2.22 % |
| 2020 | 608 | 146,107 | 2,738 | 1.87 % |
| 2021 | 609 | 145,588 | 2,718 | 1.87 % |
| 2022 | 612 | 146,381 | 2,632 | 1.80 % |

Origins 2012–2022 use publication years only; origins whose horizon would pass 2025 are not shown. Origins 2012 and later have their 3-year horizon free of the 2010 gap; their *history* still contains it.

**Estimated effect of the 2010 gap on positives (by analogy, not measured).** For each of the years 2007, 2008, 2009, 2011 and 2012 taken in turn, we counted candidate pairs whose only occurrences up to *t* fall in that single year and that reappear in (*t*, *t*+3]. Had that year been missing from the history, those pairs would have been counted as new. The counts per hidden year were 77–127 at *t* = 2013 (against 2,096 positives), 78–143 at *t* = 2016 (3,159) and 56–122 at *t* = 2019 (3,237), that is roughly 2 % to 6 % of the positives. This is an order of magnitude for a year with ordinary volume. It is not a measurement of 2010 itself, which is unobservable.

### 7.1 How many positives were already filed before the origin

For the positives of §7, using the earliest of priority and application year over the documents that make the pair a positive (the "earliest filing year", `fy`):

| Origin *t* | Positives | `fy` ≤ *t* | `fy` ≤ *t* − 5 | Every contributing document is an EP translation | No contributing document is an EP translation |
|---|---|---|---|---|---|
| 2006 | 4,532 | 96 % | 48 % | 88 % | 9 % |
| 2013 | 2,096 | 84 % | 31 % | 75 % | 23 % |
| 2016 | 3,159 | 89 % | 39 % | 83 % | 15 % |
| 2019 | 3,237 | 90 % | 39 % | 85 % | 13 % |
| 2022 | 2,632 | 89 % | 31 % | 83 % | 15 % |

Most of the positives on the publication axis therefore correspond to filings that already existed at the origin and became public later. This is consistent with the publication lag of §4.2 and is the reason the axes are kept apart in ADR 0036 §6.

### 7.2 National documents only

The same counts restricted to kinds other than `T*` (199,555 records, of which 65,953 have two or more distinct subclasses; lag median 1 year, 90th percentile 3 years). The active-subclass threshold is again 20 documents, counted within this subcorpus.

| Origin *t* | Active subclasses | Candidate pairs | Positives, publication axis | Positive rate | Of those, `fy` ≤ *t* | Positives, filing-year outcome |
|---|---|---|---|---|---|---|
| 2013 | 510 | 119,995 | 1,259 | 1.05 % | 478 (38 %) | 1,222 |
| 2016 | 529 | 128,463 | 1,262 | 0.98 % | 447 (35 %) | 1,164 |
| 2019 | 546 | 136,189 | 1,263 | 0.93 % | 365 (29 %) | 1,285 |
| 2022 | 554 | 139,221 | 1,162 | 0.83 % | 418 (36 %) | not computed (cohort incomplete) |

The filing-year outcome counts pairs unseen in publications up to *t* whose earliest filing year over all documents published up to 2025 falls in *t*+1…*t*+3. It is computed only where the national filing-year cohorts are judged at least 90 % complete (filing years up to 2022).

## 8. File identities

| File | Bytes | SHA-256 | Records | Publication dates in file | Unparseable |
|---|---|---|---|---|---|
| `BIBLIO_2000.zip` | 20,238,798 | `e4c1ecadd7c0f80247a73a622f708b38af557e35b96c44959a309743426c691b` | 19,202 | 2000-01-01 … 2000-12-16 | 10 |
| `BIBLIO_2001.zip` | 17,642,555 | `f780a3786a3951bc093bc34c6f2770cb28d1d546cf09c204743c64b4f02afda3` | 17,010 | 2001-01-01 … 2001-12-16 | 7 |
| `BIBLIO_2002.zip` | 22,188,696 | `e7ce5f7462cd6a15e8a05a3ab96aa1113593121aa3afd04182cac208b8154036` | 20,661 | 2002-01-01 … 2002-12-16 | 11 |
| `BIBLIO_2003.zip` | 25,808,578 | `4263243833bf0664e883eb6bbdf392822908924af7f29b5fbfaaefa7b1164b2b` | 23,916 | 2003-01-01 … 2003-12-16 | 16 |
| `BIBLIO_2004.zip` | 32,784,571 | `9ab3ba7f00f0c45f5e88e8c3ffbb1c07871d29455dcca8c2eb9153a47356b412` | 29,961 | 2004-01-01 … 2004-12-16 | 33 |
| `BIBLIO_2005.zip` | 32,184,129 | `dca5b173814ba7c8485ef781f571eda1b54ce8592aefc0545d4d78051bbaed9f` | 29,413 | 2005-01-01 … 2005-12-16 | 38 |
| `BIBLIO_2006.zip` | 26,195,679 | `5d070a95e3e95e90e0b0820e11327eb464f3ec8f566a47cfe46c6fc6d1154fc7` | 24,484 | 2006-01-01 … 2006-12-16 | 25 |
| `BIBLIO_2007.zip` | 32,047,045 | `eb7ed9cacdf622478ada419f6920393845e6703c5a5141be74d5bffd40a0b2bb` | 29,131 | 2007-01-01 … 2007-12-16 | 47 |
| `BIBLIO_2008.zip` | 29,827,766 | `76aa56ba4d7914262ffd0a80aa900b400086662ef6ccc3f853a1014936955271` | 27,396 | 2008-01-01 … 2008-12-16 | 69 |
| `BIBLIO_2009.zip` | 29,028,069 | `6bc5b37fabc8e425d2d90390799b5fddfe16ecb029c626fd73bea7b562f4f937` | 26,485 | 2009-01-01 … 2009-12-30 | 77 |
| `BIBLIO_2010.zip` | 473,342 | `7cc4cb7817a0e0a33c6b7a631d9e95a535d3c16402d32ddae00601f2babdd3fb` | 381 | 2011-01-10 … 2011-01-13 | 0 |
| `BIBLIO_2011.zip` | 34,528,817 | `585259a4c28258c5a464fb8b0ac5f15675ce1939d916883104e8b034292cf155` | 28,992 | 2011-01-14 … 2012-01-12 | 0 |
| `BIBLIO_2012.zip` | 36,578,688 | `d9913753fb90ea2ef01efb81e83406bf1082a1e48e00f872c97eae69d6b1bb2c` | 30,189 | 2012-01-13 … 2013-01-14 | 0 |
| `BIBLIO_2013.zip` | 39,001,123 | `ce17267745cc5c6d45cd84f6000611154cb68dae24465223116bbc18c1617a76` | 32,434 | 2013-01-15 … 2014-01-07 | 0 |
| `BIBLIO_2014.zip` | 36,876,506 | `f1b85a2eede523b45a7b1aa4a27a1a3a797642d82177217b226d514646cf1785` | 30,384 | 2014-01-08 … 2014-12-30 | 7 |
| `BIBLIO_2015.zip` | 35,296,173 | `ec3796c0e75abbe4f8bd7d9e3494dc75d2151bd6e3913421ba444d7838392b9c` | 28,555 | 2015-01-02 … 2015-12-30 | 0 |
| `BIBLIO_2016.zip` | 33,716,591 | `0eb99a92e397bb1788e33929cd2393981e82581e3f95a4a230f2e0c1c451c2dd` | 26,954 | 2016-01-04 … 2016-12-30 | 1 |
| `BIBLIO_2017.zip` | 44,005,995 | `f14b299eda41c47a43efef8fdadbebab67cd746256f27c351687d8425efbfe7d` | 36,940 | 2017-01-02 … 2017-12-29 | 0 |
| `BIBLIO_2018.zip` | 35,951,894 | `e5e891b9f2891322ed3977488d4189d88ccb316b002f71cebaa26889c5253144` | 28,949 | 2018-01-02 … 2018-12-28 | 0 |
| `BIBLIO_2019.zip` | 32,523,306 | `d367cd7ae74c9b3fb568482dd54574756552f56c51f988dd7c5082d548724338` | 27,609 | 2019-01-02 … 2019-12-30 | 0 |
| `BIBLIO_2020.zip` | 39,958,138 | `31e8b6d86092d35647d198ae0ca9d751020e7631045f9cf5796211876ea8df33` | 34,817 | 2020-01-02 … 2020-12-30 | 0 |
| `BIBLIO_2021.zip` | 43,948,695 | `58ddffaf146ddab4c322dd385bed06881d2847b8986db0f72f0debb1fb210c4d` | 41,189 | 2021-01-04 … 2021-12-30 | 0 |
| `BIBLIO_2022.zip` | 39,972,409 | `7dfdcbde9bfb8a2e703446ac1c05783a785d81f279e0bf0b91605c662d9f9558` | 31,583 | 2022-01-03 … 2022-12-30 | 0 |
| `BIBLIO_2023.zip` | 29,068,184 | `7083052788b461413f89a8627545249c0a36d74b37ef278b78e8dccf7435a927` | 21,291 | 2023-01-02 … 2024-03-14 | 0 |
| `BIBLIO_2024.zip` | 43,017,990 | `a8f1b47643a60f885c618ff9b23af9a9361565a5cb1c3fb86a401c9d3166bc7b` | 34,392 | 2024-01-02 … 2024-12-30 | 0 |
| `BIBLIO_2025.zip` | 37,896,689 | `96580d6e0bd4993e8680fac32cde86d65e4ab709bf62e88aef5bc81b9229de0c` | 29,229 | 2025-01-02 … 2025-12-30 | 0 |

## 9. How the numbers were produced, and their status

* The figures of §3–§6 and §8 were first produced by a throw-away Python parser outside the repository that read each ZIP recursively, removed XML-illegal control characters, and wrote one row per document. DuckDB queries over those rows produced the tables, including §4.2 and §7.
* On 2026-10-20 the repository's own source adapter reproduced §3–§6 and §8 from the 26 files identified in §8 (hashes verified before reading): see [the reproduction report](oepm-biblio-reproduction.md). The two corrections that this revealed are in §11.
* **§4.2 and §7 (publication lag, base rates, the effect of the 2010 gap, the delay diagnostic and the national-documents counts) are still the product of the throw-away parser and are not reproduced from the repository.**
* The analysis was exploratory: counts were produced and inspected before any protocol existed. Nothing here may be cited as confirmatory.

## 10. What this document does not establish

* That the corpus is complete for any year other than as stated in §6.
* That a publication in this corpus corresponds to a distinct invention: no family identifier exists.
* That positives in §7 are predictable, or that any candidate is an opportunity.
* That the corpus describes Spanish applicants or the world: it describes documents published by the OEPM, of which 72 % are translations of European patents.

## 11. Errata (2026-10-20)

Found when the figures were reproduced with the repository's adapter ([report](oepm-biblio-reproduction.md)). The original values are kept in that report.

1. §5 stated that the IPC version indicator has 36 distinct values, all in `YYYY.MM` form. The value 36 came from truncating the indicator to six characters before counting. The correct count of distinct raw values is 45; two of them are not `YYYY.MM` (one empty, one `3.11`).
2. §3.1 and §6 did not mention three records whose priority date is unreadable (G7). They are in the 711,547 records and are not among the 341 unreadable ones; the counts of those sections do not change.
