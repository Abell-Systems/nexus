from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.matching import EvidenceSufficiency, MatchAssessment, MatchConfidence, MatchFeatures
from domain.models.runtime_schemas import AdversarialVerdict, InventionCandidate, PatentCluster, ScoreCard
from domain.models.scientific_results import (
    DISCOVERY_DISCLAIMER,
    ChallengeStatus,
    CitationResolution,
    DiscoveryCandidateRecord,
    DiscoveryLandscapeRecord,
    DiscoveryVerificationRecord,
    EvidenceCitation,
    ScientificResultsDocument,
    ScientificResultsExecution,
    TechnologyClusterObservation,
    Track,
    VerificationMatchRecord,
    executions_are_aggregable,
)


def _execution(**overrides) -> ScientificResultsExecution:
    defaults = {
        "execution_id": "exec-0001",
        "track": Track.DISCOVERY,
        "domain": "solid_state_battery",
        "query": "improve dendrite suppression",
        "created_at": datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return ScientificResultsExecution(**defaults)


def _candidate(**overrides) -> InventionCandidate:
    defaults = {
        "candidate_id": "cand-0001",
        "cluster_id": "H01M",
        "title": "Composite electrolyte membrane",
        "description": "A layered membrane design reducing dendrite propagation.",
    }
    defaults.update(overrides)
    return InventionCandidate(**defaults)


def _verdict(**overrides) -> AdversarialVerdict:
    defaults = {
        "candidate_id": "cand-0001",
        "verdict": "survives",
        "rationale": "No directly anticipating prior art found in the cited set.",
        "cited_patents": ["EXAMPLE-PATENT-0001"],
    }
    defaults.update(overrides)
    return AdversarialVerdict(**defaults)


def _cluster_observation(**overrides) -> TechnologyClusterObservation:
    defaults = {
        "cluster": PatentCluster(
            cluster_id="H01M",
            label="Solid State Battery - H01M",
            representative_patents=["US-11223001-B2"],
            patent_count=1,
            white_space_score=0.42,
            is_white_space=False,
        ),
        "density": 0.1,
        "recency": 0.6,
        "citation_traction": 0.3,
        "citation_coverage": 1.0,
        "demand_intensity": 0.5,
        "quadrant": "Quadrant II (Co-developed / Saturated)",
        "mean_age_years": 4.0,
    }
    defaults.update(overrides)
    return TechnologyClusterObservation(**defaults)


def _match_assessment(**overrides) -> MatchAssessment:
    defaults = {
        "demand_id": "INNOGET-0001",
        "publication_id": "EXAMPLE-PATENT-0001",
        "overall_score": 0.72,
        "confidence": MatchConfidence.MODERATE,
        "sufficiency": EvidenceSufficiency.SUFFICIENT,
        "features": MatchFeatures(lexical_score=0.5, semantic_score=0.6, cpc_concordance=0.8),
        "rationale": "Shared CPC classification and overlapping technical terms.",
        "policy_id": "default-matching-policy",
        "policy_version": "1.0.0",
        "policy_sha256": "a" * 64,
        "fusion_transform_id": "adr0016-fusion-v1",
    }
    defaults.update(overrides)
    return MatchAssessment(**defaults)


class ScientificResultsExecutionTest:
    def test_should_construct_when_required_fields_present(self) -> None:
        execution = _execution()
        assert execution.execution_id == "exec-0001"
        assert execution.track == Track.DISCOVERY
        assert execution.dataset_id is None

    def test_should_reject_execution_when_execution_id_missing(self) -> None:
        with pytest.raises(ValidationError):
            ScientificResultsExecution(
                track=Track.DISCOVERY,
                domain="solid_state_battery",
                query="q",
                created_at=datetime(2026, 9, 9, tzinfo=UTC),
            )

    def test_should_reject_execution_when_track_is_not_discovery_or_verification(self) -> None:
        with pytest.raises(ValidationError):
            _execution(track="synthesis")

    def test_should_reject_execution_when_created_at_is_naive(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            _execution(created_at=datetime(2026, 9, 9, 12, 0))

    def test_should_reject_execution_when_policy_sha256_is_malformed(self) -> None:
        with pytest.raises(ValidationError, match="Invalid SHA-256"):
            _execution(policy_sha256="not-a-real-sha")

    def test_should_accept_execution_when_policy_sha256_is_valid(self) -> None:
        execution = _execution(policy_sha256="a" * 64)
        assert execution.policy_sha256 == "a" * 64


class ScientificResultsAggregationTest:
    def test_should_allow_aggregation_when_track_dataset_and_policy_version_match(self) -> None:
        a = _execution(execution_id="e1", track=Track.VERIFICATION, dataset_id="ds-1", policy_version="1.0.0")
        b = _execution(execution_id="e2", track=Track.VERIFICATION, dataset_id="ds-1", policy_version="1.0.0")
        assert executions_are_aggregable(a, b) is True

    def test_should_reject_aggregation_when_tracks_differ(self) -> None:
        a = _execution(execution_id="e1", track=Track.DISCOVERY, dataset_id="ds-1", policy_version="1.0.0")
        b = _execution(execution_id="e2", track=Track.VERIFICATION, dataset_id="ds-1", policy_version="1.0.0")
        assert executions_are_aggregable(a, b) is False

    def test_should_reject_aggregation_when_dataset_ids_differ(self) -> None:
        a = _execution(execution_id="e1", track=Track.VERIFICATION, dataset_id="ds-1", policy_version="1.0.0")
        b = _execution(execution_id="e2", track=Track.VERIFICATION, dataset_id="ds-2", policy_version="1.0.0")
        assert executions_are_aggregable(a, b) is False

    def test_should_reject_aggregation_when_policy_versions_differ(self) -> None:
        a = _execution(execution_id="e1", track=Track.VERIFICATION, dataset_id="ds-1", policy_version="1.0.0")
        b = _execution(execution_id="e2", track=Track.VERIFICATION, dataset_id="ds-1", policy_version="2.0.0")
        assert executions_are_aggregable(a, b) is False

    def test_should_reject_aggregation_when_dataset_id_missing_on_either_side(self) -> None:
        a = _execution(execution_id="e1", track=Track.DISCOVERY, dataset_id=None, policy_version="1.0.0")
        b = _execution(execution_id="e2", track=Track.DISCOVERY, dataset_id=None, policy_version="1.0.0")
        # Two executions both missing dataset_id must NOT be treated as a wildcard match.
        assert executions_are_aggregable(a, b) is False


class EvidenceCitationTest:
    def test_should_construct_when_resolved_citation_carries_metadata(self) -> None:
        citation = EvidenceCitation(
            publication_id="EXAMPLE-PATENT-0001",
            role="challenges",
            resolution=CitationResolution.RESOLVED,
            title="Example patent title",
            publication_date="2020-01-01",
        )
        assert citation.resolution == CitationResolution.RESOLVED

    def test_should_construct_when_unresolved_citation_carries_no_metadata(self) -> None:
        citation = EvidenceCitation(
            publication_id="EXAMPLE-PATENT-0002",
            role="challenges",
            resolution=CitationResolution.UNRESOLVED,
        )
        assert citation.title is None

    def test_should_reject_citation_when_resolved_but_missing_title(self) -> None:
        with pytest.raises(ValidationError, match="resolved.*must carry a resolved title"):
            EvidenceCitation(
                publication_id="EXAMPLE-PATENT-0001",
                role="challenges",
                resolution=CitationResolution.RESOLVED,
            )

    def test_should_reject_citation_when_unresolved_but_carries_title(self) -> None:
        with pytest.raises(ValidationError, match="unresolved.*must not carry resolved metadata"):
            EvidenceCitation(
                publication_id="EXAMPLE-PATENT-0001",
                role="challenges",
                resolution=CitationResolution.UNRESOLVED,
                title="Should not be here",
            )


class DiscoveryLandscapeRecordTest:
    def test_should_construct_when_disclaimer_and_clusters_are_valid(self) -> None:
        record = DiscoveryLandscapeRecord(
            execution_id="exec-0001",
            query="solid electrolyte",
            clusters=(_cluster_observation(),),
        )
        assert record.disclaimer == DISCOVERY_DISCLAIMER
        assert record.clusters[0].cluster.cluster_id == "H01M"

    def test_should_construct_when_clusters_are_empty(self) -> None:
        record = DiscoveryLandscapeRecord(execution_id="exec-0001", query="solid electrolyte")
        assert record.clusters == ()

    def test_should_reject_record_when_disclaimer_is_paraphrased(self) -> None:
        with pytest.raises(ValidationError, match="exact required epistemic disclaimer"):
            DiscoveryLandscapeRecord(
                execution_id="exec-0001",
                query="solid electrolyte",
                disclaimer="AI-generated, use with caution.",
            )

    def test_should_expose_metrics_that_patent_cluster_alone_does_not_carry(self) -> None:
        observation = _cluster_observation()
        assert observation.quadrant == "Quadrant II (Co-developed / Saturated)"
        assert observation.demand_intensity == 0.5
        assert not hasattr(observation.cluster, "quadrant")
        assert not hasattr(observation.cluster, "demand_intensity")


class DiscoveryCandidateRecordTest:
    def test_should_construct_when_disclaimer_and_candidate_are_valid(self) -> None:
        record = DiscoveryCandidateRecord(execution_id="exec-0001", candidate=_candidate())
        assert record.disclaimer == DISCOVERY_DISCLAIMER

    def test_should_reject_record_when_disclaimer_is_paraphrased(self) -> None:
        with pytest.raises(ValidationError, match="exact required epistemic disclaimer"):
            DiscoveryCandidateRecord(
                execution_id="exec-0001",
                candidate=_candidate(),
                disclaimer="This is AI-generated, take it with a grain of salt.",
            )

    def test_should_reject_record_when_disclaimer_is_empty(self) -> None:
        with pytest.raises(ValidationError, match="exact required epistemic disclaimer"):
            DiscoveryCandidateRecord(execution_id="exec-0001", candidate=_candidate(), disclaimer="")

    @pytest.mark.parametrize(
        "field,phrase",
        [
            ("title", "This invention is patentable"),
            ("description", "offers freedom to operate in this space"),
            ("claimed_novelty", "clinically proven to outperform prior art"),
        ],
    )
    def test_should_reject_record_when_candidate_text_asserts_forbidden_claim(self, field: str, phrase: str) -> None:
        with pytest.raises(ValidationError, match="must not assert"):
            DiscoveryCandidateRecord(execution_id="exec-0001", candidate=_candidate(**{field: phrase}))


class DiscoveryVerificationRecordTest:
    def test_should_construct_when_not_yet_challenged_has_no_verdict_or_citations(self) -> None:
        record = DiscoveryVerificationRecord(
            execution_id="exec-0001",
            candidate_id="cand-0001",
            challenge_status=ChallengeStatus.NOT_YET_CHALLENGED,
        )
        assert record.verdict is None
        assert record.citations == ()

    def test_should_reject_record_when_not_yet_challenged_carries_a_verdict(self) -> None:
        with pytest.raises(ValidationError, match="not_yet_challenged.*must carry no verdict"):
            DiscoveryVerificationRecord(
                execution_id="exec-0001",
                candidate_id="cand-0001",
                challenge_status=ChallengeStatus.NOT_YET_CHALLENGED,
                verdict=_verdict(),
            )

    def test_should_construct_when_challenged_carries_a_verdict(self) -> None:
        record = DiscoveryVerificationRecord(
            execution_id="exec-0001",
            candidate_id="cand-0001",
            challenge_status=ChallengeStatus.CHALLENGED,
            verdict=_verdict(),
            citations=(
                EvidenceCitation(
                    publication_id="EXAMPLE-PATENT-0001",
                    role="challenges",
                    resolution=CitationResolution.UNRESOLVED,
                ),
            ),
        )
        assert record.challenge_status == ChallengeStatus.CHALLENGED

    def test_should_reject_record_when_challenged_but_missing_verdict(self) -> None:
        with pytest.raises(ValidationError, match="challenged.*must carry its verdict"):
            DiscoveryVerificationRecord(
                execution_id="exec-0001",
                candidate_id="cand-0001",
                challenge_status=ChallengeStatus.CHALLENGED,
            )

    def test_should_reject_record_when_verdict_rationale_asserts_forbidden_claim(self) -> None:
        with pytest.raises(ValidationError, match="must not assert"):
            DiscoveryVerificationRecord(
                execution_id="exec-0001",
                candidate_id="cand-0001",
                challenge_status=ChallengeStatus.CHALLENGED,
                verdict=_verdict(rationale="This candidate is patentable given the cited art."),
            )

    def test_should_reject_record_when_scorecard_evidence_asserts_forbidden_claim(self) -> None:
        scorecard = ScoreCard(
            candidate_id="cand-0001",
            novelty=0.8,
            prior_art_risk=0.2,
            differentiation=0.7,
            evidence=0.6,
            supporting_evidence=["scientifically verified against EXAMPLE-PATENT-0001"],
        )
        with pytest.raises(ValidationError, match="must not assert"):
            DiscoveryVerificationRecord(
                execution_id="exec-0001",
                candidate_id="cand-0001",
                challenge_status=ChallengeStatus.CHALLENGED,
                verdict=_verdict(),
                scorecard=scorecard,
            )


class VerificationMatchRecordTest:
    def test_should_construct_when_assessment_is_valid_and_carries_no_disclaimer_field(self) -> None:
        record = VerificationMatchRecord(execution_id="exec-verify-0001", assessment=_match_assessment())
        assert not hasattr(record, "disclaimer")


class ScientificResultsDocumentTest:
    def _document_kwargs(self, **overrides) -> dict:
        defaults = {
            "schema_version": "0.1.0",
            "generated_at": datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
        }
        defaults.update(overrides)
        return defaults

    def test_should_construct_when_document_is_empty(self) -> None:
        doc = ScientificResultsDocument(**self._document_kwargs())
        assert doc.executions == ()
        assert doc.candidates == ()

    def test_should_reject_document_when_schema_version_missing(self) -> None:
        with pytest.raises(ValidationError):
            ScientificResultsDocument(generated_at=datetime(2026, 9, 9, tzinfo=UTC))

    def test_should_reject_document_when_generated_at_is_naive(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            ScientificResultsDocument(schema_version="0.1.0", generated_at=datetime(2026, 9, 9))

    def test_should_reject_document_when_execution_ids_collide(self) -> None:
        execution = _execution()
        with pytest.raises(ValidationError, match="duplicate execution_id"):
            ScientificResultsDocument(**self._document_kwargs(executions=(execution, execution)))

    def test_should_construct_when_discovery_candidate_references_discovery_execution(self) -> None:
        execution = _execution(track=Track.DISCOVERY)
        candidate = DiscoveryCandidateRecord(execution_id=execution.execution_id, candidate=_candidate())
        doc = ScientificResultsDocument(**self._document_kwargs(executions=(execution,), candidates=(candidate,)))
        assert len(doc.candidates) == 1

    def test_should_reject_document_when_candidate_references_verification_execution(self) -> None:
        execution = _execution(track=Track.VERIFICATION)
        candidate = DiscoveryCandidateRecord(execution_id=execution.execution_id, candidate=_candidate())
        with pytest.raises(ValidationError, match="discovery and verification cannot be mixed"):
            ScientificResultsDocument(**self._document_kwargs(executions=(execution,), candidates=(candidate,)))

    def test_should_construct_when_landscape_references_discovery_execution(self) -> None:
        execution = _execution(track=Track.DISCOVERY)
        landscape = DiscoveryLandscapeRecord(
            execution_id=execution.execution_id, query="solid electrolyte", clusters=(_cluster_observation(),)
        )
        doc = ScientificResultsDocument(**self._document_kwargs(executions=(execution,), landscapes=(landscape,)))
        assert len(doc.landscapes) == 1
        assert doc.landscapes[0].clusters[0].cluster.cluster_id == "H01M"

    def test_should_reject_document_when_landscape_references_verification_execution(self) -> None:
        execution = _execution(track=Track.VERIFICATION)
        landscape = DiscoveryLandscapeRecord(execution_id=execution.execution_id, query="solid electrolyte")
        with pytest.raises(ValidationError, match="discovery and verification cannot be mixed"):
            ScientificResultsDocument(**self._document_kwargs(executions=(execution,), landscapes=(landscape,)))

    def test_should_reject_document_when_landscape_references_unknown_execution(self) -> None:
        landscape = DiscoveryLandscapeRecord(execution_id="does-not-exist", query="solid electrolyte")
        with pytest.raises(ValidationError, match="references unknown execution_id"):
            ScientificResultsDocument(**self._document_kwargs(landscapes=(landscape,)))

    def test_should_reject_document_when_match_references_discovery_execution(self) -> None:
        execution = _execution(execution_id="exec-disc", track=Track.DISCOVERY)
        match = VerificationMatchRecord(execution_id=execution.execution_id, assessment=_match_assessment())
        with pytest.raises(ValidationError, match="discovery and verification cannot be mixed"):
            ScientificResultsDocument(**self._document_kwargs(executions=(execution,), matches=(match,)))

    def test_should_reject_document_when_candidate_references_unknown_execution(self) -> None:
        candidate = DiscoveryCandidateRecord(execution_id="does-not-exist", candidate=_candidate())
        with pytest.raises(ValidationError, match="references unknown execution_id"):
            ScientificResultsDocument(**self._document_kwargs(candidates=(candidate,)))

    def test_should_construct_when_verification_match_references_verification_execution(self) -> None:
        execution = _execution(execution_id="exec-verify-0001", track=Track.VERIFICATION)
        match = VerificationMatchRecord(execution_id=execution.execution_id, assessment=_match_assessment())
        doc = ScientificResultsDocument(**self._document_kwargs(executions=(execution,), matches=(match,)))
        assert len(doc.matches) == 1

    def test_should_reject_document_when_payload_is_not_a_mapping(self) -> None:
        with pytest.raises(ValidationError):
            ScientificResultsDocument.model_validate("not-a-document")


_REPO_ROOT = Path(__file__).resolve().parents[4]
_ADR_0025_PATH = _REPO_ROOT / "docs" / "adr" / "0025-scientific-results-publication-and-track-semantics.md"
_CONTRACT_DOC_PATH = _REPO_ROOT / "docs" / "SCIENTIFIC_RESULTS_CONTRACT.md"

# The pre-ADR-0025 naming this codebase used to carry before ADR 0025 (the normative
# document) settled on discovery/verification. Their presence as a *track value* in
# either governing doc means the docs and this module's Track vocabulary have drifted.
_LEGACY_TRACK_VALUE_PATTERNS: tuple[str, ...] = (
    'track: "synthesis"',
    'track: "deterministic"',
    '"track": "synthesis"',
    '"track": "deterministic"',
    '`"synthesis"`',
    '`"deterministic"`',
)


class TrackVocabularyDocumentationSyncTest:
    """Guards against exactly the drift PR #71 review caught: ADR 0025 and
    SCIENTIFIC_RESULTS_CONTRACT.md must use the same track vocabulary as this module's
    `Track` enum, not an earlier or divergent naming.
    """

    def test_should_define_track_as_exactly_discovery_and_verification(self) -> None:
        assert {t.value for t in Track} == {"discovery", "verification"}

    @pytest.mark.parametrize("doc_path", [_ADR_0025_PATH, _CONTRACT_DOC_PATH])
    def test_should_keep_governing_doc_free_of_legacy_track_values(self, doc_path: Path) -> None:
        assert doc_path.exists(), f"expected governing doc at {doc_path}"
        text = doc_path.read_text(encoding="utf-8")
        for legacy in _LEGACY_TRACK_VALUE_PATTERNS:
            assert legacy not in text, (
                f"{doc_path.name} still contains legacy track-value literal {legacy!r} — "
                "Track is now {'discovery', 'verification'} (ADR 0025 §1); update the doc "
                "to match rather than letting code and documentation vocabulary diverge"
            )

    @pytest.mark.parametrize("doc_path", [_ADR_0025_PATH, _CONTRACT_DOC_PATH])
    def test_should_use_current_track_values_in_governing_doc(self, doc_path: Path) -> None:
        text = doc_path.read_text(encoding="utf-8")
        # Docs render a track value either as a code span (`discovery`) or, in a JSON
        # example, a quoted string ("discovery") — accept either form.
        assert "`discovery`" in text or '"discovery"' in text
        assert "`verification`" in text or '"verification"' in text
