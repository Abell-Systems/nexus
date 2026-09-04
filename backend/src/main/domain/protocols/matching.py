from typing import Any, Protocol, runtime_checkable

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    Candidate,
    CandidatePool,
    EligibilityResult,
    MatchAssessment,
    MatchFeatures,
    MatchingPolicyConfig,
    PatentCandidateEvidence,
    RankedCandidate,
)
from domain.models.patent import PatentDocument


@runtime_checkable
class PatentCandidateRetriever(Protocol):
    """Port for first-stage candidate retrieval strategies."""

    def retrieve(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        """Retrieves candidates from the corpus for the demand."""
        ...


@runtime_checkable
class PatentEligibilityPolicy(Protocol):
    """Port for pre-retrieval candidate eligibility filtering."""

    def evaluate(
        self,
        patent: PatentDocument,
        demand: DemandRecord | DemandSignal,
    ) -> EligibilityResult:
        """Evaluates whether a patent publication is eligible as a candidate for a demand."""
        ...


@runtime_checkable
class CandidateRanker(Protocol):
    """Port for second-stage ranking over a shared fixed candidate pool."""

    def rank(
        self,
        pool: CandidatePool,
    ) -> list[RankedCandidate]:
        """Ranks candidates within the fixed candidate pool."""
        ...


@runtime_checkable
class MatchingFeatureExtractor(Protocol):
    """Port for extracting multi-dimensional alignment features between a demand and a patent."""

    def extract_features(
        self,
        demand: DemandRecord | DemandSignal,
        patent: PatentDocument,
    ) -> MatchFeatures:
        """Extracts deterministic MatchFeatures between the demand and the candidate patent."""
        ...


@runtime_checkable
class TechnologyMatcher(Protocol):
    """Port for evaluating technology problem-solution compatibility."""

    def assess_match(
        self,
        demand: DemandRecord | DemandSignal,
        patent: PatentDocument,
    ) -> MatchAssessment:
        """Evaluates compatibility and returns an auditable, explainable MatchAssessment."""
        ...


@runtime_checkable
class MatchingEngine(Protocol):
    """Core domain contract for evaluating candidates for a demand under a matching policy."""

    def evaluate(
        self,
        demand: DemandRecord | DemandSignal,
        candidates: CandidatePool,
        policy: MatchingPolicyConfig,
        patent_metadata: dict[str, Any] | list[PatentCandidateEvidence] | None = None,
    ) -> list[MatchAssessment]:
        """Evaluates and produces an explainable MatchAssessment for each candidate in the pool."""
        ...
