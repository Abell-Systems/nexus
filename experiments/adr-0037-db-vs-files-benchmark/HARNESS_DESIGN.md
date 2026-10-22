# Benchmark harness: design and state

**State: skeleton, blocked.** Execution is blocked until the protocol PR (#155) is merged and a person creates `AUTHORISATION.json`; this branch is separate from the protocol so that the protocol was fixed before the execution code existed. The stores, comparisons, recorder and the authorisation barrier exist and are tested on synthetic data. The orchestration of workloads W1–W7 is **not written** and no measurement has been run. `PREREGISTRATION.md` (with revision R1) remains the methodological authority; this file only describes how the code serves it and must not be read as protocol.

## Layout

| File | Role |
|---|---|
| `harness/tables.py` | The `biblio_v1` tables defined once; `rows_from_outcomes` builds the **same rows** for A and B from the adapter's output |
| `harness/contract.py` | The `Store` protocol (prepare, verify, read_records, alter, backup, restore, drop, size, configuration), `IntegrityError`, exit codes, and `analysis_record` (one construction for both stores) |
| `harness/store_pg.py` | A: PostgreSQL, one schema per version (`<namespace>_<version>`), per-table canonical digest in a `manifest` table, foreign keys, `COLLATE "C"` in the contractual query |
| `harness/store_files.py` | B: one Parquet per table (zstd, sorted by key, fixed row group), `manifest.json` with per-file sha256, DuckDB views, binary collation checked on connect |
| `harness/compare.py` | Canonical JSON, pairs, records (field by field, in order), load checks. Refuses missing, empty or different-length inputs (`IncompleteComparison`) |
| `harness/recorder.py` | Timing entries tagged with workload, alternative, `prepare`/`execute`, `first_run_after_start`/`warm`, repetition and order; nested sections are refused; materiality rule of §5 |
| `harness/guard.py` | Barrier: `AUTHORISATION.json` must exist, name who authorised and the protocol's merge commit, and carry the sha256 of the current `PREREGISTRATION.md` |
| `run_benchmark.py` | Entry point; exits 2 (refused) without authorisation; workloads not implemented |

Exit codes: 0 all acceptance checks passed; 1 a check failed; 2 refused; 3 environment incident (nothing graded).

## How the harness protects the comparison

* **Same input, same code.** Both stores receive identical rows and produce `AnalysisRecord`s through the same function; only the storage engine differs. Reports run the unchanged `subclass_pairs`.
* **Isolation.** A uses its own schema namespace; B its own directory. Each version is immutable: `prepare` refuses to overwrite, a version is published only when complete (A in one transaction, B by renaming a staging directory), alterations touch a stored copy and never the shared rows, and restores never overwrite.
* **Preparation versus execution.** The recorder tags every section; conversion to Parquet, loading PostgreSQL and creating each manifest are `prepare`; parsing the zips is outside both alternatives and is not recorded as either.
* **Detection must be explicit.** `verify` raises `IntegrityError`; a warning that lets a run continue is not a detection.
* **No silent equivalence.** Comparisons raise instead of returning "equal" when a side is incomplete.
* **Configuration captured.** `configuration()` records engine versions and parameters that can affect results (A: server version, shared_buffers, work_mem, parallel workers, effective_cache_size, database collation; B: DuckDB and pyarrow versions, compression, row-group size, sorting, collation).

## Asymmetries and how they are handled

1. **Referential constraints.** A enforces foreign keys in the database. B now calls `check_references` on the same rows at `prepare`, raising the same `ReferentialError`; both stores refuse the same orphan rows (tested) and nothing is published when they do. Its cost sits in B's preparation, and the engines still differ in *how* they check (database constraint versus a Python pass over the rows), so preparation times are reported with that caveat and not read as engine-only costs.
2. **Parquet determinism.** Tested: preparing the same rows twice gives identical manifests on this machine and library version. If that ever fails, `logical_digest` (below) tells a serialisation difference from a corpus change.
3. **Content equivalence versus integrity.** `logical_digest` reads the stored rows back and digests them in a canonical form (rows sorted in Python by primary key, canonical JSON), independent of collation, physical order and file bytes; it is what A and B are compared on, and it must equal the digest of the source rows. `verify()` keeps each store's own integrity control (A: manifest digest of the rows; B: file hashes), reported separately. Test (iv), a physical reorder, is expected not to be flagged by A and to be flagged by B; it is reported, not graded.
4. **A's backup and restore** run `pg_dump`/`pg_restore` through `docker exec` in the spike container; restore recreates the dumped schema name, so W6 drops the version first (as pre-registered).
5. `swap_rows` for A is exercised only through the pre-registered reporting, not asserted in the synthetic tests.

## Tests (correctness of the harness, not of the engines)

`tests/` on synthetic data: equal and different records and pairs, refusal of incomplete comparisons, timing and phase tags, nesting refusal, materiality rule, authorisation barrier, and both stores (prepare, verify, order of mixed-case symbols, counts, alterations detected before reading, immutability, previous version intact, backup/restore, no overwrite, equal logical content, orphan rows refused, Parquet determinism). The PostgreSQL variants run only when `NEXUS_BENCH_PG_DSN` is set. Run: `NEXUS_BENCH_PG_DSN=... python -m pytest experiments/adr-0037-db-vs-files-benchmark/tests`.

## Not yet written

Orchestration of W1–W7 (alternation of A/B, first runs in fresh sessions, repetitions), W7 operational retrieval, output collection into `RESULTS.md`, and the real-data run. They follow the review of the protocol PR.
