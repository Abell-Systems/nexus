# ADR 0037 spike: results

Run 2026-10-22 on the development machine (4 cores, 11 GB), PostgreSQL 17.11 + pgvector in Docker (`pgvector/pgvector:pg17`, default settings, database collation `en_US.utf8`). Rules: `PREREGISTRATION.md` and its amendment A1. Raw data: `operational_raw.json`, `integrity_raw.json`. Throwaway code; no threshold was changed after seeing data.

## 1. Original pre-registered results

| | Result | Rule | Verdict |
|---|---|---|---|
| P1 parity (operational, 39 demands x limit 5 and 100) | ids and order identical in 78/78; scores at 6 decimals identical in 37, differ by exactly 1e-6 in 41 (7 at limit 5, 34 at limit 100) | 78/78 identical | **FAIL** |
| P2 latency, p95 per request, warm | SQL 0.128 s, numpy 0.158 s | <= 0.5 s and <= 3x numpy | **PASS** |
| P3 BIBLIO load checks | 711,547 publications, 341 rejected, 660 subclasses, 2,749 without IPC, 707,985 distinct doc_id: all exact | exact | **PASS** |
| P3 pairs | 24,583 (2006) and 40,585 (2022) observed pairs; both results equal the versioned `oepm-subclass-pairs-results.json` | exact | **PASS** |

P1 stays FAIL. Cause of the score difference: pgvector accumulates in float32 in a different order than numpy, so values near a rounding boundary land in the adjacent 6th decimal. Not investigated further.

## 2. Alternative criterion (A1, posterior to P1/P2, not a replacement)

P1b (ids and order exact, |score difference| <= 1e-6 after rounding both): **78/78**. No case differs by more than one unit.

## 3. BIBLIO equivalence and timings (P3 detail, P4 informational, no threshold)

| | Seconds |
|---|---|
| Parse the 26 files through the adapter | 177.4 |
| Pairs report in memory (both origins) | 11.2 |
| Report from the zips, parse + report | 188.6 |
| Load the normalised schema into PostgreSQL (tables, indexes, ANALYZE) | 77.3 |
| Report from the database, read + report | 26.5 |
| Database size | 1.29 GB |

First run through the database (load + report) 103.8 s against 188.6 s from the zips; each later run saves about 162 s. Operational cost (server, backup, 1.29 GB) is not in these numbers.

**Anomaly and its cause.** Records read back from the database differed from the adapter's in field `subclasses` for 2 of 711,547 records and in no other field. Both contain a lowercase symbol in the source (`b01J`, `A61k`). Python orders by code point (`A61K, A61Q, C11D, D06M, b01J`); the database collation `en_US.utf8` orders `A61K, A61Q, b01J, C11D, D06M`. Verified for the first record: `ORDER BY ... COLLATE "C"` gives the Python order. The sets are equal, which is why the pairs are. Scope of that check: one expression-level collation on one record; the database-level collation was not changed or tested.

## 4. Integrity (P5, mechanism only)

| Check | Result |
|---|---|
| Digest deterministic (computed twice); stable after `CLUSTER` (physical reorder) | yes / yes |
| Identical copy in another schema has the same digest | yes |
| One-row UPDATE changes the digest; manifest untouched | yes / yes |
| Altered candidate load verified in one transaction against the manifest: refused, ROLLBACK | yes |
| Relations in the database before/after the refusal | 34 / 34; candidate schema absent |
| Digest time over the whole schema | 18.2 s |

Digest: sha256 of per-table digests; each table is its rows as `to_jsonb` text ordered by primary key.

## 5. Incidents and limitations

- **Environment incident, not a result:** the first BIBLIO run failed at import (`httpx` missing in the spike venv) before any measurement; it was installed and the run repeated.
- No real loader exists: "altered source" in P5 is an altered row of a stored copy, so integration with a loader is not demonstrated.
- The digest canonical form (jsonb text) depends on PostgreSQL's output formats; its stability across PostgreSQL versions is untested.
- Two OEPM symbols are lowercase (`A61k`, `b01J`); they were kept as distinct symbols (660 includes them). Normalising them is a separate decision.
- P2 compares SQL against numpy on one machine with the eligible set in a temp table; the eligibility policy stays in code as the ADR says. The plan was a parallel sequential scan, no index.
- Costs not measured: operating the server, backups, memory under concurrent load.
