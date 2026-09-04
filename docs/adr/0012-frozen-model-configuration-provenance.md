# ADR 0012: Frozen Model Configuration Provenance (No Tuning)

**Status:** Accepted
**Date:** 2026-09-04
**Scope:** `config/evaluations/model_configurations_m0_m6.json`, `domain/models/evaluation.py`

---

## Context

The frozen benchmark (ADR 0006, ADR 0011) contains exactly 3 annotated demands,
and those same 3 demands constitute the entire frozen inferential benchmark
(PR #23). No independent, unannotated development set exists. Optimizing any
model hyperparameter (e.g. the `HybridRanker` fusion weights `alpha`, `beta`,
`gamma`) against these 3 demands would contaminate the final inferential
evaluation (PR #26): the same data used to select a configuration cannot also
be used to test it.

The current `HybridRanker` weights (`alpha=0.35`, `beta=0.45`, `gamma=0.20`,
`config/policies/matching/default_matching_policy.json`) match the weights
already present in the PR #23 pilot run (`scripts/evaluation/run_pilot_benchmark.py`
labels them "Frozen Pilot-16 heuristic weights"). No evidence of
benchmark-based hyperparameter tuning (grid search, Bayesian optimization,
cross-validation) was identified in a repository audit. Absence of a tuning
harness does not prove tuning never happened by some undocumented means, but
combined with the matching pilot provenance it is the strongest claim this
repository's evidence supports: these are pre-existing initial values, not a
result this team can claim was validated or optimized.

M3 (tripartite evidence assessment), M4 (origin policy resolution), and M5
(multi-agent synthesis) are downstream pipeline stages
(`DefaultEvidenceEvaluator`, `origin_resolver.py`, `synthesis_engine.py`) layered
on top of the same `HybridRanker` output. The codebase defines exactly one
`MatchingPolicyConfig`/`RankerWeights` — there is no per-stage weight
variant for M3, M4, or M5. They inherit M6's weights because there is
nothing else in the code to give them.

## Decision

1. **No development set is created.** Fabricating a synthetic split of the
   3 annotated demands to justify tuning would misrepresent statistical
   power that does not exist. None is created for PR #24 or later.
2. **All M0–M6 configurations are frozen as-is** in
   `config/evaluations/model_configurations_m0_m6.json`, recording once
   (`frozen_at`, `tuning_status`, `source_policy`) and per model (ranker,
   weights where applicable, version, provenance category).
   `source_policy` records the exact path and `policy_sha256` of
   `default_matching_policy.json` this freeze was derived from — a
   self-hash alone would prove the manifest's own internal consistency,
   but not that its weights still match the policy file months later, after
   that file has legitimately changed for unrelated reasons. `verify_source_policy`
   compares the manifest's declared digest against a caller-supplied,
   already-loaded policy object, rather than the manifest silently walking
   the filesystem to find it — this codebase's dataset loader (ADR 0006)
   already establishes that config loaders take explicit paths and stay
   CWD-independent, and drift verification is no exception. The policy
   parameter is typed structurally (matched by `MatchingPolicyConfig`
   without importing it), keeping `domain/models/evaluation.py` outside
   `domain.models.matching` — the evaluation-adapter-boundary Import Linter
   contract restricts that import to `application.evaluation.matching_adapter`
   alone, and even a type-checking-only import creates the transitive edge
   the contract forbids.
3. **Provenance categories are closed to three values:**
   `PRE_EXISTING_INITIAL_CONFIGURATION`, `INHERITED`, `DERIVED`, enforced via
   a `Literal` type on `ModelConfigurationRecord.provenance_status`. The
   values `TUNED`, `OPTIMIZED`, and `VALIDATED` cannot be expressed.
4. **The manifest carries a top-level `tuning_status` field fixed to the
   single `Literal` value `"NOT_TUNED_NO_INDEPENDENT_DEV_SET"`**, so the
   artifact itself states the epistemic boundary rather than relying on
   prose alone.
5. **The artifact is integrity-checked** with a self-referential SHA-256
   (`config_sha256`), following the exact pattern already used for
   `MatchingPolicyConfig.policy_sha256` and `StudyProtocol.protocol_sha256`.
   This detects accidental drift or corruption of the file at load time — it
   is **not** a cryptographic seal: anyone with write access can edit the
   payload and recompute the digest. The `ModelConfigurationManifest` model
   verifies internal consistency of the artifact's *claims*; it cannot
   verify, and does not claim to verify, that no tuning against the
   benchmark ever occurred outside this artifact. That guarantee comes from
   Git history and PR review, not from this file.
6. Should additional annotated demands become available later, tuning may
   be considered in a **new, explicitly named development phase** — never by
   editing this frozen artifact in place.

## Consequences

### Positive
- No benchmark-based hyperparameter fitting is evidenced by the repository
  provenance reviewed for this freeze, and the artifact's own epistemic
  claims are machine-validated rather than asserted only in prose.
- Provenance is explicit per model variant, and now traceable to the exact
  source policy file and digest each frozen configuration was derived from
  (`source_policy`), not merely to values that happen to match today.

### Negative
- `alpha/beta/gamma` may be suboptimal. This is accepted; correctness of the
  evaluation matters more than the score it produces.
- This artifact cannot, by itself, stop someone from tuning against the
  benchmark in a future PR. That risk is managed by review, not tooling.

## Enforcement

A Pull Request is **non-compliant** if it:
1. Sets any M0–M6 provenance status to `TUNED`, `OPTIMIZED`, or `VALIDATED`
   (the `Literal` type makes this a validation error, not a style nit).
2. Changes `tuning_status` away from `"NOT_TUNED_NO_INDEPENDENT_DEV_SET"`
   without a new ADR superseding this one.
3. Introduces a grid search, Bayesian optimization, or cross-validation
   routine that consumes the frozen benchmark.
4. Modifies `config/evaluations/model_configurations_m0_m6.json` weights to
   improve a metric on the frozen benchmark.
