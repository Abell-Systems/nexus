# PR-E Dry-Run Execution: Demand Selection, Embeddings, Guide, Blind Batches

**Status:** Draft — presented for approval before any artifact is produced.
**Roadmap anchor:** `docs/roadmap.md` §3, table row **PR-E** ("Blinded re-annotation + IAA dry-run + CPC-auto card"), acceptance criteria: "κ reported, classifier precision/recall reported." PR #56 (merged, `ae3d111`) implemented the instrument (`CandidatePoolBuilder`, `AnnotationPoolEligibilityPolicy`, blind-export boundary, `compute_iaa`) but explicitly deferred everything in this document.
**Depends on:** ADR 0019, and the PR-E instrument spec (`docs/superpowers/specs/2026-09-08-pr-e-candidate-pool-blind-annotation-iaa-design.md`).

## 1. Purpose

#56 built and merged the *instrument*. This phase is the *execution of the scientific protocol* on that instrument: produce one frozen, reproducible dry-run — a real candidate pool, a real blind batch, and real independent judgments from Valentín and Lydia — to validate that the annotation protocol itself works, before scaling to the full N=39 corpus (and, later, before PR-F).

This document is the contract for that execution. It exists so that human decisions made during this phase (which demands, where the 1↔2/2↔3 boundaries sit) get made deliberately and then frozen — not improvised while an artifact is already half-built.

## 2. Scope

**In scope for this document:** defining the steps, their artifacts, their entry/exit criteria, and — critically — which of them are automatable, which require a domain judgment call, and which are human annotation that only Valentín/Lydia can do. It does not itself select the 6-8 demands, write the guide's boundary criteria, or annotate anything — those happen after this document is approved.

**Out of scope (unchanged from the instrument spec):** the full 39-demand corpus, DEV/TEST split, any M0/M1/M2 efficacy claim, statistical testing (Wilcoxon/paired bootstrap/BH) — all PR-F.

## 3. The 7 steps, and who owns each

(Originally 8 — step 3, embedding generation, is struck through below: §6 resolves it as deferred, not executed in this dry-run.)

