"""Boundary and invariant tests for the ADR 0016 fusion transform (PR-B).

Scope (authorized):
- f_lex / f_sem unit properties (boundaries, monotonicity, exact anchor values).
- DefaultEvidenceEvaluator fusion: structural overall_score in [0, 1] for extreme
  raw inputs, raw features preserved, active_signals read from raw values.
- Model bounds: semantic raw in [-1, 1]; Candidate negatives only for SEMANTIC.
- Per-result provenance: fusion_transform_id stamped on every MatchAssessment.
- ADR 0012 regression: manifest still NOT_TUNED, weights untouched, transform
  provenance present on M3-M6 and absent (None) on M0-M2.

Explicitly out of scope (not in this PR):
- M1 embeddings, sealed benchmark datasets, pilot results, weight tuning,
  metric definitions, ADK agents, product stores. All inputs below are
  synthetic unit fixtures, never EvaluationDataset content.
"""

import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from application.matching.evaluator import (
    DefaultEvidenceEvaluator,
    fuse_lexical_score,
    fuse_semantic_score,
)
from domain.models.evaluation import ModelConfigurationManifest
from domain.models.matching import (
    FUSION_LEX_K,
    FUSION_TRANSFORM_ID,
    Candidate,
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
    RetrievalMethod,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MATCHING_POLICY_PATH = _REPO_ROOT / "config" / "policies" / "matching" / "default_matching_policy.json"
MANIFEST_PATH = _REPO_ROOT / "config" / "evaluations" / "model_configurations_m0_m6.json"

_SHA64 = "a" * 64


def _evaluator() -> DefaultEvidenceEvaluator:
    return DefaultEvidenceEvaluator()


def _policy() -> MatchingPolicyConfig:
    return MatchingPolicyConfig.load_from_json(DEFAULT_MATCHING_POLICY_PATH)


def _features(
    lex: float = 0.0,
    sem: float = 0.0,
    cpc: float = 0.0,
) -> MatchFeatures:
    return MatchFeatures(
        lexical_score=lex,
        semantic_score=sem,
        cpc_concordance=cpc,
        temporal_valid=True,
        delta_days=100,
    )


class FusionTransformUnitTest:
    def test_should_map_zero_lexical_to_zero(self) -> None:
        # "No shared terms" must stay zero signal, never a manufactured 0.5.
        assert fuse_lexical_score(0.0) == 0.0

    def test_should_map_unit_lexical_to_half(self) -> None:
        assert fuse_lexical_score(FUSION_LEX_K) == pytest.approx(0.5)

    def test_should_be_strictly_increasing_in_lexical(self) -> None:
        inputs = [0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0, 1e6]
        outputs = [fuse_lexical_score(x) for x in inputs]
        assert all(b > a for a, b in zip(outputs, outputs[1:], strict=False))
        assert all(0.0 <= y < 1.0 for y in outputs)

    def test_should_saturate_without_clamping_in_lexical_tail(self) -> None:
        # Compression, not clamping: distinct large inputs stay distinct.
        assert fuse_lexical_score(10.0) == pytest.approx(10.0 / 11.0)
        assert fuse_lexical_score(100.0) == pytest.approx(100.0 / 101.0)
        assert fuse_lexical_score(100.0) > fuse_lexical_score(10.0)

    def test_should_remap_semantic_anchors_exactly(self) -> None:
        assert fuse_semantic_score(-1.0) == pytest.approx(0.0)
        assert fuse_semantic_score(0.0) == pytest.approx(0.5)
        assert fuse_semantic_score(1.0) == pytest.approx(1.0)

    def test_should_be_strictly_increasing_in_semantic(self) -> None:
        inputs = [-1.0, -0.5, -0.1, 0.0, 0.3, 0.7, 1.0]
        outputs = [fuse_semantic_score(x) for x in inputs]
        assert all(b > a for a, b in zip(outputs, outputs[1:], strict=False))
        assert all(0.0 <= y <= 1.0 for y in outputs)


class FusionEvaluatorBoundednessTest:
    def test_should_keep_overall_within_unit_interval_for_extreme_raw_inputs(self) -> None:
        policy = _policy()
        cases = [
            _features(lex=0.0, sem=-1.0, cpc=0.0),
            _features(lex=0.0, sem=0.0, cpc=0.0),
            _features(lex=0.0, sem=1.0, cpc=0.0),
            _features(lex=100.0, sem=1.0, cpc=1.0),
            _features(lex=1e6, sem=1.0, cpc=1.0),
            _features(lex=100.0, sem=-1.0, cpc=1.0),
            _features(lex=0.0, sem=-1.0, cpc=1.0),
        ]
        for features in cases:
            assessment = _evaluator().evaluate_candidate("D", "P", features, policy)
            assert 0.0 <= assessment.overall_score <= 1.0

    def test_should_reproduce_adr0015_overflow_case_within_bounds(self) -> None:
        # The exact raw inputs that overflowed overall_score to 1.119308 under the
        # pre-ADR-0016 raw weighted sum (demand INNOGET-2292 / ES-2634129-B1).
        policy = _policy()
        assert (policy.weights.alpha, policy.weights.beta, policy.weights.gamma) == (0.35, 0.45, 0.20)
        assessment = _evaluator().evaluate_candidate(
            "D", "P", _features(lex=1.970066, sem=0.732856, cpc=0.5), policy
        )
        expected = round(
            0.35 * (1.970066 / 2.970066) + 0.45 * ((0.732856 + 1.0) / 2.0) + 0.20 * 0.5,
            6,
        )
        assert assessment.overall_score == pytest.approx(expected)
        assert assessment.overall_score <= 1.0

    def test_should_keep_raw_features_intact_after_evaluation(self) -> None:
        policy = _policy()
        features = _features(lex=2.5, sem=-0.4, cpc=0.75)
        assessment = _evaluator().evaluate_candidate("D", "P", features, policy)
        assert assessment.features.lexical_score == 2.5
        assert assessment.features.semantic_score == -0.4
        assert assessment.features.cpc_concordance == 0.75

    def test_should_count_active_signals_from_raw_values_not_fused_views(self) -> None:
        # sem_raw = 0.0 fuses to 0.5 but must NOT count as an active signal.
        policy = _policy()
        orthogonal = _evaluator().evaluate_candidate("D", "P", _features(lex=0.0, sem=0.0, cpc=0.5), policy)
        assert orthogonal.sufficiency == EvidenceSufficiency.PARTIAL
        negative = _evaluator().evaluate_candidate("D", "P", _features(lex=0.0, sem=-0.6, cpc=0.5), policy)
        assert negative.sufficiency == EvidenceSufficiency.PARTIAL

    def test_should_treat_single_raw_signal_as_partial_under_default_policy(self) -> None:
        policy = _policy()
        assessment = _evaluator().evaluate_candidate("D", "P", _features(lex=3.0, sem=0.0, cpc=0.0), policy)
        assert assessment.sufficiency == EvidenceSufficiency.PARTIAL
        assert assessment.overall_score == pytest.approx(round(0.35 * (3.0 / 4.0) + 0.45 * 0.5, 6))

    def test_should_be_monotone_in_each_raw_signal(self) -> None:
        policy = _policy()

        def base(lex: float, sem: float, cpc: float) -> float:
            return _evaluator().evaluate_candidate(
                "D", "P", _features(lex=lex, sem=sem, cpc=cpc), policy
            ).overall_score

        lex_scores = [base(x, 0.2, 0.5) for x in (0.0, 0.5, 2.0, 20.0)]
        assert all(b > a for a, b in zip(lex_scores, lex_scores[1:], strict=False))
        sem_scores = [base(1.0, x, 0.5) for x in (-1.0, -0.2, 0.4, 1.0)]
        assert all(b > a for a, b in zip(sem_scores, sem_scores[1:], strict=False))

    def test_should_hold_unit_interval_under_extreme_weight_configurations(self) -> None:
        policy = _policy()
        for weights in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
            extreme = policy.model_copy(deep=True)
            extreme.weights.alpha, extreme.weights.beta, extreme.weights.gamma = weights
            for features in (
                _features(lex=50.0, sem=1.0, cpc=1.0),
                _features(lex=50.0, sem=-1.0, cpc=0.0),
            ):
                assessment = _evaluator().evaluate_candidate("D", "P", features, extreme)
                assert 0.0 <= assessment.overall_score <= 1.0

    def test_should_stamp_fusion_transform_provenance_on_every_assessment(self) -> None:
        policy = _policy()
        assessment = _evaluator().evaluate_candidate("D", "P", _features(lex=1.0, sem=0.5, cpc=0.5), policy)
        assert assessment.fusion_transform_id == FUSION_TRANSFORM_ID
        assert assessment.policy_sha256 == policy.policy_sha256
        assert assessment.policy_version == policy.policy_version
        assert FUSION_TRANSFORM_ID in assessment.rationale


class FusionModelBoundsTest:
    def test_should_accept_negative_semantic_scores_in_match_features(self) -> None:
        features = MatchFeatures(semantic_score=-1.0)
        assert features.semantic_score == -1.0

    def test_should_reject_out_of_domain_semantic_scores(self) -> None:
        with pytest.raises(ValidationError):
            MatchFeatures(semantic_score=1.5)
        with pytest.raises(ValidationError):
            MatchFeatures(semantic_score=-1.5)

    def test_should_accept_negative_semantic_retrieval_scores_only(self) -> None:
        candidate = Candidate(
            publication_id="ES-1-B2",
            retrieval_scores={RetrievalMethod.SEMANTIC: -0.3},
        )
        assert candidate.retrieval_scores[RetrievalMethod.SEMANTIC] == -0.3
        with pytest.raises(ValidationError):
            Candidate(
                publication_id="ES-2-B2",
                retrieval_scores={RetrievalMethod.LEXICAL: -0.3},
            )
        with pytest.raises(ValidationError):
            Candidate(
                publication_id="ES-3-B2",
                retrieval_scores={RetrievalMethod.CPC: -0.3},
            )

    def test_should_reject_assessment_without_explicit_fusion_provenance(self) -> None:
        # Provenance is mandatory, never inferred: omitting fusion_transform_id
        # must fail loudly instead of silently inheriting an identity the object
        # did not earn through the evaluator.
        with pytest.raises(ValidationError):
            MatchAssessment(
                demand_id="D",
                publication_id="P",
                overall_score=0.5,
                confidence=MatchConfidence.MODERATE,
                sufficiency=EvidenceSufficiency.PARTIAL,
                features=MatchFeatures(),
                rationale="direct",
                policy_id="pid",
                policy_version="1.0.0",
                policy_sha256=_SHA64,
            )


class FusionManifestProvenanceTest:
    """ADR 0012 regression: the transform entry changes provenance records only —
    tuning status, weights, model set, and source-policy binding are untouched."""

    def test_should_declare_fusion_transform_on_fused_models_only(self) -> None:
        manifest = ModelConfigurationManifest.load_from_json(MANIFEST_PATH)
        by_id = {r.model_id: r for r in manifest.models}
        for model_id in ("M3", "M4", "M5", "M6"):
            transform = by_id[model_id].fusion_transform
            assert transform is not None
            assert transform.transform_id == FUSION_TRANSFORM_ID
            assert transform.f_lex_k == pytest.approx(FUSION_LEX_K)
            assert transform.adr == "ADR 0016"
        for model_id in ("M0", "M1", "M2"):
            assert by_id[model_id].fusion_transform is None

    def test_should_keep_tuning_status_weights_and_model_set_frozen(self) -> None:
        manifest = ModelConfigurationManifest.load_from_json(MANIFEST_PATH)
        assert manifest.tuning_status == "NOT_TUNED_NO_INDEPENDENT_DEV_SET"
        assert {r.model_id for r in manifest.models} == {"M0", "M1", "M2", "M3", "M4", "M5", "M6"}
        m6 = next(r for r in manifest.models if r.model_id == "M6")
        policy = _policy()
        assert m6.weights == {
            "alpha": policy.weights.alpha,
            "beta": policy.weights.beta,
            "gamma": policy.weights.gamma,
        }
        manifest.verify_source_policy(policy)

    def test_should_reject_undeclared_transform_parameters(self) -> None:
        from domain.models.evaluation import FusionTransformRecord

        with pytest.raises(ValidationError):
            FusionTransformRecord(
                transform_id="x",
                f_lex="x/(x+k)",
                f_lex_k=0.0,
                f_sem="(x+1)/2",
                applied_at="fusion",
                adr="ADR 0016",
            )


class FusionDeterminismTest:
    def test_should_produce_bit_exact_repeat_assessments(self) -> None:
        policy = _policy()
        features = _features(lex=1.970066, sem=0.732856, cpc=0.5)
        first = _evaluator().evaluate_candidate("D", "P", features, policy)
        second = _evaluator().evaluate_candidate("D", "P", features, policy)
        assert first == second
        assert math.isfinite(first.overall_score)
