# Eligible-Universe Relevance Denominators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the shared defect ADR 0018 and ADR 0027 both independently inherited: `temporal_pool_mode="strict"` and `family_policy` in `{"collapse", "exclude_related"}` shrink the candidate pool handed to the ranking port, but the Recall/nDCG relevance-judgement denominators computed in `application/evaluation/metrics.py` still come from the dataset's full, unrestricted per-demand annotations — so a patent removed from the pool can still count as "relevant but missed" in the denominator, systematically deflating Recall/nDCG for no reason related to ranking quality.

**Architecture:** Define one formal concept, the *eligible evaluation universe* for a demand: the exact set of publication_ids present in the pool after temporal-eligibility filtering and family-policy transformation (the same pool `ranking_port.rank_candidates` receives). `DefaultEvaluationRunner.run_evaluation` builds the judgements dict it passes to `compute_demand_metrics` by restricting the demand's annotations to that universe — dropping judgements for patents no longer in the pool, and, for `collapse` specifically, remapping a suppressed family member's judged relevance onto the surviving representative (max of the judged, non-`UNCERTAIN` grades in the family) so a genuinely relevant invention is never lost from the denominator just because a less-relevant sibling happened to win the deterministic tie-break. `application/evaluation/metrics.py` is untouched — the fix is entirely a matter of what `runner.py` passes in, not how the pure math functions compute over it. A new `EvaluationRunReport.denominator_semantics` field stamps every run with the fixed value `"eligible_universe_v1"`, letting a future comparative guard refuse to pair a post-fix run against any of the frozen pre-fix historical artifacts.

**Tech Stack:** Python 3.12, Pydantic v2 (frozen domain models), pytest.

**Spec:** No separate spec document — the roadmap gap and its resolution are captured directly in this plan and in the ADR it produces (`docs/adr/0028-eligible-universe-relevance-denominators.md`, written by Task 3). ADR 0018 (`docs/adr/0018-temporal-pool-eligibility-contract.md`) and ADR 0027 (`docs/adr/0027-family-aware-evaluation-contract.md`) are the two prior ADRs this one corrects; both travel with this plan as required reading.

## Global Constraints

- Clean Architecture layering (CLAUDE.md): all changes stay in `domain/models/evaluation.py` and `application/evaluation/{runner,comparative}.py`. `application/evaluation/metrics.py` is NOT modified — its pure math functions already do the right thing with whatever `judgements` dict they are given; the defect is entirely in what `runner.py` builds and passes to them.
- `runner.py` remains a pure independent auditor: no import from `domain.models.matching` or `domain.protocols.matching` (existing invariant, unchanged).
- Every commit ends with the three required attribution trailers (see repo `CLAUDE.md` — Lydia Bares co-author — plus the session's Claude Sonnet 5 co-author and `Claude-Session` trailers already used on this branch's prior commits).
- `denominator_semantics` is a fixed-value fact about how this codebase's runner computes denominators, not a caller-selected policy axis — it is stamped by the runner every time, never accepted as caller input, and MUST NOT be added to `EvaluationExecutionContext` or any CLI flag.
- Never touch files under `data/experiments/` — Task 3 adds a regression test that pins their content hash specifically to guarantee this.
- Run the full suite from the repo/worktree root: `python -m pytest backend/test -q` (one test has a repo-root-relative path assumption). Also run `python -m mypy backend/src/main --ignore-missing-imports` after every task.

---

### Task 1: Eligible-universe judgement restriction in `DefaultEvaluationRunner`

**Files:**
- Modify: `backend/src/main/domain/models/evaluation.py` (`EvaluationRunReport`)
- Modify: `backend/src/main/application/evaluation/runner.py` (`_apply_family_policy`, new `_restrict_judgements_to_eligible_universe`, `DefaultEvaluationRunner.run_evaluation`)
- Modify (fixture-only, add the new mandatory field): `backend/test/unit/domain/test_evaluation_protocol_models.py`, `backend/test/unit/application/test_metrics_endpoint.py`, `backend/test/unit/application/evaluation/test_comparative_evaluation.py`
- Test: `backend/test/unit/application/test_evaluation_runner.py`

