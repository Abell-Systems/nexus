"""Domain protocols for provider-agnostic LLM and agent invocation under ADR 0009.

Invariants:
- The domain core has ZERO dependency on any concrete LLM vendor or agent framework (Google ADK, OpenAI, Anthropic, Groq).
- Application use cases (synthesis, prior-art critique, governance) interact strictly with these protocols.
- Concrete provider adapters live in infrastructure/ and implement these structural interfaces.
"""

from typing import Any, Protocol, runtime_checkable

from domain.models.runtime_schemas import (
    AdversarialVerdict,
    DemandSignal,
    InventionCandidate,
    PatentRecord,
    ScoreCard,
)


@runtime_checkable
class LlmClientProtocol(Protocol):
    """Low-level protocol for structured text/JSON chat completion."""

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Returns dictionary containing at least {"content": str}."""
        ...


@runtime_checkable
class InventorAgentProtocol(Protocol):
    """Port for proposing invention candidates from demand signals and prior art."""

    def propose_candidate(
        self,
        cluster_id: str,
        demands: list[DemandSignal],
        prior_art: list[PatentRecord],
    ) -> InventionCandidate:
        ...


@runtime_checkable
class AdversarialAgentProtocol(Protocol):
    """Port for attacking invention candidates with prior art citations."""

    def critique_candidate(
        self,
        candidate: InventionCandidate,
        prior_art: list[PatentRecord],
    ) -> AdversarialVerdict:
        ...


@runtime_checkable
class GovernorAgentProtocol(Protocol):
    """Port for evaluating novelty, prior-art risk, differentiation, and evidence."""

    def evaluate_candidate(
        self,
        candidate: InventionCandidate,
        prior_art: list[PatentRecord],
        verdict: AdversarialVerdict | None = None,
    ) -> ScoreCard:
        ...
