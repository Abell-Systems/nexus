# Benchmark harness: design and state

**State: orchestration written and tested on synthetic data; never run on the real corpus; blocked.** The protocol (R1 in #155 and R2 in #157, both merged; sha256 in force `e443232d…c23b`) is the methodological authority; this file only describes how the code serves it and must not be read as protocol. Execution stays blocked until a person creates `AUTHORISATION.json` naming that hash and the merge commit, after the review of this branch. No measurement has been run.

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
| `harness/workloads.py`, `harness/operational.py`, `harness/session.py` | Orchestration of W1–W7, roll-up, valid-run gate (see below) |
| `run_benchmark.py` | Entry point; exits 2 (refused) without authorisation; then runs the session |

Exit codes: 0 all acceptance checks passed; 1 a check failed; 2 refused; 3 environment incident (nothing graded).

## How the harness protects the comparison

* **Same input, same code.** Both stores receive identical rows and produce `AnalysisRecord`s through the same function; only the storage engine differs. Reports run the unchanged `subclass_pairs`.
* **Isolation.** A uses its own schema namespace; B its own directory. Each version is immutable: `prepare` refuses to overwrite, a version is published only when complete (A in one transaction, B by renaming a staging directory), alterations touch a stored copy and never the shared rows, and restores never overwrite.
* **Preparation versus execution.** The recorder tags every section; conversion to Parquet, loading PostgreSQL and creating each manifest are `prepare`; parsing the zips is outside both alternatives and is not recorded as either.
* **Detection must be explicit.** `verify` raises `IntegrityError`; a warning that lets a run continue is not a detection.
* **No silent equivalence.** Comparisons raise instead of returning "equal" when a side is incomplete.
* **Configuration captured.** `configuration()` records engine versions and parameters that can affect results (A: server version, shared_buffers, work_mem, parallel workers, effective_cache_size, database collation; B: DuckDB and pyarrow versions, compression, row-group size, sorting, collation).

## Asymmetries and how they are handled

1. **Constraints of the compared schema.** The comparison covers: primary keys, the extra unique set `source_record(file_id, archive_path)`, the allowed values of `party.role`, and the foreign keys of `tables.py`. A enforces them in the database; B runs `check_constraints` on the same rows at `prepare`; both raise `ConstraintError` (`ReferentialError` for references), refuse the same rows (tested) and publish nothing. **Not** part of the comparison: NOT NULL, column types beyond Arrow/PostgreSQL typing, the generated `doc_id` column and the indexes of the ADR schema (A creates two indexes, B none), and any constraint of `operational_v1`. Equal rows are therefore not equal schema guarantees; the results state this. Its cost sits in B's preparation, and the engines still differ in *how* they check (database constraint versus a Python pass over the rows), so preparation times are reported with that caveat and not read as engine-only costs.
2. **Parquet determinism.** Tested: preparing the same rows twice gives identical manifests on this machine and library version. If that ever fails, `logical_digest` (below) tells a serialisation difference from a corpus change.
3. **Content equivalence versus integrity.** `logical_digest` reads the stored rows back and digests them in a canonical form (rows sorted in Python by primary key, canonical JSON), independent of collation, physical order and file bytes; it is what A and B are compared on, and it must equal the digest of the source rows. `verify()` keeps each store's own integrity control (A: manifest digest of the rows; B: file hashes), reported separately. Test (iv), a physical reorder, is expected not to be flagged by A and to be flagged by B; it is reported, not graded.
4. **A's backup and restore** run `pg_dump`/`pg_restore` through `docker exec` in the spike container; restore recreates the dumped schema name, so W6 drops the version first (as pre-registered).
5. `swap_rows` for A is exercised only through the pre-registered reporting, not asserted in the synthetic tests.

## Tests (correctness of the harness, not of the engines)

`tests/` on synthetic data: equal and different records and pairs, refusal of incomplete comparisons, timing and phase tags, nesting refusal, materiality rule, authorisation barrier, and both stores (prepare, verify, order of mixed-case symbols, counts, alterations detected before reading, immutability, previous version intact, backup/restore, no overwrite with `FileExistsError` specifically and the existing version still verifying, equal logical content, orphan, duplicate-key, unique and allowed-value violations refused, Parquet determinism). The PostgreSQL variants run only when `NEXUS_BENCH_PG_DSN` is set. Run: `NEXUS_BENCH_PG_DSN=... python -m pytest experiments/adr-0037-db-vs-files-benchmark/tests`.

## Orchestration (written after R2 was merged)

`harness/workloads.py` implements W1–W6 and the roll-up (`evaluate`) exactly as `WORKLOAD_CONTRACTS.md`: status by exception type (`ok` / `check_failed` / `incident`), `first_run_after_start` then 5 warm runs alternating A/B, the valid-run gate (`session.wait_for_quiet`, load <= 1.0, up to 5 minutes, else incident), W4's four alterations, W5's rebuild with the previous version preserved, W6a (restore to a new location: `Store.restore_new`, a new database for A and a new directory for B) and W6b (drop and restore in place; a failure after the drop is a check failure). `harness/operational.py` implements W7 (pooled 780 observations, p95 by Python's default quantile method, per-demand diagnostics, ids and order graded). `run_benchmark.py` wires them after the authorisation barrier.

Tests on synthetic data (the count changes with each review; run the suite, do not trust a number written here; the PostgreSQL variants are skipped, and reported as skipped by pytest, when `NEXUS_BENCH_PG_DSN` is not set): full BIBLIO sessions for each store, the incident and check-failure rules, the load gate, alternation, C3 on the maximum, the roll-up and exit codes, pgvector against an exact numpy formula. They show the code follows the contracts; they say nothing about real results.

## Not yet done

* No run on the real corpus; the real-context builders (`run_benchmark.build_real_context`, `operational.build_real_operational`) are untested because the barrier stops them.
* The 'separate fresh sessions' measurement of initial performance is run by invoking `run_benchmark.py --only A` and `--only B` separately; nothing compares them automatically.
* `RESULTS.md` is written by a person from `raw.jsonl`, `summary.json`, `timings.json` and `environment.json`, with the operational section of the protocol (§6).

## Destructive operations: audit (verifiable rule)

Rule 0 (how ownership is established): never by 'check, then create' (a race can land between the two); always by an atomic exclusive creation (`os.mkdir`, `open("xb")`, `CREATE SCHEMA`, `CREATE DATABASE`) whose failure means the name was already taken and leaves it untouched. Early `exists`/`_exists` checks exist only to give a friendlier error; correctness never rests on them. Cleanup acts only on what the failing call itself created, and a claimed directory is released with `os.rmdir`, which refuses to remove anything another process put there. Rule 1: no pre-existing resource is modified or deleted because a run failed to create it. Rule 2: an operation that fails midway removes what *it* created and nothing else, so a failure leaves no partial artifact that blocks the next attempt (`prepare`, `restore`, `restore_new`, `backup`, `PgRetriever` construction). Every destructive call in `harness/` and `run_benchmark.py`, and why it is allowed (re-check with `grep -n "rmtree\|unlink\|rename\|DROP \|write_text\|write_bytes\|open(.*\"[wx]" harness/*.py run_benchmark.py`):

| Call | Operates on | Why it is safe |
|---|---|---|
| `FilesStore` `_atomic_publish` (prepare, backup, restore) | destination and `<destination>.staging` | `os.mkdir` claims each name atomically; a taken name raises `FileExistsError` and is untouched; the staging directory is filled and `os.rename`d over our own empty claim; on failure only our staging is removed and the claim via `os.rmdir` (refuses a non-empty directory) |
| `FilesStore.restore_new` | `<root>_restored_new` | `os.mkdir` is the atomic claim; on failure the claim is released with `os.rmdir`; `dispose` removes it only if this object created it |
| `FilesStore.drop`, `PostgresStore.drop` | a version | called by the orchestration only for versions in `Context.created`, or by W6b after it prepared that version itself |
| `FilesStore.alter`, `PostgresStore.alter` | a version | called only on a version this run prepared for W4 |
| `FilesStore.remove_leftover_staging`, `PostgresStore.remove_leftover_database`, `PgRetriever.remove_leftover_schema` | named leftovers | explicit, return the name, never called by the harness itself |
| `PostgresStore.prepare` | schema `<ns>_<version>` | one transaction whose `CREATE SCHEMA` is the claim; a lost race raises `FileExistsError` and only our transaction rolls back |
| `PostgresStore.backup` | destination file | opened exclusively (`"xb"`): an existing file is refused untouched; a partial file created by this call is unlinked if `pg_dump` fails, so the next attempt is not blocked |
| `PostgresStore.restore_new` | database `<ns>_restored_new` | `CREATE DATABASE` is the atomic claim (a lost race raises `FileExistsError`, nothing dropped); drops only the one it created, when its own `pg_restore` fails |
| `PgRetriever` | schema `<ns>_operational_v1` | `CREATE SCHEMA` is the atomic claim (a lost race raises `FileExistsError` and `_created` stays false); `close` drops it only if this object created it |
| `run_benchmark.py` result files | `--work-dir` | refuses a non-empty directory, so earlier results are never overwritten |

The race regressions are deterministic (`tests/test_races.py`): a racer creates the destination, with a sentinel file, at the first moment the code touches its path, and the tests assert the sentinel survives. The same tests fail against the previous 'check, then create' implementation (commit `bde407d`), which is how they were validated.
