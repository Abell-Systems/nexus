from typing import Any, Protocol
from domain.models.patent import PatentDocument
from domain.models.demand import DemandSignal
from domain.models.opportunity import OpportunityScore


class OpportunityModelProtocol(Protocol):
    """Protocol for calculating innovation gap and white-space metrics across clusters."""

    def compute_opportunity(
        self,
        cluster_id: str,
        patents: list[PatentDocument],
        demands: list[DemandSignal],
        context: Any = None,
        strict_mode: bool = False,
    ) -> OpportunityScore:
        ...


class SensitivityAnalyzerProtocol(Protocol):
    """Protocol for evaluating mathematical model robustness and ranking stability."""

    def evaluate_stability(
        self,
        model: OpportunityModelProtocol,
        clusters: list[str],
        landscape: Any,
        perturbation_regimes: list[Any],
    ) -> Any:
        ...
