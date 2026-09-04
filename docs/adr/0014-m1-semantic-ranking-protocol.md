# ADR 0014: M1 Semantic Ranking Protocol — Frozen Embedding Artifact, Not a Live Provider

**Status:** Proposed
**Date:** 2026-09-04
**Scope:** Scientific definition of M1 (semantic/dense retrieval) for the sealed evaluation benchmark. Doc only — no code, no `EmbeddingProvider`/`SemanticRankingFeature`/`VectorStore`/`EmbeddingRepository` abstraction, no implementation. A follow-up PR implements exactly what this ADR decides, once it is Accepted.

---

## Context

M0 (ADR 0013, PR #28) is now a real, executable `derived_ranking_feature`: BM25 lexical scores computed deterministically from each patent's own observed title/abstract text, with no external dependency and no live computation surface beyond pure arithmetic. M1 (semantic/dense retrieval) has no equivalent today — `infrastructure/matching/dense_semantic.py` defines a working cosine-similarity retriever, but it has only ever been exercised with test-mock embedders, and the sealed benchmark's patents carry no embedding field. Making M1 real requires deciding, for the first time, what a semantic score for this benchmark actually *is* — not just wiring existing code together, the way M0 was.

The central question this ADR answers:

> **Is M1 a frozen, reproducible semantic model, or a live call to an external provider?**

**Decision: frozen.** A live API call (OpenAI, Google, Anthropic, or any other hosted embedding provider) is rejected for this evaluation harness, for three reasons specific to a sealed scientific benchmark:

1. **Reproducibility.** A hosted provider can silently change model weights behind a stable-looking endpoint name. A number computed today may not be the same number computed in six months, with no way to detect the drift from outside the provider.
2. **External dependency in the audit path.** ADR 0011 establishes the evaluation harness as an independent auditor of the product, deliberately decoupled from live infrastructure. A live embedding call during evaluation makes the audit depend on a third party's uptime, billing, and rate limits — the same category of problem ADR 0011 already excluded for the product's own retrieval.
3. **Precedent already set.** M0's derived feature is computed once, deterministically, entirely from observed data with no network access (ADR 0013 condition 3). A live-provider M1 would be a semantic feature under a weaker reproducibility standard than the lexical feature sitting next to it in the same ranking fusion — an inconsistency the ablation (M0-M6) would then have to explain away rather than rely on.

The alternative — computing embeddings once, offline, from a specific pinned model, and freezing the result as a sealed artifact — matches the pattern this repository already uses for everything else in the evaluation harness: the dataset (ADR 0006), the matching policy (ADR 0005), the study protocol (ADR 0011), and the model configuration manifest (ADR 0012) are all frozen, hash-sealed artifacts with explicit provenance. A frozen embedding artifact is the same pattern applied to embeddings.

---

## Decision

### 1. Embedding model

**Proposed: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.**

Rationale:
- **Multilingual, including Spanish.** The benchmark's patents are Spanish OEPM publications; demands are in Spanish and English. This model is explicitly trained for multilingual paraphrase/semantic-search across 50+ languages, not English-only.
- **Apache-2.0 license** — permissive, no field-of-use restriction, safe for a published scientific artifact (verified against the model's Hugging Face card: [sentence-transformers/paraphrase-multilingual-mpnet-base-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2)).
- **Open weights, runnable entirely offline** — no API key, no network call required at embedding-generation time or at evaluation time.
- **Widely validated** — a mature, heavily-used sentence-embedding model, not an obscure or unaudited one; failure modes are well understood in the literature.

An alternative considered: `intfloat/multilingual-e5-base` (also open-weight, MIT-licensed, also multilingual). Rejected only as the *primary* choice for this ADR — not because it is unsuitable, but because `paraphrase-multilingual-mpnet-base-v2` is explicitly tuned for paraphrase/semantic-similarity (the task M1 actually needs), while the E5 family expects a `"query: "` / `"passage: "` prefix convention that adds a formatting decision this ADR would otherwise have to make and justify. Recorded here so a future reviewer does not have to re-derive that this alternative was considered, not overlooked.

**This is a proposal for review, not a locked decision** — Status: Proposed. If a domain expert has a stronger reason to prefer a different model (patent-specific fine-tune, a model with demonstrated Spanish-patent-domain performance, etc.), that supersedes this default before implementation.

### 2. Exact version / pinning

The implementation PR must pin the **exact Hugging Face repository revision (commit hash)** used to download the model weights — not the mutable `main` branch reference. This ADR does not hardcode that hash now, because pinning it prematurely (before the implementation PR actually downloads and runs the model) risks recording a hash that was never the one actually used. The implementation PR records the revision hash it actually pulled, in the frozen artifact's provenance (§7).

### 3. Where it runs

**Offline, once, outside the evaluation harness** — a standalone generation script (analogous to `scripts/evaluation/run_pilot_benchmark.py`), not a code path inside `application/evaluation/matching_adapter.py` or any component invoked during an evaluation run. The evaluation harness reads the frozen artifact; it never computes an embedding itself. This mirrors ADR 0011's decoupling of the "laboratory" from the product, and ADR 0013's requirement that a derived feature's computation be reproducible from declared inputs, algorithm, and version — a one-time offline generation step is what makes those declarations checkable at all.

### 4. Licensing

Apache-2.0 (verified above). The generation script's own dependencies (the `sentence-transformers` library and its transitive dependencies) must also be checked for license compatibility before implementation — not assumed compatible because the model weights are permissively licensed.

### 5. How embeddings are generated

- **Input text:** the same fields already used for observed evidence elsewhere in this benchmark — patent `title + ' ' + abstract`, demand `title + ' ' + description`. No new text sources, no annotation text.
- **Determinism:** the model is run in inference (eval) mode — no dropout, no sampling. Given a fixed model revision, fixed input text, and a fixed library version, output vectors are bit-for-bit reproducible on CPU. (GPU floating-point non-associativity across different hardware/driver combinations is a known source of small numerical variance in deep learning inference; the implementation PR must state which hardware class the frozen artifact was generated on, and should generate on CPU if bit-exact cross-machine reproducibility is required — this ADR flags the tradeoff rather than resolving it, since it depends on choices the implementation PR makes.)
- **No annotations, no ground truth** as input, under the same ADR 0013 condition 2 that governs M0.

### 6. Frozen as an artifact

Yes. A new sealed artifact (working name: `data/evaluation/embeddings_pilot_benchmark.json`, or a more storage-appropriate format such as `.npy`/Parquet with a companion manifest — the implementation PR decides the file format; this ADR decides that it must be sealed the same way) stores one embedding vector per patent and one per demand from the closed benchmark, generated once and never regenerated in place.

### 7. Hash / provenance

The frozen embedding artifact's manifest must record, at minimum:
- Model name and exact pinned revision (§2)
- License (§4)
- Generation script identity (path + git commit it was generated from)
- Library versions used (`sentence-transformers`, `torch`/backend, etc.)
- Hardware class used for generation (§5)
- A self-referential integrity hash, following the same pattern as `MatchingPolicyConfig.policy_sha256`, `StudyProtocol.protocol_sha256`, and `ModelConfigurationManifest.config_sha256` (ADR 0006/0011/0012) — tamper-evident, not a cryptographic seal, exactly as those ADRs already state about their own hashes.

### 8. Dimensionality

768 (the native output dimension of `paraphrase-multilingual-mpnet-base-v2`). Recorded explicitly in the artifact's manifest so a future reader does not have to look it up externally.

### 9. Normalization

Embeddings are L2-normalized before storage. This is standard practice for cosine-similarity retrieval and matches the existing `DuckDbDenseSemanticRetriever`'s assumption that vectors are comparable via cosine similarity.

### 10. Similarity metric

Cosine similarity, via the existing `infrastructure/matching/vector_math.cosine_similarity` — already implemented, already used by `DuckDbDenseSemanticRetriever`. No new similarity computation is introduced; M1's derived-feature computation reuses this exactly the way M0 reused `DuckDbBM25Retriever`'s existing scoring math.

### 11. What happens if the model changes

Changing the embedding model, its revision, or its generation procedure produces a **new** frozen artifact under a new version identifier — never an in-place edit of the sealed one. This is the same principle ADR 0012 §6 already states for model configurations: a changed input requires a new, explicitly named artifact and provenance record, not a silent overwrite. Any such change must be re-justified against this ADR (or a superseding one) before use in an ablation or final inference.

### 12. Reproducibility

Given the pinned model revision (§2), the documented generation procedure (§5), the pinned library versions (§7), and the frozen input text (already sealed by ADR 0006), a third party can regenerate the embedding artifact and verify it against the declared hash (§7). This is the same reproducibility contract ADR 0013 §2 condition 3 already requires of M0, restated for what M1 specifically needs to declare to satisfy it.

---

## What this ADR does not do

- Does not implement any code. No `EmbeddingProvider`, `SemanticRankingFeature`, `VectorStore`, `EmbeddingRepository`, or multi-provider abstraction is introduced — none of that is needed to state this decision, and building it now would be designing for a future this ADR has not yet earned by having a working M1.
- Does not generate the frozen embedding artifact. That is the follow-up implementation PR's job, once this ADR is Accepted.
- Does not decide M1's exact file format, the generation script's exact structure, or how `DefaultMatchingAdapter` wires the frozen artifact in — those are implementation details for the follow-up PR, analogous to how ADR 0013 authorized the *category* of derived ranking features without deciding `compute_bm25_scores`'s exact signature.
- Does not touch M0, ADR 0007, ADR 0013, or any code from PR #28.

## Consequences

### Positive
- M1 becomes as reproducible and audit-independent as M0 — no live dependency introduced into the evaluation harness at any point.
- The choice of model, license, and generation procedure is recorded and reviewable *before* any embedding is computed, rather than being discovered after the fact from whatever a first implementation happened to do.

### Negative
- A locally-run open-weight model may underperform a state-of-the-art hosted embedding API on raw semantic quality. This is accepted: reproducibility and independence from a live provider matter more to this study's validity than maximizing M1's absolute score — the same tradeoff ADR 0012 already accepted for `alpha/beta/gamma` ("correctness of the evaluation matters more than the score it produces").
- Generating and freezing an embedding artifact is a real implementation cost the M0-M6 ablation cannot proceed without, once this ADR is Accepted.

## Enforcement

A future implementation PR is **non-compliant** with this ADR if it:
1. Calls a live, hosted embedding provider from any code path invoked during an evaluation run.
2. Uses an unpinned model reference (a mutable branch or "latest" tag) for the frozen artifact's provenance.
3. Regenerates or edits the frozen embedding artifact in place rather than producing a new versioned artifact.
4. Computes an embedding from annotation or relevance-grade text.
5. Introduces a general-purpose embedding/vector-store abstraction not required by the specific model and format this ADR (or its accepted revision) actually specifies.
