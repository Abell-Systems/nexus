# ADR 0037: Operational Corpus in a Database, Not in Loose Artifact Files

**Status:** Proposed
**Date:** 2026-10-22
**Scope:** Where the operational service (`infrastructure.mvp_entrypoint`) reads its frozen corpus, embeddings and demands from, and how their integrity is verified. **This ADR is documentary: it changes no code.** It does not touch ADR 0014 (frozen embeddings, no live provider), which stays in force.

---

## 1. Context

The service loads `data/snapshots/operational_corpus_v1/` (229 MB, git-ignored): `publications.parquet`, two `.npy` embedding matrices with manifests, `demands_v1.json`. `load_operational_artifacts` verifies every hash and the alignment of ids, model and dimension, and aborts startup on any mismatch; `demo_preflight.py` compares the served `corpus_parquet_sha256` and `embedding_index_sha256` with the files on disk.

Deploying to the Lenovo staging host (role `workload` of the `infrastructure` repository) exposed the cost of this shape: a checkout at a commit does not contain the data, the role has no mechanism to move it, and the workload security contract allows only `/srv/apps`, `/srv/config` and `/srv/secrets` as workload storage. The project owner's position is that the corpus should be ingested into a database rather than shipped as files. This ADR decides whether, which database, and what must be preserved.

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

**Option C, PostgreSQL with pgvector, loaded by an explicit, versioned ingest command; ranking stays an exact scan.** Option B is the fallback if C's operational cost is judged not worth it.

Reasons, in order of weight:

* Only C makes the corpus a property of the **environment** instead of a payload of each **deployment**. Under A and B the data still has to be copied onto every host by something outside the database.
* The `workload` role already deploys a Compose stack with a Postgres service, secrets and backup, so C reuses a solved path.
* Updates (a new corpus version, the white-space explorer's observed-pairs data) become loads into a new versioned schema, not file replacement.

Conditions that make C acceptable, none negotiable:

1. **Versioned, immutable load.** Each corpus version lives in its own schema (`operational_v1`, ...), written once by the ingest command, then granted read-only to the application role. A change is a new schema, never an `UPDATE`.
2. **Manifest table.** One row per load: `dataset_id`, model name and revision, dimension, row counts, the source file hashes that produced it (`publications.parquet`, embeddings, demand corpus, texts hash) and a `content_sha256` computed over the rows in a defined order.
3. **Startup verification stays fail-closed.** The service recomputes `content_sha256` from the rows (or from a canonical per-table digest) and compares it with the manifest, checks id alignment, model and dimension equality and the demand-texts hash, and aborts on any mismatch. `/health` answers only after this, as today.
4. **Identity fields keep their meaning.** `meta.corpus_id` is the manifest `dataset_id`; the two hashes in `meta` are the manifest's, so `demo_preflight.py` compares them with what the loader declared at ingest time instead of files on disk.
5. **Exact scan.** Rank by exact cosine in SQL with the same eligibility, rounding and tie rules. No approximate index is used for anything shown or cited, because ADR 0014 and the evaluation rely on reproducible orderings. An index may be added later only after an equivalence test against the exact result on all 39 demands.
6. **Parity gate before switching.** The adapter ships behind the same `PatentCandidateRetriever` port and a test that, over the real artifacts, returns identical ids, scores and order to `NumpyDenseRetriever` for every demand. Without it the old path stays the default.
7. **No embedding at runtime.** Embeddings are generated offline as today (ADR 0014); the ingest command only loads them.

## 4. Consequences

**Positive.** Deployment no longer depends on a data copy; reload and rollback are schema switches; backups and access control are the database's; more than one consumer can read the same verified corpus.

**Negative.**
* A server to run, secure, back up and monitor on a host that also holds the backup repository.
* The numpy path is fast and dependency-light; SQL retrieval must be measured against the current ~0.2 s and may not match it.
* Integrity moves from "hash of a file" to "hash of rows"; the canonical row ordering and serialization of that digest become part of the contract and must be specified and tested.
* More failure modes at startup (connection, role grants, schema missing).

## 5. Open questions (to answer before Accepted)

1. **What is the reason for the database?** Incremental updates, several consumers, host-side deployment, or something else? The answer decides between B and C: if it is only "the data should reach the host reproducibly", B plus a sync step is cheaper.
2. **Does the white-space explorer's observed-pairs data (`subclass_pairs`) move too,** or stay a versioned file? It has its own contract and is not retrieval data.
3. **Where is the load run from?** The controller over the tailnet (needs the DB port reachable from the tailnet only) or on the host. The former keeps the corpus off the host's filesystem.
4. **Is pgvector's exact scan fast enough** over the 44,195 eligible rows? It must be measured with the real data before this ADR is accepted.
5. **Licensing and retention.** The text is third-party (Google Patents Public Data, CC BY 4.0); a DB in a shared host keeps the same obligations (attribution on screen, not legal advice).

## 6. Enforcement

An implementation is non-compliant with this ADR if it: updates a loaded corpus version in place; starts serving before the manifest and content digest are verified; falls back to files, BM25 or a live model when the database check fails; uses an approximate index for shown results without the equivalence test; or switches the default path without the parity gate of §3.6.
