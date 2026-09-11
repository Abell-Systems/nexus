# ADR 0028: Eligible-Universe Relevance Denominators

**Status:** Accepted
**Date:** 2026-09-11
**Scope:** Fixes a defect shared by ADR 0018 (temporal pool eligibility) and ADR 0027
(family-aware evaluation contract): both mechanisms shrink the candidate pool handed
to the ranking port, but neither shrinks the relevance-judgement set used to compute
Recall/nDCG denominators in `application/evaluation/metrics.py`.

## Context

ADR 0018 §3 claims: "a temporally-ineligible patent is not counted in any Recall/nDCG
denominator." This was never actually true. `DefaultEvaluationRunner.run_evaluation`
filtered the *candidate pool* passed to `ranking_port.rank_candidates` (correct), but
still passed the demand's full, unrestricted annotation dict to
`compute_demand_metrics` — so a temporally-ineligible patent that happened to carry a
relevant judgement continued to inflate `total_relevant`, deflating Recall/nDCG for a
reason unrelated to ranking quality: the ranker was never even given the chance to
retrieve a patent that could not possibly appear in its output.

ADR 0027 introduced `family_policy="collapse"|"exclude_related"`, which shrinks the
pool the same way, and inherited the identical shape of gap — documented at the time
in ADR 0027's own "Known gap" section and enforced against premature comparative
claims by its Enforcement item 6.

Both ADRs speculated the fix would require changing `application/evaluation/metrics.py`
itself, since that is where Recall/nDCG denominators are computed. This turned out to
be unnecessary: `metrics.py`'s pure functions already compute correctly over whatever
`judgements` dict they are given. The actual defect was narrower and entirely local to
`runner.py`: it built that dict from the wrong source (the full per-demand annotation
set) instead of the one that matters (the eligible pool the ranking port actually saw).

## Decision

### 1. The eligible evaluation universe

For a given demand, the *eligible evaluation universe* is the exact set of
publication_ids present in the candidate pool after `_filter_temporally_eligible_patents`
(ADR 0018 §3, gated by `temporal_pool_mode`) and `_apply_family_policy` (ADR 0027 §2/§4,
gated by `family_policy`) have both run — i.e., precisely the list `ranking_port.rank_candidates`
receives for that demand.

### 2. Judgements are restricted (and, for `collapse`, remapped) to that universe

`DefaultEvaluationRunner.run_evaluation` no longer passes a demand's full annotation
dict to `compute_demand_metrics`. It builds a restricted dict via
`_restrict_judgements_to_eligible_universe`:

- A patent excluded from the pool (temporally ineligible, or dropped by
  `exclude_related`) contributes nothing — its judgement, if any, is dropped, never
  counted toward Recall/nDCG denominators, `judged_count`, or `uncertain_count`.
- A patent collapsed into a representative (`collapse`) contributes its judged,
  non-`UNCERTAIN` grade to that representative via a **max-relevance remap** across
  the whole family group present in the pool at collapse time. This prevents a
  genuinely relevant invention from silently vanishing from the denominator merely
  because a less-relevant sibling won the deterministic lexicographically-smallest-
  `publication_id` tie-break (ADR 0027 §2).
- `RelevanceGrade.UNCERTAIN` never wins the remap's `max()` comparison — it cannot
  promote a representative to "relevant" — but is preserved verbatim when no member
  of the group carries a definitive grade, keeping `uncertain_count` honest for the
  eligible universe rather than silently dropping it.

`application/evaluation/metrics.py` is unmodified by this ADR.

### 3. `allow` + `unconstrained` is provably unaffected

Under `family_policy="allow"` and `temporal_pool_mode="unconstrained"`, the eligible
universe is exactly the sealed dataset's full patent list — the same set every valid
annotation already references (`EvaluationDataset.validate_referential_integrity`).
The restriction step is therefore a no-op in that condition, byte-for-byte preserving
every pre-ADR-0028 metric value computed under it. This is the historical baseline
every `data/experiments/*.json` frozen artifact was produced under, and it is the one
condition this ADR is provably a no-op for.

### 4. `denominator_semantics` provenance field

