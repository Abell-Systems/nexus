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
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75)

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
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75)

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
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75)

        adapter.rank_candidates(_demand(), patents)

        assert engine.received_candidates is not None
        candidate = engine.received_candidates.candidates[0]
        from domain.models.matching import RetrievalMethod

        assert candidate.retrieval_scores[RetrievalMethod.LEXICAL] == 0.0, (
            "A candidate with no term overlap must be scored 0.0, not dropped from the pool."
        )

    def test_should_use_injected_bm25_parameters_when_they_differ_from_library_defaults(self):
        """Proves the constructor's bm25_k1/bm25_b actually reach the scoring computation.

        Two adapters differing only in constructor k1/b must produce different scores for the
        same input — this is what makes the frozen manifest (ADR 0012) the real authority over
        execution rather than decorative documentation next to an implementation default. If a
        future change made the adapter silently ignore these constructor arguments and fall
        back to compute_bm25_scores' own defaults, this test would fail even though every other
        test in this file (which happens to pass the same values as the library defaults) would
        keep passing.
        """
        prov = _provenance()
        patents = [
            EvaluationPatent(
                publication_id="EP-1",
                publication_date=date(2022, 3, 15),
                classifications_cpc=["C11D1/00"],
                title="Biodegradable surfactant composition",
                abstract="A biodegradable surfactant formulated for low-temperature washing.",
                provenance=prov,
            ),
        ]

        engine_default = _RecordingEngine()
        DefaultMatchingAdapter(
            engine=engine_default, policy=_policy(), bm25_k1=1.5, bm25_b=0.75
        ).rank_candidates(_demand(), patents)

        engine_other = _RecordingEngine()
        DefaultMatchingAdapter(
            engine=engine_other, policy=_policy(), bm25_k1=2.5, bm25_b=0.25
        ).rank_candidates(_demand(), patents)

        from domain.models.matching import RetrievalMethod

        score_default = engine_default.received_candidates.candidates[0].retrieval_scores[
            RetrievalMethod.LEXICAL
        ]
        score_other = engine_other.received_candidates.candidates[0].retrieval_scores[
            RetrievalMethod.LEXICAL
        ]
        assert score_default != score_other, (
            "Different constructor k1/b must produce different scores — otherwise the "
            "adapter is not actually using the injected parameters."
        )

    def test_should_match_frozen_manifest_declared_parameters_when_scoring(self):
        """End-to-end: loads the real frozen manifest (ADR 0012), extracts M0's declared k1/b,
        and confirms the adapter constructed with them produces exactly what an independent
        direct call to compute_bm25_scores with those same declared values produces. This is
        the actual chain the review required: manifest -> declared configuration -> execution.
        """
        from pathlib import Path

        from domain.models.evaluation import ModelConfigurationManifest
        from domain.models.matching import RetrievalMethod, compute_bm25_scores

        manifest_path = (
            Path(__file__).resolve().parents[5] / "config" / "evaluations" / "model_configurations_m0_m6.json"
        )
        manifest = ModelConfigurationManifest.load_from_json(manifest_path)
        m0 = next(m for m in manifest.models if m.model_id == "M0")
        assert m0.weights is not None, "M0 must declare BM25 parameters in the frozen manifest"

        prov = _provenance()
        patent = EvaluationPatent(
            publication_id="EP-1",
            publication_date=date(2022, 3, 15),
            classifications_cpc=["C11D1/00"],
            title="Biodegradable surfactant composition",
            abstract="A biodegradable surfactant formulated for low-temperature washing.",
            provenance=prov,
        )
        demand = _demand()

        engine = _RecordingEngine()
        DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=m0.weights["k1"], bm25_b=m0.weights["b"]
        ).rank_candidates(demand, [patent])

        expected = compute_bm25_scores(
            f"{demand.title} {demand.description}",
            {patent.publication_id: f"{patent.title} {patent.abstract}"},
            k1=m0.weights["k1"],
            b=m0.weights["b"],
        )[patent.publication_id]

        actual = engine.received_candidates.candidates[0].retrieval_scores[RetrievalMethod.LEXICAL]
        assert actual == expected
