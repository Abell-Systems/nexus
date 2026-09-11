"""Unit tests for EvaluationRunner orchestrator under ADR 0007.

Invariants verified:
- Runner delegates exclusively to EvaluationRankingPort.rank_candidates().
- Runner is independent of matching-domain types (no CandidatePool, MatchAssessment, etc.).
- Runner uses the closed candidate universe defined in ValidatedDataset.
- Runner preserves the port's original ranking order without re-sorting.
- Runner delegates all metric calculations to metrics.py.
- Runner produces sealed EvaluationRunReport with exact dataset and policy SHAs.
- Runner stamps injected EvaluationExecutionContext without filesystem or Git lookups.
- Runner does not mutate the dataset or policy.
- Runner operates purely in memory with zero filesystem access.

The FakeRankingPort below implements EvaluationRankingPort without any matching-domain type,
mirroring the clean boundary that DefaultMatchingAdapter provides in production.
"""

from datetime import UTC, date, datetime

import pytest

from application.evaluation.runner import (
    DefaultEvaluationRunner,
    family_metadata_available,
    validate_family_policy_feasible,
    validate_temporal_pool_mode_consistency,
)
from domain.models.evaluation import (
    DataModality,
    EvaluationAnnotation,
    EvaluationDataset,
    EvaluationDatasetManifest,
    EvaluationDemand,
    EvaluationExecutionContext,
    EvaluationPatent,
    EvaluationProvenance,
    RelevanceGrade,
    ValidatedDataset,
)
from domain.models.matching import (
    ConfidenceThresholds,
    CPCConcordanceLevels,
    MatchingPolicyConfig,
    OperationalLimits,
    RankerWeights,
    SufficiencyRules,
)
from domain.protocols.evaluation import EvaluationRankingPort


class FakeRankingPort:
    """Explicit fake implementing EvaluationRankingPort.

    Simulates the boundary that DefaultMatchingAdapter provides in production.
    The runner should call rank_candidates() with EvaluationDemand and list[EvaluationPatent].
    This fake records the calls and returns a deterministic fixed ranking.
    """

    def __init__(self, fixed_order: list[str]) -> None:
        self.fixed_order = fixed_order
        self.received_demands: list[EvaluationDemand] = []
        self.received_patents: list[list[EvaluationPatent]] = []

    def rank_candidates(
        self,
        demand: EvaluationDemand,
        patents: list[EvaluationPatent],
    ) -> list[str]:
        self.received_demands.append(demand)
        self.received_patents.append(patents)
        universe_ids = {p.publication_id for p in patents}
        # Return fixed_order preserving only those in the universe
        return [pub_id for pub_id in self.fixed_order if pub_id in universe_ids]


@pytest.fixture
def sample_policy() -> MatchingPolicyConfig:
    return MatchingPolicyConfig(
        policy_id="test_matching_policy",
        policy_version="1.0.0",
        description="Deterministic test policy",
        weights=RankerWeights(alpha=0.25, beta=0.45, gamma=0.30),
        operational_limits=OperationalLimits(retrieval_limit=100, max_candidate_pool_size=300),
        cpc_concordance_levels=CPCConcordanceLevels(
            subgroup=1.0, main_group=0.8, subclass=0.5, section=0.2, none=0.0
        ),
        confidence_thresholds=ConfidenceThresholds(strong=0.75, moderate=0.50, weak=0.25),
        sufficiency_rules=SufficiencyRules(
            min_active_signals=2, min_signals_for_sufficient=3, require_temporal_validity=True
        ),
        concept_to_cpc_taxonomy={"drainage": ["E03C"]},
        policy_sha256="c" * 64,
    )


