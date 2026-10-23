# Inventory of the third-party samples tracked in the public repository: EPO OPS, OEPM, WIPO, Minesoft

Follows `third-party-files-d1-inventory.md` (ADR 0037 gate 5, D1). Compiled 2026-10-23. **Facts observed are kept apart from recommendations.** Nothing was removed or modified in this phase. "Terms located" means a text was found and read; it does not mean the conditions were assessed for this use. Not a legal conclusion. The guard test is not extended until the owner decides what stays in the versioned tree.

## 0. Summary

| Source | Files (tracked) | Provenance | Terms | Provisional recommendation |
|---|---|---|---|---|
| EPO OPS | 2 XML fixtures (9 KB) | Not recorded; one of them is written out in a plan document, which points to hand authorship; the other is not verified | **Not located** | Keep pending; confirm authorship with the owner, then label as synthetic |
| OEPM (BOPI sample, pilot "raw" JSON, snapshots) | 1 XML fixture, 1 JSON, 3 snapshot files (about 43 KB) | **Contradictory**: metadata claims an OEPM extraction; the content looks constructed | OEPM legal notice located and read (2026-10-22); not applied to these files | **Pending provenance confirmation**; if constructed, relabel as synthetic and correct the metadata |
| WIPO | 1 PDF (113 KB) + a transcribed register | Well recorded (author, title, URL, hash) | WIPO terms located (Open Access Policy, CC BY 4.0 for "new" online publications); not applied to this 2008 report | Keep provisionally; read the report's own rights statement; attribute |
| Minesoft | 34 CSV files (1.9 MB) in four folders, 7 XLSX exports (0.7 MB), `lookup_results.json`, logs, figures, 3 manuscripts; `experiments/article/` as a whole has 82 tracked files (7.8 MB) | Well recorded (Origin Patent API through MCP, 2026-09-14) | A general subscription agreement located and read; **its storage and redistribution clauses are restrictive**; not confirmed that it governs this service or who the customer is | **Highest priority**: pending; candidate for the restricted corpus |

Also found while searching: `docs/data_provenance.md` lists Innoget call titles with "technical requirements" for calls #2292, #2293, #2297 and #2245. The title given for #2297 differs from the one in the frozen corpus, so the passage is either an earlier version or not the platform's text. Not verified; added to the pending list.

## 1. EPO OPS

| | |
|---|---|
| Files | `backend/test/fixtures/epo_ops_sample.xml` (4,751 B, added 2026-09-03, commit `a447ba9`), `epo_ops_multi_jurisdiction_sample.xml` (4,295 B, added 2026-09-08, commit `99fbaa5`) |
| Provenance | No source URL, query date or retrieval method is recorded for either. The query echoed in `epo_ops_sample.xml` is `pn=ES and pd within '2016 2024'` and elapsed-time 45. The multi-jurisdiction file appears verbatim inside `docs/superpowers/plans/2026-09-08-patent-corpus-ops-ingestion.md` as the content of a "Create the multi-jurisdiction fixture" step |
| Content | OPS-format XML: 3 documents (Spanish detergent titles, applicant and inventors) and 7 documents of generic English titles ("Heat exchanger assembly", "Battery management circuit", and so on) for EP, US, JP, CN, KR and WO |
| Terms | The EPO OPS page was fetched; the terms or fair-use document was **not found** in the part read (the page is 127,000 characters and the answer covered the first 100,000). **Pending** |
| Use | `test_epo_ops.py` and `test_epo_ops_multi_jurisdiction_normalization.py` (client in fixture mode); `EpoOpsClient.from_fixture_file` |
| Risks and gaps | Authorship not confirmed; whether the Spanish record content reproduces real EPO data is not verified. The same publication number and titles (`ES2849102`, "Formulación detergente enzimática…") appear in the OEPM sample and in the pilot corpus below |
| Recommendation | Ask the owner whether both were written for the tests (the evidence points that way). If so, record them as synthetic and mark the numbers as invented; if not, locate the source and terms. Keep, unchanged, in the meantime |

## 2. OEPM

