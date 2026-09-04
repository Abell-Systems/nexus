# ADR 0014: M1 Semantic Ranking Protocol — Frozen Embedding Artifact, Not a Live Provider

**Status:** Accepted
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

**Decision: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.**

This is an **a priori selection by exogenous criteria** (license, language coverage, offline-runnability, architecture maturity) — explicitly *not* a selection tuned or validated against this benchmark's 3 demands and 15 patents. Doing the latter would contaminate the same frozen benchmark ADR 0012 already protects from exactly this kind of post-hoc fitting. Whether this model actually performs well on Spanish-patent semantic matching is an **empirical question the ablation (M0-M6) answers later**, not a claim this ADR makes now. This ADR is explicit about the difference:

```text
technically reasonable choice for the task     ≠     empirically validated on this benchmark
```

Exogenous criteria for this choice, each independently verifiable and verified below (not asserted from training-data memory):
- **Multilingual, including Spanish.** The benchmark's patents are Spanish OEPM publications; demands are in Spanish and English. Trained for multilingual paraphrase/semantic-similarity across 50+ languages (confirmed via the model's `config.json`: `model_type: xlm-roberta`), not English-only.
- **Apache-2.0 license** — permissive, no field-of-use restriction, safe for a published scientific artifact. Verified directly against the model's Hugging Face repository (fetched 2026-09-04, see §2 for the exact revision).
- **Open weights, runnable entirely offline** — no API key, no network call required at embedding-generation time or at evaluation time.
- **Architecturally mature and inspectable, not a black box.** XLM-RoBERTa base, 768-dim hidden size, a widely-deployed base architecture whose failure modes are documented in the literature — this is a claim about auditability, not about proven fitness for patent-domain retrieval.

An alternative considered: `intfloat/multilingual-e5-base` (also open-weight, MIT-licensed, also multilingual). Rejected only as the *primary* choice for this ADR — not because it is unsuitable, but because `paraphrase-multilingual-mpnet-base-v2` is explicitly tuned for paraphrase/semantic-similarity (the task M1 actually needs), while the E5 family expects a `"query: "` / `"passage: "` prefix convention that adds a formatting decision this ADR would otherwise have to make and justify. Recorded here so a future reviewer does not have to re-derive that this alternative was considered, not overlooked.

**This is a proposal for review, not a locked decision** — Status: Proposed. If a domain expert has a stronger reason to prefer a different model (patent-specific fine-tune, a model with demonstrated Spanish-patent-domain performance, etc.), that supersedes this default before implementation.

### 2. Exact version / pinning

**Decision: pin now, not at implementation time.** The implementation PR must use exactly:

```text
model:    sentence-transformers/paraphrase-multilingual-mpnet-base-v2
revision: 4328cf26390c98c5e3c738b4460a05b95f4911f5
```

Fetched directly from the Hugging Face repository API on 2026-09-04 (`GET https://huggingface.co/api/models/sentence-transformers/paraphrase-multilingual-mpnet-base-v2`) — this is the commit SHA of `main` as of that date, not invented or estimated. Downloading by this exact revision (not the mutable `main` branch reference) guarantees the implementation PR uses the same weights this ADR reviewed, even if the repository's `main` branch is later updated. If the implementation PR runs after this revision is no longer resolvable (repository deleted, revision garbage-collected — not expected for an actively maintained `sentence-transformers` model, but not impossible over a long timeline), that is a deviation from this ADR requiring an explicit note in the implementation PR, not a silent substitution of whatever `main` resolves to at that time.

### 3. Where it runs

**Offline, once, outside the evaluation harness** — a standalone generation script (analogous to `scripts/evaluation/run_pilot_benchmark.py`), not a code path inside `application/evaluation/matching_adapter.py` or any component invoked during an evaluation run. The evaluation harness reads the frozen artifact; it never computes an embedding itself. This mirrors ADR 0011's decoupling of the "laboratory" from the product, and ADR 0013's requirement that a derived feature's computation be reproducible from declared inputs, algorithm, and version — a one-time offline generation step is what makes those declarations checkable at all.

### 4. Licensing

Apache-2.0 (verified above). The generation script's own dependencies (the `sentence-transformers` library and its transitive dependencies) must also be checked for license compatibility before implementation — not assumed compatible because the model weights are permissively licensed.

### 5. How embeddings are generated

This section is the science freeze — every value here changes the resulting vectors and must not be left to the implementation PR's discretion (see §13 for what is deliberately left open instead).

