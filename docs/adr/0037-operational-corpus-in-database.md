# ADR 0037: Corpora in a Database, Not in Loose Artifact Files

**Status:** Proposed
**Date:** 2026-10-22
**Scope:** Where the two corpora of the project live and how they are synchronised and verified: the operational corpus (matcher: `infrastructure.mvp_entrypoint` reads its frozen corpus, embeddings and demands) and the OEPM BIBLIO corpus (white-space study and explorer). **This ADR is documentary: it changes no code.** It does not touch ADR 0014 (frozen embeddings, no live provider), which stays in force.

---

## 1. Context

The service loads `data/snapshots/operational_corpus_v1/` (229 MB, git-ignored): `publications.parquet`, two `.npy` embedding matrices with manifests, `demands_v1.json`. `load_operational_artifacts` verifies every hash and the alignment of ids, model and dimension, and aborts startup on any mismatch; `demo_preflight.py` compares the served `corpus_parquet_sha256` and `embedding_index_sha256` with the files on disk.

Deploying to the Lenovo staging host (role `workload` of the `infrastructure` repository) exposed the cost of this shape: a checkout at a commit does not contain the data, the role has no mechanism to move it, and the workload security contract allows only `/srv/apps`, `/srv/config` and `/srv/secrets` as workload storage. The project owner's current deployment requirement is that the corpus be available reproducibly to the Lenovo staging workload without manually shipping git-ignored artifacts. This ADR proposes PostgreSQL + pgvector to satisfy that requirement, subject to the alternatives and validation gates below.

What the move must NOT lose (all exist today and are tested):

1. **Fail-closed integrity.** The service never answers on unverified data and never falls back to BM25 or a live model.
2. **Identity in responses.** `meta.corpus_id`, `corpus_parquet_sha256`, `embedding_index_sha256`, so a stale server with the same shape is detectable.
3. **Frozen, versioned artifacts** (ADR 0014): a changed corpus, model or revision is a new version, never an in-place edit.
4. **Deterministic ranking:** eligibility filter first, score `(cos + 1) / 2` rounded to 6 decimals, ties by `(score DESC, publication_id ASC)`.

The seams already exist: `AssetCatalog`, `DemandRepository` and `PatentCandidateRetriever` are domain ports, and `OperationalArtifacts` is the only place that knows the files. A database is an infrastructure adapter behind them; `domain` and `application` do not change.

## 2. Options

