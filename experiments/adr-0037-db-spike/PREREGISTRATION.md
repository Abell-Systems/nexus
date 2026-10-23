# ADR 0037 spike: pre-registration

Written and committed before any measurement. Throwaway: a local Postgres 17 + pgvector in Docker, schemas `operational_spike` and `biblio_spike`. Nothing here is production code. Outcome "unresolved" is valid.

## Questions and decision rules

**P1 – Parity (operational).** For each of the 39 demands, `limit` in {5, 100}: SQL exact scan returns the same ordered `publication_id` list and the same score (rounded to 6 decimals) as `NumpyDenseRetriever`.
- PASS: 78/78 identical.
- If only order among equal scores differs: report, not PASS; fix tie rule `(score DESC, publication_id ASC)` in SQL and rerun once.
- Any other mismatch: FAIL, option C is not equivalent as specified.

**P2 – Latency (operational).** Warm, 20 repetitions per demand (limit 5), single connection, p95 over all calls, against numpy on the same machine measured the same way.
- PASS: SQL p95 <= 0.5 s AND <= 3x numpy p95.
- Otherwise FAIL for C as specified; then evaluate DuckDB (B) with the same P1/P2 rules before any ADR change.

**P3 – BIBLIO load and equivalence.** Load all 26 files through the existing ST36 adapter into the §3.2 schema.
- Load checks of the ADR: 711,547 publications, 341 rejected, 660 subclasses, 2,749 without IPC, 707,985 distinct doc_id.
- Pairs: observed pairs among active subclasses (min 20 distinct documents, O4 rules) computed from SQL record-level data by the existing `subclass_pairs` code equal 24,583 (origin 2006) and 40,585 (origin 2022) and the versioned JSON.
- PASS: all checks exact. Any difference: FAIL, reported with the diff; nothing is adjusted to make it pass.

**P4 – BIBLIO report time (informational, no threshold).** Wall time of the pairs report: from zips (current script) vs from the database. Reported as measured, once warm and once cold.

## Reporting
Machine, versions, row counts, raw timings and every deviation go in `RESULTS.md`. No threshold is changed after seeing data; a changed rule would be a new, dated amendment.

## Amendment A1 (2026-10-22, after P1/P2 results, before any P3/P4 result)

Written knowing the P1 outcome; it does not change it.

- **P1 stays FAIL** under the original rule (41 of 78 cases differ in score by exactly 1e-6; ids and order identical in 78/78).
- **P1b (alternative, post hoc, reported separately):** ids and order exactly equal AND |score_sql - score_numpy| <= 1e-6, applied to the scores **after** both are rounded to 6 decimals (so a one-unit last-digit difference is accepted, two units are not). Cases: 39 demands x limit {5, 100}. It is not a replacement for P1.
- **P5 (new, integrity of the load):** on a scratch copy of the loaded schema, (a) re-running the loader on the same version with an identical manifest changes nothing; (b) re-running it with one altered source row (a flipped subclass in one record) is refused; (c) a recomputed content digest over the rows differs from the manifest after a single-row UPDATE. The spike implements the digest as `sha256` over a canonical ordered dump of each table; the canonical form is part of what is being tested. PASS: (a), (b), (c) all behave as stated. It is a design check, not a finished loader.
