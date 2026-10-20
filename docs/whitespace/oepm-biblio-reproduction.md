# Reproduction of the OEPM bibliographic corpus characterization

**Status:** Result of five runs of `scripts/reproduce_oepm_biblio_characterization.py`, in the order they happened. Descriptive; no figure was adjusted to force agreement.
**Date:** 2026-10-20
**Checks:** [corpus characterization](oepm-biblio-corpus-characterization.md), [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) §11.1
**Scope:** Whether the figures published in the characterization can be reproduced from the 26 source files through the repository's adapter, and what the reproduction changed. **Documentary only.**

---

## 1. What was run

* Adapter: `OepmBiblioSource` (`infrastructure/sources/patent/oepm_biblio.py`); figures by `application/whitespace/corpus_report.py`.
* Published figures: `config/whitespace/oepm_biblio_2000_2025.json`, transcribed from the characterization (228 figures from sections 3, 4.1, 4.3, 5, 6 and 8). A test checks that the file names, sizes and SHA-256 of that JSON equal those printed in the characterization.
* Input: `BIBLIO_2000.zip` … `BIBLIO_2025.zip`, downloaded on 2026-10-20, kept outside git.
* About 2.5 minutes per run on one process.

## 2. Integrity

All 26 files matched their expected SHA-256 before any record was read, in every run. The file identities are exactly those of §8 of the characterization.

## 3. Results, in order

### 3.1 Run 1 — adapter that rejected a record with an unreadable optional date (historical, superseded by runs 2 and 3)

The figures of this section describe a behaviour that no longer exists and are kept only to show what the reproduction found. 711,544 records read, 344 rejected. Of the 228 published figures, 213 matched and 15 differed:

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

Differences 1–14 had one cause: three records whose priority date is not a valid date (§5) were rejected by the adapter, while the exploratory parser behind the characterization had kept the raw string. Difference 15 was an error of the characterization (§3.3).

### 3.2 Decision: keep the record, leave the date absent

An unreadable optional date (application or priority) should not cost a usable publication. The adapter now keeps the record, leaves that date absent, keeps the raw value and the reason as a `SourceAnomaly`, and counts the anomaly. A record without a readable publication date, or with an incomplete IPC entry, is still rejected. ADR 0036 §11.1 asks the adapter to keep the original values and the provenance of every record and to document and test its handling of invalid XML, repeated identifiers and IPC entries; it does not ask for a record to be rejected for an unreadable optional field, so no amendment was needed.

This is a decision about the data contract, taken on that principle. It is the reason differences 1–14 disappeared in run 2, and it was not taken to make the counts agree.

### 3.3 Run 2 — against the original published figures

711,547 records read, 341 rejected. One of the 228 published figures differs, and two figures that were not published appear:

```text
/ipc/first_entry_versions: published 36, reproduced 45
/records_with_source_anomalies: reproduced 3, not published
/source_anomalies_by_field: reproduced {'priority_date': 3}, not published
3 difference(s) from 228 published figures
```

The `first_entry_versions` value was published as 36 "distinct year-month values". It came from truncating the version string to six characters before counting, which merged different versions (for example `2016.01` … `2016.12`). The 45 raw values are 43 in `YYYY.MM` form, one empty value and one that is not a date (`3.11`). So the characterization was wrong, and the reproduction is right.

### 3.4 Run 3 — after the errata

The characterization received errata (its §11: 45 versions with their forms, and the three records of §5) and the JSON of published figures was updated accordingly. Result:

```text
All 230 published figures reproduced
```

The agreement of the last two figures is by construction: the errata were written from run 2. It shows that the document and the adapter now describe the same corpus, not that the original document was right.

### 3.5 Runs 4 and 5 — after the review of the adapter

The review of pull request #130 raised two points about data fidelity, both checked against the files:

* The adapter decoded with `errors="replace"`, so bytes that are not valid UTF-8 became U+FFFD with no trace. **17 records** are affected (2019: 2, 2020: 11, 2021: 3, 2023: 1). They are still read, and each now carries a `SourceAnomaly` with field `encoding` and the first offending bytes. No value is repaired.
* The 86 records rejected for undefined entities are investigated in §4. They stay rejected; the reason now lists the entity names.

Run 4 against the figures of run 3 (parsing results unchanged: 711,547 read, 341 rejected):

```text
/records_with_source_anomalies: published 3, reproduced 20
/source_anomalies_by_field/encoding: reproduced 17, not published
2 difference(s) from 230 published figures
```

