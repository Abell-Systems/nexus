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

## 3. The 8 steps, and who owns each

| # | Step | Owner | Artifact |
|---|---|---|---|
| 1 | Propose 6–8 demands from N=39, justified against selection criteria (§4) | **Me — proposal only** | `docs/annotation/phase2-dry-run-selection.md` (draft) |
| 2 | Final demand selection | **Valentín + Lydia** | same file, finalized |
| 3 | Generate frozen embedding artifact for the selected demands | Me (script), same pattern as `embeddings_pilot_benchmark.json` (ADR 0014) | `data/evaluation/embeddings_phase2_dry_run.json` + manifest/hash — **blocked on §6 open question** |
| 4 | Write annotation guide: 0-3 scale, worked examples | **Me — draft only** | `docs/annotation/phase2-guide.md` (draft) |
| 5 | Fix operational criteria for 1↔2 and 2↔3 boundaries | **Valentín + Lydia** | same file, finalized |
| 6 | Build the independent candidate pool per demand (BM25 top-20 ∪ CPC top-20 ∪ semantic top-20 → dedup → eligibility) and the single frozen `AnnotationBatch` per demand | Me (script, using #56's `CandidatePoolBuilder`/`build_annotation_batch` directly — no new library code) | `data/annotation/dry_run/batch_<demand_id>.json` |
| 7 | Independent annotation | **Valentín + Lydia, separately, no shared judgments, pool/batch frozen and untouched** | `data/annotation/dry_run/judgments_valentin.json`, `judgments_lydia.json` (hashed, frozen — same pattern as the N=39 corpus artifacts) |
| 8 | Compute IAA (`compute_iaa`, already merged) and review confusion matrix | Me (run the calculator) — **interpretation and the freeze/revise decision is Valentín + Lydia's** | `data/annotation/dry_run/iaa_report.json` + written summary |

Steps 3 and 6 are mechanical once their inputs (finalized demand list, finalized guide) exist — no new production code beyond what #56 already merged, plus small orchestration scripts (same category as `scripts/freeze_phase2_demand_corpus.py`).

## 4. Demand selection criteria (for step 1's proposal — not the final decision)

Per the design agreed for the instrument itself: this is a **stress test of the protocol**, not a statistical sample.

- Technical/domain diversity across the 6-8.
- Lexical ambiguity (terms with multiple plausible technical readings).
- At least one or two demands where CPC concordance is likely to carry real signal (a well-populated `target_cpc_prefixes`).
- Demands where BM25/CPC/semantic are likely to diverge (different candidates surfaced by different methods) — deliberately sought out, not avoided.
- **Practical filter, discovered during instrument planning (ADR 0019):** all 39 demands have `posted_date: null`. Wayback Machine gave a confirmed upper-bound capture for 6 of them (`INNOGET-1625/1689/1932/1935/1972/2258`) — preferring some of these in the proposal narrows the `TEMPORAL_UNKNOWN` fraction of the dry-run pool, which is useful for exercising the `ELIGIBLE`/`EXCLUDED_TEMPORAL` branches too, not just `TEMPORAL_UNKNOWN`. Not a hard requirement — a proposal of all-`TEMPORAL_UNKNOWN` demands would still be valid, just less informative about the eligibility policy's other branches.

## 5. Guide draft criteria (for step 4's draft — not the final boundaries)

Ordinal 0-3 (spec §7, unchanged): 0 not relevant, 1 marginally relevant, 2 relevant, 3 highly relevant. The draft will propose example pairs per grade and a first pass at 1↔2/2↔3 language, but **§7's non-negotiable statement stands**: annotators grade technical relevance, not temporal/prior-art eligibility, and the guide draft must not smuggle date-based reasoning into the grading criteria (consistent with removing `publication_date` from the annotator-facing evidence in #56's review).

## 6. Open question: does `FrozenEmbeddingArtifact` fit the dry-run corpus?

Checked against the real model (`domain/models/evaluation.py::FrozenEmbeddingArtifact`) before assuming it applies: it requires `dataset_sha256` — validated (`verify_source_dataset`) against an already-loaded `ValidatedDataset`, which wraps a sealed `EvaluationDataset` (patents + annotations already present). The N=39 corpus is a `DemandCorpus` (pre-annotation, pre-patent-pairing) — a different, earlier-stage sealed type. There is no `EvaluationDataset` for the dry-run yet, because producing the annotations *is* this phase's goal.

**This must be resolved before step 3, not assumed — and not resolved by picking whichever option is less code.**

> **`FrozenEmbeddingArtifact` is not modified, and no second embedding-artifact contract is created, until the question below is answered.**

The question to answer first is not "how do we make the model accept a `DemandCorpus`" — it's **what entity is this dry-run scientifically freezing**. Here, the artifact is demand embeddings for a *selected subset*, produced *before any judgment exists* — conceptually `embedding artifact → (N=39 DemandCorpus identity, selection identity, model/pipeline identity)`, not `embedding artifact → ValidatedDataset` (which presupposes patents + annotations already sealed, the thing this phase is producing evidence toward, not starting from). Extending `FrozenEmbeddingArtifact` to accept a `DemandCorpus` risks a bad abstraction — a demand-stage artifact wearing an evaluation-dataset-stage artifact's shape — not just a validation-path change.

This is left an **open architectural decision**, with that framing as its resolution criterion, to be settled explicitly (in writing, one paragraph is enough) before step 3 starts — not discovered mid-script.

## 7. What gets versioned

Two different statuses, not one undifferentiated "committed and hashed":

- **Drafts** (step 1's demand-selection proposal, step 4's guide draft): committed to git for review, but explicitly labeled draft — no manifest, no sha256, no frozen status. A draft superseded by the human-finalized version is not a scientific artifact and must not be presented as one.
- **Frozen scientific artifacts** (the finalized selection + guide from steps 2/5, the embedding artifact from step 3 once §6 is resolved, the pool/batch files from step 6, and the two annotators' judgment files from step 7): committed, hashed, and manifested the same way `dataset_phase2_demand_corpus_n39.*` was. Judgment files in particular are frozen the moment each annotator finishes, before IAA is computed (spec §9 non-negotiable: judgments cannot alter pool membership, and by the same logic, judgments already submitted are not revised after seeing the other annotator's or after computing κ).

## 8. Entry / exit criteria

**Entry to step 6 (pool/batch generation):** steps 2 and 5 finalized (demand list and guide boundaries signed off by Valentín + Lydia), §6's open question resolved.

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
