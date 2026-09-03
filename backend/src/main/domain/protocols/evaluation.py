"""Domain protocols for evaluation dataset loading and verification under ADR 0006 and ADR 0007.

Invariants:
- The evaluation subsystem is an INDEPENDENT AUDITOR of the matching subsystem.
- domain/protocols/evaluation.py MUST NOT import from domain.protocols.matching or domain.models.matching.
- Structural protocols (EvaluationAssessment, EvaluationCandidatePool, EvaluatableEngine,
  EvaluationPolicyIdentity) express only what the evaluation subsystem needs from its collaborators,
  using types from domain.models.demand and locally-defined evaluation-owned protocols.
- Concrete matching types (CandidatePool, MatchAssessment, MatchingPolicyConfig) satisfy these
  protocols via structural subtyping — the coupling lives only in the application/evaluation layer
  where it constructs those objects.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.evaluation import (
    EvaluationExecutionContext,
    EvaluationRunReport,
    ValidatedDataset,
)


@runtime_checkable
class EvaluationAssessment(Protocol):
    """Minimal structural view of what the EvaluationRunner reads from engine output.

    MatchAssessment from domain.models.matching satisfies this protocol.
    The evaluation runner only needs publication_id to reconstruct the ranked list.
    """

    publication_id: str


@runtime_checkable
class EvaluationCandidate(Protocol):
    """Minimal structural view of a candidate entry in the pool, as seen by the evaluation port."""

    publication_id: str


@runtime_checkable
class EvaluationCandidatePool(Protocol):
    """Minimal structural view of the candidate pool, as seen by the evaluation port.

    CandidatePool from domain.models.matching satisfies this protocol via structural subtyping.
    The `candidates` field is typed as Sequence[Any] at this abstraction level to avoid mypy
    covariance issues with list[Candidate] — the concrete layer enforces individual item types.
    """

    demand_id: str
    candidates: Sequence[Any]


@runtime_checkable
class EvaluationPolicyIdentity(Protocol):
    """Minimal structural protocol for what the evaluation subsystem needs from a policy object.

    Only the identity/provenance fields required to stamp the EvaluationRunReport are declared here.
    The full MatchingPolicyConfig satisfies this protocol via structural subtyping.
    """

    policy_id: str
    policy_version: str
    policy_sha256: str


@runtime_checkable
class EvaluatableEngine(Protocol):
    """Minimal structural protocol for any engine that the EvaluationRunner can invoke.

    Deliberately avoids importing MatchingEngine, CandidatePool, MatchAssessment, or any
    matching-domain type. The evaluation subsystem's port expresses the collaboration in terms
    of evaluation-owned abstractions and the demand model (which is cross-cutting, not matching-specific).

    The `candidates` parameter uses `Any` because Pydantic model fields are invariant for mypy,
    which prevents `CandidatePool` (with `candidates: list[Candidate]`) from formally satisfying
    `EvaluationCandidatePool` (with `candidates: Sequence[Any]`) at the type-checker level.
    The runtime structural compatibility is correct; the Any is a precise, documented concession
    to mypy's Pydantic invariance — not a loss of domain clarity.

    The patent_metadata parameter is declared here because the evaluation runner ALWAYS passes
    real patent content (title, abstract, CPC) from the benchmark dataset so the engine can
    compute CPC concordance and text features from authentic observed data. It is typed as
    Sequence[Any] at this protocol level — the concrete implementation (DefaultMatchingEngine)
    accepts list[PatentCandidateEvidence], which satisfies this via structural subtyping.

    DefaultMatchingEngine satisfies this protocol via structural subtyping.
    """

    def evaluate(
        self,
        demand: DemandRecord | DemandSignal,
        candidates: Any,
        policy: EvaluationPolicyIdentity,
        patent_metadata: Sequence[Any] | None = None,
    ) -> Sequence[EvaluationAssessment]:
        """Evaluates candidates for a demand under a policy, returning ordered assessments."""
        ...


@runtime_checkable
class EvaluationDatasetLoader(Protocol):
    """Port for loading and cryptographically validating evaluation benchmark datasets."""

    def load_validated_dataset(
        self,
        dataset_path: Path,
        checksum_path: Path,
        manifest_path: Path,
    ) -> ValidatedDataset:
        """Loads dataset from exact paths, verifies byte-exact SHA-256 and manifest, returning ValidatedDataset."""
        ...


@runtime_checkable
class EvaluationRunner(Protocol):
    """Port for running scientific evaluation over a validated dataset and matching engine.

    The engine and policy parameters are typed as EvaluatableEngine and EvaluationPolicyIdentity
    — minimal structural protocols owned by the evaluation subsystem — so that the evaluation port
    is architecturally independent of the matching bounded context.

    The concrete DefaultMatchingEngine and MatchingPolicyConfig satisfy these structural protocols.
    """

    def run_evaluation(
        self,
        dataset: ValidatedDataset,
        engine: EvaluatableEngine,
        policy: EvaluationPolicyIdentity,
        context: EvaluationExecutionContext,
    ) -> EvaluationRunReport:
        """Executes full evaluation run, producing a sealed, reproducible EvaluationRunReport."""
        ...
