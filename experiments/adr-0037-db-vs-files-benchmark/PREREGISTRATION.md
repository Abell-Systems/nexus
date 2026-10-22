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
* Repetitions: 1 cold run and 5 warm runs per measured operation. "Cold" = first execution after a fresh process (and a restarted container for A); the OS page cache cannot be dropped without root and is not, so cold is reported as "first run after start", never as disk-cold. Warm runs follow immediately. A and B run in alternating order across repetitions to avoid a systematic order effect. Report min, median and max.
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

**Alteration tests (W4), same in both alternatives:** (i) change one `ipc_entry` subclass in one record; (ii) change one byte of storage (A: update a row through SQL; B: flip one byte of one Parquet file); (iii) delete one file or table; (iv) swap two rows' order (must not be reported as an alteration if the integrity definition is order-independent for A and byte-based for B; the result is reported for what it is). Each must be detected by the verification of W3, not by luck during a query.

**Backup/restore (W6):** A = `pg_dump -Fc` of the schema, drop it, `pg_restore`, recompute the digest; B = copy the directory elsewhere, verify the hashes. Both then run W2 on the restored copy.

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
* **C3 Usability:** warm report (W2) no slower than the status quo of generating the report from the zips (188.6 s in the spike). This bound is the current practice, not a performance target.
* **C4 Recovery:** W6 completes, the restored copy verifies, and W2 on it gives the same result.
* **C5 Preservation:** W5 leaves the previous version intact and verifiable.

W7 is informational for A (the spike already passed P2); it is graded only for equivalence on ids and order.

**What the benchmark can conclude.** If only one alternative is acceptable, the other is eliminated for the stated reason. If both are acceptable, the benchmark does **not** rank them: a timing difference is called *material* only if the min–max ranges do not overlap and the medians differ by at least 2x; otherwise it is reported as not distinguishable. The choice then rests on the dimensions of §6 and on the owner's recorded reason, not on speed.

## 6. Operational dimensions (qualitative, recorded before measuring)

For each alternative, written down factually at the end: processes to run and monitor; new dependencies and their licences; ports and network exposure; credentials and who holds them; unit of backup and its measured restore time (W6); steps to deploy a new corpus version to the Lenovo; steps to roll back; failure modes at startup; what an operator must know. No scores, no weights. Concurrency, volume growth and server operating cost over time are **not** measured here and no extrapolation is made from this single-machine run; they remain required before production in ADR 0037 §7.3.

## 7. Reporting and deviations

`RESULTS.md` with: environment table, the §3 table with min/median/max, the §5 verdict per alternative, the §6 text, every deviation and incident. Raw outputs committed. A change to this protocol after the first measurement is a dated amendment (A1, A2, …) stating what was already known; results already obtained are never edited. A failed run caused by the environment is reported as an incident and repeated, never silently dropped.