| | A. Files (status quo) | B. DuckDB file | C. PostgreSQL + pgvector |
|---|---|---|---|
| Runtime | in-process numpy | in-process, `duckdb==1.5.5` already a dependency and used by `DuckDb*Retriever` | separate server (compose service, like career-os's `db`) |
| Reaches the Lenovo | needs a file-sync mechanism | the same single file: **same problem** | loaded **over the tailnet from the controller**; nothing but the DB volume on the host |
| Integrity | per-file sha256, existing | one file sha256 plus the existing checks against a manifest table | content checksum recomputed from rows at load, manifest table, checked at startup |
| Incremental updates / several consumers | no | no (single writer) | yes |
| Retrieval | numpy matvec, ~0.2 s | `array_cosine_similarity` or the VSS extension, to be measured | exact scan or HNSW; exact scan is the only option that is bit-for-bit comparable to today |
| New operational surface | none | none | server, credentials (SOPS env), backups (Kopia of the volume), migrations, a restricted app role |

## 3. Decision (proposed)

**Proposed option: C, PostgreSQL with pgvector, loaded by an explicit, versioned ingest command; ranking stays an exact scan.** This is not an unconditional acceptance of the database choice: §5.1 defines the acceptance gate against option B and the measured operational cost.

Reasons, in order of weight:

* Only C makes the corpus a property of the **environment** instead of a payload of each **deployment**. Under A and B the data still has to be copied onto every host by something outside the database.
* The `workload` role already deploys a Compose stack with a Postgres service, secrets and backup, so C may reuse an existing path; the Nexus-specific workload and role grants must still be verified during implementation.
* Updates (a new corpus version, the white-space explorer's observed-pairs data) become loads into a new versioned schema, not file replacement.

Conditions that make C acceptable, none negotiable:

1. **Versioned, immutable load.** Each corpus version lives in its own schema (`operational_v1`, ...), written once by the ingest command, then granted read-only to the application role. A change is a new schema, never an `UPDATE`.
2. **Manifest table.** One row per load: `dataset_id`, model name and revision, dimension, row counts, the source file hashes that produced it (`publications.parquet`, embeddings, demand corpus, texts hash) and a `content_sha256` computed over the rows in a defined order.
3. **Startup verification stays fail-closed.** The service recomputes `content_sha256` from the rows (or from a canonical per-table digest) and compares it with the manifest, checks id alignment, model and dimension equality and the demand-texts hash, and aborts on any mismatch. `/health` answers only after this, as today.
4. **Identity fields keep their meaning.** `meta.corpus_id` is the manifest `dataset_id`; the two hashes in `meta` are the manifest's, so `demo_preflight.py` compares them with what the loader declared at ingest time instead of files on disk.
5. **Exact scan.** Rank by exact cosine in SQL with the same eligibility, rounding and tie rules. No approximate index is used for anything shown or cited, because ADR 0014 and the evaluation rely on reproducible orderings. An index may be added later only after an equivalence test against the exact result on all 39 demands.
6. **Parity gate before switching.** The adapter ships behind the same `PatentCandidateRetriever` port and a test that, over the real artifacts, returns identical ids, scores and order to `NumpyDenseRetriever` for every demand. Without it the old path stays the default.
7. **No embedding at runtime.** Embeddings are generated offline as today (ADR 0014); the ingest command only loads them.
8. **Deterministic order of text keys.** Every ordering the contract depends on (the subclasses of a record, ties by `publication_id`) is `ORDER BY ... COLLATE "C"`, i.e. code-point order as in Python. Startup verifies the contract itself, not only the configuration: the service reads the two OEPM records whose symbols are mixed case in the source (`b01J`, `A61k`) through the contractual query and aborts if the full subclass sequences differ from the ones recorded in the manifest. A regression test covers both records and compares sequences, not sets.
9. **Numeric policy of the parity gate.** The gate requires identical ids and order and a score difference of at most 1e-6 **after both scores are rounded to 6 decimals** (so one unit in the last digit passes, two fail). This is a new decision taken after the spike (§7.1), not a retroactive pass of the strict criterion.

## 3.1 Two corpora, one pattern (amendment, 2026-10-22)

Requirements stated by the project owner: the corpus must be consumable efficiently for the white-space work, and there must be synchronisation.

| | Operational corpus | OEPM BIBLIO 2000–2025 |
|---|---|---|
| Use | demand-to-asset matching | pair counts, base rates, section density, explorer data |
| Source of truth today | `data/snapshots/operational_corpus_v1/` (229 MB) built from BigQuery + 2.2 h CPU embeddings | 26 public zips, 793 MB in `data/raw/oepm_open/`, re-downloadable with `scripts/download_oepm_opendata.py`; names, sizes and sha256 versioned in `config/whitespace/oepm_biblio_2000_2025.json` |
| In the database | rows + embeddings, as in §3 | the parsed bibliographic records (publication id, dates, kind, IPC subclasses per source record), the grain every white-space count is computed from |
| Current consumption | numpy matrix in memory | each report script re-parses the zips |

The same pattern applies to both: immutable schema per version, manifest table, `content_sha256`, fail-closed verification. For BIBLIO the manifest also records the sha256 of every source zip, which are already pinned in git, and the Authority File hash. The database is therefore a **derived, rebuildable** form of a source that is reproducible from public data, never a new source of truth.

**Synchronisation** is one ingest command per corpus, run from the controller (OMEN) against the host database over the tailnet, so that nothing but the database volume holds the corpus on the host. Re-running it for an existing version must either find an identical manifest and do nothing, or fail; it never overwrites. A new version is a new schema.

**Derived results stay files.** `docs/whitespace/oepm-subclass-pairs-results.json` (6.2 MB) and the other versioned results remain static, git-versioned files served to the browser, as vertical 2 requires (no endpoint, no computation in the browser). What changes is their producer: the report scripts read BIBLIO from the database, and the JSON keeps carrying the corpus identity hashes, which now equal the manifest's. The unit rules (O4: activity by publication identifier at its earliest date; pairs from single source records) stay in `application/whitespace` and are not re-implemented in SQL; SQL provides the record-level data, not the metrics, so the existing invariants (565/612 active subclasses, 24,583/40,585 observed pairs) remain the equivalence test between the file-based and the database-based producer.

## 3.2 Relational schema, not raw payload (amendment, 2026-10-22)

The database is not a container for the files. Each corpus is **parsed into a normalised schema** with keys, foreign keys and constraints, so that it can be queried by record, subclass or code without re-parsing, and so that the load itself is validated by the database. Loading a Parquet blob, a JSON column or a zip into a table is not compliant with this ADR.

Principles:

* **Preserve source observations and provenance in the base tables** (consistent with ADR 0036 §5.1): do not deduplicate repeated source records or store derived measures as if they were observations. Schema normalization (keys, foreign keys, generated identifiers and constraints) is allowed to represent those observations relationally. Repeated `doc_id`s are kept (a repeat is a row, never merged). Derived measures (distinct documents, activity at an origin, pairs) are computed by the existing code in `application/whitespace`, which reads these tables through a port.
* **One loader per corpus, built on the existing readers.** BIBLIO reuses `PatentPublicationSource` and the ST36 adapter, so parsing rules, rejected records and anomalies are the ones already tested; the loader maps `PatentPublication` / `RejectedRecord` to rows and contains no parsing of its own. The operational loader maps the same domain objects `load_operational_assets` already builds.
* **Constraints encode the invariants.** Row counts and key relations that are today asserted in tests (§3.1 and the characterization) become load-time checks recorded in the manifest.
* Schema versions are immutable (§3.1). The names below are the contract; column types are fixed at implementation.

**`biblio_v1`** (source: 26 files, 711,547 read records and 341 rejected)

| Table | Key | Content |
|---|---|---|
| `source_file` | `file_id` | name, `sha256`, bytes (the 26 pinned hashes) |
| `source_record` | `record_id` (source order) | `file_id` FK, `archive_path`; unique `(file_id, archive_path)`. Provenance of every row below |
| `publication` | `record_id` FK | country, doc_number, kind, publication_date, application_country/number/kind (nullable), application_date, title. `doc_id` is a generated column and **not unique** (3,562 repeats are kept) |
| `priority_date` | `(record_id, ordinal)` | one readable priority date per row |
| `party` | `(record_id, role, ordinal)` | `role` in (`applicant`, `inventor`); raw name, no entity resolution |
| `ipc_subclass` | `symbol` | four-character symbol with section, class, subclass; the 660 observed subclasses |
| `ipc_entry` | `(record_id, ordinal)` | `subclass_symbol` FK, main_group, subgroup, version, level, value, exactly as stated |
| `anomaly` | `(record_id, field, ordinal)` | field, raw_value, reason |
| `rejected_record` | `(file_id, archive_path)` | reason; counted, never lost |
| `manifest` | one row | as in §3.1 |

Load-time checks: 711,547 `publication` rows and 341 `rejected_record` rows; 660 `ipc_subclass`; 2,749 publications without `ipc_entry`; 707,985 distinct `doc_id`; every `ipc_entry.record_id` has a `publication`. Indexes follow the access paths of the white-space work: `ipc_entry(subclass_symbol, record_id)` for pairs and activity, `publication(publication_date)` for origins and lags, `publication(application_country, application_number)` for the legal-status link.

**`operational_v1`** (source: 54,997 assets, 39 demands)

| Table | Key | Content |
|---|---|---|
| `asset` | `asset_id` (corpus row order) | `publication_number` unique, country, kind, ip_type, family_id, title, abstract, abstract_language, filing_date, publication_date |
| `asset_party` | `(asset_id, role, ordinal)` | `role` in (`assignee`, `inventor`) |
| `asset_cpc` | `(asset_id, ordinal)` | CPC code as stated |
| `asset_embedding` | `asset_id` FK | `vector(768)`, L2-normalised; model name/revision/dimension only in the manifest |
| `demand` | `demand_id` | title, description, posted_date, origin_country, source_url |
| `demand_embedding` | `demand_id` FK | `vector(768)` |
| `manifest` | one row | as in §3 |

Eligibility (Spanish patents and utility models with an abstract, 44,195 of 54,997) stays in `operational_eligibility_policy` and is not stored as a column: it is policy, not observation. `asset_id` order must reproduce the corpus row order, because the parity gate (§3.6) compares against it.

Rejected by this decision: storing the derived pair tables or the study's result JSONs in the database; row-per-subclass-pair materialisations. They duplicate versioned results (§3.1).

## 4. Consequences

**Positive.** Deployment no longer depends on a data copy; reload and rollback are schema switches; backups and access control are the database's; more than one consumer can read the same verified corpus.

**Negative.**
* A server to run, secure, back up and monitor on a host that also holds the backup repository.
* The numpy path is fast and dependency-light; SQL retrieval must be measured against the current ~0.2 s and may not match it.
* Integrity moves from "hash of a file" to "hash of rows"; the canonical row ordering and serialization of that digest become part of the contract and must be specified and tested.
* More failure modes at startup (connection, role grants, schema missing).

## 5. Open questions (acceptance gates; resolve with evidence before changing status to Accepted)

1. **Database choice versus a synchronized file.** The immediate requirement is reproducible delivery to the Lenovo. Before accepting option C, compare its ongoing maintenance cost with option B (DuckDB/file) plus a verifiable, idempotent artifact-sync step. Record the measured trade-off and the owner-approved reason for preferring PostgreSQL.
2. **ST36 fidelity.** Characterize the source adapter's complete output and explicitly account for fields retained, intentionally ignored, and rejected. The normalized database mapping must preserve all fields required by existing consumers and tests; expanding the contract to retain currently ignored fields requires a documented change to the adapter and its tests.
3. **Network and credential custody.** Proposed: load from the controller over the tailnet and expose the database port only on the tailnet. Before implementation, specify and test the SOPS/age custody of the loader and application roles, least-privilege grants, rotation, and failure behavior.
4. **Performance acceptance.** Benchmark pgvector exact scan over the 44,195 eligible rows and the BIBLIO reports against the current zip-based process on the real corpora. Record environment, cold/warm timings, and acceptable thresholds before this ADR is accepted.
5. **Licensing and retention.** Document retention/deletion behavior for third-party text and confirm that the current attribution and data-use restrictions remain applied to database-backed serving; this is an engineering gate, not legal advice.

## 5.1 Acceptance gate

Do not change status from Proposed to Accepted, change the default retrieval path, or advertise PostgreSQL as the settled architecture until the database-vs-sync comparison, ST36 fidelity inventory, credential/network model, and real-data performance measurements in §5 have evidence recorded in this ADR or linked reproducible reports. The parity gate in §3 remains mandatory before any switch. If PostgreSQL does not justify its operational cost for this host-side deployment, prefer the simpler versioned file-sync option rather than retaining a database for deployment convenience alone.

## 6. Enforcement

An implementation is non-compliant with this ADR if it: orders contract-relevant text keys with the database default collation; updates a loaded corpus version in place; starts serving before the manifest and content digest are verified; falls back to files, BM25 or a live model when the database check fails; uses an approximate index for shown results without the equivalence test; or switches the default path without the parity gate of §3.6.

## 7. Spike evidence (2026-10-22)

Pre-registration (with amendment A1), scripts, raw outputs and `RESULTS.md` are in `experiments/adr-0037-db-spike/`. PostgreSQL 17.11 + pgvector in Docker, default settings, database collation `en_US.utf8`.

### 7.1 Results, kept as measured

| | Result |
|---|---|
| P1 strict parity (operational, 39 demands x limit 5 and 100) | **FAIL**: ids and order identical in 78/78, scores identical in 37 and differing by exactly 1e-6 in 41 |
| P1b tolerance, defined after P1 (amendment A1) | 78/78; it does not replace P1 |
| P2 latency, p95 | PASS: SQL 0.128 s, numpy 0.158 s (rule: <= 0.5 s and <= 3x numpy) |
| P3 BIBLIO | PASS: load checks exact; observed pairs 24,583 and 40,585 equal the versioned results |
| P4 (informational) | report from zips 188.6 s (177.4 s of parsing), from the database 26.5 s; load 77.3 s; 1.29 GB |
| P5 integrity | PASS as a mechanism: deterministic digest, stable after physical reorder, one-row change detected, altered candidate load refused with ROLLBACK, 34 relations before and after, no candidate schema left; digest of the whole schema 18.2 s |

The score difference is attributed to float32 accumulation order in pgvector against numpy; it was not investigated further. Of 711,547 records, 2 differed between the database read and the adapter, only in the order of `subclasses`, because two source records carry a lowercase symbol; the database collation `en_US.utf8` orders them differently from Python. Verified for one record with `COLLATE "C"`; the database-level collation was not tested. These two symbols are kept as distinct in the corpus; normalising them is a separate decision.

### 7.2 Limits of the spike

No real loader (the altered source of P5 is an altered row of a stored copy); stability of the digest across PostgreSQL versions (it uses `jsonb` text) untested; no concurrent load, no backup or recovery, no measurement of the cost of operating the server; the plan was a parallel sequential scan with no index; one machine.

### 7.3 Required before production, whatever the status

Each in its own change: the real loaders with the load checks of §3.2; the backup and recovery strategy (including restoring and re-verifying the digest); behaviour under concurrency; digest compatibility across PostgreSQL versions; the parity gate of §3.6 run against the real adapter with the policy of §3.9.

### 7.4 Status of the acceptance gates of §5.1

| Gate (§5) | Evidence | State |
|---|---|---|
| 4. Performance on real corpora | §7.1: P2 PASS, P4 informational with cold/warm split not separated; environment stated | **Met** for latency and report time; thresholds were pre-registered |
| 1. Database versus synchronized file | The spike measured PostgreSQL only; option B (DuckDB/file + sync) was not benchmarked and the cost of operating the server was not measured | **Open** |
| 2. ST36 fidelity inventory | `biblio_v1` follows what the adapter reads; the inventory of retained, ignored and rejected fields is not written | **Open** |
| 3. Network and credential custody | Not addressed by the spike | **Open** |
| 5. Licensing and retention | Not addressed | **Open** |

Conditions 8 and 9 of §3 are added by this change as consequences of the spike; they do not alter the gates. The status stays **Proposed** until gates 1, 2, 3 and 5 have evidence recorded here or in linked reproducible reports.
