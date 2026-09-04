# ADR 0013: Derived Ranking Features in Sealed Evaluation

**Status:** Accepted
**Date:** 2026-09-04
**Scope:** Sealed benchmark evaluation evidence and derived ranking features (conceptual; this ADR changes no files under `domain/models/evaluation`, `application/evaluation/matching_adapter.py`, or `docs/adr/0007-scientific-evaluation-protocol-and-metrics.md` — those remain the scope of a future implementation PR)

---

## Context

ADR 0007 (§8, line 144) establishes that `PatentCandidateEvidence` passed to the matching engine during evaluation is constructed strictly from `EvaluationDataset.patents`' real observed data (title, abstract, CPC codes, publication date) — "no synthetic retrieval scores are fabricated." This is enforced today by `backend/test/unit/architecture/test_adr_0007_invariants.py`, which hard-asserts `candidate.retrieval_scores == {}` for every candidate and statically forbids the literals `RetrievalMethod.LEXICAL` / `RetrievalMethod.SEMANTIC` from ever appearing in `application/evaluation/matching_adapter.py`.

That rule was, and remains, correct for what it was written to prevent: an adapter hardcoding or guessing a retrieval score with no basis in the sealed benchmark's actual content — a real risk, since a fabricated number dressed up as "evidence" would silently corrupt every downstream metric. Nothing in this ADR disputes that a *fabricated* score must never enter evaluation.

The rule as currently worded, however, does not distinguish between two different things:

1. **A number invented or asserted with no basis in the dataset** — a real risk, correctly forbidden.
2. **A number deterministically computed from data that *is* in the dataset** — e.g. a BM25 lexical relevance score computed from a patent's own title and abstract text, which are themselves observed dataset content.

Case 2 is not fabrication in the sense ADR 0007 was guarding against: the inputs are real, the transformation is deterministic and reproducible, and no information from outside the sealed benchmark (and critically, no ground-truth annotation) enters the computation. But the current rule's literal wording — "no synthetic retrieval scores," enforced by banning the retrieval-score fields outright — does not currently distinguish case 2 from case 1, which is why building a real M0 (lexical) ranking signal for the frozen benchmark is blocked today, even though the benchmark's own patent text already contains everything BM25 would need.

