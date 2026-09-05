# ADR 0016: Fusion Transform for Heterogeneous Ranking Features

**Status:** Proposed
**Date:** 2026-09-05
**Scope:** Resolves the open question ADR 0015 §3 explicitly left undecided — which transformation, if any, maps `lexical_score` (raw BM25, ADR 0013) and `semantic_score` (raw cosine, ADR 0014) into `[0,1]` before `DefaultEvidenceEvaluator.evaluate_candidate` fuses them into `overall_score`. Doc only — no code. The follow-up implementation PR this ADR authorizes must land `MatchFeatures.semantic_score`'s bound correction (already decided in ADR 0015 §2, not re-decided here), the transform below, and its provenance entry in `config/evaluations/model_configurations_m0_m6.json`, in that PR, before any M1-wired or M6 comparative result is reported.

---

## Context

ADR 0015 named a real scoring-domain conflict — a weighted sum of raw, differently-bounded features (`lexical_score ∈ [0,+∞)`, `semantic_score ∈ [-1,1]`, `cpc_concordance ∈ [0,1]`) is not guaranteed to land in `overall_score`'s declared `[0,1]` bound, and on the real 45-pair pilot, 2/45 pairs already overflow it. ADR 0015 deliberately did not choose a transformation, to avoid picking one *after* seeing what it does to a result on the frozen benchmark — exactly the post-hoc parameter selection ADR 0012 forbids, since the benchmark's 3 annotated demands are the only data this system will ever be tested against (no independent dev set exists, and none will be created).

This ADR makes that choice, using only properties of the raw features and the existing contracts — never the diagnostic numbers in ADR 0015's own table, which remain, as declared there, descriptive only.

### Constraints this decision must satisfy

1. **No benchmark-fitting (ADR 0012).** Any transform parameter must be defensible from the feature's mathematical properties or an existing codebase convention, not from what it produces on the 45 pilot pairs.
2. **Raw features stay raw (ADR 0013 §1, ADR 0015 §1).** `MatchFeatures.lexical_score`/`semantic_score` are not reinterpreted or silently transformed at the point they're computed — whatever transform this ADR chooses applies only at the fusion step, is declared, and is reproducible from stated inputs.
3. **No tail-clamping (ADR 0015 Enforcement #2).** `min(1.0, raw)` was already explicitly rejected: it collapses every high-signal pair to the same value, destroying exactly the ranking information a "white-space opportunity" system exists to surface.
4. **Confidence thresholds must stay portable.** `ConfidenceThresholds.strong/moderate/weak` (`MatchingPolicyConfig`) are fixed, global constants applied uniformly across all demands and candidate-pool sizes. Any transform whose output depends on the pool it's computed within (not just the single candidate's own raw score) would make a fixed threshold mean something different per demand — a correctness problem independent of ADR 0015's overflow bug.
5. **Must generalize past the pilot.** Per `.circle/cycle.md` and the current roadmap, this pilot is a protocol rehearsal for a large-scale dataset, not the final study. A transform whose parameters are corpus-size-dependent (e.g. derived from this pilot's own score distribution) would need re-deriving — and re-justifying against ADR 0012 — every time the dataset grows. A transform that needs no such re-derivation is strictly preferable.

### Evaluating ADR 0015's five candidates against these constraints

| Candidate | Fails on |
|---|---|
| Min-max normalization of BM25 | (1) and (5): the bounds are either derived from this benchmark's own score distribution (contamination) or from an arbitrarily assumed corpus size that won't match the eventual large dataset. |
| Corpus-statistics-based BM25 normalization (divide by a theoretical/corpus max) | (1) and (5): BM25 has no fixed theoretical max — it depends on IDF, which depends on corpus size and composition. "Corpus-derived" here means "derived from the sealed benchmark," the same contamination as min-max, and non-portable to a differently-sized future corpus. |
| Rank-based / softmax normalization within the closed candidate pool | (4): by construction, a softmax score depends on every other candidate in the same pool. A demand with weak evidence everywhere would still yield a "high" relative top score, indistinguishable from a demand with one genuinely strong match — exactly the failure mode fixed, global confidence thresholds cannot tolerate. |
| Reformulate `overall_score` with a non-`[0,1]` bound | Doesn't fail a constraint outright, but doesn't resolve one either: it relocates the ambiguity (what bound *is* correct? what do the existing threshold values then mean?) rather than resolving the domain mismatch, and is the least concrete of the five as stated. |
| A fixed monotonic transform, parameters chosen a priori | Satisfies all five — detailed below. |

## Decision

### 1. Two feature-specific transforms, applied only at fusion time

`DefaultEvidenceEvaluator.evaluate_candidate` (`application/matching/evaluator.py`) applies these immediately before computing the weighted sum. `MatchFeatures.lexical_score` and `.semantic_score` are **not** modified at extraction time and continue to report the exact raw BM25/cosine values ADR 0013/0014 established — the transform is a fusion-time view over them, not a redefinition of them.

```text
f_lex(lexical_score)  = lexical_score / (lexical_score + k),   k = 1.0
f_sem(semantic_score) = (semantic_score + 1) / 2
f_cpc(cpc_concordance) = cpc_concordance                          # already [0,1]; unchanged

overall_score = alpha * f_lex(lexical_score)
              + beta  * f_sem(semantic_score)
              + gamma * f_cpc(cpc_concordance)
```

**Why `f_lex(x) = x / (x + k)`, not a generic sigmoid.** BM25 is zero-floored and, per ADR 0015's own diagnostic, right-skewed with median and p75 exactly `0.0` — most demand/patent pairs share no lexical evidence at all, and that `0.0` is itself meaningful signal ("no shared terms"), not an artifact to smooth away. A transform must satisfy `f(0) = 0` to preserve that meaning; a generic sigmoid centered at zero would instead map "no lexical evidence" to `0.5`, manufacturing moderate-looking signal out of nothing. The rational/Michaelis-Menten form `x/(x+k)` is the simplest monotonic function satisfying `f(0)=0`, `f` strictly increasing, `f(x) \to 1` as `x \to \infty` (compresses, never clamps, so high-signal pairs stay ordered relative to each other), and needs exactly one parameter.

**Why `k = 1.0`.** `k` is a real hyperparameter, not a parameter-free consequence of the transform's shape — it sets where `f_lex` crosses `0.5` (`f_lex(k) = 0.5`), so choosing `k` is a genuine scale decision, not an incidental one. `k=1.0` is fixed here as a unit-scale, parameter-minimal *prior*, not a calibrated value: no benchmark-derived evidence (this pilot's or any other) is used to select it, and none is needed to justify it beyond "the simplest possible scale in BM25's own raw units." What *is* parameter-independent is the guarantee this ADR actually needs: `f_lex` is bounded in `[0,1)` and monotonic for **any** `k > 0`, so `overall_score`'s boundedness is a property of the transform's shape, not of this specific value. That distinction matters: it means `k=1.0` is a reproducibility convention this ADR commits to up front, not an empirically optimized parameter — and it means a future revision changing `k` (e.g., once the large-scale dataset shows `k=1.0` saturates BM25 too aggressively or too gently) is honestly a new decision, subject to the same a priori discipline as this one, not a bug fix.