| | |
|---|---|
| Files | `backend/test/fixtures/oepm_bopi_sample.xml` (4,351 B, 2026-09-03, `582e433`); `data/raw/oepm_open_data_es.json` (18,071 B, 2026-09-03, `a447ba9`); `data/snapshots/patents_es_corpus.parquet` (8,548 B), `.jsonl` (10,307 B), `patents_es_manifest.json` (1,567 B), same commit |
| Provenance as declared | `dataset_metadata` of the JSON: id `OEPM-BOPI-ES-INVENES-SNAPSHOT-2024-V1`, extraction timestamp `2026-08-25T11:08:53Z`, licence "Ley 37/2007 / CC-BY 4.0", catalogue URL on datos.gob.es. The manifest adds: "publication-level source verification pending" |
| Observations against the declaration | (a) The 16 publication numbers of the JSON were searched as exact text in the real BIBLIO files 2000-2025 (26 archives held locally): **0 of 16 found** (limit: exact substring search; a formatting difference was not ruled out). (b) `scripts/build_spanish_patents_snapshot.py` contains a hand-written `SAMPLE_ES_PATENTS` list with the same first record (title, assignee "Laboratorios Bilper S.A."); 1 of the 16 titles appears verbatim there. (c) The BOPI XML has comments such as "Case 1: Standard National Granted Patent (B2)" and "Case 2: European Patent Translation (T3) with Claims fallback", the style of a written test case |
| Content | Title, abstract (or claims fallback), applicant, inventors, classification, dates; 16 records in the JSON and its derived snapshots |
| Terms | OEPM legal notice (`sede.oepm.gob.es/eSede/datos/es/aviso-legal/`), read 2026-10-22, summarised in gate 5 §3. Applicable only if the records are OEPM data |
| Use | Default paths of `oepm_raw_source.py` and `duckdb_patents.py`; `scripts/ingest_oepm_ops.py`; `scripts/audit_dataset_identity.py`; the unit and integration tests of the BOPI normaliser; `data/experiments/dataset_identity_audit.json` |
| Risks and gaps | The metadata asserts an OEPM extraction and an open licence for content that may be constructed: if so, the provenance claim is wrong, which matters more than the rights question. If the records are real, the OEPM conditions (attribution, not distorting the information, update date) are not recorded in the files |
| Recommendation | **Pending provenance confirmation by the owner.** If constructed: relabel as synthetic, correct the manifest and the licence field, and keep. If real: record the extraction method and add the OEPM attribution. Either way, do not cite these files as OEPM data until settled. The real OEPM corpus is the git-ignored BIBLIO set, which is not in this inventory |

## 3. WIPO

| | |
|---|---|
| Files | `data/external/wipo_schmoch_2008_ipc_technology_concordance.pdf` (113,367 B, added 2026-09-25, `a9f2c97`) and its `.sha256`; the register `config/policies/data/wipo_ipc8_technology_concordance_v1.json` transcribed from Table 2 |
| Provenance | Recorded: author U. Schmoch (Fraunhofer ISI), "Concept of a Technology Classification for Country Comparisons - Final Report to the World Intellectual Property Organisation (WIPO)", 2008-06, URL `wipo.int/documents/2948119/3215563/wipo_ipc_technology.pdf`, sha256 `ba61ab9e…ea8a` (recomputed today: matches). The legacy Excel link returned 404 on 2026-09-25 |
| Content | The whole report as PDF; the register is a derived transcription of one table |
| Terms | WIPO Terms of Use, Open Access Policy, read 2026-10-23: new WIPO online publications and other online content are issued under CC BY 4.0 "except for some content published under more restrictive terms"; acknowledgement of WIPO as source and indication of changes; no use of the emblem or implied endorsement; "WIPO retains full copyright ownership"; third-party material excluded. **Not established** whether a 2008 report by an external author is covered; the PDF's own rights statement was not read (no PDF text tool in this environment) |
| Use | The register is used for the technology-sector enrichment; `test_wipo_ipc_technology_concordance_freeze.py` |
| Risks and gaps | Applicability of CC BY 4.0 to this document; the attribution and the "changes made" statement are not visible in the register |
| Recommendation | Keep provisionally. A person reads the first pages of the report for its rights statement; add attribution and a change note to the register's provenance block. Move to the restricted corpus only if the statement is restrictive |