**Interfaces:**
- Consumes: `EvaluationPatent.family_id` (`domain/models/evaluation.py`, already exists), `RelevanceGrade` (already exists), existing `_require_family_id` helper (already exists, unchanged).
- Produces: `EvaluationRunReport.denominator_semantics: Literal["eligible_universe_v1"]` (new field, consumed by Task 2's comparative guard). `_apply_family_policy`'s new return type `tuple[list[EvaluationPatent], dict[str, list[str]]]` (second element: representative publication_id → every publication_id collapsed into it, including itself; empty dict for `"allow"`/`"exclude_related"`) is internal to `runner.py` and not consumed elsewhere.

- [ ] **Step 1: Add `denominator_semantics` to `EvaluationRunReport`**

In `backend/src/main/domain/models/evaluation.py`, add the field right after `family_metadata_complete` (around line 434):

```python
    # ADR 0027: whether every patent in this run's sealed universe carried family_id.
    # Recorded unconditionally (even under family_policy="allow") so the audit trail
    # is honest about whether a family-sensitive policy could have been requested.
    family_metadata_complete: bool
    # ADR 0028: fixed identifier for how this run's Recall/nDCG denominators were
    # computed. Always "eligible_universe_v1" for any run produced by this codebase's
    # current DefaultEvaluationRunner -- never caller-selected, never a policy choice.
    # Its purpose is comparative safety: a frozen pre-ADR-0028 EvaluationRunReport
    # (e.g. data/experiments/m0_run_report.json) has no such field and therefore
    # fails to parse as this model at all, which is the correct, honest outcome --
    # it must never be silently paired against a post-fix run (see comparative.py's
    # guard, Task 2 of the eligible-universe-denominators plan).
    denominator_semantics: Literal["eligible_universe_v1"]
```

- [ ] **Step 2: Update the three fixture files to supply the new field**

Add `denominator_semantics="eligible_universe_v1"` immediately after each existing `family_metadata_complete=True` in these three files' `EvaluationRunReport(...)` constructions:

- `backend/test/unit/domain/test_evaluation_protocol_models.py:153`
- `backend/test/unit/application/test_metrics_endpoint.py:270`
- `backend/test/unit/application/evaluation/test_comparative_evaluation.py:91`

- [ ] **Step 3: Run the full suite to confirm the new required field is the only break**

Run: `python -m pytest backend/test -q`
Expected: FAIL only at `runner.py`'s own `EvaluationRunReport(...)` construction (every test that calls `DefaultEvaluationRunner.run_evaluation` now raises a Pydantic `ValidationError` for the missing `denominator_semantics` field). No other failures should appear — if they do, stop and investigate before continuing.

- [ ] **Step 4: Change `_apply_family_policy` to also return collapse groupings**

In `backend/src/main/application/evaluation/runner.py`, replace the existing `_apply_family_policy` function (currently lines 112-133) with:

```python
def _apply_family_policy(
    family_policy: str, patents: list[EvaluationPatent]
) -> tuple[list[EvaluationPatent], dict[str, list[str]]]:
    """ADR 0027 §2/§4: pre-ranking pool transform, mirroring _filter_temporally_eligible_patents's
    placement. Caller must have already called validate_family_policy_feasible -- this function
    assumes family_id is populated on every patent when family_policy != "allow".

    Returns (surviving_patents, collapse_groups). collapse_groups maps a surviving
    representative's publication_id to every publication_id collapsed into it
    (including itself) -- ADR 0028 uses this to remap a suppressed family member's
    relevance judgement onto the representative that absorbed it. Non-empty only for
    "collapse": "allow" and "exclude_related" never let one patent absorb another's
    judgement, so their collapse_groups is always {}.
    """
    if family_policy == "allow":
        return list(patents), {}

    if family_policy == "collapse":
        by_family: dict[str, list[EvaluationPatent]] = {}
        for p in patents:
            family_id = _require_family_id(p)
            by_family.setdefault(family_id, []).append(p)

        representatives: list[EvaluationPatent] = []
        collapse_groups: dict[str, list[str]] = {}
        for members in by_family.values():
            members_sorted = sorted(members, key=lambda p: p.publication_id)
            rep = members_sorted[0]
            representatives.append(rep)
            collapse_groups[rep.publication_id] = [m.publication_id for m in members_sorted]
        return sorted(representatives, key=lambda p: p.publication_id), collapse_groups

    # exclude_related
    family_counts: dict[str, int] = {}
    for p in patents:
        family_id = _require_family_id(p)
        family_counts[family_id] = family_counts.get(family_id, 0) + 1
    surviving = [p for p in patents if family_counts[_require_family_id(p)] == 1]
    return surviving, {}
```

- [ ] **Step 5: Add `_restrict_judgements_to_eligible_universe`**

Add this new function immediately after `_apply_family_policy` (before `_filter_temporally_eligible_patents`):

```python
def _restrict_judgements_to_eligible_universe(
    eligible_patents: list[EvaluationPatent],
    collapse_groups: dict[str, list[str]],
    judgements: dict[str, RelevanceGrade],
) -> dict[str, RelevanceGrade]:
    """ADR 0028: the relevance-judgement set fed into compute_demand_metrics must
    exactly match the eligible pool handed to the ranking port -- never the full,
    unrestricted per-demand annotation set (the pre-ADR-0028 defect ADR 0018 §3 and
    ADR 0027 both inherited: a patent excluded from the pool still counted as
    relevant-but-missed in the Recall/nDCG denominator).

    - A patent excluded from the pool (temporal ineligibility, exclude_related)
      contributes nothing: its judgement, if any, is simply dropped.
    - A patent collapsed into a representative (collapse) contributes its judged
      grade to that representative via a max-relevance remap over the whole family
      group, so a relevant family member is never lost from the denominator just
      because a less-relevant sibling won the deterministic publication_id tie-break.
    - RelevanceGrade.UNCERTAIN never counts as a "judged" grade for the remap (it
      must never win a max() against a real grade) but is preserved verbatim when
      no member of the group has a definitive grade, so uncertainty_rate stays an
      accurate reflection of the eligible universe rather than silently dropping it.
    """
    restricted: dict[str, RelevanceGrade] = {}
    for patent in eligible_patents:
        pub_id = patent.publication_id
        members = collapse_groups.get(pub_id, [pub_id])
        judged_grades = [
            judgements[m]
            for m in members
            if m in judgements and judgements[m] != RelevanceGrade.UNCERTAIN
        ]
        if judged_grades:
            restricted[pub_id] = max(judged_grades, key=lambda g: g.value)
        elif pub_id in judgements:
            restricted[pub_id] = judgements[pub_id]
    return restricted
```

- [ ] **Step 6: Wire both changes into `run_evaluation`**

In `DefaultEvaluationRunner.run_evaluation`, replace:

```python
            # ADR 0027: family-policy pool transform, applied after temporal
            # eligibility and before ranking -- same insertion point convention
            # ADR 0018 established for _filter_temporally_eligible_patents.
            eligible_patents = _apply_family_policy(context.family_policy, eligible_patents)

            # 1. Delegate ranking to port — receives only evaluation-domain objects,
            #    returns ranked publication_ids in engine's original order.
            ranked_ids = ranking_port.rank_candidates(eval_demand, eligible_patents)

            # 2. Align with expert annotations and compute per-demand metrics
            judgements = annotations_by_demand.get(d_id, {})
            demand_report = compute_demand_metrics(
                demand_id=d_id,
                ranked_publication_ids=ranked_ids,
                judgements=judgements,
                candidate_universe_size=len(eligible_patents),
            )
```

with:

```python
            # ADR 0027: family-policy pool transform, applied after temporal
            # eligibility and before ranking -- same insertion point convention
            # ADR 0018 established for _filter_temporally_eligible_patents.
            eligible_patents, collapse_groups = _apply_family_policy(context.family_policy, eligible_patents)

            # 1. Delegate ranking to port — receives only evaluation-domain objects,
            #    returns ranked publication_ids in engine's original order.
            ranked_ids = ranking_port.rank_candidates(eval_demand, eligible_patents)

            # 2. ADR 0028: restrict (and, for collapse, remap) judgements to the
            #    eligible evaluation universe -- the same pool the ranking port
            #    just received -- before computing per-demand metrics.
            judgements_full = annotations_by_demand.get(d_id, {})
            judgements = _restrict_judgements_to_eligible_universe(
                eligible_patents, collapse_groups, judgements_full
            )
            demand_report = compute_demand_metrics(
                demand_id=d_id,
                ranked_publication_ids=ranked_ids,
                judgements=judgements,
                candidate_universe_size=len(eligible_patents),
            )
```

- [ ] **Step 7: Stamp `denominator_semantics` on the returned report**

In the same method's final `EvaluationRunReport(...)` construction, add after `family_metadata_complete=family_metadata_complete(patent_universe),`:

```python
            denominator_semantics="eligible_universe_v1",
```

- [ ] **Step 8: Run the full suite — expect exactly one remaining failure**

Run: `python -m pytest backend/test -q`
Expected: every test passes except `test_run_evaluation_collapse_recall_denominator_is_not_shrunk_with_the_pool` in `backend/test/unit/application/test_evaluation_runner.py`, which now FAILS because it pinned the pre-fix `recall_at_5 == 2/3` value. This is expected and is fixed in Step 9 below — this is precisely the test ADR 0027's own docstring said "a future PR that resolves it must update this assertion deliberately."

- [ ] **Step 9: Replace the obsolete "known gap" pin with a test of the fixed behavior**

In `backend/test/unit/application/test_evaluation_runner.py`, replace the entire `test_run_evaluation_collapse_recall_denominator_is_not_shrunk_with_the_pool` function (lines 701-728) with:

```python
def test_run_evaluation_collapse_recall_denominator_reflects_eligible_universe(
    dataset_with_known_family, sample_policy
):
    """ADR 0028: supersedes the old "known gap" pin. collapse's relevance-judgement
    denominator must now reflect the same 2-patent eligible universe the ranking
    port received (P-A1, P-B1), not the original 3-patent annotation set. P-A2's
    GRADE_2 judgement is remapped onto its family's surviving representative
    (P-A1, the lexicographically smallest publication_id), so a perfect ranking of
    the eligible pool reads Recall@5 == 1.0 -- not 2/3 as it incorrectly did before
    ADR 0028 fixed the shared ADR 0018/ADR 0027 denominator defect.
    """
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("collapse"),
    )

    d_rep = report.demand_reports[0]
    assert d_rep.candidate_count == 2
    assert d_rep.broad_metrics.recall_at_5 == pytest.approx(1.0)
```

- [ ] **Step 10: Add a test proving temporal exclusion no longer inflates the denominator**

`dataset_with_temporal_violation` already annotates P-INELIGIBLE with `RelevanceGrade.GRADE_3` (a relevant judgement for a patent that never reaches the ranking port in strict mode) — exactly the scenario ADR 0018 §3 claimed was already excluded but wasn't. Add this test after `test_runner_strict_mode_computes_candidate_universe_size_from_filtered_pool`:

```python
def test_runner_strict_mode_excludes_temporally_ineligible_judgement_from_denominator(
    dataset_with_temporal_violation, sample_policy, strict_context
):
    """ADR 0028: P-INELIGIBLE's GRADE_3 judgement must not count in the Recall/nDCG
    denominator once strict mode has excluded it from the pool -- this is the exact
    defect ADR 0018 §3 claimed was already fixed but wasn't (P-INELIGIBLE remained
    in the raw judgements dict passed to compute_demand_metrics)."""
    ranking_port = FakeRankingPort(fixed_order=["P-ELIGIBLE"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_temporal_violation, ranking_port=ranking_port,
        policy=sample_policy, context=strict_context,
    )

    d_rep = report.demand_reports[0]
    # Only P-ELIGIBLE (GRADE_2, broad-relevant) is in the eligible universe.
    # P-INELIGIBLE's GRADE_3 must not inflate the denominator to 2.
    assert d_rep.broad_metrics.recall_at_5 == pytest.approx(1.0)
```

- [ ] **Step 11: Add a test proving `exclude_related` drops judgements without remapping them**

Add after `test_runner_exclude_related_policy_drops_every_multi_member_family`:

```python
def test_run_evaluation_exclude_related_denominator_excludes_dropped_family_judgements(
    dataset_with_known_family, sample_policy
):
    """ADR 0028: exclude_related drops both FAM-A members entirely -- their GRADE_2
    judgements must not survive anywhere (not remapped, unlike collapse). Only
    P-B1's judgement remains in the denominator."""
    ranking_port = FakeRankingPort(fixed_order=["P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("exclude_related"),
    )

    d_rep = report.demand_reports[0]
    assert d_rep.candidate_count == 1
    assert d_rep.broad_metrics.recall_at_5 == pytest.approx(1.0)
```

- [ ] **Step 12: Add a test proving collapse remaps a *partially*-relevant family correctly**

This is the "familia parcialmente relevante" case: the representative itself is unjudged, but a suppressed sibling carries the family's only relevant judgement — the remap must still surface it. Add this new fixture and test at the end of the file:

```python
@pytest.fixture
def dataset_with_partially_judged_family() -> ValidatedDataset:
    """FAM-C: P-C1 (lexicographically first, unjudged) and P-C2 (GRADE_3, judged).
    Tests that collapse's remap picks up a relevant judgement from a suppressed
    member even when the surviving representative itself carries no judgement."""
    prov = EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-FAM-C",
        title="Sanitary Fixtures",
        description="Drainage equipment",
        posted_date=date(2023, 1, 1),
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id="P-C1", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent C1", abstract="Abstract",
            provenance=prov, family_id="FAM-C",
        ),
        EvaluationPatent(
            publication_id="P-C2", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent C2", abstract="Abstract",
            provenance=prov, family_id="FAM-C",
        ),
    ]
    annotations = [
        EvaluationAnnotation(
            demand_id="D-FAM-C", publication_id="P-C2", grade=RelevanceGrade.GRADE_3,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        ),
    ]
    dataset = EvaluationDataset(
        dataset_id="eval-corpus-family-c", schema_version="1.0.0", dataset_version="1.0.0",
        description="Partially-judged family test corpus", demands=[demand], patents=patents,
        annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="eval-corpus-family-c", schema_version="1.0.0", dataset_version="1.0.0",
        source_authorities=["oepm"], demand_count=1, patent_count=2, annotation_count=1,
        content_sha256="a" * 64,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


def test_run_evaluation_collapse_remaps_relevance_from_suppressed_member_to_representative(
    dataset_with_partially_judged_family, sample_policy
):
    """P-C1 (representative) has no judgement of its own; P-C2 (suppressed) is
    GRADE_3. The remap must carry P-C2's relevance onto P-C1, or a perfect
    ranking of the collapsed pool would score Recall@5 == 0.0 despite the family
    genuinely containing the target solution."""
    ranking_port = FakeRankingPort(fixed_order=["P-C1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_partially_judged_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("collapse"),
    )

    d_rep = report.demand_reports[0]
    assert d_rep.candidate_count == 1
    assert d_rep.strict_metrics.recall_at_5 == pytest.approx(1.0)
```

- [ ] **Step 13: Add a test proving `UNCERTAIN` never becomes relevant via the remap**

```python
def test_run_evaluation_collapse_remap_never_promotes_uncertain_to_relevant():
    """A family where every judged grade is UNCERTAIN must not surface as relevant
    on the representative after collapse -- UNCERTAIN is excluded from the max()
    comparison entirely, per RelevanceGrade's epistemic invariant (never coerced
    to a real grade, ADR 0007)."""
    prov = EvaluationProvenance(
        source_authority="oepm", source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64, modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-FAM-D", title="Sanitary Fixtures", description="Drainage equipment",
        posted_date=date(2023, 1, 1), target_cpc_prefixes=["E03C"], provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id="P-D1", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent D1", abstract="Abstract",
            provenance=prov, family_id="FAM-D",
        ),
        EvaluationPatent(
            publication_id="P-D2", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent D2", abstract="Abstract",
            provenance=prov, family_id="FAM-D",
        ),
    ]
    annotations = [
        EvaluationAnnotation(
            demand_id="D-FAM-D", publication_id="P-D2", grade=RelevanceGrade.UNCERTAIN,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        ),
    ]
    dataset = EvaluationDataset(
        dataset_id="eval-corpus-family-d", schema_version="1.0.0", dataset_version="1.0.0",
        description="Uncertain-only family test corpus", demands=[demand], patents=patents,
        annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="eval-corpus-family-d", schema_version="1.0.0", dataset_version="1.0.0",
        source_authorities=["oepm"], demand_count=1, patent_count=2, annotation_count=1,
        content_sha256="b" * 64,
    )
    validated_dataset = ValidatedDataset(dataset=dataset, manifest=manifest)

    ranking_port = FakeRankingPort(fixed_order=["P-D1"])
    runner = DefaultEvaluationRunner()
    sample_policy_instance = _make_policy_for_uncertain_test()

    report = runner.run_evaluation(
        dataset=validated_dataset, ranking_port=ranking_port,
        policy=sample_policy_instance, context=_family_context("collapse"),
    )

    d_rep = report.demand_reports[0]
    assert d_rep.broad_metrics.recall_at_5 is None  # zero relevant judged items: undefined, not 0.0
    assert d_rep.uncertain_count == 1
```

This test needs its own policy instance rather than the `sample_policy` fixture (which is function-scoped and not directly callable outside pytest's injection) — add this small helper near the top of the file, right after the `sample_policy` fixture definition:

```python
def _make_policy_for_uncertain_test() -> MatchingPolicyConfig:
    """Non-fixture policy loader for the one test that needs a MatchingPolicyConfig
    outside pytest's fixture injection (it builds its own dataset)."""
    return MatchingPolicyConfig.load_from_json(
        Path(__file__).resolve().parents[4] / "config" / "policies" / "matching" / "default_matching_policy.json"
    )
```

Check the top of the file for how `sample_policy` fixture already loads `MatchingPolicyConfig` (it likely already does something equivalent) — reuse that exact loading logic instead of guessing a path, and add whatever imports (`Path`, `MatchingPolicyConfig`) are not already present at the top of the file.

- [ ] **Step 14: Run the full suite and mypy**

Run: `python -m pytest backend/test -q`
Expected: all tests pass.

Run: `python -m mypy backend/src/main --ignore-missing-imports`
Expected: `Success: no issues found in 124 source files` (or more, if any new files were added — none should be in this task).

- [ ] **Step 15: Commit**

```bash
git add backend/src/main/domain/models/evaluation.py \
        backend/src/main/application/evaluation/runner.py \
        backend/test/unit/application/test_evaluation_runner.py \
        backend/test/unit/domain/test_evaluation_protocol_models.py \
        backend/test/unit/application/test_metrics_endpoint.py \
        backend/test/unit/application/evaluation/test_comparative_evaluation.py
git commit -m "fix(evaluation): align relevance denominators with the eligible evaluation universe"
```

---

### Task 2: Comparative guard against mismatched run identity

**Files:**
- Modify: `backend/src/main/application/evaluation/comparative.py`
- Test: `backend/test/unit/application/evaluation/test_comparative_evaluation.py`

**Interfaces:**
- Consumes: `EvaluationRunReport.context.temporal_pool_mode`, `.context.family_policy`, `.denominator_semantics` (all from Task 1 / pre-existing).
- Produces: nothing new consumed by later tasks — this closes the "comparative guard" requirement standalone.

- [ ] **Step 1: Read the current `evaluate_study_protocol` per-hypothesis loop**

Confirm the insertion point: in `backend/src/main/application/evaluation/comparative.py`, `evaluate_study_protocol`'s `for hypothesis in protocol.hypotheses:` loop currently does:

```python
        baseline_run = runs[hypothesis.baseline]
        treatment_run = runs[hypothesis.treatment]

        baseline_vec, treatment_vec, excluded_ids = _extract_paired_vectors(
            baseline_run, treatment_run, hypothesis
        )
```

- [ ] **Step 2: Write the failing tests first**

Add to `backend/test/unit/application/evaluation/test_comparative_evaluation.py` (adapt the existing `EvaluationRunReport(...)`/`StudyProtocol`/`StudyHypothesis` construction helpers already in that file rather than rebuilding them from scratch — read the file first to match its existing fixture style exactly):

```python
def test_evaluate_study_protocol_rejects_mismatched_temporal_pool_mode(
    ... existing fixture args as needed ...
):
    """ADR 0018 Enforcement #6: pairing runs with different temporal_pool_mode
    silently attributes a pool-composition difference to the ranking engine."""
    baseline_run = <build via existing helper, context.temporal_pool_mode="strict">
    treatment_run = <build via existing helper, context.temporal_pool_mode="unconstrained">
    protocol = <existing single-hypothesis protocol fixture, baseline vs treatment>

    with pytest.raises(ValueError, match="temporal_pool_mode"):
        evaluate_study_protocol(
            runs={"baseline": baseline_run, "treatment": treatment_run},
            protocol=protocol,
        )


def test_evaluate_study_protocol_rejects_mismatched_family_policy(
    ...
):
    """ADR 0027 Enforcement #6: pairing runs with different family_policy compares
    pools of different composition, not a like-for-like ranking comparison."""
    baseline_run = <build via existing helper, context.family_policy="allow">
    treatment_run = <build via existing helper, context.family_policy="collapse">
    protocol = <existing single-hypothesis protocol fixture, baseline vs treatment>

    with pytest.raises(ValueError, match="family_policy"):
        evaluate_study_protocol(
            runs={"baseline": baseline_run, "treatment": treatment_run},
            protocol=protocol,
        )


def test_evaluate_study_protocol_rejects_mismatched_denominator_semantics(
    ...
):
    """ADR 0028: a frozen pre-fix run and a post-fix run must never be paired --
    their Recall/nDCG values are not computed under the same definition."""
    baseline_run = <build via existing helper>
    treatment_run = baseline_run.model_copy(update={"denominator_semantics": "some_other_value"})
    protocol = <existing single-hypothesis protocol fixture, baseline vs treatment>

    with pytest.raises(ValueError, match="denominator_semantics"):
        evaluate_study_protocol(
            runs={"baseline": baseline_run, "treatment": treatment_run},
            protocol=protocol,
        )
```

`treatment_run.model_copy(update={"denominator_semantics": "some_other_value"})` will raise a Pydantic validation error itself, since the field is a single-value `Literal`. Use `model_construct` instead to bypass validation for this one test, since the whole point is simulating a value that could only arise from parsing an old frozen artifact under a hypothetically widened type — or, simpler and equally valid: skip this specific test if constructing an invalid literal is awkward, and instead rely on the fact that any two runs both built by the current code always share `"eligible_universe_v1"`, making the temporal_pool_mode and family_policy mismatch tests (Step 2's other two) sufficient coverage for the guard's existence and message format. Use judgment here: if `model_construct` cleanly bypasses validation, keep this third test; if it produces an awkward or misleading test, drop it and note the reason in the implementer's report.

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `python -m pytest backend/test/unit/application/evaluation/test_comparative_evaluation.py -v -k "mismatched"`
Expected: FAIL (no such guard exists yet — either no exception raised, or a different, unrelated exception from deeper in `_extract_paired_vectors`).

- [ ] **Step 4: Implement `_validate_paired_run_identity`**

Add this function to `comparative.py`, right before `evaluate_study_protocol`:

```python
def _validate_paired_run_identity(
    baseline_run: EvaluationRunReport, treatment_run: EvaluationRunReport, hypothesis_id: str
) -> None:
    """ADR 0018 Enforcement #6 / ADR 0027 Enforcement #6 / ADR 0028: two runs built
    under different pool-construction or denominator semantics are not a like-for-like
    ranking comparison. Pairing them would silently attribute a pool-composition or
    denominator-definition difference to the ranking engine under test, contaminating
    the very hypothesis test this harness exists to run honestly.
    """
    if baseline_run.context.temporal_pool_mode != treatment_run.context.temporal_pool_mode:
        raise ValueError(
            f"Hypothesis '{hypothesis_id}': baseline and treatment runs use different "
            f"temporal_pool_mode ('{baseline_run.context.temporal_pool_mode}' vs "
            f"'{treatment_run.context.temporal_pool_mode}') -- not a like-for-like "
            "comparison (ADR 0018 Enforcement #6)."
        )
    if baseline_run.context.family_policy != treatment_run.context.family_policy:
        raise ValueError(
            f"Hypothesis '{hypothesis_id}': baseline and treatment runs use different "
            f"family_policy ('{baseline_run.context.family_policy}' vs "
            f"'{treatment_run.context.family_policy}') -- not a like-for-like "
            "comparison (ADR 0027 Enforcement #6)."
        )
    if baseline_run.denominator_semantics != treatment_run.denominator_semantics:
        raise ValueError(
            f"Hypothesis '{hypothesis_id}': baseline and treatment runs use different "
            f"denominator_semantics ('{baseline_run.denominator_semantics}' vs "
            f"'{treatment_run.denominator_semantics}') -- comparing runs computed under "
            "different Recall/nDCG denominator definitions is scientifically invalid (ADR 0028)."
        )
```

- [ ] **Step 5: Call it from `evaluate_study_protocol`**

Insert the call immediately after `treatment_run = runs[hypothesis.treatment]` and before `_extract_paired_vectors` is called:

```python
        baseline_run = runs[hypothesis.baseline]
        treatment_run = runs[hypothesis.treatment]
        _validate_paired_run_identity(baseline_run, treatment_run, hypothesis.id)

        baseline_vec, treatment_vec, excluded_ids = _extract_paired_vectors(
            baseline_run, treatment_run, hypothesis
        )
```

- [ ] **Step 6: Run the new tests to verify they pass, then the full suite**

Run: `python -m pytest backend/test/unit/application/evaluation/test_comparative_evaluation.py -v`
Expected: all pass, including the new ones.

Run: `python -m pytest backend/test -q`
Expected: all pass (existing comparative tests already pair runs with matching `temporal_pool_mode`/`family_policy`/`denominator_semantics`, so the new guard must not break them).

Run: `python -m mypy backend/src/main --ignore-missing-imports`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add backend/src/main/application/evaluation/comparative.py \
        backend/test/unit/application/evaluation/test_comparative_evaluation.py
git commit -m "feat(evaluation): guard comparative hypothesis tests against mismatched run identity"
```

---

### Task 3: ADR 0028, cross-references, and frozen-artifact regression pin

**Files:**
- Create: `docs/adr/0028-eligible-universe-relevance-denominators.md`
- Modify: `docs/adr/0018-temporal-pool-eligibility-contract.md` (add a pointer to ADR 0028's correction)
- Modify: `docs/adr/0027-family-aware-evaluation-contract.md` (mark "Known gap" and Enforcement item 6 resolved, point to ADR 0028)
- Modify: `docs/roadmap.md` (mark this gap closed, if §6 still lists it open)
- Create: `backend/test/unit/architecture/test_frozen_experiment_artifacts_unmodified.py`

**Interfaces:**
- Consumes: nothing new — this task is documentation plus one regression-safety test.
- Produces: nothing consumed by other tasks (this is the final task).

- [ ] **Step 1: Write the frozen-artifact regression pin**

Create `backend/test/unit/architecture/test_frozen_experiment_artifacts_unmodified.py`:

```python
"""ADR 0028 reproducibility guarantee: this PR (and any future PR) must never
overwrite the frozen pre-ADR-0028 experiment artifacts under data/experiments/ --
they were computed under the old, defective denominator semantics and must stay
byte-for-byte as historical evidence of what that produced, distinguishable from
any future re-run under the fixed eligible-universe semantics.

If this test fails, a file listed below was edited. That is only ever the correct
outcome as a DELIBERATE, separately reviewed re-freeze -- never as a side effect
of an unrelated change. Update the corresponding hash here only when that is true.
"""

import hashlib
from pathlib import Path

import pytest

_EXPECTED_SHA256 = {
    "dataset_identity_audit.json": "7d9152ab5fcd9b2a1cfa712dda5ce492f3072768f0754a9b372c9d20a846bc02",
    "m0_run_report.json": "86aaefefdba75c4575a82b21210c42b78f8c809b08f3a6fcadbb6a4b697fca9b",
    "m0_run_report_strict.json": "2f680d9a0673acad0bb60738f8737d32b22ba9ce374b82b772931bd97979a6d4",
    "m0_vs_m1_comparative_report.json": "cc0b4bb1433c0bf627a5c447598411b3edb8ee707f4335f34c74ebd7c905da0c",
    "m0_vs_m1_comparative_report_strict.json": "ce9417c794b391c87b5bc497eded29c6632446101b75103d78a73340f61e6d10",
    "m1_run_report.json": "203c694db657212f0a554f3779903b33b2d7b3a4dbdf876a6923e3fc238a5581",
    "m1_run_report_strict.json": "62f33196c770a441042b56fea2dfd7c15d65b7d23214e5d11645c30083137a79",
    "pilot_evaluation_report.json": "792e7e078ff467c7cf430792bd5727ba7f4f01f9ae2f4393e97944f55e95dbe4",
    "power_analysis_wilcoxon.json": "8d41d3d28efe60bfe2712257639db9a36b313f0327704ffc356fe31583bf9d87",
    "power_analysis_wilcoxon_n39_sensitivity.json": "793bb6b648672ca321f1c0325abb33385222b9f9e053f0c37f024cf3a3fc095a",
    "power_analysis_wilcoxon_n43_sensitivity.json": "ee06886e6f86d9defdc46efb5025b7d50b3a85d8afa811f44eabccfe583e3bd5",
    "power_analysis_wilcoxon_n48_sensitivity.json": "98e1d195047407c02f2abef59108fa208a9f77b81b6436a34d2504f604ae4f84",
}


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("filename,expected_sha256", sorted(_EXPECTED_SHA256.items()))
def test_frozen_experiment_artifact_unmodified(filename: str, expected_sha256: str) -> None:
    path = _get_repo_root() / "data" / "experiments" / filename
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected_sha256, (
        f"data/experiments/{filename} has changed content (sha256 {actual} != "
        f"expected {expected_sha256}). These files were frozen under the "
        "pre-ADR-0028 denominator semantics -- if this is a deliberate, "
        "separately-reviewed re-freeze, update the expected hash here; "
        "otherwise this file was edited by accident."
    )


def test_frozen_experiment_artifacts_directory_has_no_untracked_new_files() -> None:
    """Catches the complementary mistake: a new file dropped into data/experiments/
    without updating _EXPECTED_SHA256 above to account for it."""
    actual_files = {
        p.name for p in (_get_repo_root() / "data" / "experiments").glob("*.json")
    }
    assert actual_files == set(_EXPECTED_SHA256.keys()), (
        f"data/experiments/*.json contents changed: {actual_files ^ set(_EXPECTED_SHA256.keys())}. "
        "Update _EXPECTED_SHA256 in this test to match."
    )
```

- [ ] **Step 2: Run the new test to verify it passes against the current, untouched files**

Run: `python -m pytest backend/test/unit/architecture/test_frozen_experiment_artifacts_unmodified.py -v`
Expected: both tests PASS (Tasks 1-2 never touched `data/experiments/`).

- [ ] **Step 3: Write ADR 0028**

Create `docs/adr/0028-eligible-universe-relevance-denominators.md`:

```markdown
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
```

- [ ] **Step 4: Amend ADR 0018 with a pointer to ADR 0028**

In `docs/adr/0018-temporal-pool-eligibility-contract.md`, find §3's claim about Recall/nDCG denominators (the sentence ADR 0028 quotes above) and add a footnote-style correction immediately after it:

```markdown
> **Correction (ADR 0028, 2026-09-11):** this claim was not accurate as originally
> implemented — `DefaultEvaluationRunner` filtered the *candidate pool* but continued
> to pass the demand's full, unrestricted annotation set to `compute_demand_metrics`,
> so a temporally-ineligible patent's judgement still inflated the Recall/nDCG
> denominator. Fixed by ADR 0028's `_restrict_judgements_to_eligible_universe`.
```

(Read the file first to find the exact paragraph and match its surrounding markdown formatting before inserting.)

- [ ] **Step 5: Amend ADR 0027 to mark the "Known gap" section and Enforcement item 6 resolved**

In `docs/adr/0027-family-aware-evaluation-contract.md`:

- Change the `## Known gap: ...` heading to `## Known gap (RESOLVED by ADR 0028): ...` and add one sentence at the top of that section: "Resolved by ADR 0028 (`docs/adr/0028-eligible-universe-relevance-denominators.md`), which fixes this defect jointly for `temporal_pool_mode` and `family_policy` — see that ADR for the mechanism."
- In the Enforcement section, change item 6 to note it is superseded: prefix it with "**(Superseded by ADR 0028's code-enforced comparative guard — this item is now historical context, not an active constraint.)**" followed by the original text unchanged.

- [ ] **Step 6: Update `docs/roadmap.md` if it still lists this gap as open**

Read `docs/roadmap.md` §6 (the section that originally named the family-policy gap this branch's earlier PR closed). If it separately lists the denominator/comparability gap as still open, mark it closed with a one-line pointer to ADR 0028, following whatever formatting convention the rest of that section already uses for closed items. If no such line exists (the earlier PR's roadmap update already folded this in generically), skip this step and note that in the implementer's report.

- [ ] **Step 7: Run the full suite and mypy one final time**

Run: `python -m pytest backend/test -q`
Expected: all pass.

Run: `python -m mypy backend/src/main --ignore-missing-imports`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add docs/adr/0028-eligible-universe-relevance-denominators.md \
        docs/adr/0018-temporal-pool-eligibility-contract.md \
        docs/adr/0027-family-aware-evaluation-contract.md \
        docs/roadmap.md \
        backend/test/unit/architecture/test_frozen_experiment_artifacts_unmodified.py
git commit -m "docs(adr): add ADR 0028, resolve ADR 0027 known gap, pin frozen experiment artifacts"
```

## Self-Review

**1. Spec coverage:** All five points from the user's PR #98 scope are covered — (1) contract defining the eligible evaluation universe (ADR 0028 §1, Task 1); (2) tests-first covering temporal exclusion (Task 1 Step 10), family collapse remap (Task 1 Steps 9/12), family exclusion (Task 1 Step 11), `allow` no-op (ADR 0028 §3, provable from existing untouched tests), partially-relevant family (Task 1 Step 12), `UNCERTAIN` non-promotion (Task 1 Step 13); (3) implementation in the application/evaluation layer, not ranking (Task 1 modifies only `runner.py`, never `matching_adapter.py`/`engine.py`); (4) reproducibility / frozen-artifact protection (Task 3 Steps 1-2); (5) comparative guard (Task 2).

**2. Placeholder scan:** Task 2's test bodies use `<build via existing helper...>` placeholders deliberately, with explicit instruction to read the existing file's fixture style first — this is the one spot where the plan defers to the implementer reading existing test infrastructure rather than guessing its exact shape, flagged inline rather than silently assumed. Every other step has complete, runnable code.

**3. Type consistency:** `_apply_family_policy`'s new return type `tuple[list[EvaluationPatent], dict[str, list[str]]]` is used consistently in both its Task 1 Step 4 definition and its Step 6 call site (`eligible_patents, collapse_groups = _apply_family_policy(...)`). `denominator_semantics: Literal["eligible_universe_v1"]` matches the fixed string literal used everywhere it's constructed (Task 1 Steps 1, 2, 7) and compared (Task 2 Step 4).
