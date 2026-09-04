# ADR 0015: Score-Space and Fusion Contract for Heterogeneous Ranking Features

**Status:** Proposed
**Date:** 2026-09-04
**Scope:** Names and blocks a real scoring-domain conflict discovered while wiring M1 into the evaluation harness. Doc only — no code, no chosen normalization/transformation, no implementation. Does not touch M0's existing lexical wiring (unaffected, see Consequences). A follow-up decision (amendment to this ADR, or a new one) must pick a specific transformation before M1 can be wired into `MatchFeatures`/`MatchAssessment`, and before any M0+M1(+CPC) comparative evaluation (M6 or otherwise) can be trusted.

---

## Context

While implementing the M1 wiring PR (frozen embedding artifact → `DefaultMatchingAdapter` → `Candidate.retrieval_scores[SEMANTIC]`, per ADR 0014), an end-to-end test against the **real** sealed dataset, the **real** frozen M1 artifact, and the **real** `DefaultEvidenceEvaluator` (not a synthetic fixture or a fake engine) raised:

```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for MatchAssessment
overall_score
  Input should be less than or equal to 1 [type=less_than_equal, input_value=1.119308, ...]
```

For demand `INNOGET-2292` / patent `ES-2634129-B1`:

```text
lexical_score  (raw BM25, ADR 0013)   = 1.970066
semantic_score (raw cosine, ADR 0014) = 0.732856
cpc_concordance                       = 0.5
policy weights: alpha=0.35, beta=0.45, gamma=0.20

overall_score = 0.35×1.970066 + 0.45×0.732856 + 0.20×0.5 = 1.119308
```

This is not a wiring bug in the M1 PR. It is a pre-existing mismatch between two design decisions that had never been exercised together on real data before:

1. **ADR 0013** deliberately keeps `lexical_score` (BM25) **raw and unbounded** — `MatchFeatures.lexical_score = Field(ge=0.0)`, no upper bound, no normalization, "pre-existing production defaults, not tuned." This was a correct decision on its own terms: no undeclared transformation should be smuggled into a derived ranking feature's computation.
2. **`MatchAssessment.overall_score`** is contractually bounded to `[0, 1]` (`Field(ge=0.0, le=1.0)`), and the fusion formula (`application/matching/evaluator.py`) is a **weighted sum** — `alpha*lexical + beta*semantic + gamma*cpc` — which is only guaranteed to land in `[0,1]` if every input is itself normalized to `[0,1]` and the weights sum to `1.0` (a convex combination). `alpha+beta+gamma = 0.35+0.45+0.20 = 1.0` — the weights *do* sum to 1, but that guarantee is void the moment one input isn't bounded to `[0,1]` in the first place.

A second, related inconsistency: `MatchFeatures.semantic_score = Field(ge=0.0, le=1.0)` assumes an already-normalized `[0,1]` value. The live production path (`DuckDbDenseSemanticRetriever`) satisfies that assumption by storing `(cos+1)/2` rather than raw cosine. ADR 0014 §10 says M1's derived feature "reuses [cosine_similarity] exactly... no new similarity computation is introduced" — which was written correctly against ADR 0013's raw-BM25 precedent, but produces a value (`[-1, 1]`) that violates `MatchFeatures.semantic_score`'s declared domain. On the current 45-pair pilot (3 demands × 15 patents), no real pair has negative cosine (min observed: `0.076`), so this second inconsistency has not yet crashed anything — but the domain declared by the field (`ge=0.0`) does not match the true mathematical range of cosine similarity (`[-1, 1]`), and a future dataset could easily produce a negative value.

A third instance of the same root cause, found on closer inspection: `Candidate.retrieval_scores`'s own validator (`domain/models/matching.py`) rejects any score `< 0.0` for *any* `RetrievalMethod` — `Candidate` construction itself would already reject a raw negative cosine before the value ever reached `MatchFeatures`. This is not a separate bug; it is the same "every retrieval score is assumed non-negative/normalized" assumption, present at one more layer than initially found.

### Diagnostic (descriptive only — not used to choose anything below)

Computed once, directly, over the real 45 demand-patent pairs in the pilot benchmark, using the actual frozen M0 (BM25, k1=1.5/b=0.75) and M1 (the committed embedding artifact) values and the current default policy's weights. This is evidence characterizing the scale of the problem, not an input to any parameter decision — reading it to select a transformation would be exactly the kind of post-hoc tuning against the benchmark ADR 0012/0013/0014 all reject.

