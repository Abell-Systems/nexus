# Third-party files tracked in the public repository: D1 inventory

Follows ADR 0037 gate 5 (PR #159), decision D1, adopted provisionally on 2026-10-22. Operational measure, not a legal conclusion. **History is not rewritten**: replacing a file in the working tree leaves it in existing commits, forks and clones; that decision is separate and still open.

| Path | Status after this PR | Next step |
|---|---|---|
| `backend/test/fixtures/innoget_*` | **Replaced** by `innoget_synthetic_us_call.html` and `innoget_synthetic_spanish_call.html`: invented content with the markup the extractor reads, ids 900001/900002, marked synthetic in the file. The real page (which carried Innoget's copyright notice and a third-party reCAPTCHA key) and the small Spanish page are no longer in the tree; the now-unneeded gitleaks allowlist for that key is removed | None; still in history |
| `backend/test/fixtures/lombardia_sample_*.html` (3) | Unchanged, **pending review**. The tests assert on real titles, POD references and text | Decide per file: ask Open Innovation Lombardia, or synthesise as for Innoget |
| `backend/test/fixtures/epo_ops_*.xml`, `oepm_bopi_sample.xml` | Unchanged, **pending review**. Small samples; whether they are real records or hand-written was not checked | Compare against the sources; replace if real |
| `data/snapshots/patents_es_corpus.*`, `patents_es_manifest.json` | Unchanged, **pending review** (OEPM terms: attribution, no denaturing, date of update) | Check the OEPM conditions against the files |
| `experiments/wpi-demand-patent-matching/data/`: the 6 JSON files with demand text (`dataset_phase2_demand_corpus_n39.json`, `.origin_audit.json`, `dataset_phase2_eligible_corpus_n24_v1.json`, `dataset_phase2_organization_audited_corpus_v1.json`, `phase2_demand_construct_eligibility_n39_v1.json`, `sector_assignments_n24_v1.json`) | **Retired from the tree** (still in history, forks, clones and backups). Identity recorded in `data/RETIRED_FILES.json` (name, bytes, sha256; checked equal to the committed sidecars; not recomputed). Sidecars, manifests and the files without demand text stay | Restricted copy only with a documented basis to hold it (open) |
| `checks/generate_construct_eligibility_audit.py`, `generate_sector_assignments.py` | **Migrated.** The 63 verbatim `evidence` quotes moved to an external `evidence_quotes.json` (restricted); the scripts keep a `None` placeholder and fill it at run time, failing if a quote is missing. Regenerated artefacts are byte-identical to the originals (all files of the data directory compared) | None |
| The other 15 scripts of `checks/` (`generate_*`, `check_*`) and `config/devtest_split_*` | **Migrated** to `restricted_inputs.data_dir()` (`WPI_DATA_DIR`, default `restricted/data/`, git-ignored). They stop with an explicit message when the original corpus is absent. Their identities (organisation names, ids, counts, frozen hashes) tie them to the original study | None |
| `scripts/build_demands_snapshot.py`, `extract_operational_texts.py`, `freeze_phase2_demand_corpus.py`, `experiments/operational-dense-probe/build_probe_sheets.py` | **Migrated**: they require the restricted corpus and stop with a clear message instead of building a different snapshot. With the restricted corpus `build_demands_snapshot.py` reproduces the existing snapshot byte for byte; `freeze_phase2_demand_corpus.py` now writes to the restricted directory | None |
| `experiments/wpi-demand-patent-matching/synthetic/` | **New**: deterministic invented corpus (37 + 2 records, `synthetic_control`), README stating it is not the study's data | None |
| `docs/validation/validation_sheet_v1.csv` | **Titles removed** (`demand_title` empty; checked equal to the full sheet minus that column). `scripts/build_validation_sheet.py --without-titles` regenerates it; the full sheet is generated without the flag and delivered to validators privately. `docs/validation/README.md` and `docs/deploy.md` updated | None |
| `docs/phase2-demand-construct-eligibility-audit-protocol.md` | One quoted Innoget title replaced by a pointer; the rest of the protocol is unchanged | None |
| `data/annotations/*`, `data/experiments/*`, `docs/*` audit documents | **Reviewed by whole-repository content search on 2026-10-23**: they contain demand ids (`INNOGET-n`), patent text (OEPM/Google Patents) and, in places, requesting-organisation names, but **no Innoget title or description text**. Left unchanged | Owner decision: keep ids and organisation names as traceability (proposal), or neutralise them. Not decided |
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

## Dependencies of the 39-demand corpus (migration status in the table above) (read-only analysis, 2026-10-22)

Retiring these files is not a plain deletion. What references them:

* **Pipeline of hash-verified checks** in `experiments/wpi-demand-patent-matching/checks/` (17 scripts: `generate_*` and `check_*`) and the `config/devtest_split_v*.json` and `*.manifest.json` files, which anchor to the corpus files by name and hash. None of these runs in CI (`ci.yml` runs `backend/test` and `scripts/check_architecture.py`), so removal would not turn CI red; it would silently break the ability to re-run the checks.
* **Protocols and ADRs** citing the files and their hashes: ADR 0019, 0020, 0026, 0029, 0030 and the `docs/phase2-*` protocols, `docs/empirical-study-protocol.md`, `docs/roadmap.md`. These must keep describing what existed; the records should not be rewritten as if the files had never been there.
* **Operational MVP builders** that read the corpus: `scripts/build_demands_snapshot.py`, `scripts/extract_operational_texts.py`, `scripts/freeze_phase2_demand_corpus.py` and `experiments/operational-dense-probe/build_probe_sheets.py`. They produce the git-ignored operational snapshot, so the operational corpus cannot be rebuilt from a clean checkout once the file is gone.
* `backend/test/unit/application/test_demand_independence.py` names a file only in a docstring; it does not read it.

## Separation (adopted provisionally by the owner on 2026-10-22; implemented in the PR that follows #160)

1. **Public artefact:** a synthetic demand set with the same schema, enough to run the software tests and the check scripts' logic.
2. **Scientific record:** methodology, schema, code version, transformations and the hashes already documented, without the protected text. The hashes of the retired files stay recorded as the identity of what was used, not as files that exist in the tree.
3. **Restricted corpus:** only with a documented basis for access and retention; moving it to a private server does not by itself settle the right to use it.
4. The retirement is **not** a deletion: it stays in history, forks, clones and backups. Rewriting history is a separate decision.
5. The 2 Lombardia demands need their own request; the Innoget permission does not cover them.

## Three levels of reproducibility, kept apart

1. **The code runs:** the synthetic set passes the generic conformance check (`check_demand_corpus.py`) and feeds `build_demands_snapshot.py`. Nothing computed on it reproduces or supports a result of the study.
2. **The identity of the original files:** `data/RETIRED_FILES.json`, with the hashes already documented, unchanged; ADRs and protocols keep describing the corpus that was used.
3. **The original study:** needs the restricted original corpus. Not available from the public tree, and a restricted copy needs a documented basis, not just a different location. The 2 Open Innovation Lombardia demands are a separate authorisation from Innoget's.

## Known limits of this change

* A pre-existing failure, not caused by this change: `check_construct_eligibility.py` asserts that `protocol-reference.json`'s protocol hash is current and it is stale (recorded `160c585d…`, actual `fbf5a077…`); it fails the same on `main`.
* The synthetic set exercises one generic check; the others assert original identities by design.
* A guard test fingerprints the first 60 normalised characters of each original description and recorded quote (hashes only, no text) and scans tracked files of the experiment, `scripts/` and the dense-probe directory. It would not catch a paraphrase, a quote not among those fingerprinted, or text split across string literals.
* The judging and escalation sheets of `experiments/operational-dense-probe/outputs/` contain demand text but are git-ignored, so they are not in the public tree.
* Annotation sheets, the validation sheet, `judgments-A.json` and the derived reports are unchanged (separate reviews).
* The local `restricted/` directory (git-ignored) holds the original data on this machine; that is a working copy, not an authorisation.

## Continuous check and where restricted data may live

* CI runs `pytest experiments/wpi-demand-patent-matching/checks/check_restricted_separation.py` after the unit tests (job "Unit Tests"). It verifies that the **versioned tree** of the experiment, `scripts/` and the dense-probe directory contains none of the fingerprinted original text, that the scripts stop when the corpus is absent, and that the synthetic set is deterministic. It does not inspect git history, forks, clones or backups, and does not detect paraphrase, text split across literals or quotes not among the fingerprints. A docs-only change skips CI (`paths-ignore`), which is fine here: the guard scans code and data paths.
* `.gitignore` covers only the default location `experiments/wpi-demand-patent-matching/restricted/`. A restricted copy placed elsewhere through `WPI_DATA_DIR` is protected only if that location is outside the repository or ignored; the guard would flag a copy of the original text if it were committed in the scanned paths, not elsewhere in the repository.
* The auditors' own `rationale` and `primary_technical_object` texts remain in the generator scripts. They are not assumed free of third-party content nor treated as protected; they are reviewed with the annotation sheets and derived reports.

## Whole-repository content search (2026-10-23, before this change)

All tracked text files were searched for the normalised full title (25+ characters) and the first 60 characters of the description of each of the 39 demands. Results: Innoget titles in `docs/validation/validation_sheet_v1.csv` (21) and in one protocol example (1); Lombardia title and description in the 2 Lombardia fixtures and in their unit test (pending a separate authorisation); no Innoget description text anywhere. The guard test now also fingerprints the first 25 normalised characters of the 37 Innoget titles and scans `docs/validation`, the construct-eligibility protocol, `data/annotations` and `data/experiments`. Same limits: exact match only, tracked files only, not the git history.

## Demand ids and requesting-organisation names: provisional decision and review

Provisional decision recorded 2026-10-23, as two separate decisions:

* **Demand ids (`INNOGET-n`): keep.** They link annotations, judgments and results without bringing the Innoget text back. Being an identifier rather than literal text does not by itself make it harmless; it is kept because the scientific traceability needs it, and the decision can be revisited.
* **Requesting-organisation names: pending a specific review; not approved for keeping.**

What the search found (names taken from the organisation-audit files; 15 distinct strings, some are not organisations):

* About 30 tracked files carry at least one of them: `docs/adr/0029` and `0030`, `docs/phase2-demand-independence-audit-protocol.md`, `docs/empirical-study-protocol.md`, `docs/roadmap.md`, `docs/data_provenance.md`, `docs/superpowers/` plans and specs, `experiments/wpi-demand-patent-matching/` scripts and data, and `backend/test` (also `data/raw` and `data/snapshots` for one common name, Repsol, which may be unrelated).
* **Personal given names appear with an employer** in the display strings `Alberto from Pharmactive Biotech Products` and `Indira from Bax&Co`: in `backend/src/main/domain/models/annotation.py` (a docstring), `backend/test/unit/application/test_demand_independence.py`, ADR 0029, the independence-audit protocol and the plans. These are the most sensitive and the least necessary.
* Analytic value: the exact strings are the data of the independence audit (ADR 0029 relies on exact string equality, and its argument against fuzzy matching uses the `Bax & Company` / `Indira from Bax&Co` pair). In the test and the docstring they are only examples.

Proposal for the owner (not applied): (1) replace the two personal-name strings in `annotation.py` and the unit test by synthetic names with the same shape, which keeps the behaviour; (2) keep the company names in ADRs and protocols as the historical record of what the audit used, until the review decides; (3) decide the retained scope of names in `experiments/` data after (1)-(2). The guard does not cover names; it would need its own fingerprints once the scope is decided.