## 4. Minesoft

| | |
|---|---|
| Files | Under `experiments/article/` (82 tracked files, 7.8 MB in all): 34 CSV files in four folders (`minesoft_global_2000_2025_family_jurisdictions` 13 files 865 KB; `minesoft_origin_2000_2025` 13 files 564 KB; `minesoft_spain_2000_2025_classification` 5 files 456 KB; `minesoft_spain_2000_2025_screening` 3 files 24 KB), `exports/A_familias.xlsx` to `G_citas_leader.xlsx` (7 files, 0.7 MB), `lookup_results.json` (44 KB), `query_log.md`, figures, three manuscript `.docx`. Which of the other files hold Minesoft-derived data was not classified one by one |
| Provenance | Recorded in `query_log.md`: Minesoft Origin Patent API through the `minesoft` MCP server, extraction date 2026-09-14, 247 Spanish publication numbers (228 unique), tools `number_lookup` and `bulk_publications`, about 230 calls. Whose account or subscription was used is **not recorded** |
| Content | Family and publication identifiers, titles, family countries, classifications, legal status, assignees and inventors, citations (the exports); the project's own relevance classification with rationale that quotes patent claims (the `classification` folder); figures and manuscript derived from them |
| Terms | Located and read: "UK & International Annual Subscription Terms and Conditions" (Minesoft Ltd, `minesoft.com/wp-content/uploads/2025/06/31.07-UK-TCs-0.pdf`; the file name carries "31.07", the upload folder 2025/06; no explicit version date seen). Clauses: 4.0(b) an "Archive Copy" kept at most 12 months after expiry and not distributed outside the company; 5.0(a)-(b) the customer may not "sell, distribute or commercially exploit" the Product or the Information, with an exception for search results given to a third party under a client relationship, nor make it available on a network; 5.1 electronic copies for use within the customer's premises provided they are not "stored in a database format and made searchable"; "any external redistribution require the prior agreement in writing". **Not established:** that this agreement governs Origin and the API access used; who the customer is; whether an academic or research agreement exists; whether published tabular extracts count as "the Information" |
| Use | The article pipeline (`experiments/article/`), the figures and the manuscript; `audit_minesoft_origin_v0_1.py`; `extraction_contract_v1.json` |
| Risks and gaps | If the located agreement applies, versioning tabular extracts of the Information in a public repository could be an "external redistribution"; that is a hypothesis, not a finding. The classification CSVs mix the project's own judgments with quoted claim text |
| Recommendation | **Highest priority.** Pending: the owner confirms which agreement and which customer apply and whether a research arrangement exists; the contact printed in the agreement is `customerbilling@minesoft.com` (billing, not necessarily the right office for rights). Candidate for the restricted corpus with the same separation pattern as the demand corpus (record of hashes, synthetic or aggregate public artefact). No change until then |

## 4b. Questions open for the repository owner (2026-10-23)

None is answered; no gap is filled by inference, and an unknown provenance is not turned into a statement of authorship.

1. OEPM pilot files: were the 16 records extracted from OEPM, or written for tests? Until answered they are not presented as OEPM data.
2. EPO OPS fixtures: who wrote them, and from what? That one is reproduced in a plan document does not establish authorship.
3. Minesoft: under which subscription or agreement were the data extracted, who is the customer, and is there a research arrangement? Until answered, no new Minesoft extracts are added to the public repository.
4. WIPO: the rights statement inside the report itself has to be read and its attribution recorded; the Open Access Policy alone does not settle it.
5. `docs/data_provenance.md`: the Innoget call titles that differ from the frozen corpus are a provenance discrepancy; no assumption that they are an earlier version.

Order of work: OEPM and EPO provenance first (it bears on the validity of the pilot evidence), then the Minesoft agreement, then the WIPO report.

## 5. Not checked

* The EPO OPS terms document; the OEPM conditions against the actual files; the first pages of the WIPO report; whether the Minesoft agreement governs this service; the git history for earlier versions of these files; the contents of the `.docx` manuscripts beyond their names.
* Any redistribution by forks or clones of the public repository.
