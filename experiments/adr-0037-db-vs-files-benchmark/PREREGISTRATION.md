# ADR 0037 gate 1: PostgreSQL versus synchronized files, pre-registration

Written and committed before any measurement. Evidence for gate 1 of [ADR 0037](../../docs/adr/0037-operational-corpus-in-database.md) §5 and §5.1 (database versus a synchronized file). It does not accept the ADR. "Unresolved" and "both viable" are valid outcomes. The ADR stays Proposed.

## 1. Alternatives

**A – PostgreSQL.** The spike's design: PostgreSQL 17 + pgvector (image `pgvector/pgvector:pg17`, digest recorded at run time), the normalised `biblio_v1` and `operational_v1` tables, per-table canonical digest in a manifest table, no vector index, `COLLATE "C"` for contract orderings.

**B – synchronized files.** One concrete implementation, fixed now:
* BIBLIO: the same `biblio_v1` tables written as one Parquet file per table (zstd, rows sorted by primary key), plus `manifest.json` with the sha256 of every file and a manifest hash; queried with DuckDB (`duckdb==1.5.5`, already a backend dependency) using the same SQL as A, with binary (code point) collation verified before use. Synchronization = copy the directory and verify the hashes.
* Operational corpus: the current artifacts (`publications.parquet`, `.npy` matrices, manifests) read with the current `NumpyDenseRetriever`. B changes nothing there; DuckDB similarity is **not** evaluated.

No vector index is used in either alternative. The adapter, the schema, the ST36 fields kept and the numeric parity contract are not changed by this benchmark; A's score policy stays as recorded (P1 strict FAIL, P1b 78/78) and is not re-argued.

## 2. Fixed conditions

* Machine of the spike (4 cores, 11 GB), nothing else running; hardware, OS, kernel, Python, PostgreSQL, DuckDB, pyarrow and image digests recorded in the raw output.
* Shared input: the adapter's output for the 26 files (`OepmBiblioSource`), parsed **once** per process and held in memory; its time (about 177 s) is reported but belongs to neither alternative. Preparation of A and B starts from the same in-memory objects.
* Repetitions: one `first_run_after_start` and 5 warm runs per measured operation. `first_run_after_start` = first execution after a fresh process (and a restarted container for A). It is **not** disk-cold: the OS page cache cannot be dropped without root and is not. Which alternative runs first is recorded, and the first runs of A and B are **not** compared with each other as if their conditions were identical, because the second one may benefit from the cache the first warmed. If initial performance is to be compared, A and B are run in separate fresh sessions with the same procedure and configuration, and that is reported as its own measurement. The main comparison uses the 5 warm runs, alternating A/B across repetitions to avoid a systematic order effect. Report min, median and max.
* Both alternatives use the same code path to produce the reports: SQL → `AnalysisRecord` list → `subclass_pairs` (unchanged `application/whitespace`). Only the storage engine differs.

## 3. Workloads

| ID | Operation | Measured |
|---|---|---|
| W1 | Prepare BIBLIO from the in-memory adapter output (load tables / write Parquet + manifest) | seconds, size on disk |
| W2 | Report: read all records from the store + pairs for origins 2006 and 2022 | seconds, split into read and compute |
| W3 | Integrity verification of the stored corpus against its manifest | seconds |
| W4 | Alteration tests (below) | detected yes/no, seconds |
| W5 | Rebuild a new version after one altered source record; the previous version must stay intact and still verify | seconds, previous version verified yes/no |
| W6 | Backup and restore into a new location, then verify | seconds for each step, verified yes/no |
| W7 | Operational retrieval, 39 demands x limit {5, 100} correctness and p95 over 20 repetitions of limit 5, warm (same protocol as spike P2) | p95, median, parity P1 and P1b counts reported as in the spike |

**Alteration tests (W4), same in both alternatives.** What must happen, by test:
* (i) *change one `ipc_entry` subclass in one record:* the verification detects that the stored content differs from the manifest.
* (ii) *change one byte of storage* (A: update a row through SQL; B: flip one byte of one Parquet file): the verification detects the corruption of the corresponding table or file.
* (iii) *delete one file or table:* the verification detects the missing Parquet file or PostgreSQL table.
* (iv) *swap two rows' order:* reported, not graded, neither as a semantic alteration nor for acceptance.

Detection counts only if it happens in the verification of W3 **before any report is generated**, and the system fails explicitly (non-zero exit / raised error, nothing served). A hash mismatch that only logs a warning and lets the run continue is recorded as **not detected**. For each test it is also recorded whether the detection occurred before a report could be produced.

**Backup/restore, rebuild and preservation (W5, W6).** Controls fixed in advance: the previous version is identified by its immutable manifest (digest recorded) before anything starts; the new version is built in a separate location (A: another schema; B: another directory); a restore passes only if integrity verification passes **and** W2 on the restored copy gives the expected outputs; after rebuilding, the previous version is re-verified against its recorded manifest. The guarantees of PostgreSQL transactions and of publishing a directory are not assumed equivalent; what each mechanism actually guarantees is described in §6. A = `pg_dump -Fc` of the schema, drop it, `pg_restore`, recompute the digest; B = copy the directory elsewhere, verify the hashes.

## 4. Outputs compared (C1)

All of the following, not only counts, compared as canonical JSON (sorted keys, no whitespace) or exact equality:
1. The complete `subclass_pairs` result for 2006 and 2022 from A, from B, and from the versioned `docs/whitespace/oepm-subclass-pairs-results.json`.
2. The full `AnalysisRecord` list read from A and from B and from the adapter (equality of every field, in order; subclass order per the `COLLATE "C"` contract).
3. The load checks of ADR 0037 §3.2 (711,547 publications, 341 rejected, 660 subclasses, 2,749 without IPC, 707,985 distinct `doc_id`).
4. W7 outputs of A against the numpy path.