```text
weights: alpha=0.35, beta=0.45, gamma=0.20
n pairs = 45

                min       p25       median    p75       p90       max       mean
lexical (raw)   0.0000    0.0000    0.0000    0.0000    1.8422    1.9701    0.3296
semantic (raw)  0.0763    0.2004    0.3010    0.4238    0.5866    0.7580    0.3347
cpc (raw)       0.0000    0.0000    0.0000    0.2500    0.5000    0.5000    0.1444

lex contrib     0.0000    0.0000    0.0000    0.0000    0.6448    0.6895    0.1154
sem contrib     0.0343    0.0902    0.1354    0.1907    0.2640    0.3411    0.1506
cpc contrib     0.0000    0.0000    0.0000    0.0500    0.1000    0.1000    0.0289

overall_raw     0.0343    0.1020    0.1510    0.3140    0.8961    1.1193    0.2948

pairs with overall_raw > 1.0:       2 / 45
pairs where lex_c alone > 1.0:      0 / 45
pairs with negative semantic:       0 / 45
```

Two observations, stated precisely (not generalized beyond what the data shows):

- **On this specific 15-patent pilot corpus, BM25 alone never pushed `overall_raw` above 1.0** (`lex_c` alone maxes at `0.6895`). The overflow (`2/45` pairs) only appears once M1's contribution is added. BM25 being unbounded is still latently capable of overflowing alone on a different (larger, higher-term-overlap) corpus — the ceiling was never actually tested by M0 alone, not proven safe.
- Most lexical scores are exactly `0.0` (median and p75 are `0.0`) — only the small minority of genuinely on-topic pairs carry any BM25 signal at all on this pilot's short abstracts, which is why the fusion's behavior at the tail (the on-topic pairs) is exactly where this ADR's unresolved question matters most.

### The open question this ADR exists to name

> **Are the M6 weights (`alpha`/`beta`/`gamma`) meant to weight *normalized* features, or *raw* features?**

The code currently assumes the former (a bounded `overall_score` only makes sense as a convex combination of `[0,1]`-bounded inputs). ADR 0013 (M0) and ADR 0014 (M1) both establish the latter (raw, undeclared-transformation-free derived features) as the correct scientific discipline for a sealed benchmark. Both cannot be true at once, and no prior ADR noticed the collision because M0 and M1 had never both been wired to real data at the same time before this end-to-end test.

---

## Decision

### 1. Raw feature domains — declared explicitly, no change to existing values

```text
lexical_score (BM25, ADR 0013)      ∈ [0, +∞)
semantic_score (cosine, ADR 0014)   ∈ [-1, 1]
cpc_concordance                     ∈ [0, 1]
```

These are the **true mathematical domains** of each derived ranking feature. ADR 0013's raw BM25 and ADR 0014's raw cosine are both reaffirmed here — neither is being walked back.

### 2. `MatchFeatures.semantic_score` and `Candidate.retrieval_scores`'s declared bounds are corrected, not reinterpreted

`MatchFeatures.semantic_score`: `Field(ge=0.0, le=1.0)` → `Field(ge=-1.0, le=1.0)`. `Candidate.retrieval_scores`'s validator must likewise stop rejecting negative values for `RetrievalMethod.SEMANTIC` specifically (it may still reject negatives for `LEXICAL`/`CPC`, whose true domains are `[0,+∞)` and `[0,1]` respectively). These are **domain corrections**, not transformation decisions: they make the declared ranges match what cosine similarity actually is. Neither, by itself, fixes the `overall_score` overflow — they only stop these two fields from silently rejecting a mathematically valid negative cosine value that simply hasn't appeared in this pilot's 45 pairs yet. Implementing these changes is deferred to the follow-up PR that resolves the fusion question below (not done in this doc-only ADR), so they land together with whatever else that PR needs to touch in the same files.

### 3. The fusion transformation is explicitly **not decided here**

The weighted-sum formula in `application/matching/evaluator.py`, and the `MatchAssessment.overall_score` bound in `domain/models/matching.py`, remain **as they are today** pending a follow-up decision. This ADR does not choose among the candidate approaches, because picking one now — after seeing the real 45-pair diagnostic above — would be exactly the kind of post-hoc parameter selection against the frozen benchmark that ADR 0012 §1 and ADR 0013 condition 3 already forbid. Candidates on the table for that follow-up decision (recorded here so a future reviewer does not have to re-derive the option space, not because any is preferred):

