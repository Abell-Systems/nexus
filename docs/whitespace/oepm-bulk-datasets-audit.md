# Audit of the OEPM OpenData bulk datasets (patents and utility models)

**Status:** Read-only inventory of what the OEPM publishes besides the bibliographic files already in use, with the reuse terms and an exploratory comparison of the OEPM's own document inventory with the corpus. Descriptive; no dataset was added to the corpus and ADR 0036 is not changed.
**Date:** 2026-10-21 (catalogue last updated 2026-10-19)
**Checks:** [corpus characterization](oepm-biblio-corpus-characterization.md) · [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (A6, P6, P9, O3, C3)
**Scope:** Which datasets exist, under what terms, how big, how they link to the corpus, and what the Authority File says about the corpus' coverage. **Documentary and one counting script only.**

Every statement carries one of three states: **verified** (read from the source or computed here), **inferred** (reasoned from verified facts) or **pending** (not established).

---

## 1. How this was done

* A logged-in session of the user's own OEPM account read the catalogue page, its nine dataset pages, the legal notice and the "Sobre OpenData" page (**verified**, 2026-10-21). The crawl script is throw-away and not in the repository; the same inventory is obtained with `python scripts/download_oepm_opendata.py --page <dataset page> --list` (the `--page` option is in `main`).
* One sample file per dataset was downloaded with that script, and the Authority File in full. Sample hashes are in §4.
* The server answers a plain `HEAD` or `GET` of a file with "Usted no tiene permisos para poder descargar el archivo" (106 bytes): the site only serves files through its own page. No attempt was made to get around that, so **file sizes are not exposed** (verified).
* The Authority File comparison is reproducible: `python scripts/audit_oepm_authority_file.py ES_Authority_File_20260930.zip`.

## 2. Reuse terms (verified, from the sede's legal notice)

The OpenData pages say the data are reusable under the general conditions of the legal notice (Ley 37/2007, RD 1495/2011). The notice (`/eSede/datos/es/aviso-legal/`) states:

* Reuse for **commercial and non-commercial** purposes is authorised, including copying, distribution, modification, adaptation, extraction, reordering and combination, with a free, non-exclusive transfer of intellectual-property rights "para todo el mundo".
* Conditions: do not distort the meaning of the information; cite the source ("Origen de los datos: Oficina Española de Patentes y Marcas"); mention the date of the last update when the original document includes it; do not suggest that the OEPM participates in, sponsors or supports the reuse; keep the update-date and reuse-condition metadata of the original document.
* Responsibility for the use rests with the reuser.

Consequences for Nexus (**inferred**): redistribution of derived products is not forbidden by these terms, provided the conditions above are met; a derived table that corrects or drops records must say so, because of the "do not distort" rule. This replaces the earlier note that reuse terms were unverified for the OpenData files (not for the SOAP service, whose terms are separate and unread). It is a reading of the notice, not legal advice.

## 3. The datasets

All have a registered-account download. Files for earlier years are single annual files; the current year is split into monthly and daily or weekly files.

| Dataset | Start | Specification | Annual files | Join key in the file | Sample read |
|---|---|---|---|---|---|
| Authority File (inventory) | 1826 | ST.37 XSD | 1 zip with 150 yearly XML files | publication number + kind + date, **application number** + filing date | Yes, in full |
| Bibliographic data (in use) | 01/06/1987 | ST36 `es-patent-document-v1-2.dtd` | 39 (1987–2025) | country + number + kind + date; application reference | Yes |
| Abstracts | 01/01/1987 | ST32 (SGML) | 39 | country + number + kind; **no publication date in the record** | 2013 file, 9.6 MB |
| Full text | 01/06/1987 | ST36 OCR DTD from 2019; proprietary XML before | 38 | not seen (example holds only the DTD) | **No record read** |
| Booklets (PDF) | 01/06/1987 | PDF | 38 | not applicable | No |
| Legal status | 10/11/2010 | ST17 `es-legal-document-v1-0.dtd` | 16 (2010–2025) | **application** number (indicator F) or publication number (P), event code, date | 2018 file, 1.8 MB |
| CPC | 06/10/2013 | ST36 `es-patent-document-v1-2-1.dtd` | 13 (2013–2025) | country + number + kind + date, hangs off an `R1` document in the example | 2018 file, 1.1 MB |
| Cited documents | 06/10/2013 | same | 13 | same | 2018 file, 1.8 MB |
| Cited documents and ECLA, before 2013 | 01/01/1993 | ST32 SGML | 42 files (annual to 2005, semesters 2006, quarters 2007–2013) | **application** number (`<PATDOC FILE>`) | Example only (934 documents) |

Status: the file counts, dates, specifications and join keys listed are **verified** from the pages and the sample files. Coverage inside each file (how many documents, which kinds) is **pending** except where §5 says otherwise.

Every dataset page also links an `*Feed.xml` file (verified as links, **content unread**).

## 4. Sizes

Not exposed by the service (§1). What was measured by downloading:

| File | Bytes | SHA-256 (first 16) |
|---|---|---|
| `RESUMENES_2013.zip` | 9,562,102 | `462160e8d02d64af` |
| `CPC_2018.zip` | 1,057,769 | `b0d353f11eb6027c` |
| `CITACIONES_2018.zip` | 1,791,613 | `c9a49d3f6abdaa33` |
| `LEGAL_2018.zip` | 1,769,207 | `b933b6198e9f2836` |
| `ES_Authority_File_20260930.zip` | 46,022,603 (2.4 GB uncompressed, 152 members) | `80a7fe1713f7b063` |
| the 26 bibliographic files in use, 2000–2025 | 830.8 MB in total | in `config/whitespace/oepm_biblio_2000_2025.json` |

(Sample examples from the previous audit: `biblio_example.zip` `ea29eefd…`, the other examples in that record.) Full text and booklets were **not** measured; the booklets are PDF files of every publication and will be far larger than the XML datasets. The abstract sample suggests that abstracts, CPC, citations and legal status are small next to the bibliographic files (one year each is 1–10 MB), but one year per dataset is not a bound on the rest (**inferred**).

## 5. The Authority File against the corpus (exploratory)

The Authority File lists every document the OEPM has published, with kind, publication date and application number, but no classification: it says how many documents exist, not what they contain. Its 2,066,479 entries (152 members) were counted by publication year and compared with the corpus (`BIBLIO_2000`–`BIBLIO_2025`, 711,547 records). Group: `T*` kinds against all others. **Exploratory; not reproduced elsewhere.**

| Year | Authority | Corpus | Authority − corpus (T / others) |
|---|---|---|---|
| 2000 | 22,484 | 19,202 | 3,282 (8 / 3,274) |
| 2003 | 27,161 | 23,916 | 3,245 (15 / 3,230) |
| 2006 | 27,091 | 24,484 | 2,607 (25 / 2,582) |
| 2009 | 28,821 | 26,485 | 2,336 (77 / 2,259) |
| **2010** | **25,849** | **0** | **25,849 (15,816 / 10,033)** |
| 2011 | 29,996 | 28,630 | 1,366 (866 / 500) |
| 2013 | 31,646 | 32,262 | −616 |
| 2018 | 34,127 | 28,949 | 5,178 (2,574 / 2,604) |
| 2019 | 29,347 | 27,609 | 1,738 (−77 / 1,815) |
| 2022 | 31,190 | 31,583 | −393 |
| 2023 | 21,294 | 21,290 | 4 (1 / 3) |

(The full table is the output of the script.) Observations, with their state:

1. **2010 was published.** The inventory has 25,849 documents dated 2010, 15,816 EP translations and 10,033 others, in line with neighbouring years. The corpus has none. The gap is therefore in the bibliographic files that the OpenData portal distributes, not in the OEPM's publications (**verified** as a count; the cause of the missing files is **pending**, and the inventory is the OEPM's own, so it is not an independent source).
2. **National documents are under-covered in 2000–2009.** The inventory has 101,795 non-`T` documents in those ten years; the corpus has 73,744, so 28,051 (about 28 %) are missing, every year between 2,259 and 3,399. `T` documents differ by 4–77 a year. The cause is **pending**. It matters because the development origins 2003 and 2006 have a history in which about a quarter of the national documents are absent (**inferred**).
3. **Other years differ too.** 2017–2019 are over 1,300 documents short in the corpus (2018: 5,178, half `T`), and 2011 by 1,366, mostly `T`. In 2013, 2014 and 2022 the corpus has more records than the inventory (−616, −353, −393); the corpus counts repeated records, which the inventory does not (**inferred**, not checked).
4. **The 2023 drop of EP translations is in the inventory** (14,847 against 24,626 in 2022 and 27,712 in 2024): it is not a missing-file effect of the OpenData portal. Its cause remains unknown.
5. Exception codes in 2000–2025: `X` (bibliographic data only in the Official Gazette) on 65,669 entries and none for paper or missing documents; the rest carry no exception. The net difference between the inventory (774,552 entries dated 2000–2025) and the corpus (711,547 records) is 63,005 documents, of which 2010 accounts for 25,849; whether the rest overlaps with the `X` entries is **pending**.
6. Application numbers in the inventory carry a letter prefix (`P`, `U`) followed by the digits, for example `U200502626`, whereas the bibliographic record states the digits and the kind separately. The inventory is therefore the natural bridge to normalise the application key (**inferred**; the mapping is not built or tested here).