## 5. Acceptance criteria (fixed before running)

An alternative is **acceptable** only if all hold:
* **C1 Equivalence:** items 1–3 of §4 identical to the adapter path / versioned JSON.
* **C2 Integrity:** tests (i), (ii), (iii) all detected by verification. (iv) is reported, not graded.
* **C3 Usability:** warm report (W2) no slower than the status quo of generating the report from the zips (188.6 s in the spike). C3 compares the warm report time with the **total** time of the current route from the zips, parsing included (about 177 s of the 188.6 s), while A and B receive data already prepared. It is not an isolated comparison of query performance and must not be read as if the whole saving came from the storage engine. Preparation (W1) is accounted separately, and the cumulative cost of several runs may be shown as a complementary analysis. This bound is the current practice, not a performance target.
* **C4 Recovery:** W6 completes, the restored copy verifies, and W2 on it gives the same result.
* **C5 Preservation:** W5 leaves the previous version intact and verifiable.

W7 is informational for A (the spike already passed P2); it is graded only for equivalence on ids and order.

**What the benchmark can conclude.** If only one alternative is acceptable, the other is eliminated for the stated reason. If both are acceptable, the benchmark does **not** rank them: a timing difference is called *material* only if the min–max ranges do not overlap and the medians differ by at least 2x; otherwise it is reported as not distinguishable. The choice then rests on the dimensions of §6 and on the owner's recorded reason, not on speed.

## 6. Operational dimensions (qualitative, recorded before measuring)

For each alternative, written down factually at the end: processes to run and monitor; new dependencies and their licences; ports and network exposure; credentials and who holds them; unit of backup and its measured restore time (W6); steps to deploy a new corpus version to the Lenovo; steps to roll back; failure modes at startup; what an operator must know. No scores, no weights. Concurrency, volume growth and server operating cost over time are **not** measured here and no extrapolation is made from this single-machine run; they remain required before production in ADR 0037 §7.3.

## 7. Reporting and deviations

**Revision R1 (2026-10-22), before any measurement:** four clarifications after review: definition of the first run and the A/B comparison rules (§2), interpretation of C3 (§5), what each alteration test must do and what counts as detection (§3), and the controls of rebuild, restore and preservation (§3). No criterion of §5 and no materiality rule was changed.


`RESULTS.md` with: environment table, the §3 table with min/median/max, the §5 verdict per alternative, the §6 text, every deviation and incident. Raw outputs committed. A change to this protocol after the first measurement is a dated amendment (A1, A2, …) stating what was already known; results already obtained are never edited. A failed run caused by the environment is reported as an incident and repeated, never silently dropped.

**Amendment R2 (2026-10-22), before any measurement, found in the review of the workload contracts; owner decisions recorded the same day.** Clarifications of three points where R1 was ambiguous or inconsistent; no run has produced data, so no result can have influenced them. C1, C2, C5, the materiality rule, the alternatives and the outputs compared are unchanged.

1. **W6 is two procedures, both required (R1 described it in two incompatible ways: the workload table says "into a new location", the detailed text says "drop it, `pg_restore`" for A and "copy elsewhere" for B).**
   * **W6a, restore to a new location, original untouched.** A: create a new database and `pg_restore` the `pg_dump -Fc` of the schema into it; B: copy the directory to a new path. Verify the restored copy against the manifest digest recorded before the backup, run W2 on it, and re-verify the original against its recorded digest (it must be unchanged).
   * **W6b, recovery in place after loss.** Drop the original (A: the schema; B: the directory), restore it under the same name from the backup, verify against the recorded digest, run W2.
   * Each step is timed separately for both alternatives. C4 requires **both** W6a and W6b to complete and give the expected digest and W2 outputs. If a restore fails in W6b after the original was dropped, that is a **failure of the procedure** and counts against the alternative; it is not reclassified as an environment incident unless there is evidence of an environment cause recorded at the time (for example the container or the disk was unavailable).
2. **W7 aggregation.** Unit of observation: one retrieval call (limit 5) of one demand. For each alternative there are 20 warm observations per demand x 39 demands = 780, **pooled** for the main figure, with all demands included and none selected on results. p95 = `statistics.quantiles(observations, n=20)[-1]` (Python's default method); median = `statistics.median`. A and B alternate per demand across the 20 repetitions. The p95 and median per demand are kept and reported as a **diagnostic only**; they are not an acceptance criterion and cannot become one after the data are seen. W7's acceptance rule is the one already in R1 (ids and order identical); timings are informational.
3. **C3 reading, fixed without room for interpretation.** The bound 188.6 s applies to each of the **5 valid warm W2 runs**: acceptance requires `max(warm_runs) <= 188.6 s`. Minimum, median and maximum are all recorded. A slow run is **not** discarded as atypical. A warm run is invalid (an incident, repeated) only if, defined now and not after seeing a time: (a) it ended in an exception or crash outside the store's contract, (b) the container or the disk was unavailable, or (c) before it started, the 1-minute load average of the machine was above 1.0 (the harness records it and waits up to 5 minutes for it to fall; if it does not, the run is an incident). A valid run that exceeds the bound is a result, is never repeated to obtain a pass, and counts against C3.

The hash of this file changes with R2: any authorisation must refer to the hash of the version in force when it is created, and R2 must be merged before the authorisation exists.
