# Reproduction of the OEPM bibliographic corpus characterization

**Status:** Result of one run of `scripts/reproduce_oepm_biblio_characterization.py`. Descriptive; no figure was adjusted to force agreement.
**Date:** 2026-10-20
**Checks:** [corpus characterization](oepm-biblio-corpus-characterization.md), [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) §11.1
**Scope:** Whether the figures published in the characterization can be reproduced from the 26 source files through the repository's adapter. **Documentary only.**

---

## 1. What was run

* Adapter: `OepmBiblioSource` (`infrastructure/sources/patent/oepm_biblio.py`), figures by `application/whitespace/corpus_report.py`.
* Published figures: `config/whitespace/oepm_biblio_2000_2025.json`, transcribed from the characterization (228 figures: sections 3, 4.1, 4.3, 5, 6 and 8). A test checks that the file hashes and sizes of that JSON equal those printed in the characterization.
* Input: the 26 files `BIBLIO_2000.zip` … `BIBLIO_2025.zip`, downloaded on 2026-10-20 and kept outside git.
* Run time: about 2.5 minutes on one process.

## 2. Integrity

All 26 files matched their expected SHA-256 before any record was read. The reproduced file identities are therefore exactly those of §8 of the characterization.

| | Count |
|---|---|
| Records read | 711,544 |
| Records rejected (counted, not dropped) | 344 |
| Records in the source | 711,888 |

## 3. Result

Of the 228 published figures, **213 were reproduced exactly and 15 differ**. No figure was corrected.

| # | Figure | Published | Reproduced |
|---|---|---|---|
| 1 | `records` | 711,547 | 711,544 |
| 2 | `rejected` | 341 | 344 |
| 3 | `distinct_doc_ids` | 707,985 | 707,982 |
| 4 | `distinct_doc_id_publication_dates` | 708,176 | 708,173 |
| 5 | `kind_groups.ep_translation` | 511,992 | 511,991 |
| 6 | `kind_groups.patent` | 105,065 | 105,063 |
| 7 | `by_publication_year.2007.records` | 29,131 | 29,130 |
| 8 | `by_publication_year.2007.ep_translations` | 21,972 | 21,971 |
| 9 | `by_publication_year.2013.records` | 32,262 | 32,260 |
| 10 | `by_publication_year.2013.national` | 12,697 | 12,695 |
| 11 | `by_file.BIBLIO_2007.zip.records` | 29,131 | 29,130 |
| 12 | `by_file.BIBLIO_2007.zip.rejected` | 47 | 48 |
| 13 | `by_file.BIBLIO_2013.zip.records` | 32,434 | 32,432 |
| 14 | `by_file.BIBLIO_2013.zip.rejected` | 0 | 2 |
| 15 | `ipc.first_entry_versions` | 36 | 45 |

### 3.1 Differences 1–14: three records with an unreadable priority date

Fourteen of the fifteen differences have one cause. The adapter rejects a record whose priority date is not a valid `YYYYMMDD` date; the exploratory parser behind the characterization kept the raw string. Three records are affected:

| Record | File | Priority date in the source |
|---|---|---|
| `ES2283462` kind `T3`, published 2007-11-01 | `BIBLIO_2007.zip` | `00000000` |
| `ES2394445` kind `A1`, published 2013-01-31 | `BIBLIO_2013.zip` | `101108` |
| `ES2394445` kind `B1`, published 2013-08-20 | `BIBLIO_2013.zip` | `101108` |

These three are now rejected with their provenance and reason. Nothing else about them was changed. Whether such a record should be rejected, or kept with the malformed priority date set aside, is a decision, not a bug fix, and is left open (§6).

### 3.2 Difference 15: an error in the characterization

`ipc.first_entry_versions` was published as 36 "distinct year-month values" and is 45. The published number came from truncating the version string to six characters before counting, which merged different versions (for example `2016.01` … `2016.12`). The 45 raw values include an empty value and the non-date `3.11`, so the statement in §5 of the characterization that the indicator is in `YYYY.MM` form is not true of every record. The reproduced value is the correct one.

## 4. Rejected records

The reproduction is the first complete accounting of rejected records: 344 in total, all counted and each kept with its file, its path inside the archive and its reason.

| Reason | Records | First example |
|---|---|---|
| Not well-formed XML (invalid token) | 244 | `ES2139094_20000201_T3.xml` in `BIBLIO_2000.zip` |
| Undefined entity | 86 | `ES2174601_20021101_T3.xml` in `BIBLIO_2002.zip` |
| Junk after the document element | 7 | `ES1125530_20140929_U.xml` in `BIBLIO_2014.zip` |
| Mismatched tag | 3 | `ES2221875_20050116_T3.xml` in `BIBLIO_2005.zip` |
| Unreadable priority date | 3 | `ES2283462_20071101_T3.xml` in `BIBLIO_2007.zip` |
| No element found (empty or truncated) | 1 | `ES2555789_20160617_B1.xml` in `BIBLIO_2016.zip` |

By file: 2000 10, 2001 7, 2002 11, 2003 16, 2004 33, 2005 38, 2006 25, 2007 48, 2008 69, 2009 77, 2013 2, 2014 7, 2016 1; no other file has a rejected record. The "undefined entity" records may hold legitimate text with an `&` entity that the removal of the DOCTYPE leaves undefined; that has not been investigated and no record was repaired.

## 5. What this does not cover

* Section 4.2 of the characterization (publication lag and completeness of filing-year cohorts).
* Section 7 (descriptive base rates, the estimate of the effect of the 2010 gap, the delay diagnostic and the national-documents counts). They need decisions that ADR 0036 keeps open (for example the activity threshold) and are left to a later change.
* The facts that no record carries a CPC code, abstract or family identifier are taken from the structure of the XML and not computed.

## 6. Open points raised by the reproduction

1. **Malformed priority dates:** reject the record (current behaviour) or keep it and set the priority aside. Three records out of 711,888.
2. **Errata to the characterization:** correct the count of distinct IPC versions to 45 and the wording about their form, and add the three rejected records to §3 and §6. Not applied here, so that the published document and its transcription stay comparable.
3. **Undefined-entity records (86):** worth a look before they are given up for lost.

## 7. How to repeat

```text
python scripts/reproduce_oepm_biblio_characterization.py --data-dir data/raw/oepm_open [--write-figures FILE]
```

Exit code 0: all published figures reproduced; 1: differences listed, one per line; 2: the source could not be verified, nothing was read.
