# Linking by application number: contract and measurements

**Status:** Normalisation rules for the application number, and a measurement of how they link the bibliographic corpus to the OEPM Authority File and to a legal-status file. Exploratory; nothing is added to the corpus and no published figure or ADR decision changes.
**Date:** 2026-10-21
**Checks:** [bulk datasets audit](oepm-bulk-datasets-audit.md) · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (C3, O5)
**Scope:** Which application keys can be built, from which sources, with which ambiguity and which exceptions. **Measurement only.**

Reproduction: `python scripts/report_oepm_application_links.py ES_Authority_File_20260930.zip --corpus-dir data/raw/oepm_open --legal-zip LEGAL_2018.zip` (about 4 minutes). The figures are in [`oepm-application-links-results.json`](oepm-application-links-results.json) with the SHA-256 of the two downloaded files. The corpus is read through the adapter after its hashes are verified; the other two files are untrusted downloads.

---

## 1. The key and its rules (`domain/models/whitespace.py`)

An application is identified by a **series** and its digits. National patents (`P`) and utility models (`U`) are numbered in separate series that share the digit space; European applications (`E`) have their own. Digits alone are therefore not a key.

| Source | What it states | Rule | If it does not fit |
|---|---|---|---|
| Bibliographic record | application kind + number (`U` / `201000660`) | series = kind, number must be digits only | no key |
| Authority File, office `ES` | letter + digits (`U200502626`) | series = the letter (`P` or `U`) | no key |
| Authority File, office `EP` | digits only (`06743854`) | series `E` | no key |
| Source without series (legal status, ECLA `FILE`) | country + digits | **candidates**, not a key: `ES` gives `P` and `U`, `EP` gives `E` | none |

No prefix is removed indiscriminately: a letter is read as a series only where a source states it that way. A key is never guessed; an anomaly gives no key and is counted.

## 2. Corpus against the Authority File (verified)

Matching publications by number, kind code and publication date (707,792 of the corpus' 708,176 distinct keys are in the inventory; 384 are not):

| Outcome among the 707,792 | Publications |
|---|---|
| Same application key and same filing date | 707,638 |
| Same key, filing date differs | 111 |
| Different keys | 37 |
| The corpus record has no usable key | 6 |

* The 6 are EP translations whose bibliographic number carries a letter inside the digits (`P98924378`, kind `E`); the inventory states the digits alone. They are left without a key on purpose.
* The 37 different keys include, for example, publication `ES2138518` (`A1` and `B1`) with the bibliographic number `200050035` against `P9650031` in the inventory, with the same filing date. Which source is right is **pending**.
* The 111 filing-date differences share a key; the dates differ by months or years (examples in the results file). **Pending.**
* The corpus has no repeated publication key whose copies disagree on the application (0).

For EP translations, the bibliographic country is `ES` (or `EP` for 513 records) while the inventory's office is `EP`: the office is not part of the key, the series is.

## 3. Collisions inside the inventory (verified)

* 1,633,183 application keys; **3 have more than one filing date** (for example `E99911033`). The key is almost, but not always, one to one.
* 650,653 national digit strings; **335,106 (51.5 %) exist in both the `P` and the `U` series.** A source that omits the series, such as legal status or the pre-2013 ECLA files, is therefore ambiguous for about half of its numbers by construction.
* 259 application numbers could not be parsed: 254 `ES` numbers with a letter suffix (`P0002585B1`, nineteenth and early twentieth century), 3 `WO`, 2 `EP` with a letter. None is in the corpus' range.

## 4. A legal-status file against the inventory (verified on one year)

`LEGAL_2018.zip`, filing-number records (indicator `F`), 77,351 distinct (country, number) pairs:

| Outcome | Pairs |
|---|---|
| Matched to exactly one application | 59,311 |
| Ambiguous between series (`P` and `U`) | 11,756 |
| No application in the inventory | 6,284 |

(Of the 77,351: `EP` numbers, about 54,900, match one application each; `ES` numbers are where the ambiguity and the missing ones arise.) The 6,284 without an application are probably applications not yet published, but that is **inferred**: nothing here establishes it. One year of one dataset does not describe the other years.

## 5. Consequences (nothing is changed by this document)

* The inventory is a usable bridge for **national publications and EP translations**, with 37 + 6 + 111 exceptions out of 707,792 (0.02 %).
* Legal status for national applications cannot be linked reliably by number alone; about 15 % of the pairs of the year measured would need a second criterion (for example the filing date) that has not been examined.
* For ADR 0036 this concerns only future extensions. It does not touch O5, which is about the effect of the corpus' omissions on the development origins.

## 6. Pending

* Why 37 applications have different numbers in the two sources, and why 111 have different filing dates.
* Whether the legal-status ambiguity can be resolved with the filing date.
* The ECLA files (keyed by application without series) were not measured, only the format of the example.
* Anything about 2010 and the other omitted publications: the inventory has them but no classification.
