"""Domain protocols for provider-agnostic agent invocation under ADR 0009.

Invariants:
- The domain core defines capability-based ports, not LLM transport mechanisms.
- Application use cases (synthesis, prior-art critique, governance) interact strictly with these protocols.
- Concrete provider adapters live in infrastructure/ and implement these structural interfaces.
"""

from typing import Protocol, runtime_checkable

from domain.models.runtime_schemas import (
    AdversarialVerdict,
    DemandSignal,
    InventionCandidate,
    PatentRecord,
    ScoreCard,
)


@runtime_checkable
class InventorAgentProtocol(Protocol):
    """Port for proposing invention candidates from demand signals and prior art."""

    def propose_candidate(
        self,
        cluster_id: str,
        demands: list[DemandSignal],
        prior_art: list[PatentRecord],
    ) -> InventionCandidate:
        ...  # pragma: no cover


@runtime_checkable
class AdversarialAgentProtocol(Protocol):
    """Port for attacking invention candidates with prior art citations."""

    def critique_candidate(
        self,
        candidate: InventionCandidate,
        prior_art: list[PatentRecord],
    ) -> AdversarialVerdict:
        ...  # pragma: no cover


@runtime_checkable
class GovernorAgentProtocol(Protocol):
    """Port for evaluating novelty, prior-art risk, differentiation, and evidence."""

    def evaluate_candidate(
        self,
        candidate: InventionCandidate,
        prior_art: list[PatentRecord],
        verdict: AdversarialVerdict | None = None,
    ) -> ScoreCard:
        ...  # pragma: no cover