The errata (characterization §11, item 3; entry G8) and the JSON were updated from run 4. Run 5: `All 231 published figures reproduced`. As in run 3, that agreement is obtained after the errata.

## 4. Rejected records

341 in total, each kept with its file, hash, path inside the archive and reason; the same number the characterization published.

| Reason | Records | First example |
|---|---|---|
| Not well-formed XML (invalid token) | 244 | `ES2139094_20000201_T3.xml` in `BIBLIO_2000.zip` |
| Undefined named entity (§4.1) | 86 | `ES2174601_20021101_T3.xml` in `BIBLIO_2002.zip` |
| Junk after the document element | 7 | `ES1125530_20140929_U.xml` in `BIBLIO_2014.zip` |
| Mismatched tag | 3 | `ES2221875_20050116_T3.xml` in `BIBLIO_2005.zip` |
| No element found (empty or truncated) | 1 | `ES2555789_20160617_B1.xml` in `BIBLIO_2016.zip` |

By file: 2000 10, 2001 7, 2002 11, 2003 16, 2004 33, 2005 38, 2006 25, 2007 47, 2008 69, 2009 77, 2014 7, 2016 1; no other file has a rejected record. ### 4.1 The records with undefined entities

Nearly every record (711,887 of 711,888) declares `<!DOCTYPE es-patent-document SYSTEM "../es-patent-document-v1-2.dtd">`: an external DTD, referenced by a relative path, that is **not distributed with the data files** (the archives inspected contain only the XML records and `authorityFile.txt`). The adapter removes the DOCTYPE before parsing, so the DTD is never loaded and no entity is ever expanded or fetched.

The non-predefined named entities found in the records of the 26 files are: `&OSLASH;` (44 records), `&SZLIG;` (25), `&AMP;` (8), `&ODBLACC;` (2), and once each `&SCARONON;`, `&CCARONANCI;`, `&CCARONON;`, `&OMACRCR;`, `&Delta;`, `&alpha;`, `&ICIRC;`, `&ATILDE;`, `&ECIRC;`, `&EUML;`. They are in the files of 2002 and 2005–2009. The names are old SGML-style upper-case names. Several (`&SCARONON;`, `&CCARONANCI;`, `&CCARONON;`, `&OMACRCR;`, `&ODBLACC;`) match no standard entity set, so resolving them would mean guessing.

**Decision: they stay rejected, counted, with the entity names in the reason.** Recovering them safely needs the official DTD, which the data do not include. The page of the dataset links an example file (`biblio_example.zip`, described as "ST36 / es-patent-document-v1-2.dtd") behind the registered account; whether it contains the DTD has not been checked. If it does, a closed table of character entities built from the declarations in that DTD could be passed to the adapter; nothing would be loaded from the network or from the DTD's own external references.

### 4.2 Records with bytes that are not valid UTF-8

See §3.5. They are not rejected. Their text fields may contain U+FFFD, and the anomaly says so.

## 5. Records kept with an anomaly

| Record | File | Field | Raw value in the source |
|---|---|---|---|
| `ES2283462` kind `T3`, published 2007-11-01 | `BIBLIO_2007.zip` | priority date | `00000000` |
| `ES2394445` kind `A1`, published 2013-01-31 | `BIBLIO_2013.zip` | priority date | `101108` |
| `ES2394445` kind `B1`, published 2013-08-20 | `BIBLIO_2013.zip` | priority date | `101108` |

All three count as having a priority claim, since the source states one. The raw value is kept and is not used as a date. `ES2283462` keeps its other, readable priority date (2000-12-27); the two `ES2394445` records are left with no readable priority date. Their IPC entries, applicants and the rest of the record are intact.

## 6. What this does not cover

* Section 4.2 of the characterization (publication lag and completeness of filing-year cohorts).
* Section 7 (base rates, the estimate of the effect of the 2010 gap, the delay diagnostic, the national-documents counts). They need decisions that ADR 0036 keeps open, such as the activity threshold, and are left to a later change.
* That the XML carries no CPC code, abstract or family identifier is taken from its structure, not computed.

## 7. Open points

1. The 86 "undefined entity" records need the official DTD (§4.1) to be recovered safely. Obtaining it is a pending step.
2. Only the two optional dates follow the keep-and-record rule. An incomplete IPC entry still rejects the record; extending the rule to IPC entries would change what the classification counts mean and is not done here.

## 8. How to repeat

```text
python scripts/reproduce_oepm_biblio_characterization.py --data-dir data/raw/oepm_open [--write-figures FILE]
```

Exit code 0: all published figures reproduced; 1: differences listed, one per line; 2: the source could not be verified, nothing was read.
