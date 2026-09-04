"""Behavioral tests for DefaultMatchingAdapter's M0 lexical derived ranking feature (ADR 0013).

Architectural invariants (closed-universe preservation, no annotation access) are covered by
test_adr_0007_invariants.py::DerivedRankingFeaturesTest. These tests cover the observable
scoring/ranking behavior the derived feature actually produces.
"""

from datetime import UTC, date, datetime

from application.evaluation.matching_adapter import DefaultMatchingAdapter
from domain.models.evaluation import (
    DataModality,
    EvaluationDemand,
    EvaluationPatent,
    EvaluationProvenance,
)
from domain.models.matching import (
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


def _policy() -> MatchingPolicyConfig:
    return MatchingPolicyConfig(
        policy_id="matching-adapter-test-policy",
        policy_version="1.0.0",
        description="Matching adapter test policy",
        weights=RankerWeights(alpha=0.35, beta=0.45, gamma=0.20),
        operational_limits=OperationalLimits(retrieval_limit=100, max_candidate_pool_size=300),
        cpc_concordance_levels=CPCConcordanceLevels(
            subgroup=1.0, main_group=0.8, subclass=0.5, section=0.2, none=0.0
        ),
        confidence_thresholds=ConfidenceThresholds(strong=0.75, moderate=0.50, weak=0.25),
        sufficiency_rules=SufficiencyRules(
            min_active_signals=1, min_signals_for_sufficient=2, require_temporal_validity=True
        ),
        concept_to_cpc_taxonomy={},
        policy_sha256="e" * 64,
    )


class _RecordingEngine:
    """Fake matching engine ranking candidates purely by their lexical retrieval_scores.

    This isolates the adapter's lexical scoring from DefaultEvidenceEvaluator/feature
    extraction, which is exercised separately by test_adr_0007_invariants.py.
    """

    def __init__(self) -> None:
        self.received_candidates = None

    def evaluate(self, demand, candidates, policy, patent_metadata=None):
        self.received_candidates = candidates
        from domain.models.matching import RetrievalMethod

        scored = [
            (c.publication_id, c.retrieval_scores.get(RetrievalMethod.LEXICAL, 0.0))
            for c in candidates.candidates
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            MatchAssessment(
                demand_id=demand.demand_id,
                publication_id=pub_id,
                # MatchAssessment.overall_score is bounded to [0, 1]; raw BM25 scores are
                # unbounded, so this fake clamps for assessment-model validity only — ranking
                # order (what these tests actually check) is unaffected by clamping either
                # value to the same ceiling.
                overall_score=min(score, 1.0),
                confidence=MatchConfidence.MODERATE,
                sufficiency=EvidenceSufficiency.SUFFICIENT,
                features=MatchFeatures(),
                rationale="fake",
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                policy_sha256=policy.policy_sha256,
            )
            for pub_id, score in scored
        ]


def _provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="f" * 64,
        modality=DataModality.OBSERVED,
    )


def _demand() -> EvaluationDemand:
    return EvaluationDemand(
        demand_id="D-TEST",
        title="biodegradable surfactant",
        description="seeking a biodegradable surfactant for low-temperature washing",
        posted_date=date(2023, 6, 1),
        target_cpc_prefixes=["C11D"],
        provenance=_provenance(),
    )


class MatchingAdapterTest:
    """M0 lexical (BM25) derived ranking feature, exercised through DefaultMatchingAdapter."""

    def test_should_preserve_all_candidates_when_ranking(self):
        prov = _provenance()
        patents = [
            EvaluationPatent(
                publication_id=f"EP-{i}",
                publication_date=date(2022, 3, 15),
                classifications_cpc=["C11D1/00"],
                title=f"Patent {i}",
                abstract="Text with no relation to the query terms at all.",
                provenance=prov,
            )
            for i in range(5)
        ]

        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy())

        ranked = adapter.rank_candidates(_demand(), patents)

        assert set(ranked) == {p.publication_id for p in patents}
        assert len(ranked) == len(patents)

    def test_should_rank_candidates_by_lexical_score(self):
        prov = _provenance()
        patents = [
            EvaluationPatent(
                publication_id="EP-RELEVANT",
                publication_date=date(2022, 3, 15),
                classifications_cpc=["C11D1/00"],
                title="Biodegradable surfactant composition",
                abstract="A biodegradable surfactant formulated for low-temperature washing.",
                provenance=prov,
            ),
            EvaluationPatent(
                publication_id="EP-UNRELATED",
                publication_date=date(2021, 7, 20),
                classifications_cpc=["F16K1/00"],
                title="Metallurgical alloy",
                abstract="A high-strength steel alloy for industrial fasteners.",
                provenance=prov,
            ),
        ]

        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy())

        ranked = adapter.rank_candidates(_demand(), patents)

        assert ranked[0] == "EP-RELEVANT", (
            "The patent whose observed text overlaps the demand's query terms must rank first."
        )

    def test_should_keep_zero_score_candidates(self):
        prov = _provenance()
        patents = [
            EvaluationPatent(
                publication_id="EP-ZERO",
                publication_date=date(2022, 3, 15),
                classifications_cpc=["C11D1/00"],
                title="Metallurgical alloy",
                abstract="A high-strength steel alloy sharing no terms with the query.",
                provenance=prov,
            ),
        ]

        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy())

        adapter.rank_candidates(_demand(), patents)

        assert engine.received_candidates is not None
        candidate = engine.received_candidates.candidates[0]
        from domain.models.matching import RetrievalMethod

        assert candidate.retrieval_scores[RetrievalMethod.LEXICAL] == 0.0, (
            "A candidate with no term overlap must be scored 0.0, not dropped from the pool."
        )
