"""Unit tests for EvaluationRunner orchestrator under ADR 0007.

Invariants verified:
- Runner delegates exclusively to EvaluatableEngine.evaluate().
- Runner passes EvaluationPolicyIdentity without modification.
- Runner uses the closed candidate universe defined in ValidatedDataset.
- Runner preserves the engine's original ranking order without re-sorting.
- Runner delegates all metric calculations to metrics.py.
- Runner produces sealed EvaluationRunReport with exact dataset and policy SHAs.
- Runner stamps injected EvaluationExecutionContext without filesystem or Git lookups.
- Runner does not mutate the dataset or policy.
- Runner operates purely in memory with zero filesystem access.
- Candidates in the pool have retrieval_scores={} — no synthetic evidence.
- Real patent metadata (PatentCandidateEvidence) is passed to the engine from benchmark data.
"""

from datetime import UTC, date, datetime

import pytest

from application.evaluation.runner import DefaultEvaluationRunner
from domain.models.demand import DemandRecord, DemandSignal
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
    CandidatePool,
    ConfidenceThresholds,
    CPCConcordanceLevels,
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
    OperationalLimits,
    RankerWeights,
    SufficiencyRules,
)


class FakeDeterministicMatchingEngine:
    """Explicit fake implementing the EvaluatableEngine protocol without using DefaultMatchingEngine."""

    def __init__(self, fixed_order: list[str]) -> None:
        self.fixed_order = fixed_order
        self.received_demands: list[DemandRecord | DemandSignal] = []
        self.received_pools: list[CandidatePool] = []
        self.received_policies: list[MatchingPolicyConfig] = []
        self.received_patent_metadata: list[object] = []

    def evaluate(
        self,
        demand: DemandRecord | DemandSignal,
        candidates: CandidatePool,
        policy: MatchingPolicyConfig,
        patent_metadata: object = None,
    ) -> list[MatchAssessment]:
        self.received_demands.append(demand)
        self.received_pools.append(candidates)
        self.received_policies.append(policy)
        self.received_patent_metadata.append(patent_metadata)

        assessments: list[MatchAssessment] = []
        pool_ids = {c.publication_id for c in candidates.candidates}

        # Return assessments in self.fixed_order (which determines the system ranking)
        for pub_id in self.fixed_order:
            if pub_id in pool_ids:
                assessments.append(
                    MatchAssessment(
                        demand_id=demand.demand_id,
                        publication_id=pub_id,
                        overall_score=0.85,
                        confidence=MatchConfidence.STRONG,
                        sufficiency=EvidenceSufficiency.SUFFICIENT,
                        features=MatchFeatures(),
                        rationale="Fake assessment",
                        policy_id=policy.policy_id,
                        policy_version=policy.policy_version,
                        policy_sha256=policy.policy_sha256,
                    )
                )
        return assessments


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
        engine_name="FakeDeterministicMatchingEngine",
        engine_version="1.0.0",
        engine_commit_hash="a321b0c",
        execution_timestamp=datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC),
        environment="test",
    )


def test_runner_delegates_and_preserves_engine_ranking(
    sample_validated_dataset, sample_policy, sample_context
):
    # System returns ranking: [P-2 (UNCERTAIN), P-3 (GRADE_3), P-1 (GRADE_0), P-4 (GRADE_2), P-5 (GRADE_0)]
    engine_order = ["P-2", "P-3", "P-1", "P-4", "P-5"]
    engine = FakeDeterministicMatchingEngine(fixed_order=engine_order)
    from domain.protocols.evaluation import EvaluatableEngine
    assert isinstance(engine, EvaluatableEngine)

    runner = DefaultEvaluationRunner()
    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        engine=engine,
        policy=sample_policy,
        context=sample_context,
    )

    # 1. Verification of delegation
    assert len(engine.received_demands) == 1
    assert engine.received_demands[0].demand_id == "D-1"
    assert len(engine.received_pools[0].candidates) == 5
    assert engine.received_policies[0] is sample_policy

    # 1b. Verification: candidates have retrieval_scores={} (no synthetic evidence)
    for candidate in engine.received_pools[0].candidates:
        assert candidate.retrieval_scores == {}, (
            f"Candidate {candidate.publication_id} must have retrieval_scores={{}} — "
            "fabricating synthetic scores is prohibited by ADR 0007."
        )

    # 1c. Verification: real patent metadata was passed to the engine
    assert engine.received_patent_metadata[0] is not None, (
        "Runner must pass patent_metadata to the engine so it can compute CPC concordance "
        "from real benchmark data."
    )
    assert len(engine.received_patent_metadata[0]) == 5, (
        "patent_metadata must contain one PatentCandidateEvidence per patent in the dataset."
    )

    # 2. Verification of provenance and stamping
    assert report.dataset_sha256 == sample_validated_dataset.manifest.content_sha256
    assert report.policy_sha256 == sample_policy.policy_sha256
    assert report.context.engine_commit_hash == sample_context.engine_commit_hash
    assert report.context.engine_name == sample_context.engine_name

    # 3. Verification of demand metrics
    assert len(report.demand_reports) == 1
    d_rep = report.demand_reports[0]
    assert d_rep.candidate_count == 5
    assert d_rep.judged_count == 4
    assert d_rep.uncertain_count == 1

    # 4. Invariant: Engine ranking order is preserved!
    # Engine output: P-2 (UNCERTAIN), P-3 (GRADE_3), P-1 (GRADE_0), ...
    # Under strict, P-3 is at original system rank 2!
    # Therefore, strict MRR = 1/2 = 0.50!
    assert d_rep.strict_metrics.mrr == 0.50
    assert d_rep.strict_metrics.mrr_at_5 == 0.50


