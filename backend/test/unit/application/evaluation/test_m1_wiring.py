"""Wiring tests for M1 frozen-embedding artifact into the evaluation adapter (PR #42).

Scope (authorized — wiring only, zero methodology change):
- The caller-supplied FrozenEmbeddingArtifact is read (never generated, never edited).
- Raw cosine in [-1, 1] reaches Candidate.retrieval_scores[SEMANTIC], per patent,
  over the full closed pool; missing keys fail fast; M0-only mode is unchanged.
- The real sealed artifact binds to the real sealed dataset (ids + SHA).

Explicitly out of scope (PR #43 and later, never this PR):
- Any claim that M1 improves ranking (no M0-vs-M1 comparison anywhere below).
- Dataset/benchmark corrections, weight tuning, metric definitions, pilot results.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from application.evaluation.matching_adapter import DefaultMatchingAdapter
from application.matching.engine import DefaultMatchingEngine
from domain.models.evaluation import (
    DataModality,
    EvaluationDemand,
    EvaluationPatent,
    EvaluationProvenance,
    FrozenEmbeddingArtifact,
)
from domain.models.matching import (
    FUSION_TRANSFORM_ID,
    ConfidenceThresholds,
    CPCConcordanceLevels,
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
    OperationalLimits,
    RankerWeights,
    RetrievalMethod,
    SufficiencyRules,
)

_REPO_ROOT = Path(__file__).resolve().parents[5]
REAL_ARTIFACT_PATH = _REPO_ROOT / "data" / "evaluation" / "embeddings_pilot_benchmark.json"
REAL_DATASET_PATH = _REPO_ROOT / "data" / "evaluation" / "dataset_pilot_benchmark.json"
REAL_MANIFEST_PATH = _REPO_ROOT / "data" / "evaluation" / "dataset_pilot_benchmark.manifest.json"

# L2-normalized by construction (norm == 1.0 exactly).
_VEC_X = [1.0, 0.0, 0.0, 0.0]
_VEC_Y = [0.0, 1.0, 0.0, 0.0]
_VEC_NEG_X = [-1.0, 0.0, 0.0, 0.0]
_VEC_HALF = [0.6, 0.8, 0.0, 0.0]  # cos(X, HALF) == 0.6 exactly


def _make_artifact(
    demands: dict[str, list[float]] | None = None,
    patents: dict[str, list[float]] | None = None,
) -> FrozenEmbeddingArtifact:
    return FrozenEmbeddingArtifact(
        artifact_id="test-m1-artifact",
        frozen_at=date(2026, 9, 4),
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_revision="a" * 40,
        license="Apache-2.0",
        generation_script_path="scripts/generate_m1_embeddings.py",
        generation_script_commit="b" * 40,
        library_versions={"sentence-transformers": "3.4.1"},
        generation_device="cpu",
        dataset_sha256="c" * 64,
        embedding_dimension=4,
        normalization="l2",
        similarity_metric="cosine",
        demand_embeddings=demands if demands is not None else {"D1": _VEC_X},
        patent_embeddings=(
            patents
            if patents is not None
            else {
                "P-SAME": _VEC_X,
                "P-ORTH": _VEC_Y,
                "P-OPP": _VEC_NEG_X,
                "P-HALF": _VEC_HALF,
            }
        ),
        artifact_sha256="d" * 64,
    )


def _provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="f" * 64,
        modality=DataModality.OBSERVED,
    )


def _policy() -> MatchingPolicyConfig:
    return MatchingPolicyConfig(
        policy_id="m1-wiring-test-policy",
        policy_version="1.0.0",
        description="M1 wiring test policy",
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


def _demand(demand_id: str = "D1") -> EvaluationDemand:
    # Deliberately no term overlap with any patent text below and a CPC prefix no
    # patent carries, so lexical and CPC signals stay 0.0 and semantic is isolated.
    return EvaluationDemand(
        demand_id=demand_id,
        title="Kryptonite containment vessel",
        description="Seeking a kryptonite containment vessel for interstellar logistics.",
        posted_date=date(2023, 6, 1),
        target_cpc_prefixes=["C99Z"],
        provenance=_provenance(),
    )


def _patent(publication_id: str, title: str = "Ceramic teapot", abstract: str = "A ceramic teapot.") -> EvaluationPatent:
    return EvaluationPatent(
        publication_id=publication_id,
        publication_date=date(2022, 3, 15),
        classifications_cpc=["F16K1/00"],
        title=title,
        abstract=abstract,
        provenance=_provenance(),
    )


class _RecordingEngine:
    """Captures candidates and returns them unscored in pool order."""

    def __init__(self) -> None:
        self.received_candidates = None

    def evaluate(self, demand, candidates, policy, patent_metadata=None):
        self.received_candidates = candidates
        return [
            MatchAssessment(
                demand_id=demand.demand_id,
                publication_id=c.publication_id,
                overall_score=0.5,
                confidence=MatchConfidence.MODERATE,
                sufficiency=EvidenceSufficiency.SUFFICIENT,
                features=MatchFeatures(),
                rationale="fake",
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                policy_sha256=policy.policy_sha256,
                fusion_transform_id="fake-no-transform",
            )
            for c in candidates.candidates
        ]


class M1WiringTest:
    def test_should_store_raw_cosine_per_candidate_when_artifact_supplied(self) -> None:
        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=_make_artifact(),
        )
        patents = [_patent("P-SAME"), _patent("P-ORTH"), _patent("P-OPP"), _patent("P-HALF")]
        adapter.rank_candidates(_demand(), patents)

        by_id = {c.publication_id: c for c in engine.received_candidates.candidates}
        assert by_id["P-SAME"].retrieval_scores[RetrievalMethod.SEMANTIC] == pytest.approx(1.0)
        assert by_id["P-ORTH"].retrieval_scores[RetrievalMethod.SEMANTIC] == pytest.approx(0.0)
        assert by_id["P-OPP"].retrieval_scores[RetrievalMethod.SEMANTIC] == pytest.approx(-1.0)
        assert by_id["P-HALF"].retrieval_scores[RetrievalMethod.SEMANTIC] == pytest.approx(0.6)

    def test_should_store_raw_not_remapped_cosine(self) -> None:
        # The (cos + 1) / 2 remap is the evaluator's fusion-time decision (ADR 0016),
        # never the adapter's: orthogonality must arrive as 0.0, opposition as -1.0.
        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=_make_artifact(),
        )
        adapter.rank_candidates(_demand(), [_patent("P-ORTH"), _patent("P-OPP")])
        by_id = {c.publication_id: c for c in engine.received_candidates.candidates}
        assert by_id["P-ORTH"].retrieval_scores[RetrievalMethod.SEMANTIC] != pytest.approx(0.5)
        assert by_id["P-OPP"].retrieval_scores[RetrievalMethod.SEMANTIC] != pytest.approx(0.0)

    def test_should_fail_fast_when_demand_vector_missing(self) -> None:
        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=_make_artifact(),
        )
        with pytest.raises(ValueError, match="no demand vector"):
            adapter.rank_candidates(_demand("D-STALE"), [_patent("P-SAME")])

    def test_should_fail_fast_when_patent_vector_missing(self) -> None:
        engine = _RecordingEngine()
        artifact = _make_artifact(patents={"P-SAME": _VEC_X})
        adapter = DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=artifact,
        )
        with pytest.raises(ValueError, match="no patent vector"):
            adapter.rank_candidates(_demand(), [_patent("P-SAME"), _patent("P-STALE")])

    def test_should_preserve_closed_universe_with_artifact(self) -> None:
        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=_make_artifact(),
        )
        patents = [_patent("P-SAME"), _patent("P-ORTH"), _patent("P-OPP"), _patent("P-HALF")]
        ranked = adapter.rank_candidates(_demand(), patents)
        assert set(ranked) == {"P-SAME", "P-ORTH", "P-OPP", "P-HALF"}

    def test_should_leave_semantic_absent_without_artifact(self) -> None:
        # M0-only regression: no artifact → no SEMANTIC key, lexical untouched.
        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75)
        adapter.rank_candidates(_demand(), [_patent("P-SAME")])
        candidate = engine.received_candidates.candidates[0]
        assert RetrievalMethod.SEMANTIC not in candidate.retrieval_scores
        assert RetrievalMethod.LEXICAL in candidate.retrieval_scores

    def test_should_rank_deterministically_with_artifact(self) -> None:
        engine = _RecordingEngine()
        adapter = DefaultMatchingAdapter(
            engine=engine, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=_make_artifact(),
        )
        patents = [_patent("P-SAME"), _patent("P-ORTH"), _patent("P-OPP"), _patent("P-HALF")]
        assert adapter.rank_candidates(_demand(), patents) == adapter.rank_candidates(_demand(), patents)

    def test_should_fuse_wired_semantic_through_real_engine(self) -> None:
        # End-to-end raw discipline with lexical and CPC at zero:
        # P-SAME (raw cos 1.0 → f_sem 1.0 → overall = beta) ranks above P-OPP
        # (raw cos -1.0, zero active signals → INSUFFICIENT, overall 0.0).
        # Raw features stay raw inside the assessment; the transform id is stamped.
        class _AssessmentSpy(DefaultMatchingEngine):
            def __init__(self) -> None:
                super().__init__()
                self.last: list[MatchAssessment] | None = None

            def evaluate(self, demand, candidates, policy, patent_metadata=None):
                self.last = super().evaluate(demand, candidates, policy, patent_metadata)
                return self.last

        spy = _AssessmentSpy()
        adapter = DefaultMatchingAdapter(
            engine=spy, policy=_policy(), bm25_k1=1.5, bm25_b=0.75,
            semantic_artifact=_make_artifact(),
        )
        ranked = adapter.rank_candidates(_demand(), [_patent("P-SAME"), _patent("P-OPP")])
        assert ranked[0] == "P-SAME"
        assert spy.last is not None
        by_id = {a.publication_id: a for a in spy.last}

        same = by_id["P-SAME"]
        assert same.features.semantic_score == pytest.approx(1.0)
        assert same.features.lexical_score == pytest.approx(0.0)
        assert same.features.cpc_concordance == pytest.approx(0.0)
        assert same.overall_score == pytest.approx(0.45)
        assert same.sufficiency == EvidenceSufficiency.PARTIAL
        assert same.fusion_transform_id == FUSION_TRANSFORM_ID

        opp = by_id["P-OPP"]
        assert opp.features.semantic_score == pytest.approx(-1.0)
        assert opp.sufficiency == EvidenceSufficiency.INSUFFICIENT_EVIDENCE
        assert opp.overall_score == 0.0


class M1RealArtifactBindingTest:
    """The sealed artifact binds to the sealed dataset: ids, dimension, model, SHAs."""

    def test_should_bind_real_artifact_to_real_dataset(self) -> None:
        artifact = FrozenEmbeddingArtifact.load_from_json(REAL_ARTIFACT_PATH)
        assert artifact.model_name == "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        assert artifact.model_revision == "4328cf26390c98c5e3c738b4460a05b95f4911f5"
        assert artifact.embedding_dimension == 768
        assert artifact.generation_device == "cpu"

        dataset = json.loads(REAL_DATASET_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(REAL_MANIFEST_PATH.read_text(encoding="utf-8"))
        demand_ids = {d["demand_id"] for d in dataset["demands"]}
        patent_ids = {p["publication_id"] for p in dataset["patents"]}

        assert set(artifact.demand_embeddings) == demand_ids
        assert set(artifact.patent_embeddings) == patent_ids
        assert len(artifact.patent_embeddings) == 15
        assert artifact.dataset_sha256 == manifest["content_sha256"]

    def test_should_reject_tampered_dimension_before_scoring(self, tmp_path: Path) -> None:
        import hashlib

        payload = json.loads(REAL_ARTIFACT_PATH.read_text(encoding="utf-8"))
        payload["embedding_dimension"] = 512
        # Re-seal the hash so the failure under test is the dimension guard,
        # not the integrity check.
        payload.pop("artifact_sha256")
        canonical = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
        payload["artifact_sha256"] = hashlib.sha256(canonical).hexdigest()
        tampered = tmp_path / "tampered_dim.json"
        tampered.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValidationError, match="dimension"):
            FrozenEmbeddingArtifact.load_from_json(tampered)