- **Input text:** the same fields already used for observed evidence elsewhere in this benchmark — patent `title + ' ' + abstract`, demand `title + ' ' + description`. No new text sources, no annotation text. No additional Unicode normalization, casing, or whitespace collapsing beyond what the model's own tokenizer applies — the sealed dataset's text (ADR 0006) is passed through as-is.
- **Generation device: CPU.** Decided now, not deferred. This benchmark is small (15 patents + 3 demands = 18 texts to embed); the cost difference between CPU and GPU generation is immaterial at this scale, and CPU generation avoids GPU floating-point non-associativity as an experimental variable entirely — there is no scientific benefit to GPU here that would justify accepting that variance.
- **Max sequence length: 128 tokens, `do_lower_case: false`.** These are the pinned model's own stated configuration (`sentence_bert_config.json` at the pinned revision, §2) — not a choice this ADR is free to make independently, since a different value would require a different tokenization/truncation behavior than the model was designed for. Recorded explicitly because a patent abstract can exceed 128 tokens: any excess is truncated by the model's own tokenizer, not by generation-script logic. This is accepted as the pinned model's native behavior and must be recorded in the frozen artifact's provenance (§7) so a future reader can attribute any semantic score anomaly on a long abstract to this known truncation, rather than treating it as unexplained noise.
- **Pooling: mean pooling over token embeddings** (`pooling_mode_mean_tokens: true`, the pinned model's own configuration at `1_Pooling/config.json`) — not CLS-token or max-pooling. Again the model's own designed behavior, not an independent choice.
- **Encoding call: `SentenceTransformer.encode(text, normalize_embeddings=True, batch_size=1)`.** `normalize_embeddings=True` performs the L2 normalization (§9) inside the library call rather than as a separate post-processing step, removing a place for the two to silently drift apart. `batch_size=1` is pinned specifically to remove batch-composition as a variable: transformer attention masking is designed to make per-sequence output independent of what else shares its batch, but pinning batch size to 1 removes any possibility of a library-version-specific padding/masking bug silently coupling one text's embedding to its batch neighbors, at a computational cost that is irrelevant at 18 texts total.
- **Determinism:** the model is run in inference (`eval`) mode — no dropout, no sampling. Given the pinned model revision (§2), pinned library versions (§7), CPU generation, and the exact encoding call above, output vectors are reproducible: re-running the documented procedure on the same input text produces the same vectors, verifiable against the frozen artifact's declared hash (§7) — not "bit-for-bit reproducible on any machine" as an unqualified absolute, but reproducible from the declared inputs, algorithm, and environment, which is the same standard ADR 0013 condition 3 already sets for M0.
- **No annotations, no ground truth** as input, under the same ADR 0013 condition 2 that governs M0.

### 6. Frozen as an artifact, keyed and linked to the sealed dataset

Yes. A new sealed artifact (working name: `data/evaluation/embeddings_pilot_benchmark.json`, or a more storage-appropriate format such as `.npy`/Parquet with a companion manifest — the implementation PR decides the file format; this is an implementation detail, see §13) stores one embedding vector per patent, keyed by `publication_id`, and one per demand, keyed by `demand_id` — the same canonical identifiers the sealed dataset (ADR 0006) already uses, not a new identity scheme.

It is not enough for the artifact to claim it was generated "from the benchmark" in prose. The manifest must record, and a loader must verify, that its `demand_ids`/`patent_ids` are exactly the sealed dataset's `demand_ids`/`patent_ids` — the same fail-fast pattern `ModelConfigurationManifest.verify_source_policy` already established for tying the M0-M6 manifest to its source policy (ADR 0012, PR #29).

### 7. Hash / provenance

The frozen embedding artifact's manifest must record, at minimum:
- Model name and exact pinned revision (§2)
- License (§4)
- Generation script identity (path + git commit it was generated from)
- Library versions used (`sentence-transformers`, `torch`/backend, etc.)
- Generation device (§5: CPU)
- **`dataset_sha256`** — the sealed benchmark dataset's own content hash (ADR 0006), so the artifact declares *which exact byte-identical dataset* produced it, not merely "the benchmark" as a moving target. A self-referential `artifact_sha256` alone proves the artifact's own internal consistency; it says nothing about whether the dataset that fed it is still the dataset currently sealed under ADR 0006 — `dataset_sha256` is what makes that link checkable, the same way §6's `verify`-style check makes the identifier sets checkable.
- `n_demands`, `n_patents`, and the exact `demand_ids`/`patent_ids` lists (§6)
- A self-referential integrity hash (`artifact_sha256`), following the same pattern as `MatchingPolicyConfig.policy_sha256`, `StudyProtocol.protocol_sha256`, and `ModelConfigurationManifest.config_sha256` (ADR 0006/0011/0012) — tamper-evident, not a cryptographic seal, exactly as those ADRs already state about their own hashes. `artifact_sha256` proves the artifact's own bytes are self-consistent; `dataset_sha256` proves which sealed dataset it was derived from. Neither alone is sufficient; both are required.

### 8. Dimensionality

768 (the native output dimension of `paraphrase-multilingual-mpnet-base-v2`). Recorded explicitly in the artifact's manifest so a future reader does not have to look it up externally.

### 9. Normalization

Embeddings are L2-normalized before storage. This is standard practice for cosine-similarity retrieval and matches the existing `DuckDbDenseSemanticRetriever`'s assumption that vectors are comparable via cosine similarity.

### 10. Similarity metric

Cosine similarity, via the existing `infrastructure/matching/vector_math.cosine_similarity` — already implemented, already used by `DuckDbDenseSemanticRetriever`. No new similarity computation is introduced; M1's derived-feature computation reuses this exactly the way M0 reused `DuckDbBM25Retriever`'s existing scoring math.

### 11. What happens if the model changes

Changing the embedding model, its revision, or its generation procedure produces a **new** frozen artifact under a new version identifier — never an in-place edit of the sealed one. This is the same principle ADR 0012 §6 already states for model configurations: a changed input requires a new, explicitly named artifact and provenance record, not a silent overwrite. Any such change must be re-justified against this ADR (or a superseding one) before use in an ablation or final inference.

### 12. Reproducibility

Given the pinned model revision (§2), the documented generation procedure and device (§5), the pinned library versions (§7), and the frozen input text tied to a specific `dataset_sha256` (§6-7), a third party can regenerate the embedding artifact on CPU and verify it against the declared `artifact_sha256`. This is a verifiable reproduction claim, not an unqualified "bit-for-bit on any machine" one (§5) — it is the same reproducibility contract ADR 0013 §2 condition 3 already requires of M0, restated for what M1 specifically needs to declare to satisfy it.

### 13. Science freeze vs. implementation detail — explicit split

To keep this ADR from re-litigating implementation choices later as if they were scientific ones (and vice versa):

```text
SCIENCE FREEZE (this ADR, changing any of these requires a superseding ADR)
├── model + exact revision (§1-2)
├── input text fields, no annotations (§5)
├── generation device: CPU (§5)
├── max_seq_length=128, do_lower_case=false, mean pooling (§5 — pinned model's own spec)
├── encode() call shape: normalize_embeddings=True, batch_size=1 (§5)
├── dimensionality: 768 (§8)
├── normalization: L2 (§9)
├── similarity metric: cosine, via existing vector_math.cosine_similarity (§10)
└── identity keys: publication_id / demand_id, verified against dataset_sha256 (§6-7)

IMPLEMENTATION DETAIL (follow-up PR's discretion, not this ADR's)
├── artifact file format (JSON / .npy / Parquet)
├── file layout / directory structure
├── loader class or function shape
├── generation script's internal structure
└── exact library versions actually pinned in requirements (values recorded per §7,
    but which patch versions to depend on is a normal dependency-management decision)
```

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
2. Uses a model revision other than `4328cf26390c98c5e3c738b4460a05b95f4911f5` (§2), or an unpinned reference (a mutable branch or "latest" tag), without recording and justifying the deviation.
3. Deviates from the pinned encoding call shape (§5: CPU, `max_seq_length=128`, `do_lower_case=false`, mean pooling, `normalize_embeddings=True`, `batch_size=1`) without a documented reason.
4. Regenerates or edits the frozen embedding artifact in place rather than producing a new versioned artifact.
5. Computes an embedding from annotation or relevance-grade text.
6. Omits `dataset_sha256` from the artifact's manifest, or fails to verify the artifact's `demand_ids`/`patent_ids` against the sealed dataset's own identifiers (§6-7).
7. Introduces a general-purpose embedding/vector-store abstraction not required by the specific model and format this ADR (or its accepted revision) actually specifies.
8. Presents this model's performance on the frozen benchmark as validation of the model choice itself, rather than as the empirical result the ablation exists to report (§1).