**Why `f_sem(x) = (x+1)/2`, not another saturating transform.** This is the affine remap already in production use: `infrastructure/sources/patent/*` (`DuckDbDenseSemanticRetriever`, cited in ADR 0015's Context) already stores `(cos+1)/2` rather than raw cosine, specifically because `Candidate.retrieval_scores`'s validator currently rejects negative values. Choosing the same remap for the evaluation-side fusion means the M1-wired evaluation path and the already-shipped production retrieval path compute semantic contribution identically for the first time — this ADR is not just resolving ADR 0015's overflow, it is retroactively reconciling a divergence between production and evaluation that existed before ADR 0015 was even written. It also needs no free parameter at all: cosine's domain is exactly `[-1,1]` by definition (not an empirical property of this benchmark), so the remap to `[0,1]` is exact and universal, not a choice made under uncertainty.

**`cpc_concordance` is untouched.** It is already `[0,1]`-bounded by `compute_cpc_symbol_similarity_from_levels`, with `0.0` already meaning "no concordance" — it already satisfies every constraint above.

### 2. Boundedness is now a structural guarantee, not a pilot-specific observation

Given `alpha + beta + gamma = 1.0` (already enforced by `RankerWeights.validate_weights`) and each of `f_lex`, `f_sem`, `f_cpc` mapping into `[0,1]`, `overall_score` is a convex combination of three `[0,1]`-bounded terms and is therefore in `[0,1]` **for every possible input**, not merely for the 45 pairs this pilot happens to contain. This also retires a latent risk ADR 0015 flagged but left open: "BM25 being unbounded is still latently capable of overflowing alone on a different corpus — the ceiling was never actually tested by M0 alone." After this ADR, it is: an M0-only evaluation on any future, larger corpus remains bounded by the same construction, with no separate argument required.

### 3. `active_signals` counting is unaffected, by design

`DefaultEvidenceEvaluator`'s `active_signals = sum(1 for s in (lexical_score, semantic_score, cpc_concordance) if s > 0.0)` continues to read the **raw**, untransformed features — this is unchanged and does not need to change. A raw cosine of exactly `0.0` (orthogonal, no similarity) or negative (opposite direction) correctly still does not count as an active signal; `f_sem(0.0) = 0.5` if read post-transform would have incorrectly counted orthogonality as half a signal, which is exactly why this check must stay bound to the raw values, not the fusion-time view.

### 4. Provenance

The follow-up implementation PR registers the transform in `config/evaluations/model_configurations_m0_m6.json`, under M6's (and M3/M4/M5's inherited) configuration entry, recording the transform's name, functional form, and `k`, with the same `provenance_status` discipline ADR 0012 already applies to every other configuration value in that manifest. This satisfies ADR 0015 §4's requirement that M6 remain blocked "until a transformation is pre-registered... under its own explicit provenance."

