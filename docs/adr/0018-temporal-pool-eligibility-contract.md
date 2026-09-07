# ADR 0018: Temporal Pool Eligibility Contract (Φ_temporal Enforcement Point)

**Status:** Proposed
**Date:** 2026-09-07
**Scope:** Resolves an ambiguity between `empirical-study-protocol.md` §5.3's pool-level `Φ_temporal` definition and the current evaluation-time implementation, ahead of Phase-2 pool construction (roadmap.md's deferred "temporal-eligibility correction"). Doc only — no code, no ranking change, no new metric, no dataset edit. The follow-up implementation PR this ADR authorizes must not report any comparative result before landing.

---

## Context

The empirical study protocol (§5.3, "Patent Eligibility Rules & Temporal Prior-Art Criterion") defines:

```text
Φ_temporal(p, d) = 1  if t_pub,p < t_demand,d
                  = 0  otherwise

P_eligible(d) = { p ∈ P | Φ_temporal(p, d) = 1 }
```

and RQ3 explicitly requires evaluating **both** the temporally-filtered pool and the unconstrained pool, to measure "candidate pool yield and rank stability" — i.e. the protocol treats `Φ_temporal` as a **pool-membership** rule (applied before ranking), with an explicit, named, unconstrained comparison condition.

The current implementation applies `Φ_temporal` at a different point entirely:

