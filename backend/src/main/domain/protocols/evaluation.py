"""Domain protocols for evaluation dataset loading and verification under ADR 0006 and ADR 0007.

Invariants:
- The evaluation subsystem is an INDEPENDENT AUDITOR of the matching subsystem.
- domain/protocols/evaluation.py MUST NOT import from domain.protocols.matching or domain.models.matching.
- Protocols are expressed exclusively in evaluation-domain and demand-domain types.
- No `Any` is used to bridge bounded contexts. Impedance mismatch between evaluation types and
  matching types is resolved by an explicit adapter in application/evaluation/matching_adapter.py.
- The `EvaluationRankingPort` protocol defines the collaboration contract between the runner
  and any engine, using only types from domain.models.evaluation and domain.models.demand.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.evaluation import (
    EvaluationDemand,
    EvaluationExecutionContext,
    EvaluationPatent,
    EvaluationRunReport,
    ValidatedDataset,
)


@runtime_checkable
class EvaluationPolicyIdentity(Protocol):
    """Minimal structural protocol for what the evaluation subsystem needs from a policy object.

    Only the identity/provenance fields required to stamp the EvaluationRunReport are declared here.
    The full MatchingPolicyConfig from the matching bounded context satisfies this protocol via
    structural subtyping. The evaluation runner never imports MatchingPolicyConfig directly.
    """

    policy_id: str
    policy_version: str
    policy_sha256: str


@runtime_checkable
class EvaluationRankingPort(Protocol):
    """Port for ranking candidate patents against a demand, as seen by the evaluation auditor.

    This protocol is expressed exclusively in evaluation-domain types (EvaluationDemand,
    EvaluationPatent) — no matching-domain types appear here. The impedance mismatch between
    evaluation types and matching types (CandidatePool, PatentCandidateEvidence, etc.) is
    resolved by an explicit adapter in application/evaluation/matching_adapter.py, which is
    the only module permitted to import matching-domain models on behalf of evaluation.

    The contract:
    - Input: a demand and the sealed patent universe from the benchmark
    - Output: publication_ids ordered by descending relevance (the engine's ranking)

    The concrete DefaultMatchingAdapter satisfies this protocol via structural subtyping.
    """

    def rank_candidates(
        self,
        demand: EvaluationDemand,
        patents: list[EvaluationPatent],
    ) -> list[str]:
        """Returns publication_ids ranked by the engine in descending relevance order.

        The ranking must preserve the engine's original ordering without re-sorting.
        """
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
    """Port for running scientific evaluation over a validated dataset and a ranking port.

    The runner is a pure auditor: it knows nothing about CandidatePool, MatchAssessment,
    PatentCandidateEvidence, MatchingPolicyConfig, or any other matching-domain type.

    Ranking is delegated to EvaluationRankingPort, which abstracts the matching subsystem
    completely. The adapter pattern keeps the coupling at the correct layer (application).

    EvaluationPolicyIdentity is accepted only for provenance stamping in the report;
    the runner never uses it for ranking decisions.
    """

    def run_evaluation(
        self,
        dataset: ValidatedDataset,
        ranking_port: EvaluationRankingPort,
        policy: EvaluationPolicyIdentity,
        context: EvaluationExecutionContext,
    ) -> EvaluationRunReport:
        """Executes full evaluation run, producing a sealed, reproducible EvaluationRunReport."""
        ...


# DemandRecord / DemandSignal are imported above but only used in other protocols
# that may be extended in the future. Keep the import explicit.
__all__ = [
    "EvaluationPolicyIdentity",
    "EvaluationRankingPort",
    "EvaluationDatasetLoader",
    "EvaluationRunner",
]

# Suppressed: DemandRecord, DemandSignal are available for future protocol extensions
# without adding new imports to this file.
_ = (DemandRecord, DemandSignal)