| # | Step | Owner | Artifact |
|---|---|---|---|
| 1 | Propose 6–8 demands from N=39, justified against selection criteria (§4) | **Me — proposal only** | `docs/annotation/phase2-dry-run-selection.md` (draft) |
| 2 | Final demand selection | **Valentín + Lydia** | same file, finalized |
| 3 | ~~Generate frozen embedding artifact~~ — **resolved (§6): deferred, not part of this dry-run** | — | — |
| 4 | Write annotation guide: 0-3 scale, worked examples | **Me — draft only** | `docs/annotation/phase2-guide.md` (draft) |
| 5 | Fix operational criteria for 1↔2 and 2↔3 boundaries | **Valentín + Lydia** | same file, finalized |
| 6 | Build the independent candidate pool per demand (BM25 top-20 ∪ CPC top-20 → dedup → eligibility) and the single frozen `AnnotationBatch` per demand | Me (script, using #56's `CandidatePoolBuilder`/`build_annotation_batch` directly — no new library code) | `data/annotation/dry_run/batch_<demand_id>.json` |
| 7 | Independent annotation | **Valentín + Lydia, separately, no shared judgments, pool/batch frozen and untouched** | `data/annotation/dry_run/judgments_valentin.json`, `judgments_lydia.json` (hashed, frozen — same pattern as the N=39 corpus artifacts) |
| 8 | Compute IAA (`compute_iaa`, already merged) and review confusion matrix | Me (run the calculator) — **interpretation and the freeze/revise decision is Valentín + Lydia's** | `data/annotation/dry_run/iaa_report.json` + written summary |

Step 6 is mechanical once its inputs (finalized demand list, finalized guide) exist — no new production code beyond what #56 already merged, plus a small orchestration script (same category as `scripts/freeze_phase2_demand_corpus.py`).

## 4. Demand selection criteria (for step 1's proposal — not the final decision)

Per the design agreed for the instrument itself: this is a **stress test of the protocol**, not a statistical sample.

- Technical/domain diversity across the 6-8.
- Lexical ambiguity (terms with multiple plausible technical readings).
- At least one or two demands where CPC concordance is likely to carry real signal (a well-populated `target_cpc_prefixes`).
- Demands where BM25 and CPC are likely to diverge (different candidates surfaced by the two methods) — deliberately sought out, not avoided.

**Scope note (per §6's resolution): semantic-retriever divergence is not evaluated in this dry-run.** A corpus-wide semantic embedding pipeline (populating patent embeddings over an open, unbounded candidate universe) is future infrastructure — see §6 — and is not introduced solely to satisfy PR-E. The independent pool for this dry-run is `top-20 BM25 ∪ top-20 CPC → dedup → eligibility`, not the three-way union originally envisioned. This still exercises pool independence from M0/M1/M2, heterogeneous-retriever union, dedup, `AnnotationPoolEligibilityPolicy`, blind export, batch freezing, independent annotation, and IAA — everything this phase needs to validate. It does not let PR-F later claim the dry-run validated the semantic retriever's contribution to the pool; that remains open.
- **Practical filter, discovered during instrument planning (ADR 0019):** all 39 demands have `posted_date: null`. Wayback Machine gave a confirmed upper-bound capture for 6 of them (`INNOGET-1625/1689/1932/1935/1972/2258`) — preferring some of these in the proposal narrows the `TEMPORAL_UNKNOWN` fraction of the dry-run pool, which is useful for exercising the `ELIGIBLE`/`EXCLUDED_TEMPORAL` branches too, not just `TEMPORAL_UNKNOWN`. Not a hard requirement — a proposal of all-`TEMPORAL_UNKNOWN` demands would still be valid, just less informative about the eligibility policy's other branches.

## 5. Guide draft criteria (for step 4's draft — not the final boundaries)

Ordinal 0-3 (spec §7, unchanged): 0 not relevant, 1 marginally relevant, 2 relevant, 3 highly relevant. The draft will propose example pairs per grade and a first pass at 1↔2/2↔3 language, but **§7's non-negotiable statement stands**: annotators grade technical relevance, not temporal/prior-art eligibility, and the guide draft must not smuggle date-based reasoning into the grading criteria (consistent with removing `publication_date` from the annotator-facing evidence in #56's review).

## 6. Resolved: semantic retriever is deferred, not adapted into `FrozenEmbeddingArtifact`

**Original question:** does `FrozenEmbeddingArtifact` fit the dry-run corpus, and if not, do we extend it or create a PR-E-specific type?

**What inspection of the real code found — deeper than an identity/hash mismatch:**

1. `FrozenEmbeddingArtifact.verify_source_dataset` (`domain/models/evaluation.py`) requires `patent_embeddings`' keys to *exactly match* a sealed `ValidatedDataset`'s publication_ids — a **closed, predetermined patent universe**. Confirmed against the real pilot artifact (`data/evaluation/embeddings_pilot_benchmark.json`): 3 demand embeddings, 15 patent embeddings, exactly the sealed 45-pair benchmark's patents. This type is architecturally scoped to sealed evaluation (`application/evaluation/matching_adapter.py`'s raw-cosine path) — not a coincidence of the dataset it happens to reference.
2. `DuckDbDenseSemanticRetriever` (`infrastructure/matching/dense_semantic.py`) — the live retriever `CandidatePoolBuilder` would need for a semantic branch — requires the opposite shape: a *live* `TextEmbedder` call for the demand at retrieval time, and patent embeddings pre-loaded into a DuckDB column over an **open, not-predetermined universe** (whatever the table holds, since which patents end up in any given demand's pool is discovered by retrieval, not known in advance).
3. **No pipeline in this codebase populates that embedding column outside the retriever's own isolated vertical-slice test** (`backend/test/integration/infrastructure/matching/test_dense_semantic_vertical_slice.py`) — it has never been wired to a real corpus or used in production.

**Decision:** the closed-universe/open-universe mismatch means extending `FrozenEmbeddingArtifact` would misapply a sealed-evaluation-shaped contract to a live-retrieval problem — a bad abstraction regardless of whose identity it binds to, not merely a validation-path fix. Building the missing open-corpus embedding pipeline (embedding the full ES patent snapshot, persisting it, keeping it reproducible/updatable) is real, non-trivial infrastructure work — scoping it into this execution phase would silently expand PR-E from *validating the annotation instrument* into *building semantic retrieval infrastructure for the first time*, two different problems.

**Resolution: the semantic retriever is deferred out of this dry-run entirely.** The independent pool for PR-E's dry-run is `top-20 BM25 ∪ top-20 CPC → dedup → eligibility` (§4 updated accordingly). `FrozenEmbeddingArtifact` is not modified. No second embedding-artifact type is created. Step 3 (embedding generation) is removed from §3's table.

**Future work — Open-Corpus Semantic Retrieval (not PR-E, not PR-F, tracked separately):** `patent corpus → embedding generation → persistent embedding store → DuckDbDenseSemanticRetriever → validation → reproducibility/incremental-update policy`. Deciding how to freeze/version embeddings over an open, growing universe is a real architectural problem in its own right and deserves its own spec/ADR when it's actually needed — not one forced open now to unblock a dry-run that doesn't require it.

## 7. What gets versioned

Two different statuses, not one undifferentiated "committed and hashed":

- **Drafts** (step 1's demand-selection proposal, step 4's guide draft): committed to git for review, but explicitly labeled draft — no manifest, no sha256, no frozen status. A draft superseded by the human-finalized version is not a scientific artifact and must not be presented as one.
- **Frozen scientific artifacts** (the finalized selection + guide from steps 2/5, the embedding artifact from step 3 once §6 is resolved, the pool/batch files from step 6, and the two annotators' judgment files from step 7): committed, hashed, and manifested the same way `dataset_phase2_demand_corpus_n39.*` was. Judgment files in particular are frozen the moment each annotator finishes, before IAA is computed (spec §9 non-negotiable: judgments cannot alter pool membership, and by the same logic, judgments already submitted are not revised after seeing the other annotator's or after computing κ).

## 8. Entry / exit criteria

**Entry to step 6 (pool/batch generation):** steps 2 and 5 finalized (demand list and guide boundaries signed off by Valentín + Lydia — done, `phase2-dry-run-selection.md`/`phase2-guide.md` both FINAL). §6 is resolved (semantic deferred) — no longer a blocker.

**BLOCKED ON CORPUS DATA (found 2026-09-08, while starting step 6):** the only ES patent corpus in this repository (`data/snapshots/patents_es_snapshot.duckdb`) has 16 records, explicitly labeled "Pilot baseline corpus for proof-of-method validation," with a CPC distribution (detergents, batteries, plumbing, polymers, control systems, power, machining, catalysts, measurement, kitchenware, alloys, pesticides, water treatment, valves) that barely overlaps the 8 selected demands' domains (welding, hydrogen electrolysis, cosmetics/algae, water sensing, fuel oil, steel). Running `CandidatePoolBuilder` against it would produce empty or near-empty pools for most demands — a formally-executable but scientifically weak artifact, not a real test of the annotation protocol on a realistic pool.

Decided (2026-09-08): **do not** proceed with the 16-patent corpus, even caveated. **Do not** hand-pick a domain-matched ad hoc patent set either — that would introduce candidate selection before retrieval, contaminating exactly the independence PR-E exists to protect. Step 6 is blocked until a sufficiently large, technically relevant ES patent corpus is ingested and frozen — separate data-infrastructure work, not a PR-E protocol change. Steps 1-5 (selection, guide, scope, §6) remain closed and are not reopened by this blocker. Before any ingestion: define the dry-run's minimum corpus size/relevance bar, identify a reproducible source, decide how it gets frozen/versioned (same discipline as `dataset_phase2_demand_corpus_n39.*`), and confirm it works with `AnnotationPoolEligibilityPolicy` — only then ingest.

**Entry to step 7 (annotation):** step 6's batches frozen and hashed.

**Exit of this phase (the gate before any PR-F work, per spec §10 and roadmap §3):**
- κ (weighted) acceptable **and** disagreements concentrate on adjacent boundaries (1↔2, 2↔3) with no structural ambiguity → freeze protocol, proceed to scale to the full 39 demands (still Lab track, still ahead of PR-F).
- κ low, or a systematic pattern in the confusion matrix → do **not** patch labels. Revisit guide/definitions, repeat the dry-run.
- This decision belongs to Valentín + Lydia, informed by the IAA report I compute — not something I decide unilaterally.

## 9. What is deliberately outside my authority in this phase

- Final demand selection (step 2).
- Final 1↔2/2↔3 boundary language (step 5).
- The annotation itself (step 7) — I do not generate, simulate, or suggest grades.
- The freeze-vs-revise decision (§8 exit criteria) — I report the numbers, the decision is human.
