# Audit of `main` for the technology white-space pivot

**Status:** Audit snapshot. Read-only; no component was changed, removed or re-tested.
**Snapshot:** `main` at `c9d56e1` (2026-10-20)
**Date:** 2026-10-20
**Used by:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md)
**Scope:** Which parts of Nexus can serve a white-space discovery product, which depend on the offer–demand matching premise, and what must be decoupled before new work starts. **Documentary only.**

---

## 1. Method and its limits

* Source of the findings: reading the repository (README, `docs/`, ADRs 0001–0031, `backend/src/main`, `scripts/`, `frontend/src/main`), a structural code map, and `git`/`gh` queries for branches and open pull requests.
* **Not done:** the test suite was not run; test files were located and the white-space and landscape tests were read, but the roughly one thousand tests were not read one by one. The test count and coverage quoted by the README badges (995 tests, 95.5 %) are repeated here unverified.
* A "dependency on matching" below means an import or a data-model field, found by search. A zero result of such a search means "none found", not "none exists".

## 2. State of `main`

* **Product.** The deployed product is the demand-to-assets MVP: it ranks Spanish patents and utility models for one of 21 example demands with a frozen multilingual embedding model. It runs as its own process (`infrastructure/mvp_entrypoint.py`). Importing that entrypoint and inspecting the loaded modules shows that its import graph contains `application.landscape.cpc_taxonomy` (through the matching engine) but **not** `landscape/metrics.py`, `clustering.py`, `context.py`, `infrastructure/api.py`, `analysis_pipeline.py`, `application/research_service.py` or the agent stack. The README states that it does not detect unexploited assets.
* **Two heads (ADR 0017).** A generative head (landscape heuristic plus a multi-agent loop, still defined in `infrastructure/api.py` and `analysis_pipeline.py` but not served by the MVP) and a deterministic head (the matching engine and its sealed evaluation harness). ADR 0017 already states that the first is not scientific evidence for ranking efficacy.
* **Scientific state.** The matching evaluation work (ADRs 0006–0016, 0018–0020, 0027–0031) concerns whether a retrieval pipeline ranks relevant patents for a demand. Its confirmatory step is blocked: see the construct-validity issues recorded on open pull requests #112 and #113.
* **Existing white-space code.** `application/landscape/` defines a white-space score; it is analysed in §5.

## 3. Inventory

Decisions: **Reuse** (use as is), **Adapt** (reuse after a bounded change), **Freeze** (leave untouched, add no new dependency on it), **Decouple** (a dependency that must be cut before new code relies on the component), **Retire candidate** (proposed for later removal; nothing is removed by this audit).