`EvaluationRunReport` gains `denominator_semantics: Literal["eligible_universe_v1"]`,
stamped unconditionally by `DefaultEvaluationRunner` on every run — never
caller-selected, never a field on `EvaluationExecutionContext`. Its only purpose is
comparative safety (§5): a frozen pre-ADR-0028 report has no such field, so loading it
back through this Pydantic model fails fast rather than silently comparing incompatible
denominator definitions.

### 5. Comparative guard

`application.evaluation.comparative.evaluate_study_protocol` now calls
`_validate_paired_run_identity` for every hypothesis before extracting paired metric
vectors, refusing to pair two runs whose `temporal_pool_mode`, `family_policy`, or
`denominator_semantics` differ. This makes ADR 0018 Enforcement #6 and ADR 0027
Enforcement #6 code-enforced rather than prose-only.

## What this ADR does not do

- Does not touch `application/evaluation/metrics.py` — the fix is entirely in what
  `runner.py` passes into it.
- Does not re-run or re-freeze any historical experiment. `data/experiments/*.json`
  remain byte-for-byte as they were, computed under the pre-ADR-0028 semantics, pinned
  by a regression test (`backend/test/unit/architecture/test_frozen_experiment_artifacts_unmodified.py`).
  A future re-run under `denominator_semantics="eligible_universe_v1"` is a separate,
  explicitly-reviewed decision, not an automatic consequence of this ADR landing.
- Does not add any new CLI flag or caller-facing configuration — `denominator_semantics`
  is a fact about the runner's own implementation, not a policy choice.

## Consequences

### Positive

- Closes a defect both ADR 0018 and ADR 0027 independently inherited, with the same
  fix applying to both mechanisms simultaneously (they share one insertion point).
- Recall/nDCG for `temporal_pool_mode="strict"` and `family_policy` in
  `{"collapse", "exclude_related"}` now measure ranking quality over the pool the
  ranker actually saw, not an inflated denominator that penalizes it for candidates it
  was never given the chance to retrieve.
- The comparative guard makes a category of future methodological error (pairing
  incompatible runs) impossible to do silently, rather than relying on a human
  remembering to check ADR prose before running a comparison.

### Negative

- Every historical Recall/nDCG value computed under `temporal_pool_mode="strict"` or
  a non-`allow` `family_policy` prior to this ADR is now known to have been
  systematically deflated relative to what this ADR's semantics would have produced.
  None of those runs can be silently reused; any that matter scientifically must be
  explicitly re-run and re-reviewed under `denominator_semantics="eligible_universe_v1"`.
- `EvaluationRunReport`'s schema changed again (a fourth required field addition
  after `family_metadata_complete`), meaning every frozen artifact under
  `data/experiments/` was already unparseable as this model before this ADR and
  remains so after it — an existing, tracked, no-runtime-impact gap (nothing in this
  codebase currently re-parses those files as `EvaluationRunReport`), not a new one
  introduced here.

## Enforcement

A future PR is **non-compliant** with this ADR if it:

1. Reintroduces a call site that passes a demand's unrestricted, full annotation dict
   to `compute_demand_metrics` when the candidate pool for that demand has been
   filtered or transformed by any pool-construction mechanism.
2. Adds a new pool-shrinking mechanism (a third axis alongside `temporal_pool_mode`
   and `family_policy`) without extending `_restrict_judgements_to_eligible_universe`
   (or its future equivalent) to cover it.
3. Implements the eligible-universe restriction inside `application/evaluation/metrics.py`
   rather than as an input built by `DefaultEvaluationRunner` before calling it.
4. Adds `denominator_semantics` (or an equivalent run-identity field) to
   `EvaluationExecutionContext`, making it a caller-selectable policy rather than a
   fixed fact stamped by the runner.
5. Removes or weakens `_validate_paired_run_identity`'s checks in
   `evaluate_study_protocol` without an equally strong replacement guard.
6. Re-freezes any file under `data/experiments/` without updating
   `test_frozen_experiment_artifacts_unmodified.py`'s expected hashes in the same,
   separately reviewed commit.