def test_runner_never_reads_filesystem(
    sample_validated_dataset, sample_policy, sample_context, monkeypatch
):
    """Proves that EvaluationRunner executes completely in-memory without touching disk."""
    import builtins

    def forbidden_open(*args, **kwargs):
        raise AssertionError("EvaluationRunner attempted to open a file from the filesystem!")

    monkeypatch.setattr(builtins, "open", forbidden_open)

    engine = FakeDeterministicMatchingEngine(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        engine=engine,
        policy=sample_policy,
        context=sample_context,
    )
    assert report.run_id.startswith("eval-run-")


def test_runner_does_not_mutate_dataset_or_policy(
    sample_validated_dataset, sample_policy, sample_context
):
    dataset_copy = sample_validated_dataset.model_dump()
    policy_copy = sample_policy.model_dump()

    engine = FakeDeterministicMatchingEngine(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=sample_validated_dataset,
        engine=engine,
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

    engine = FakeDeterministicMatchingEngine(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        engine=engine,
        policy=sample_policy,
        context=sample_context,
    )
    assert report.context.engine_commit_hash == sample_context.engine_commit_hash


def test_runner_uses_closed_candidate_universe(
    sample_validated_dataset, sample_policy, sample_context
):
    """Verifies that the CandidatePool passed to engine.evaluate contains strictly the dataset patents."""
    engine = FakeDeterministicMatchingEngine(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=sample_validated_dataset,
        engine=engine,
        policy=sample_policy,
        context=sample_context,
    )

    received_pool = engine.received_pools[0]
    expected_ids = {p.publication_id for p in sample_validated_dataset.dataset.patents}
    actual_ids = {c.publication_id for c in received_pool.candidates}
    assert actual_ids == expected_ids
    assert len(received_pool.candidates) == len(sample_validated_dataset.dataset.patents)


def test_runner_produces_strict_and_broad_metrics(
    sample_validated_dataset, sample_policy, sample_context
):
    """Verifies that both strict and broad metrics are computed and distinct."""
    # Engine ranking: P-3 (GRADE_3), P-4 (GRADE_2), P-1 (GRADE_0), P-2 (UNCERTAIN), P-5 (GRADE_0)
    engine = FakeDeterministicMatchingEngine(fixed_order=["P-3", "P-4", "P-1", "P-2", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset,
        engine=engine,
        policy=sample_policy,
        context=sample_context,
    )

    d_rep = report.demand_reports[0]
    # Under Strict: only P-3 is relevant (1 total in universe)
    # Under Broad: P-3 and P-4 are relevant (2 total in universe)
    assert d_rep.strict_metrics.precision_at_1 == 1.0
    assert d_rep.strict_metrics.precision_at_3 == 1 / 3  # P-3, P-4, P-1 -> only P-3 strict relevant
    assert d_rep.broad_metrics.precision_at_3 == 2 / 3  # P-3, P-4, P-1 -> P-3 and P-4 broad relevant
    assert report.macro_strict.precision_at_1 == 1.0
    assert report.macro_broad.precision_at_1 == 1.0
