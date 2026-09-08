# ADR 0020: Experimental Corpus Architecture — Demand Corpus × Patent Corpus

**Status:** Proposed
**Date:** 2026-09-08
**Scope:** Resolves the blocker recorded in `docs/superpowers/specs/2026-09-08-pr-e-dry-run-execution-design.md` (PR-E dry-run step 6, blocked on corpus data 2026-09-08): the only ES patent corpus in this repository is a 16-record pilot, domain-mismatched to the 8 finalized dry-run demands. Reframes the fix from "get more ES patents" to a structural gap: the experiment has one frozen, first-class corpus (demands, N=39) and one ad-hoc dependency (patents). This ADR defines both sides as independent, symmetric, frozen experimental artifacts. Doc only — no code, no ingestion run, no PR-E1 dry-run artifact touched.

---

## Context

`DemandCorpus`/`DemandCorpusItem` (`domain/models/evaluation.py`) already exists as a frozen, hashed, manifested experimental artifact — 39 Spanish-origin technology demands, reproducibly acquired (`scripts/freeze_phase2_demand_corpus.py`), committed with a manifest + sha256 sidecar (`data/evaluation/dataset_phase2_demand_corpus_n39.*`).

Nothing equivalent exists for patents. `data/snapshots/patents_es_snapshot.duckdb` (16 records) is explicitly self-labeled in its own manifest as "Pilot baseline corpus for proof-of-method validation" — never intended as the experiment's real patent universe. When PR-E's dry-run (candidate-pool construction over 8 selected demands) reached the point of needing real patent data, this asymmetry surfaced as a hard blocker: the experimental unit `D × P → retrieval → eligibility → pool → annotation` requires **both** `D` and `P` to be defined, frozen, and reproducible — not `D` frozen and `P` left as "whatever happens to be in the DB."

Two things were explicitly rejected while diagnosing this (see the blocked-step-6 note in the execution-design spec):
- Proceeding with the 16-record pilot, even caveated as "mechanical test only" — produces empty/near-empty pools for most of the 8 demands, a formally-executable but scientifically weak artifact.
- Hand-picking a domain-matched ad hoc patent set for the 8 demands — would introduce candidate selection *before* retrieval, contaminating exactly the pool-independence property PR-E exists to protect (spec §3, ADR 0019).

Existing infrastructure, checked before assuming a new data source was needed:
- `infrastructure/sources/patent/epo_ops_client.py::EpoOpsClient` — a real, generic EPO OPS (Open Patent Services) v3.2 client, OAuth2, implementing `PatentSourceProtocol`. Its `fetch_batches(cql_query, range_start, range_end)` CQL query is fully parameterizable; the `pn="ES"` term in its example default is not a hard restriction. Already supports offline/fixture-replay mode (`from_fixture_file`) — a real path to a contract testable without live API credentials.
- `infrastructure/sources/bigquery_patents.py::BigQueryPatentsDataSource` — checked and found to be a non-functional mock (`get_status` always reports `"mock": True`; it inherits `MockPatentsDataSource` and never calls BigQuery). Not usable as-is; not relied on here.
- `application/ingestion/normalizers/oepm_xml_normalizer.py::OepmXmlNormalizer` — takes `target_country` as a constructor parameter (default `"ES"`, but not hardcoded); derives `country_code` from the parsed XML when present, falling back to `target_country` only when the source doesn't specify one. Plausibly reusable for EPO OPS XML from other jurisdictions, but this is **not assumed** — verified by contract/test in the implementation that follows this ADR, not decided here.
- EPO OPS API credentials (`EPO_OPS_KEY`/`EPO_OPS_SECRET`) are not currently available. Real ingestion is gated on obtaining them; the contract this ADR defines must be verifiable via fixtures independent of that gate.

## Decision

### 1. `D` and `P` are symmetric, independent, frozen experimental artifacts

```text
                    D                              P
       ┌─────────────────────┐        ┌─────────────────────────────┐
       │  DemandCorpus        │        │  PatentCorpus                │
       │  (exists: N=39)       │        │  (new, this ADR)             │
       │  Spanish-origin        │        │  jurisdiction+grant+window   │
       │  technology demands   │        │  determined universe         │
       └─────────────────────┘        └─────────────────────────────┘
                    │                              │
                    └──────────────┬───────────────┘
                                    ▼
                    D × P → retrieval → eligibility → pool → annotation
                              (PR-E1, unchanged, already designed)
```