@pytest.fixture
def sample_validated_dataset() -> ValidatedDataset:
    prov = EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-1",
        title="Sanitary Fixtures",
        description="Drainage equipment",
        posted_date=date(2023, 1, 1),
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id=f"P-{i}",
            publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"],
            title=f"Patent {i}",
            abstract=f"Abstract {i}",
            provenance=prov,
        )
        for i in range(1, 6)
    ]
    # P-1: GRADE_0, P-2: UNCERTAIN, P-3: GRADE_3, P-4: GRADE_2, P-5: GRADE_0
    annotations = [
        EvaluationAnnotation(
            demand_id="D-1",
            publication_id="P-1",
            grade=RelevanceGrade.GRADE_0,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-1",
            publication_id="P-2",
            grade=RelevanceGrade.UNCERTAIN,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-1",
            publication_id="P-3",
            grade=RelevanceGrade.GRADE_3,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-1",
            publication_id="P-4",
            grade=RelevanceGrade.GRADE_2,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-1",
            publication_id="P-5",
            grade=RelevanceGrade.GRADE_0,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
    ]
    dataset = EvaluationDataset(
        dataset_id="eval-corpus-v1",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        description="Test corpus",
        demands=[demand],
        patents=patents,
        annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="eval-corpus-v1",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        source_authorities=["oepm"],
        demand_count=1,
        patent_count=5,
        annotation_count=5,
        content_sha256="d" * 64,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


@pytest.fixture
def sample_context() -> EvaluationExecutionContext:
    return EvaluationExecutionContext(
        engine_name="FakeRankingPort",
        engine_version="1.0.0",
        engine_commit_hash="a321b0c",
        execution_timestamp=datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC),
        environment="test",
        temporal_pool_mode="unconstrained",
        family_policy="allow",
    )


@pytest.fixture
def strict_context() -> EvaluationExecutionContext:
    return EvaluationExecutionContext(
        engine_name="FakeRankingPort",
        engine_version="1.0.0",
        engine_commit_hash="a321b0c",
        execution_timestamp=datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC),
        environment="test",
        temporal_pool_mode="strict",
        family_policy="allow",
    )


@pytest.fixture
def dataset_with_temporal_violation() -> ValidatedDataset:
    """One demand, one temporally-eligible patent (t_pub < t_demand), one
    temporally-ineligible patent (t_pub >= t_demand) — ADR 0018 §2/§3."""
    prov = EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-TEMPORAL",
        title="Sanitary Fixtures",
        description="Drainage equipment",
        posted_date=date(2023, 6, 1),
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id="P-ELIGIBLE",
            publication_date=date(2022, 1, 1),  # t_pub < t_demand: eligible
            classifications_cpc=["E03C"],
            title="Eligible patent",
            abstract="Abstract",
            provenance=prov,
        ),
        EvaluationPatent(
            publication_id="P-INELIGIBLE",
            publication_date=date(2024, 1, 1),  # t_pub >= t_demand: ineligible
            classifications_cpc=["E03C"],
            title="Ineligible patent",
            abstract="Abstract",
            provenance=prov,
        ),
    ]
    annotations = [
        EvaluationAnnotation(
            demand_id="D-TEMPORAL",
            publication_id="P-ELIGIBLE",
            grade=RelevanceGrade.GRADE_2,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-TEMPORAL",
            publication_id="P-INELIGIBLE",
            grade=RelevanceGrade.GRADE_3,
            annotator_role="expert",
            modality=DataModality.EXPERT_LABELLED,
        ),
    ]
    dataset = EvaluationDataset(
        dataset_id="eval-corpus-temporal",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        description="Temporal-violation test corpus",
        demands=[demand],
        patents=patents,
        annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="eval-corpus-temporal",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        source_authorities=["oepm"],
        demand_count=1,
        patent_count=2,
        annotation_count=2,
        content_sha256="e" * 64,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


def test_runner_delegates_and_preserves_engine_ranking(
    sample_validated_dataset, sample_policy, sample_context
):
    """Verifies ranking delegation and invariant preservation end-to-end."""
    # Port returns: [P-2 (UNCERTAIN), P-3 (GRADE_3), P-1 (GRADE_0), P-4 (GRADE_2), P-5 (GRADE_0)]
    ranking_port = FakeRankingPort(fixed_order=["P-2", "P-3", "P-1", "P-4", "P-5"])
    assert isinstance(ranking_port, EvaluationRankingPort)

    runner = DefaultEvaluationRunner()
    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )

    # 1. Verify delegation: port received the correct evaluation-domain objects
    assert len(ranking_port.received_demands) == 1
    assert ranking_port.received_demands[0].demand_id == "D-1"
    assert len(ranking_port.received_patents[0]) == 5

    # 2. Verify provenance stamping
    assert report.dataset_sha256 == sample_validated_dataset.manifest.content_sha256
    assert report.policy_sha256 == sample_policy.policy_sha256
    assert report.context.engine_commit_hash == sample_context.engine_commit_hash
    assert report.context.engine_name == sample_context.engine_name

    # 3. Verify demand metrics
    assert len(report.demand_reports) == 1
    d_rep = report.demand_reports[0]
    assert d_rep.candidate_count == 5
    assert d_rep.judged_count == 4
    assert d_rep.uncertain_count == 1

    # 4. Invariant: ranking order is preserved!
    # Port returned: P-2 (UNCERTAIN), P-3 (GRADE_3), P-1 (GRADE_0), ...
    # Under strict, P-3 is at original rank 2! => MRR = 1/2 = 0.50
    assert d_rep.strict_metrics.mrr == 0.50
    assert d_rep.strict_metrics.mrr_at_5 == 0.50