## What this ADR does not do

- Does not implement `f_lex`/`f_sem` in `application/matching/evaluator.py` — deferred to the follow-up PR, per this repository's contract-then-test-then-code discipline (ADR 0013 §3).
- Does not implement `MatchFeatures.semantic_score`'s bound widening to `[-1,1]` or `Candidate.retrieval_scores`'s validator correction — both already decided in ADR 0015 §2 and land in the same follow-up PR, not re-litigated here.
- Does not wire M1 into `DefaultMatchingAdapter`/`MatchFeatures` — still gated on this ADR's acceptance, per ADR 0015.
- Does not touch `cpc_concordance`, `CPCConcordanceLevels`, or CPC-only evaluation in any way.
- Does not change `RankerWeights`' `alpha+beta+gamma=1.0` convexity requirement, `ConfidenceThresholds`, or `SufficiencyRules`.
- Does not evaluate, report, or reference what this transform does numerically to the 45-pair pilot's `overall_score` values — doing so before implementation and before the PR that reports a comparative result would itself violate ADR 0015 Enforcement #1.

## Consequences

### Positive
- Unblocks the M1 wiring PR and, subsequently, M6 (and any M0+M1(+CPC) comparative evaluation), per ADR 0015 §4.
- `overall_score \in [0,1]` becomes a structural guarantee independent of input scale, not an empirically-observed property of one 45-pair pilot — closes the latent M0-alone overflow risk ADR 0015 identified but left open.
- Reconciles production's existing `(cos+1)/2` semantic-score convention with the evaluation path for the first time, removing a divergence that predates ADR 0015.
- `f_sem` is parameter-free; `f_lex` has exactly one hyperparameter (`k`), fixed ex ante rather than left unstated or calibrated against the benchmark — a materially different (and honest) claim than "no hyperparameters." Nothing about this decision needs re-deriving when the dataset scales up per the roadmap, precisely because `k`'s justification never depended on this pilot's data in the first place.
- Raw features remain fully auditable exactly as ADR 0013/0014 require — `rationale` can report both raw and fused values, nothing is hidden.

### Negative
- Introduces a second numeric representation (raw vs. fusion-transformed) that anyone reading `MatchAssessment.rationale` or debugging a score must understand is not the same number as `MatchFeatures.lexical_score`/`semantic_score`.
- `f_lex`'s `k=1.0` is a defensible ex ante hyperparameter choice, not an empirically validated one — if a future, larger dataset reveals `k=1.0` saturates too aggressively or too gently for BM25's actual behavior at scale, changing it is itself a new decision requiring the same a priori discipline (and, per ADR 0012, cannot be tuned against whatever benchmark exists at that time either).
- `f_lex`'s specific geometry compresses BM25's tail deliberately and materially, not just cosmetically (`f_lex(1)=0.50`, `f_lex(2)=0.67`, `f_lex(5)=0.83`, `f_lex(10)=0.91`, `f_lex(100)=0.99`) — that compression is the entire point of choosing a saturating transform over an unbounded one, but this ADR only establishes that the transform makes BM25 *comparable in scale* to the other two features. Whether that specific geometry produces a scientifically well-behaved ranking at the scale of the eventual large dataset is a separate, open empirical question this ADR does not answer and should not be read as answering — deciding comparability of scale (this ADR) and evaluating whether that scale is effective (the large-dataset study) must not be conflated into a single question.
- Still layers on top of `MatchAssessment.overall_score`'s existing `[0,1]`/linear-combination contract rather than reopening whether that contract is the right one for combining heterogeneous evidence at all — a larger question this ADR treats as out of scope, consistent with ADR 0015 leaving it unresolved.

## Enforcement

A future implementation PR is **non-compliant** with this ADR if it:
1. Applies `f_lex`/`f_sem` (or any transform) to `MatchFeatures.lexical_score`/`semantic_score` at extraction time rather than at fusion time inside the evaluator — this would violate ADR 0013 §1/ADR 0015 §1's raw-feature discipline.
2. Chooses a `k` value (or any other transform parameter) informed by its effect on the pilot benchmark's `overall_score` distribution, rather than by the a priori justification in §1.
3. Applies any transform to `active_signals`' raw-value check in `DefaultEvidenceEvaluator`.
4. Omits the transform's provenance entry in `config/evaluations/model_configurations_m0_m6.json`, or reports any M6/comparative result before that entry exists.
5. Reports what this transform does numerically to the 45-pair pilot in the same PR that implements it, before a separate, independently reviewed evaluation PR does so deliberately.