- min-max normalization of BM25 (bounds chosen from what source — corpus-wide? candidate-pool-wide? — is itself a decision)
- a fixed monotonic transform (sigmoid, log-scaling) with parameters chosen *a priori*, not fit to this benchmark
- corpus-statistics-based BM25 normalization (e.g., dividing by a theoretical or corpus-derived maximum)
- rank-based/softmax normalization within the closed candidate pool
- reformulating `overall_score` as a non-convex combination with a different bound than `[0,1]`, if `[0,1]` itself turns out to be the wrong contract for `MatchAssessment`

### 4. M6 (and any multi-feature comparative evaluation) is blocked

**M6 is currently mis-specified for combining heterogeneous raw features and must not be used for comparative evaluation until a transformation is pre-registered** in `config/evaluations/model_configurations_m0_m6.json` (or a successor manifest) under its own explicit provenance — the same discipline ADR 0012 already requires for every other configuration value. This blocks any M6 (or M0+M1 combined) result from being reported as scientifically valid until that pre-registration exists.

### 5. What is NOT blocked

**M0 alone is unaffected and remains valid.** The diagnostic above shows BM25's contribution alone never exceeded `1.0` on this pilot corpus; PR #33 (frozen M1 artifact) and the existing M0-only lexical wiring in `matching_adapter.py` (merged, ADR 0013) are not implicated by this ADR and require no changes. Only the **combination** of features into a single bounded `overall_score` is mis-specified — M0's own scientific validity, and M1's artifact/embedding correctness, stand on their own.

---

## What this ADR does not do

- Does not pick a normalization/transformation for any feature.
- Does not implement `MatchFeatures.semantic_score`'s bound correction (§2) — deferred to the follow-up PR.
- Does not touch `application/matching/evaluator.py`'s fusion formula.
- Does not decide whether `MatchAssessment.overall_score`'s `[0,1]` bound itself is the right contract.
- Does not wire M1 into `DefaultMatchingAdapter`/`MatchFeatures` — that PR is held pending this ADR's follow-up decision.
- Does not reopen ADR 0013's or ADR 0014's decision to keep BM25/cosine raw and undeclared-transformation-free — both are reaffirmed (§1).

## Consequences

### Positive
- Names a real conflict precisely, with real numbers, before any comparative M0-vs-M1 or M0-M6 result could be reported and misinterpreted as valid.
- Keeps M0's already-merged, already-valid work untouched — this is an addition to what's frozen, not a retroactive indictment of it.
- Forces the eventual transformation choice to be made once, deliberately, and pre-registered — not improvised inside a wiring PR under the pressure of a failing test.

### Negative
- M1's wiring PR is blocked until a follow-up decision lands — a real delay to the M0-M6 ablation sequence.
- Any future comparative evaluation involving more than one raw-scored feature must wait for the same follow-up, even if the specific pair being compared wouldn't itself overflow (e.g., a hypothetical M0-vs-M2 comparison) — being conservative about the whole class of heterogeneous-feature fusion, not just the specific overflow observed.

## Enforcement

A future implementation PR is **non-compliant** with this ADR if it:
1. Picks a transformation and pre-registers it while also being the same PR that reports a comparative evaluation result — the transformation must be decided and pre-registered *before* seeing what it does to any comparative result on this benchmark, not alongside it.
2. Clamps `overall_score` (e.g., `min(1.0, raw_score)`) as a substitute for choosing a transformation — this destroys information at exactly the tail where ranking differences matter and was explicitly rejected during this ADR's review.
3. Removes or loosens `MatchAssessment.overall_score`'s `[0,1]` bound without first deciding what bound is actually correct — loosening the contract is not the same as resolving the domain mismatch that caused it to be violated.
4. Re-widens `MatchFeatures.lexical_score` or `semantic_score`'s bounds beyond what §1 declares (BM25 stays `[0,+∞)`, cosine stays `[-1,1]`) to route around this ADR rather than resolving the fusion question.
5. Reports any M6 (or other multi-heterogeneous-feature) comparative result generated before a pre-registered transformation exists.
