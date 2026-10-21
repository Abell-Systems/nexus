# Exposure of the corpus to omissions (ADR 0036, O5.1)

**Status:** Measurement of what the OEPM's inventory lists and the corpus lacks, by publication year and kind group, and accumulated up to each origin. Exploratory; it measures exposure, not the effect of the omissions on any result.
**Date:** 2026-10-21
**Checks:** [bulk datasets audit](oepm-bulk-datasets-audit.md) · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (C3, O5, §8.10)
**Scope:** Counts of publication keys. **No claim about the classification of the absent publications, which the inventory does not carry.**

Reproduction: `python scripts/report_oepm_corpus_exposure.py ES_Authority_File_20260930.zip --corpus-dir data/raw/oepm_open` (about 3 minutes). Results: [`oepm-corpus-exposure-results.json`](oepm-corpus-exposure-results.json), with the SHA-256 of the Authority File. The corpus is read through the adapter after its hashes are verified; the inventory is an untrusted download.

---

## 1. Definitions

* A **publication key** is publication number + kind code + publication date. The inventory is counted by distinct keys (a key listed twice counts once).
* **Present**: the key is in the corpus. **Absent**: it is in the inventory and not in the corpus. A corpus key that is not in the inventory is reported apart.
* **Kind groups** are code families of the inventory: `T*` (EP translations), `Y`, and every other kind. What kind `Y` denotes has not been read, and no interpretation is attached to the group.
* **History length** at an origin *t* is given in two numbers: the calendar years of the window from the first corpus year (2000) to *t*, and the years in that window that contain at least one corpus publication. They differ when a year is missing (2010 for the origins from 2010 on). The corpus starts in 2000, so the window at origin 2003 is 4 calendar years and at 2006 it is 7 (both with publications in every year), however long the OEPM has published.

## 2. Result (verified counts)

Inventory 2000–2025: 774,552 publication keys; corpus: 708,176 distinct keys.

**Accumulated absences from 2000 up to each origin**

| Origin | Window (calendar years / with publications) | Inventory | Absent | Share | `T*` absent / share | `Y` absent / share | Other absent / share |
|---|---|---|---|---|---|---|---|
| 2003 | 4 / 4 | 93,660 | 12,874 | 13.75 % | 39 / 0.08 % | 12,830 / **100 %** | 5 / 0.02 % |
| 2006 | 7 / 7 | 185,489 | 20,846 | 11.24 % | 134 / 0.12 % | 20,706 / **100 %** | 6 / 0.01 % |
| 2010 | 11 / 10 | 301,885 | 54,230 | 17.96 % | | | |
| 2013 | 14 / 13 | 394,198 | 57,794 | 14.66 % | 18,260 / 7.35 % | 30,501 / 81.59 % | 9,033 / 8.34 % |

**By year, selected** (absent / inventory, share)

| Year | `T*` | `Y` | Other |
|---|---|---|---|
| 2000 | 8 / 11,933 (0.07 %) | 3,272 / 3,272 (100 %) | 2 / 7,279 (0.03 %) |
| 2005 | 38 / 21,793 (0.17 %) | 2,623 / 2,623 (100 %) | 0 / 7,658 |
| 2009 | 77 / 18,830 (0.41 %) | 2,259 / 2,259 (100 %) | 0 / 7,732 |
| 2010 | 15,816 / 15,816 (100 %) | 2,151 / 2,151 (100 %) | 7,882 / 7,882 (100 %) |
| 2011 | 877 / 19,270 (4.55 %) | 118 / 2,546 (4.63 %) | 483 / 8,180 (5.90 %) |
| 2017 | 465 / 29,490 (1.58 %) | 714 / 2,170 (32.9 %) | 174 / 6,626 (2.63 %) |
| 2018 | 2,577 / 25,802 (9.99 %) | 2,093 / 2,220 (94.28 %) | 514 / 6,105 (8.42 %) |
| 2019 | 0 / 21,496 | 1,830 / 2,470 (74.09 %) | 3 / 5,381 (0.06 %) |

(The full table, every year and group, is in the results file.)

## 3. What it shows, and what it does not

* **In every year of 2000–2009 the corpus has none of the inventory's kind-`Y` publications**: the absence is total and systematic by kind, not a random loss. The other kinds are almost complete in those years (0 to 0.41 % absent).
* Consequently the histories behind the development origins 2003 and 2006 lack, by construction, all kind-`Y` publications: 12,830 of 93,660 (2003) and 20,706 of 185,489 (2006) inventory publications.
* A simulation that deletes observed publications at random within a year and kind cannot represent that omission, because there are no observed kind-`Y` publications of those years to delete or resemble. **The effect of the kind-`Y` omission on the pairs seen at the development origins is not identifiable from these data**, whatever is done with the observed corpus.
* From 2011 the group is mostly present, with large absences again in 2017–2019 (33 %, 94 %, 74 % of its publications) and a whole absent year, 2010, in every group.
* The history at origin 2003 is four years; that is a property of the corpus, separate from the omissions.
* Nothing here says whether the absent publications are classified differently from the present ones.

## 4. Pending

* What kind `Y` denotes, and whether the absent `Y` publications carry IPC classification at all.
* Whether an alternative source (the pre-2013 ECLA files, for example) holds classification for part of them.
* The sensitivity of the pair counts and of the baselines' metrics to the omissions that can be simulated: ADR 0036, §8.10 (O5.2 and O5.3).