| Component | Path | Decision | Reason |
|---|---|---|---|
| Patent document model (dates, IPC, CPC, family id, assignees) | `domain/models/patent.py` | Reuse | Publication-level model with the fields a white-space analysis needs. Not tied to matching. |
| Provenance primitives (`FieldObservation`, snapshot, evidence) | `domain/models/evidence.py`, `snapshot.py` | Reuse | Source, version and transformation tracking is what the pivot requires. |
| Source protocol and raw payload with SHA-256 | `domain/protocols/sources.py` | Reuse | A streaming source port already exists. |
| Ingestion pipeline, manifest builder, validator | `application/ingestion/` | Adapt | Generic shape; the normalisers are source-specific (OEPM gazette, EPO OPS, InnoGet, Lombardia). The ST36 bibliographic XML of the corpus in [the corpus characterization](oepm-biblio-corpus-characterization.md) needs its own adapter. |
| OEPM and EPO OPS clients | `infrastructure/sources/patent/` | Adapt | Reusable for patents; none handles the account-protected OpenData files. |
| BigQuery and DuckDB patent sources | `infrastructure/sources/bigquery_patents.py`, `duckdb_patents.py` | Adapt | Parameterised by query; CPC-centred. |
| Parquet store, DuckDB engine, raw store | `infrastructure/storage/` | Reuse | Format and store are neutral. |
| Frozen-artifact and hash discipline (manifests, verification at start-up) | `infrastructure/operational/artifacts.py`, ADRs 0006, 0012 | Reuse | The reproducibility pattern the pivot asks for. |
| Temporal eligibility contract | ADR 0018 | Reuse (concept) | Defines information available at a cut-off; the white-space design needs the same discipline with a different unit. |
| Family-aware evaluation contract | ADR 0027 | Reuse (concept) | The corpus has no family identifier (see ADR 0036, P4), so the principle applies but the mechanism does not. |
| Inferential statistics (Wilcoxon, bootstrap, comparative harness) | ADRs 0010, 0011; `application/evaluation/` | Adapt | The harness compares *rankers on demands*. Its statistical ideas transfer; its data model (demand, pool, relevance label) does not. |
| Scientific-results publication | ADRs 0023–0025; `storage/scientific_results_publisher.py` | Adapt | Publishing machinery is reusable; track semantics refer to the matching tracks. |
| Project status contract and architecture checker | ADRs 0008, 0021, 0022; `scripts/check_architecture.py` | Reuse | Layer rules and quality gates apply to any new context. |
| WIPO IPC technology concordance (35 fields) | `docs/phase2-wipo-ipc-technology-concordance-freeze.md` | Reuse | A frozen coarse taxonomy, usable as a taxonomy-change sensitivity. |
| Runtime patent record and cluster models | `domain/models/runtime_schemas.py` | Decouple | `PatentRecord` is CPC-only; `PatentCluster` carries `white_space_score` and `is_white_space`; the same file holds agent outputs (`ScoreCard`, `InventionCandidate`). |
| White-space score and quadrants | `application/landscape/metrics.py` | Freeze, **retire candidate** | See §5. |
| Landscape clustering | `application/landscape/clustering.py` | Freeze, **retire candidate** | Groups by the first four characters of the first CPC code and falls back to the literal `"H01M"` when a patent has no CPC code or a demand has no prefix. |
| Landscape domain context | `application/landscape/context.py` | Freeze, **retire candidate** | Hard-coded list of supported domains and keywords (battery chemistries and others). |
| Concept-to-CPC taxonomy for demands | `application/landscape/cpc_taxonomy.py` | Freeze | Maps demand text to CPC prefixes through an injected policy; a demand-side mechanism. **Loaded by the deployed MVP**, so it is not a retire candidate even though it lives in the landscape package. |
| Agent stack (inventor / adversarial / governor), research service, analysis pipeline, legacy API routes | `infrastructure/adk/`, `analysis_pipeline.py`, `application/research_service.py`, `infrastructure/api.py` | Freeze, **retire candidate** | Stochastic, quota-bound, outside the MVP import graph (checked as described in §2); ADR 0017 already classes it as non-evidential. |
| Synthesis engine | `application/synthesis/` | Freeze | Imports the demand model; not examined further. |
| Matching engine, evidence evaluator, feature extractor, candidate pool builder | `application/matching/` | Freeze | The auxiliary validation tool the brief keeps. New code must not import it, and it must not import new code. |
| BM25, CPC and dense retrievers, eligibility, vector maths | `infrastructure/matching/` | Freeze | Same. |
| Matching evaluation harness and metrics | `application/evaluation/`, `domain/models/evaluation.py` | Freeze | Built around demand–patent relevance judgements. |
| Origin policy and resolver | `domain/models/origin_policy.py`, `application/ingestion/origin_resolver.py`, ADR 0003 | Freeze | A matching-time notion of origin. |
| Demand model, demand sources, annotation and independence audits, corpus-expansion contract | `domain/models/demand.py`, `application/annotation/`, ADRs 0029–0031 | Freeze | Exist only for the demand side. |
| MVP (operational corpus, router, frontend demand picker) | `infrastructure/operational/`, `frontend/src/main` | Freeze | Deployed; not to be disturbed. A white-space view would be a separate screen if and when the evidence supports one. |
| Scientific verification workspace | ADRs 0023, 0024 | Reuse (pattern) | Independent consumer of published results. |

## 4. Dependencies that presuppose an offer and a demand

* `domain/models/demand.py` is imported by about thirty modules, including `domain/models/evaluation.py`, the protocols `matching`, `evaluation`, `agents` and `demand_repository`, all of `application/matching/`, `application/evaluation/matching_adapter.py`, the ingestion normalisers and origin resolver, `application/synthesis/`, the MVP router and demands (`infrastructure/operational/`), and the matching retrievers. The demand concept is therefore inside the domain layer, not at its edge.
* The landscape modules do not import the demand model: `metrics.py` and `clustering.py` take demand signals as untyped objects and read a `cpc_prefix` attribute from them, and the score gives them a 25 % weight (`demand_intensity`).
* `domain/models/opportunity.py` (`OpportunityHypothesis.target_demand_ids`) assumes a demand target.
* `domain/models/scientific_results.py` carries white-space metrics, including `demand_intensity`, in the published results contract.
* `scripts/publish_scientific_results.py` calls `compute_cluster_landscape`.
* Tests that import the landscape code: `test_metrics.py`, `test_clustering.py`, `test_context.py`, `test_cpc_taxonomy.py`, `test_scientific_results.py`, `test_publish_scientific_results.py`, and `providers/adk/test_api_endpoints.py`.

Removing or changing any of these therefore also changes a published-results contract and several tests, which is why this audit removes nothing.

## 5. The existing white-space score

`compute_white_space_metrics` in `application/landscape/metrics.py` computes

`W = 0.40·(1 − density) + 0.20·recency + 0.15·citation_traction + 0.25·demand_intensity`

