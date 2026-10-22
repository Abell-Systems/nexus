# Benchmark harness: design and state

**State: skeleton.** The stores, comparisons, recorder and the authorisation barrier exist and are tested on synthetic data. The orchestration of workloads W1–W7 is **not written** and no measurement has been run. `PREREGISTRATION.md` (with revision R1) remains the methodological authority; this file only describes how the code serves it and must not be read as protocol.

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

## Known asymmetries (to be reported, not hidden)

1. **Foreign keys** are enforced by A and not by B (`references` in `tables.py`). A's load cost therefore includes constraint checking that B does not do. This reflects the two designs, not an error, and goes into §6.
2. **Parquet determinism:** manifest hashes assume the same writer version on the same input produces the same bytes; the harness does not check that yet (W1 should rebuild once and compare).
3. **A's backup and restore** run `pg_dump`/`pg_restore` through `docker exec` in the spike container; restore recreates the dumped schema name, so W6 drops the version first (as pre-registered).
4. **A's digest** is order-independent (rows ordered by key); B's manifest is byte-based. Test (iv) swaps physical order only: A is expected not to flag it, B to flag it. It is reported, not graded.
5. `swap_rows` for A is checked only through the pre-registered reporting, not asserted in the synthetic tests.

## Tests (correctness of the harness, not of the engines)

`tests/` on synthetic data: equal and different records and pairs, refusal of incomplete comparisons, timing and phase tags, nesting refusal, materiality rule, authorisation barrier, and both stores (prepare, verify, order of mixed-case symbols, counts, alterations detected before reading, immutability, previous version intact, backup/restore, no overwrite). The PostgreSQL variants run only when `NEXUS_BENCH_PG_DSN` is set. Run: `NEXUS_BENCH_PG_DSN=... python -m pytest experiments/adr-0037-db-vs-files-benchmark/tests`.

## Not yet written

Orchestration of W1–W7 (alternation of A/B, first runs in fresh sessions, repetitions), W7 operational retrieval, output collection into `RESULTS.md`, and the real-data run. They follow the review of the protocol PR.
