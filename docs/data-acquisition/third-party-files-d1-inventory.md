# Third-party files tracked in the public repository: D1 inventory

Follows ADR 0037 gate 5 (PR #159), decision D1, adopted provisionally on 2026-10-22. Operational measure, not a legal conclusion. **History is not rewritten**: replacing a file in the working tree leaves it in existing commits, forks and clones; that decision is separate and still open.

| Path | Status after this PR | Next step |
|---|---|---|
| `backend/test/fixtures/innoget_*` | **Replaced** by `innoget_synthetic_us_call.html` and `innoget_synthetic_spanish_call.html`: invented content with the markup the extractor reads, ids 900001/900002, marked synthetic in the file. The real page (which carried Innoget's copyright notice and a third-party reCAPTCHA key) and the small Spanish page are no longer in the tree; the now-unneeded gitleaks allowlist for that key is removed | None; still in history |
| `backend/test/fixtures/lombardia_sample_*.html` (3) | Unchanged, **pending review**. The tests assert on real titles, POD references and text | Decide per file: ask Open Innovation Lombardia, or synthesise as for Innoget |
| `backend/test/fixtures/epo_ops_*.xml`, `oepm_bopi_sample.xml` | Unchanged, **pending review**. Small samples; whether they are real records or hand-written was not checked | Compare against the sources; replace if real |
| `data/snapshots/patents_es_corpus.*`, `patents_es_manifest.json` | Unchanged, **pending review** (OEPM terms: attribution, no denaturing, date of update) | Check the OEPM conditions against the files |
| `data/annotations/pilot_strict_annotation_*.csv`, `judgments-A.json`, `docs/validation/validation_sheet_v1.csv` | Unchanged, **pending decision**. They hold Innoget demand titles, ids and patent text from the study | Owner decision with D2: these are research data, not test fixtures |
| `data/experiments/*run_report*.json`, `dataset_identity_audit.json`, audit documents under `docs/` | Unchanged, **pending review**. Contain demand ids and names derived from Innoget | Review together with the row above |
| `data/external/wipo_schmoch_2008_ipc_technology_concordance.pdf` | Unchanged, **pending review** | WIPO terms are still unread |
| `experiments/article/minesoft_*` (31 files), `exports/*.xlsx` | Unchanged, **pending review** | Minesoft terms are still unread |

Not covered: plans and specs under `docs/superpowers/` that quote Innoget text were not searched beyond the identifiers above.

## Verification of this change

* `pytest backend/test/unit/application/ingestion`: 81 passed, the same count as `main`. The Innoget tests assert the synthetic values, so they read the new files.
* The new fixtures contain none of the previous organisation names, call text or Innoget's copyright line.
* Docs correctness gate passes.
* No change to the harness, the protocol, the infrastructure or ADR 0037.