This ADR does not claim the existing pilot evaluation (PR #23, ADR 0011/0012) was flawed. CPC concordance already works today, computed directly from observed `classifications_cpc` metadata in `application/matching/feature_extractor.py` — it has simply never needed a `retrieval_scores` entry to do so. This ADR generalizes that same principle (compute from observed data, never from labels) to the case where a feature is arithmetically derived from *text* rather than read directly off a metadata field.

---

## Decision

### 1. Two distinct categories, not one

Every evaluation candidate's data going into the matching engine falls into exactly one of two categories:

```text
observed_evidence
    Data present verbatim in the sealed dataset: title, abstract,
    classifications_cpc, publication_date. Nothing is computed.

derived_ranking_feature
    A value deterministically computed FROM observed_evidence
    (never from annotations/ground truth), reproducible given the
    same inputs, with its computation method and parameters known
    and fixed.
```

`derived_ranking_feature` is not reclassified as `observed_evidence`, and must never be represented or logged as if it were an observed fact of the dataset. The dataset's sealed content (ADR 0006) remains exactly what it always was: title, abstract, CPC, date, and expert annotations. A derived feature is something the *model* computes when it looks at that content — it does not change what the benchmark itself contains.

### 2. What qualifies as a derived ranking feature

A computed value may be treated as `derived_ranking_feature` only if all of the following hold. (Whether the existing `retrieval_scores` field remains the right representation for such a feature, or a distinct representation is warranted, is an implementation question for the follow-up PR — this ADR authorizes the category, not a specific data-model change.)

1. **Computed strictly from `observed_evidence`.** Its inputs are limited to the sealed dataset's title, abstract, CPC codes, and publication date (and the demand's own text) — nothing else.
2. **Never computed from, or informed by, ground-truth annotations.** `EvaluationAnnotation` / relevance grades must never appear as an input, directly or indirectly, to any derived feature. This is the line that keeps the frozen benchmark's ground truth meaningful: a feature that peeked at the answer key would invalidate every metric computed against it.
3. **Deterministic and reproducible.** The computation must be reproducible from its declared inputs, algorithm, algorithm/library version, and parameters — not merely "the same on any machine at any time" in the abstract, since floating-point behavior, tokenizer versions, or locale can legitimately vary across environments. Reproducibility is achieved by declaring those variables as provenance (condition 5), not by asserting an absolute machine-independent identity the ADR does not itself define. No live network calls, no unseeded randomness, no dependence on wall-clock time.
4. **Does not alter the closed candidate universe.** A derived feature may score a candidate (including a score of exactly `0.0`), but must never cause a candidate to be excluded, filtered, or newly introduced. The candidate universe is fixed by ADR 0006; ranking features only inform how the fixed universe is ordered.
5. **Provenance-bearing when its parameters could affect the scientific result.** If a derived feature has tunable parameters (e.g. BM25's `k1`/`b`), those parameters must be recorded wherever the feature's values are reported, the same way `MatchingPolicyConfig` and `ModelConfigurationManifest` already record the provenance of the parameters they govern (ADR 0006, ADR 0012).

A lexical BM25 score computed from a patent's own title/abstract text satisfies all five conditions and is the motivating example for this ADR — **this ADR authorizes the category, it does not itself implement M0.** Semantic/embedding-based features (M1) are a separate, still-open decision: they would need their own embedder/model choice, provenance, and (most likely) a frozen embedding artifact before they could satisfy condition 3 and 5 — nothing in this ADR resolves that question, and no implementation work follows from this ADR alone.

### 3. Relationship to ADR 0007

ADR 0007 established a conservative boundary: the evaluation adapter introduces no retrieval score that is not itself observed evidence from the benchmark. That boundary was the right call at the time — nothing in the codebase could compute a retrieval score without risking exactly the fabrication it was written to prevent, so drawing the line at "no computed scores, period" was the safe default.

Experience since then shows that boundary conflates two distinct categories: (1) observed evidence, and (2) deterministic features derived from observed evidence. This ADR does not claim ADR 0007 already drew that line and was merely under-specified — it did not. This ADR **introduces** the distinction for the first time and proposes permitting category (2) under the conditions in §2. That is a change to the boundary's operative effect, not a restatement of what ADR 0007 always meant.

ADR 0007's text is not edited by this ADR and remains an accurate record of the decision as it was made. If this ADR is Accepted, the specific implementation guard that currently enforces the pre-ADR-0013 boundary — `test_adr_0007_invariants.py`'s `retrieval_scores == {}` assertion and its ban on `RetrievalMethod.LEXICAL`/`SEMANTIC` literals in `matching_adapter.py` — must be revised to reflect the new boundary. That revision, and the `matching_adapter.py` implementation it would then permit, are deliberately left to a separate, independently reviewed follow-up PR: contract (this ADR), then test, then code, never the reverse.

---

## Consequences

### Positive
- Preserves ADR 0007's actual concern (no fabricated evidence) while removing an incidental side effect (no computation at all) that was never the goal.
- Gives a precise, checkable bar (§2) for evaluating any future proposal to add a derived feature — including M1, whenever that separate decision is made.
- Keeps the sealed benchmark's ground truth (ADR 0006) and the model's ranking behavior conceptually and mechanically separate: labels are never reachable from a derived-feature computation.

### Negative
- Introduces a second technical category (`derived_ranking_feature`) alongside `observed_evidence` that future contributors must understand correctly — the boundary in §2 must be applied carefully, not assumed.
- Does not, by itself, unblock M0 or M1. A separate implementation PR must still change `test_adr_0007_invariants.py` and `matching_adapter.py`, and is expected to cite this ADR when doing so.

---

## Enforcement

Once this ADR is Accepted, a future implementation PR introducing a derived ranking feature is **non-compliant** if it:
1. Computes a feature from `EvaluationAnnotation` or any relevance grade, directly or indirectly.
2. Introduces non-determinism (network calls, unseeded randomness, wall-clock dependence) into a derived feature's computation.
3. Filters, excludes, or adds candidates to the closed universe as a side effect of computing a derived feature.
4. Omits provenance for a derived feature's tunable parameters where those parameters could affect the scientific result.
5. Reclassifies a derived feature as `observed_evidence` in code, comments, or reports.

This ADR itself makes no code or test changes. `test_adr_0007_invariants.py` continues to enforce the pre-clarification rule until a specific follow-up PR updates it in light of §2.