Neither corpus is constructed with knowledge of the other's content beyond what this ADR fixes as shared contract (jurisdiction/date/schema fields needed for eligibility). In particular: **`P`'s composition is fixed before any demand-side selection is consulted** — see §3's pipeline order. `D`'s 39 demands and the 8-demand dry-run selection are already frozen (execution-design spec, `phase2-dry-run-selection.md`) and are not reopened or referenced during `P`'s construction.

### 2. `PatentCorpus` inclusion contract (defined ex ante, independent of any demand)

- **Jurisdictions:** EP, US, JP, CN, KR, plus WO (PCT) publications. Chosen as an objective, volume-based rule (the offices/track concentrating the large majority of global patenting activity) — not selected for topical fit to any demand.
- **Publication type:** grants only (matches the existing ES pilot corpus's own inclusion criterion; excludes pending/withdrawn/rejected applications).
- **Temporal window:** publication date within the 10 years preceding the corpus's freeze cutoff date (approximately 2016–2026 if frozen now). This is the corpus's own window, independent of and prior to any per-demand `AnnotationPoolEligibilityPolicy` (ADR 0019) evaluation, which still applies per-demand at candidate-pool-build time exactly as already designed.
- **Topical/CPC composition:** unrestricted. No CPC-section stratification, no keyword filter, no domain curation. The technological composition is whatever the jurisdiction+grant+window universe actually contains — measured and reported after freezing, never corrected beforehand to "balance" domains.

### 3. Composition pipeline and selection rule (deterministic, reproducible, demand-blind)

```text
EPO OPS / DOCDB (via EpoOpsClient, CQL query encoding jurisdiction+grant+window)
        │
        ▼
Normalize (OepmXmlNormalizer or a verified-adequate generalization) → dedupe
        │
        ▼
Sort by sha256(publication_id)
        │
        ▼
Take first N_final records
        │
        ▼
Frozen PatentCorpus (manifest + sha256 sidecar)
```

`sha256(publication_id)`-order selection is deterministic (same universe → same N records, byte-identical), auditable (recomputable by anyone from the raw fetched set), and independent of API delivery order (EPO OPS makes no ordering guarantee) or of any demand-side property.

### 4. Volume: target, not a fixed constant, with an ex ante floor

- **Target N:** 50,000.
- **N_final = min(target_N, eligible_available_records)** after applying §2's inclusion contract — not assumed to hit the target.
- **minimum_acceptable_N: 5,000.** Chosen because it was the volume this ADR's own discussion first considered as a viable, computationally-manageable floor for live BM25/CPC retrieval before revising the target upward for domain-coverage reasons — reusing that number as a principled floor, not an arbitrary one. **If `N_final < minimum_acceptable_N`, corpus construction is treated as failed** (the inclusion contract as specified cannot be satisfied), not silently accepted as a shrunken-but-usable corpus. Resolving a below-floor result means revisiting §2's contract (e.g. widening jurisdictions or the temporal window) — a new decision, made explicitly, not a silent fallback.

### 5. Freezing discipline

`PatentCorpus` SHALL be a first-class frozen experimental artifact, with deterministic content selection (§3), a manifest, and a cryptographic hash, following the repository's established corpus-freezing discipline (as demonstrated by `dataset_phase2_demand_corpus_n39.*` and `scripts/freeze_phase2_demand_corpus.py`: reproducible acquisition script → committed dataset file → manifest JSON → sha256 sidecar).

This ADR does **not** specify `PatentCorpus`'s exact field schema, nor claim it reuses `DemandCorpus`'s Pydantic model or `EvaluationDatasetManifest`'s specific shape (that model is scoped to closed-universe sealed evaluation — see ADR 0019's related finding for `FrozenEmbeddingArtifact` about not misapplying a differently-shaped contract). The exact `PatentCorpusItem`/manifest schema is a contract-then-test-then-code decision for the implementation that follows this ADR, informed by what fields `AnnotationPoolEligibilityPolicy` and the existing retrievers (`DuckDbBM25Retriever`, `DuckDbCPCRetriever`) actually require (confirmed already compatible in principle: both operate on `PatentDocument`, which is agnostic to which corpus supplied it).