- `DefaultMatchingAdapter.rank_candidates` (`application/evaluation/matching_adapter.py`) always builds one `Candidate` per input patent, unconditionally — this is the sealed ADR 0013 condition 4 closed-universe guarantee (`test_should_preserve_closed_candidate_universe_when_ranking`, `backend/test/unit/architecture/test_adr_0007_invariants.py`). No pool filtering happens here today, by design.
- `DefaultMatchingFeatureExtractor.extract_candidate_features` (`application/matching/feature_extractor.py:76-82`) computes `temporal_valid = (t_demand - t_pub).days > 0` — this **is** `t_pub < t_demand`, matching the protocol's strict inequality exactly. The date sources (`PatentCandidateEvidence.publication_date` for `t_pub`, the demand's `posted_date` for `t_demand`) also already match the protocol. **This part is correct today and this ADR does not change it.**
- `DefaultEvidenceEvaluator.evaluate_candidate` (`application/matching/evaluator.py`), when `temporal_valid` is `False` and `policy.sufficiency_rules.require_temporal_validity` is `True` (the real default policy's actual value), sets `overall_score = 0.0` and `sufficiency = INELIGIBLE_TEMPORAL`. `DefaultMatchingEngine.evaluate` then sorts by `(-overall_score, publication_id)`, so the candidate sinks to the bottom of the ranking — but it is never removed from the candidate universe, the ranked list, or the metrics denominators.

So today there is exactly one pool, always: what the protocol would call the **unconstrained** condition, with temporally-ineligible candidates demoted to the bottom of the ranking rather than excluded. The protocol's own **strict** condition — an actually smaller `P_eligible(d)` — has never been implemented, and no run has ever declared which of the two conditions it used.

### Concrete impact on the 3 known temporal violations (PR #43, `docs/dataset-identity-audit.md`)

| demand_id | publication_id | grade | t_pub | t_demand | Effect of the ambiguity |
|---|---|---|---|---|---|
| `INNOGET-2415` | `ES-2901234-A1` | **2** (relevant) | 2023-04-20 | 2023-01-10 | **Only pair with real metric impact.** Today: demoted to `overall_score=0.0`, still counted in Recall/nDCG denominators. Under strict pool exclusion: removed from the pool and its denominators entirely. The two enforcement mechanisms produce *different* metric values for this one pair. |
| `INNOGET-2501` | `ES-2901234-A1` | 0 | 2023-04-20 | 2023-03-20 | None — already irrelevant under either mechanism. |
| `INNOGET-2292` | `ES-2856789-A1` | 0 | 2023-03-25 | 2023-02-15 | None — already irrelevant under either mechanism. |

Per #43, these 3 pairs are sealed, historical, annotated evidence and are **never** edited, removed, or re-annotated by this ADR or its implementation. Only what the *harness* does with them at pool-construction time is being decided here.

## Decision

### 1. `t_pub` / `t_demand` sources are unchanged

`PatentCandidateEvidence.publication_date` and the demand's `posted_date`, compared with the existing strict inequality (`t_pub < t_demand`). No date-source or comparison-operator change.

### 2. Two explicit, named run regimes — never inferred

A run declares exactly one of:

- **`strict`** — `Φ_temporal` is applied **before ranking**, constructing `P_eligible(d)` per demand. A temporally-ineligible patent never becomes a candidate: it is not scored, not ranked, not counted in any Recall/nDCG denominator, per protocol §5.3.
- **`unconstrained`** — the full patent universe is retained, exactly as today's only behavior. For this to be a genuine no-temporal-enforcement condition (not merely "same pool, but still secretly zeroed"), a run declaring `unconstrained` **must** pair it with a policy whose `sufficiency_rules.require_temporal_validity` is `False`. A harness that allows `temporal_pool_mode="unconstrained"` together with a policy where `require_temporal_validity=True` produces a contaminated condition — neither truly unconstrained (scores are still zeroed) nor truly strict (ineligible candidates are still in the pool, just demoted) — and **must fail fast**, not silently run.

This is a binding invariant, independent of any specific implementation:

> **`temporal_pool_mode` must be declared as an explicit, mandatory, typed field on the evaluation run's execution identity. It must never be inferred from a CLI flag string, from evaluator-side score manipulation, or from any implicit filtering.**

### 3. Pool construction happens in `DefaultEvaluationRunner`, never in the adapter or engine

`DefaultEvaluationRunner.run_evaluation` (`application/evaluation/runner.py`) already computes one `patent_universe` per run and passes it to `ranking_port.rank_candidates(eval_demand, patent_universe)` before computing `candidate_universe_size` for metrics. This is the correct, and only correct, location for `strict`-mode filtering:

- It requires no new dependency: `EvaluationPatent.publication_date` and `EvaluationDemand.posted_date` are both evaluation-domain types already available to the runner, which today imports nothing from `domain.models.matching` or `domain.protocols.matching` (ADR 0007's "pure independent auditor" invariant) — date comparison needs neither.
- It keeps `DefaultMatchingAdapter.rank_candidates`'s sealed closed-universe guarantee (ADR 0013 condition 4, `test_should_preserve_closed_candidate_universe_when_ranking`) **completely untouched**: the adapter still receives whatever patent list it's given and still preserves it exactly. Filtering happens one layer up, before the adapter is ever called — the runner passes a smaller `patents` list to the adapter for `strict` mode, a full one for `unconstrained` mode. No change to the adapter's contract.
- It matches the protocol's own two-stage structure: §5.3 "Patent Eligibility Rules" (pre-ranking selection of `P_eligible`) is a distinct step from §5.2 "Scoring Components within `P_shared`" (ranking/fusion over whatever pool was selected) — `Φ_temporal` belongs to the first stage, `f_lex`/`f_sem`/`f_cpc` fusion (ADR 0016) to the second. This ADR does not conflate them.

A future implementation PR that filters inside `DefaultMatchingAdapter`, `DefaultMatchingEngine`, or `DefaultEvidenceEvaluator` is **non-compliant** with this decision (see Enforcement).

### 4. The evaluator's existing `INELIGIBLE_TEMPORAL` scoring is untouched, and stays scoped to sufficiency semantics

`DefaultEvidenceEvaluator`'s `overall_score=0.0` / `INELIGIBLE_TEMPORAL` behavior, gated by `policy.sufficiency_rules.require_temporal_validity`, is not removed and not relocated. It continues to exist as a **sufficiency/evaluation-semantics** concern — what an evaluator does with a candidate that *is* in its pool but fails a policy-level validity check — independent of, and not a substitute for, `Φ_temporal` pool membership. This is why `unconstrained` mode must additionally clear `require_temporal_validity` in its policy (§2 above): otherwise this pre-existing, legitimate mechanism silently reintroduces temporal enforcement into what is supposed to be the no-enforcement condition.

### 5. Provenance: `temporal_pool_mode` is part of the run's execution identity

A mandatory field (no default — ADR 0005's explicit-injection principle) is added to `EvaluationExecutionContext` (the type that already carries `engine_name`, `engine_version`, `engine_commit_hash`, `execution_timestamp`, `environment` — a run's identity, nested unconditionally inside every `EvaluationRunReport`). Two runs differing only in `temporal_pool_mode` are therefore unambiguously distinguishable from their serialized reports alone, without depending on file naming, CLI argument logs, or any other side channel.

### 6. The sealed dataset is never edited

The 3 flagged pairs (`INNOGET-2415`/`ES-2901234-A1`, `INNOGET-2501`/`ES-2901234-A1`, `INNOGET-2292`/`ES-2856789-A1`) remain in `data/evaluation/dataset_pilot_benchmark.json` exactly as sealed by #43 — same dates, same grades, same hash. `strict` mode changes what the *harness* does with them at pool-construction time for a given run; it does not touch, re-annotate, or remove them from the dataset.

## What this ADR does not do

- Does not implement pool filtering, the `temporal_pool_mode` field, or the `unconstrained`/`require_temporal_validity` consistency check — deferred to the follow-up implementation PR, per this repository's contract-then-test-then-code discipline (ADR 0013 §3, ADR 0016 precedent).
- Does not change `nDCG@10`'s status as the primary confirmatory endpoint (roadmap.md §4 item 3), introduce any new metric, or change `MetricSet`.
- Does not change BM25/CPC/fusion scoring (ADR 0013/0014/0015/0016) in any way.
- Does not edit, re-annotate, or remove any pair from the sealed dataset.
- Does not decide DEV/TEST freeze, blinded annotation, or IAA (Phase-2/PR-F track) — this ADR closes only the temporal-eligibility ambiguity named in roadmap.md's deferred item.
- Does not evaluate, report, or reference what `strict` vs `unconstrained` mode numerically does to the pilot or any future dataset — reporting a comparative result before this ADR's implementation lands, tested, and is independently reviewed would repeat the exact mistake ADR 0015/0016 Enforcement already forbid for the fusion transform.

## Consequences

### Positive

- Closes roadmap.md's last genuinely open item from the deferred "temporal-eligibility correction" (§2/§4) with a precise, testable contract instead of an ad-hoc code fix.
- Resolves RQ3 ("How does the strict enforcement of temporal prior-art eligibility impact candidate pool yield and rank stability") for the first time as an actually runnable comparison — `strict` vs `unconstrained` become two declared, reproducible conditions rather than one implicit behavior.
- Keeps ADR 0013's closed-universe guarantee (adapter/engine layer) and the new pool-eligibility rule (runner layer) as two independently testable, non-conflicting invariants — no existing sealed test needs to be weakened or reinterpreted.
- Makes the one pair with real metric consequence (`INNOGET-2415`/`ES-2901234-A1`, grade 2) an explicit, auditable design choice per run, instead of an implicit consequence of where a score happens to sort.

### Negative

- **The pre-existing PR-E artifact (#45) predates this contract and is not reproducible bit-for-bit by a compliant run.** `data/experiments/m0_run_report.json`/`m1_run_report.json`/`m0_vs_m1_comparative_report.json` were generated under what this ADR retroactively identifies as the contaminated combination — full patent universe (today's only historical behavior) paired with the default policy's `require_temporal_validity=True`. That artifact stays frozen and historical, exactly as committed, as evidence of the first empirical M0-vs-M1 harness run; it is not silently regenerated, edited, or reproduced by `scripts/run_m0_vs_m1_comparison.py` after this ADR's implementation lands. A live run of that script must declare a contract-valid `temporal_pool_mode` (`strict` works with the current default policy unmodified; `unconstrained` requires a policy variant with `require_temporal_validity=false`), which will legitimately produce different numbers than the frozen #45 artifact — reporting those new numbers is out of scope for the implementation PR (Enforcement #6).
- Introduces a second axis of run identity (`temporal_pool_mode`) that any future comparative protocol (`evaluate_study_protocol`, ADR 0011) must account for when pairing baseline/treatment runs — a hypothesis comparing runs with different `temporal_pool_mode` values would be comparing pools of different sizes, not a like-for-like ranking comparison, unless deliberately intended (as RQ3 requires).
- The `unconstrained`/`require_temporal_validity` consistency check adds one more fail-fast precondition to the evaluation harness's construction path, alongside the dataset/policy/model-config verification steps that already exist.

## Enforcement

A future implementation PR is **non-compliant** with this ADR if it:

1. Computes or infers `temporal_pool_mode` from a CLI flag string, an environment variable, or any implicit signal, rather than from an explicit, mandatory, typed field with no default.
2. Implements `strict`-mode pool filtering inside `DefaultMatchingAdapter`, `DefaultMatchingEngine`, or `DefaultEvidenceEvaluator`, rather than in `DefaultEvaluationRunner` (or an equivalent pre-ranking step) before `ranking_port.rank_candidates` is called.
3. Permits a run with `temporal_pool_mode="unconstrained"` and a policy where `sufficiency_rules.require_temporal_validity=True` to execute without failing fast.
4. Edits, re-annotates, or removes any pair (including the 3 flagged temporal violations) from `data/evaluation/dataset_pilot_benchmark.json` or its sidecars.
5. Changes `nDCG@10`'s primary-endpoint status, `MetricSet`, or any fusion/BM25/CPC scoring logic in the same PR.
6. Reports any comparative `strict` vs `unconstrained` numeric result in the same PR that implements the mode itself, before a separate, independently reviewed evaluation PR does so deliberately.