and sets `is_white_space = W ≥ 0.50`, then labels clusters with quadrants such as "Unmet Opportunity".

Observations, each checkable in the source:

* The weights and the 0.50 threshold are constants with no derivation or validation in the repository. The same score appears in `docs/architecture.md`.
* `density` is the cluster size divided by the largest cluster size, so it depends on the other clusters in the same run.
* `recency` assumes a 20-year horizon and the mean filing year, with a reference year defaulting to 2026.
* A quarter of the score is demand-side, which makes the notion unusable when no demand exists.
* The unit of analysis is the first four characters of the *first* CPC code, discarding every other code of the patent.
* The labels ("Unmet Opportunity") assert an interpretation the score does not test.

The pivot brief asks that a score not be presented as an opportunity or a probability of success and that rules not be hard-coded for domains. The existing score and the domain list in `context.py` conflict with both. This audit records the conflict and leaves the decision on retirement to a later pull request.

## 6. Where classifications, embeddings and filters are used

| Mechanism | Where | Relevant to white space? |
|---|---|---|
| CPC codes | `PatentRecord.cpc_codes`, `infrastructure/matching/duckdb_cpc.py`, `application/landscape/*`, concordance docs | Yes, as a classification, but the OEPM bibliographic corpus carries **IPC** and no CPC. |
| IPC codes | `PatentDocument.classifications_ipc`, WIPO concordance | Yes; this is the unit of ADR 0036. |
| Embeddings and cosine similarity | `infrastructure/embeddings/`, `infrastructure/matching/dense_semantic.py`, `vector_math.py`, `application/evaluation/matching_adapter.py` | Not needed by the first experiment; optional later as a representation. |
| BM25 | `infrastructure/matching/duckdb_bm25.py` | No. |
| Origin rules | `origin_policy.py`, `origin_resolver.py` | No. |
| Geographic filters | applicant-country condition in the selection SQL of `scripts/build_operational_corpus.py`; `OepmXmlNormalizer` takes `target_country` as a constructor parameter (ADR 0020) | Corpus selection must be a declared parameter of the corpus, not a code path. |
| Hard-coded domains | `landscape/context.py` | Must not be carried over. |

## 7. What the existing tests establish

* The architecture tests (`backend/test/unit/architecture/`) and the docs gate verify layer rules, ADR invariants, frozen-artifact integrity and structural documentation properties. They apply to any new code.
* The landscape tests verify that the formulas compute what they say. `test_metrics.py` checks, for example, that unobserved citations do not drag the average. They do not test whether the resulting score identifies anything real, because no ground truth or temporal outcome exists for it.
* The matching and evaluation tests verify the contracts and statistics of the ranking study.
* No existing test validates a hypothesis about technology white spaces.

## 8. Target architecture (proposal, not a decision)

A new bounded context, with the repository's three layers, that the existing contexts do not import and that does not import them:

* **Domain.** An observation (a fact from one source, with provenance), a technology unit (a classification or a set of them), an observation window and a candidate (a unit with evidence, indicators, baseline and uncertainty), plus ports for sources, detectors and baselines.
* **Application.** Construction of series and co-classification structures by window, execution of detectors and baselines, temporal evaluation.
* **Infrastructure.** One adapter per source, with its own annotation schema; reading of frozen artifacts; publication of results.

Rules: sources are never merged into one classification; a source adapter adds no code to the analytical core; detectors are configured, not hard-coded to a country, domain or sector; matching, if it returns, is a consumer.

The decisions that would turn this sketch into a design belong to later ADRs, after ADR 0036 is approved.

## 9. Numbering and cross-references of ADRs

* `main` contains ADRs 0001–0031. The docs gate passes on `main` (106 markdown files, 31 ADRs).
* The open pull requests #112 and #113 carry ADRs 0032–0035 on their branches (corpus-expansion acquisition, source-qualification gate, TED source admission, and the OEPM production-scale patent corpus contract). They are not merged, and both pull requests are blocked.
* `docs/phase2-wipo-ipc-technology-concordance-freeze.md` refers to one of those unmerged ADRs by file name and as `ADR-0035`, a form the docs gate does not match. The reference is dangling on `main`.
* **This work uses 0036**, leaving 0032–0035 to the branches that already hold them. If those branches are renumbered or abandoned, the gap remains and is harmless.
* The OEPM production-scale patent corpus contract that is proposed on those branches concerns a different corpus (retrieval universe for matching) and a different acquisition route. Nothing here supersedes it; whether the two should be reconciled is an open question (ADR 0036, P8).

## 10. Not done in this audit

No component was removed, deprecated or modified; no test was added or changed; no dependency changed; no contract changed. `application/landscape/metrics.py` and `application/landscape/clustering.py` are untouched.