### 6. Fixture/offline testability, independent of credential availability

`EpoOpsClient.from_fixture_file` already supports offline replay. The ingestion contract (query construction, normalization, dedup, hash-ordering, manifest generation) must be verifiable end-to-end against a fixture before any live EPO OPS credentials are needed. Credential acquisition (`EPO_OPS_KEY`/`EPO_OPS_SECRET`) is an operational precondition for the real ingestion run, not a precondition for specifying or testing the contract.

### 7. PR-E restructuring

- **PR-E0 (this ADR + its implementation):** define and freeze `D` (already done, N=39) and `P` (new) as independent, symmetric experimental artifacts.
- **PR-E1 (already designed, unchanged, not reopened):** the dry-run — 8 selected demands, finalized annotation guide, `top-20 BM25 ∪ top-20 CPC → dedup → eligibility` pool, blind batches, independent annotation, IAA. Resumes at step 6 once `P` exists and satisfies §4's floor.
- **PR-E2 (future, not scoped here):** the full experiment over all 39 demands against the same frozen `P`, once PR-E1's exit criteria (execution-design spec §8) are met.

## What this ADR does not do

- Does not implement `PatentCorpus`, the ingestion script, or the normalizer generalization — deferred to a follow-up implementation plan (contract → test → code, per this repository's discipline).
- Does not run any live EPO OPS ingestion, and does not require credentials to exist yet.
- Does not reopen PR-E1's closed decisions (8 demands, guide, 1↔2/2↔3 boundaries, semantic-retriever deferral) — those stand exactly as frozen.
- Does not modify `DemandCorpus`, `AnnotationPoolEligibilityPolicy`, `CandidatePoolBuilder`, or any code merged in PR #56.
- Does not decide `PatentCorpusItem`'s exact field schema or manifest type.
- Does not evaluate, report, or claim anything about the resulting corpus's CPC/domain distribution — that is measured, not designed, once `P` is frozen.

## Consequences

### Positive

- Converts a data blocker into a real architectural improvement: `D` and `P` become symmetric first-class artifacts, matching the actual scientific unit (`D × P → ...`) instead of one frozen input and one ad hoc dependency.
- The demand-blind composition pipeline (§3) makes it structurally impossible for the patent universe to be shaped around the 8 selected demands — the same independence property PR-E's pool-construction design already protects at the retrieval stage, now protected one stage earlier, at corpus construction.
- Reuses existing, real infrastructure (`EpoOpsClient`) rather than introducing a new provider integration.
- The ex ante floor (§4) prevents a "corpus" that technically satisfies the contract but is too small to be scientifically meaningful from being silently accepted.

### Negative

- International, multi-jurisdiction ingestion (~50,000 target records) is a substantially larger undertaking than the previous 16- or even hundreds-record ES-only pilots — more implementation work, more ingestion time, more storage, and a live-retrieval (BM25/CPC over DuckDB) performance profile that has not been tested at this scale.
- Blocked on EPO OPS credentials for the real run — the fixture-testable contract (§6) mitigates this for implementation but not for producing the actual frozen `P` PR-E1 needs to resume.
- `OepmXmlNormalizer`'s reusability for non-ES/non-OEPM XML is unverified; if it does not generalize cleanly, a new or adapted normalizer is additional scope discovered during implementation, not accounted for here.
- Widens PR-E's overall timeline: PR-E1 (already designed and ready to execute) now waits on PR-E0's corpus construction rather than resuming immediately.

## Enforcement

A future PR-E0 implementation is **non-compliant** with this ADR if it:

1. Selects or filters `P`'s candidate records using any information about the 8 selected demands, the 39-demand corpus, or their CPC/domain content.
2. Uses API delivery order, or any non-`sha256(publication_id)`-based rule, to select the final N records.
3. Silently accepts `N_final < minimum_acceptable_N` (5,000) as if the contract were satisfied.
4. Applies CPC-section stratification or any other topical curation to `P`'s composition.
5. Claims or assumes `OepmXmlNormalizer` generalizes to non-ES/OPS XML without a passing contract test demonstrating it.
6. Reopens PR-E1's closed decisions (demand selection, guide, boundary criteria, semantic-retriever deferral) as part of this work.
7. Requires live EPO OPS credentials to exist before the ingestion contract itself can be tested.