def test_runner_passes_full_patent_universe_to_port(
    sample_validated_dataset, sample_policy, sample_context
):
    """Verifies runner passes the sealed patent universe to the ranking port, not a subset."""
    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )

    # The port must receive all patents from the sealed dataset universe
    expected_ids = {p.publication_id for p in sample_validated_dataset.dataset.patents}
    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    assert received_ids == expected_ids, (
        "Runner must pass the complete sealed patent universe to the ranking port."
    )
    assert len(ranking_port.received_patents[0]) == 5


def test_runner_never_reads_filesystem(
    sample_validated_dataset, sample_policy, sample_context, monkeypatch
):
    """Proves that EvaluationRunner executes completely in-memory without touching disk."""
    import builtins

    def forbidden_open(*args, **kwargs):
        raise AssertionError("EvaluationRunner attempted to open a file from the filesystem!")

    monkeypatch.setattr(builtins, "open", forbidden_open)

    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )
    assert report.run_id.startswith("eval-run-")


def test_runner_does_not_mutate_dataset_or_policy(
    sample_validated_dataset, sample_policy, sample_context
):
    dataset_copy = sample_validated_dataset.model_dump()
    policy_copy = sample_policy.model_dump()

    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )

    assert sample_validated_dataset.model_dump() == dataset_copy
    assert sample_policy.model_dump() == policy_copy


def test_runner_never_invokes_git(
    sample_validated_dataset, sample_policy, sample_context, monkeypatch
):
    """Proves that EvaluationRunner never executes git subcommands."""
    import subprocess

    def forbidden_run(*args, **kwargs):
        raise AssertionError("EvaluationRunner attempted to execute an external subprocess/git command!")

    monkeypatch.setattr(subprocess, "run", forbidden_run)
    monkeypatch.setattr(subprocess, "Popen", forbidden_run)

    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )
    assert report.context.engine_commit_hash == sample_context.engine_commit_hash


def test_runner_uses_closed_candidate_universe(
    sample_validated_dataset, sample_policy, sample_context
):
    """Verifies that the port receives strictly the dataset patents as the candidate universe."""
    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )

    received_patents = ranking_port.received_patents[0]
    expected_ids = {p.publication_id for p in sample_validated_dataset.dataset.patents}
    actual_ids = {p.publication_id for p in received_patents}
    assert actual_ids == expected_ids
    assert len(received_patents) == len(sample_validated_dataset.dataset.patents)