## 6. What this suggests for ADR 0036 (nothing is changed here)

* **A6 and the 2010 gap.** The ADR already treats 2010 as missing, not zero; the inventory confirms that documents exist. The hidden-year estimate stays a counterfactual and is not replaced by this count.
* **A new limitation (C3).** The corpus omits roughly a quarter of the national documents of 2000–2009 and some documents of 2011 and 2017–2019. The ADR lists limitations of the corpus but not this one. It should be added and its effect on the development origins assessed before the pre-registration closes.
* **P6.** The 2023 drop is a property of the OEPM's publications, not of the download.
* **O3** is not affected.
* **Recovery of 2010 (hypothesis, not tested).** The cited-documents-and-ECLA files cover 1993–2013 and carry IPC and ECLA codes for the documents with a search report, keyed by application. The 2010 quarters might give IPC for part of the missing year. This has not been read.

## 7. Candidates for a test of ingestion

| Dataset | What it would add | Main risk | Suggested first test |
|---|---|---|---|
| Authority File (done) | A denominator for coverage and the application–publication bridge | Inventory of the same office, no content | Use it to explain the corpus' gaps (§5) |
| Cited documents and ECLA 2010 | IPC for part of 2010; finer classification before 2013 | Only documents with a search report; ECLA is another scheme | Read the 2010 quarters, count documents and IPC |
| Abstracts | Text for human review of candidates and a content level | No publication date; encoding defects seen in the ECLA sample | Link a year to the corpus by number and kind |
| Legal status | Survival of patents | Keyed by application; starts in 2010 | Only after the application bridge exists |
| CPC and citations | Finer classification and citation links | Start in 2013, so no development origins; hang off `R1` documents in the example | Check on one year whether the key reaches the A/B publications |
| Full text, booklets | Content | Full text pre-2019 is proprietary; the real size is unknown | None until a size is known |

## 8. Pending

* Sizes of full text and booklets; contents of the `*Feed.xml` files.
* Cause of the missing 2010 files, of the national under-coverage of 2000–2009 and of the 2017–2019 differences.
* Whether the missing documents are the `X` entries of the inventory.
* The SOAP service terms and fields (an access form is needed).
* Anything about patent families: no dataset lists them.
