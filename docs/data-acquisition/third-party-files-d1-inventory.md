# Third-party files tracked in the public repository: D1 inventory

Follows ADR 0037 gate 5 (PR #159), decision D1, adopted provisionally on 2026-10-22. Operational measure, not a legal conclusion. **History is not rewritten**: replacing a file in the working tree leaves it in existing commits, forks and clones; that decision is separate and still open.

| Path | Status after this PR | Next step |
|---|---|---|
| `backend/test/fixtures/innoget_*` | **Replaced** by `innoget_synthetic_us_call.html` and `innoget_synthetic_spanish_call.html`: invented content with the markup the extractor reads, ids 900001/900002, marked synthetic in the file. The real page (which carried Innoget's copyright notice and a third-party reCAPTCHA key) and the small Spanish page are no longer in the tree; the now-unneeded gitleaks allowlist for that key is removed | None; still in history |
| `backend/test/fixtures/lombardia_sample_*.html` (3) | Unchanged, **pending review**. The tests assert on real titles, POD references and text | Decide per file: ask Open Innovation Lombardia, or synthesise as for Innoget |
| `backend/test/fixtures/epo_ops_*.xml`, `oepm_bopi_sample.xml` | Unchanged, **pending review**. Small samples; whether they are real records or hand-written was not checked | Compare against the sources; replace if real |
| `data/snapshots/patents_es_corpus.*`, `patents_es_manifest.json` | Unchanged, **pending review** (OEPM terms: attribution, no denaturing, date of update) | Check the OEPM conditions against the files |
| `experiments/wpi-demand-patent-matching/data/`: `dataset_phase2_demand_corpus_n39.json` (62 KB) and `.origin_audit.json`, `dataset_phase2_eligible_corpus_n24_v1.json`, `dataset_phase2_organization_audited_corpus_v1.json`, `phase2_demand_construct_eligibility_n39_v1.json`, `sector_assignments_n24_v1.json` | **The largest exposure found.** Full title and description (about 500 characters each) of the 39 demands (37 Innoget, 2 Open Innovation Lombardia), with source URL and extraction timestamp, all dated 2026-09-07. Found by content search (first 70 characters of each description), not by name. Unchanged, **pending decision** | Owner decision with D2; frozen study inputs, so any change must keep their hashes and the study's reproducibility in view |
| `experiments/wpi-demand-patent-matching/checks/generate_construct_eligibility_audit.py`, `generate_sector_assignments.py` | Contain demand description text in the script (6 and 7 matching lines). Unchanged, **pending decision** | As above |
| `data/annotations/pilot_strict_annotation_*.csv`, `judgments-A.json`, `docs/validation/validation_sheet_v1.csv` | Unchanged, **pending decision**. Demand ids and titles (21 distinct titles of 25+ characters in the validation sheet) with patent text | Owner decision with D2: research data, not test fixtures |
| `data/experiments/*run_report*.json`, `dataset_identity_audit.json`, ADR 0029, `docs/data_provenance.md`, `docs/empirical-study-protocol.md`, `docs/phase2-*` and other documents naming organisations | Unchanged, **pending review**. Mention demand ids, titles and organisation names; whether any quotes description text beyond a title was not checked line by line | Review together with the rows above |
| `data/external/wipo_schmoch_2008_ipc_technology_concordance.pdf` | Unchanged, **pending review** | WIPO terms are still unread |
| `experiments/article/minesoft_*` (31 files), `exports/*.xlsx` | Unchanged, **pending review** | Minesoft terms are still unread |

## Search performed (2026-10-22)

`git grep -F` over tracked files with (a) the 21 distinct demand titles of 25+ characters from `docs/validation/validation_sheet_v1.csv`, (b) the first 70 characters of each of the 39 demand descriptions, (c) the text of the removed fixtures and the organisation names `INDUSAC` and `Procter`. Titles appear in 11 tracked files; description text in the 8 files listed above plus the two Lombardia fixtures. `docs/superpowers/` plans and specs matched only on names and ids (listed under "documents naming organisations"); no description text was found there. **Limits:** exact-string matching; a paraphrased or truncated quote beyond 70 characters, or a description not among the 39, would not be found.

## Verification of this change

* `pytest backend/test/unit/application/ingestion`: 81 passed, the same count as `main`. The Innoget tests assert the synthetic values, so they read the new files.
* The new fixtures contain none of the previous organisation names, call text or Innoget's copyright line.
* The content search above was run and its result recorded.
* Docs correctness gate passes.
* No change to the harness, the protocol, the infrastructure or ADR 0037.