def test_runner_produces_strict_and_broad_metrics(
    sample_validated_dataset, sample_policy, sample_context
):
    """Verifies that both strict and broad metrics are computed and distinct."""
    # Ranking: P-3 (GRADE_3), P-4 (GRADE_2), P-1 (GRADE_0), P-2 (UNCERTAIN), P-5 (GRADE_0)
    ranking_port = FakeRankingPort(fixed_order=["P-3", "P-4", "P-1", "P-2", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )

    d_rep = report.demand_reports[0]
    # Under Strict: only P-3 is relevant (1 total in universe)
    # Under Broad: P-3 and P-4 are relevant (2 total in universe)
    assert d_rep.strict_metrics.precision_at_1 == 1.0
    assert d_rep.strict_metrics.precision_at_3 == 1 / 3  # P-3, P-4, P-1 → only P-3 strict relevant
    assert d_rep.broad_metrics.precision_at_3 == 2 / 3  # P-3, P-4, P-1 → P-3 and P-4 broad relevant
    assert report.macro_strict.precision_at_1 == 1.0
    assert report.macro_broad.precision_at_1 == 1.0


# ---------------------------------------------------------------------------
# ADR 0018: temporal pool eligibility (temporal_pool_mode)
# ---------------------------------------------------------------------------


def test_runner_strict_mode_excludes_temporally_ineligible_patents_from_pool(
    dataset_with_temporal_violation, sample_policy, strict_context
):
    """ADR 0018 §3: strict mode excludes t_pub >= t_demand patents before ranking —
    the ranking port must never even see P-INELIGIBLE."""
    ranking_port = FakeRankingPort(fixed_order=["P-ELIGIBLE", "P-INELIGIBLE"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=dataset_with_temporal_violation,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=strict_context,
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    assert received_ids == {"P-ELIGIBLE"}, (
        "Strict mode must exclude the temporally-ineligible patent from the pool "
        "before it ever reaches the ranking port."
    )


def test_runner_strict_mode_computes_candidate_universe_size_from_filtered_pool(
    dataset_with_temporal_violation, sample_policy, strict_context
):
    """ADR 0018 §3: candidate_universe_size (and therefore Recall/nDCG denominators)
    must reflect the filtered pool, not the full sealed dataset universe."""
    ranking_port = FakeRankingPort(fixed_order=["P-ELIGIBLE"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_temporal_violation,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=strict_context,
    )

    d_rep = report.demand_reports[0]
    assert d_rep.candidate_count == 1, (
        "candidate_count must equal the filtered pool size (1), not the sealed "
        "dataset's full patent count (2)."
    )


def test_runner_unconstrained_mode_preserves_full_universe_including_ineligible_patents(
    dataset_with_temporal_violation, sample_policy, sample_context
):
    """ADR 0018 §3/§4: unconstrained mode is the pre-ADR-0018 baseline — the full
    universe, ineligible patents included, is preserved exactly as before."""
    ranking_port = FakeRankingPort(fixed_order=["P-ELIGIBLE", "P-INELIGIBLE"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_temporal_violation,
        ranking_port=ranking_port,
        policy=sample_policy,
        context=sample_context,
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    assert received_ids == {"P-ELIGIBLE", "P-INELIGIBLE"}
    assert report.demand_reports[0].candidate_count == 2


# ---------------------------------------------------------------------------
# ADR 0018 §2: unconstrained + require_temporal_validity=True must fail fast
# ---------------------------------------------------------------------------


def test_validate_temporal_pool_mode_consistency_rejects_contaminated_unconstrained():
    """ADR 0018 §2: unconstrained paired with require_temporal_validity=True would
    silently reintroduce temporal enforcement into the no-enforcement condition."""
    with pytest.raises(ValueError, match="unconstrained"):
        validate_temporal_pool_mode_consistency(
            temporal_pool_mode="unconstrained", require_temporal_validity=True
        )


def test_validate_temporal_pool_mode_consistency_accepts_clean_unconstrained():
    """unconstrained + require_temporal_validity=False is the genuine, uncontaminated
    no-enforcement condition RQ3 requires — must not raise."""
    validate_temporal_pool_mode_consistency(
        temporal_pool_mode="unconstrained", require_temporal_validity=False
    )


def test_validate_temporal_pool_mode_consistency_accepts_strict_regardless_of_flag():
    """ADR 0018 §4: in strict mode, require_temporal_validity is vacuous (ineligible
    candidates never reach the evaluator) but not contradictory — must not raise
    whether the policy flag is True or False."""
    validate_temporal_pool_mode_consistency(temporal_pool_mode="strict", require_temporal_validity=True)
    validate_temporal_pool_mode_consistency(temporal_pool_mode="strict", require_temporal_validity=False)


# ---------------------------------------------------------------------------
# ADR 0027: family-aware evaluation fail-fast validator
# ---------------------------------------------------------------------------


def test_family_metadata_available_true_when_all_patents_have_family_id(sample_validated_dataset):
    patents = [
        p.model_copy(update={"family_id": f"FAM-{i}"})
        for i, p in enumerate(sample_validated_dataset.dataset.patents)
    ]
    assert family_metadata_available(patents) is True


def test_family_metadata_available_false_when_any_patent_missing_family_id(sample_validated_dataset):
    patents = list(sample_validated_dataset.dataset.patents)  # family_id is None on all of these
    assert family_metadata_available(patents) is False


def test_validate_family_policy_feasible_allows_allow_regardless_of_metadata(sample_validated_dataset):
    validate_family_policy_feasible("allow", sample_validated_dataset.dataset.patents)


def test_validate_family_policy_feasible_raises_for_collapse_without_metadata(sample_validated_dataset):
    with pytest.raises(ValueError, match="FAMILY_METADATA_UNAVAILABLE"):
        validate_family_policy_feasible("collapse", sample_validated_dataset.dataset.patents)


def test_validate_family_policy_feasible_raises_for_exclude_related_without_metadata(sample_validated_dataset):
    with pytest.raises(ValueError, match="FAMILY_METADATA_UNAVAILABLE"):
        validate_family_policy_feasible("exclude_related", sample_validated_dataset.dataset.patents)


def test_validate_family_policy_feasible_accepts_collapse_with_full_metadata(sample_validated_dataset):
    patents = [
        p.model_copy(update={"family_id": f"FAM-{i}"})
        for i, p in enumerate(sample_validated_dataset.dataset.patents)
    ]
    validate_family_policy_feasible("collapse", patents)


# ---------------------------------------------------------------------------
# ADR 0027: family-aware pool transform, wired into run_evaluation
# ---------------------------------------------------------------------------


@pytest.fixture
def dataset_with_known_family() -> ValidatedDataset:
    """Two patents sharing FAM-A (P-A1, P-A2), one singleton family FAM-B (P-B1)."""
    prov = EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-FAM",
        title="Sanitary Fixtures",
        description="Drainage equipment",
        posted_date=date(2023, 1, 1),
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id="P-A1", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent A1", abstract="Abstract",
            provenance=prov, family_id="FAM-A",
        ),
        EvaluationPatent(
            publication_id="P-A2", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent A2", abstract="Abstract",
            provenance=prov, family_id="FAM-A",
        ),
        EvaluationPatent(
            publication_id="P-B1", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent B1", abstract="Abstract",
            provenance=prov, family_id="FAM-B",
        ),
    ]
    annotations = [
        EvaluationAnnotation(
            demand_id="D-FAM", publication_id=pid, grade=RelevanceGrade.GRADE_2,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        )
        for pid in ("P-A1", "P-A2", "P-B1")
    ]
    dataset = EvaluationDataset(
        dataset_id="eval-corpus-family", schema_version="1.0.0", dataset_version="1.0.0",
        description="Family test corpus", demands=[demand], patents=patents, annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="eval-corpus-family", schema_version="1.0.0", dataset_version="1.0.0",
        source_authorities=["oepm"], demand_count=1, patent_count=3, annotation_count=3,
        content_sha256="f" * 64,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


def _family_context(family_policy: str) -> EvaluationExecutionContext:
    return EvaluationExecutionContext(
        engine_name="FakeRankingPort", engine_version="1.0.0", engine_commit_hash="a321b0c",
        execution_timestamp=datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC), environment="test",
        temporal_pool_mode="unconstrained", family_policy=family_policy,
    )


def test_runner_allow_policy_passes_full_pool_unchanged(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("allow"),
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    assert received_ids == {"P-A1", "P-A2", "P-B1"}


def test_runner_collapse_policy_keeps_one_representative_per_family(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("collapse"),
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    # FAM-A has two members (P-A1, P-A2): only the lexicographically smallest
    # publication_id (P-A1) survives. FAM-B is a singleton and survives whole.
    assert received_ids == {"P-A1", "P-B1"}
    assert report.demand_reports[0].candidate_count == 2


def test_runner_exclude_related_policy_drops_every_multi_member_family(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("exclude_related"),
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    # FAM-A has two members: both are dropped entirely. FAM-B is a singleton: kept.
    assert received_ids == {"P-B1"}
    assert report.demand_reports[0].candidate_count == 1


def test_run_evaluation_raises_when_collapse_requested_without_family_metadata(
    sample_validated_dataset, sample_policy
):
    """sample_validated_dataset's patents all have family_id=None (Task 1 default)."""
    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    with pytest.raises(ValueError, match="FAMILY_METADATA_UNAVAILABLE"):
        runner.run_evaluation(
            dataset=sample_validated_dataset, ranking_port=ranking_port,
            policy=sample_policy, context=_family_context("collapse"),
        )


def test_run_evaluation_records_family_metadata_available_false_under_allow(
    sample_validated_dataset, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("allow"),
    )

    assert report.family_metadata_available is False


def test_run_evaluation_records_family_metadata_available_true_under_collapse(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("collapse"),
    )

    assert report.family_metadata_available is True
