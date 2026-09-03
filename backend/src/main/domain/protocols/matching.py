from typing import Any, Protocol, runtime_checkable

from domain.models.demand import DemandSignal
from domain.models.matching import (
    Candidate,
    CandidatePool,
    EligibilityResult,
    MatchingResult,
    RankedCandidate,
)
from domain.models.patent import PatentDocument


@runtime_checkable
class PatentCandidateRetriever(Protocol):
    """Port for first-stage candidate retrieval strategies."""

    def retrieve(
        self,
        demand: DemandSignal,
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
        demand: DemandSignal,
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
class MatchingTelemetrySink(Protocol):
    """Port for persisting immutable, reproducible matching execution artifacts."""

    def record_run(
        self,
        result: MatchingResult,
        metadata: dict[str, Any],
        patent_evidence: dict[str, dict[str, Any]] | None = None,
    ) -> str:
        """Persists run artifacts and returns the unique run_id."""
        ...


@runtime_checkable
class MatchingFeatureExtractor(Protocol):
    """Port for extracting multi-dimensional alignment features between a demand and a patent."""

    def extract_features(
        self,
        demand: Any,  # DemandRecord or DemandSignal
        patent: PatentDocument,
    ) -> Any:  # MatchFeatures
        """Extracts deterministic MatchFeatures between the demand and the candidate patent."""
        ...


@runtime_checkable
class TechnologyMatcher(Protocol):
    """Port for evaluating technology problem-solution compatibility."""

    def assess_match(
        self,
        demand: Any,  # DemandRecord or DemandSignal
        patent: PatentDocument,
    ) -> Any:  # MatchAssessment
        """Evaluates compatibility and returns an auditable, explainable MatchAssessment."""
        ...


@runtime_checkable
class MatchingEngine(Protocol):
    """Core domain contract for evaluating candidates for a demand under a matching policy."""

    def evaluate(
        self,
        demand: Any,  # DemandRecord or DemandSignal
        candidates: CandidatePool,
        policy: Any,  # MatchingPolicyConfig
    ) -> list[Any]:  # list[MatchAssessment]
        """Evaluates and produces an explainable MatchAssessment for each candidate in the pool."""
        ...
