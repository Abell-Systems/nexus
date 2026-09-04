"""Domain protocols for provider-agnostic LLM and agent invocation under ADR 0009.

Invariants:
- The domain core has ZERO dependency on any concrete LLM vendor or agent framework (Google ADK, OpenAI, Anthropic, Groq).
- Application use cases (synthesis, prior-art critique, governance) interact strictly with these protocols.
- Concrete provider adapters live in infrastructure/ and implement these structural interfaces.
"""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from domain.models.runtime_schemas import (
    AdversarialVerdict,
    DemandSignal,
    InventionCandidate,
    PatentRecord,
    ScoreCard,
)


class LlmChatMessage(BaseModel):
    """A single chat message with a role and content."""

    role: str
    content: str


class LlmChatRequest(BaseModel):
    """Typed request payload for LLM completions."""

    messages: list[LlmChatMessage]
    temperature: float = 0.2
    response_format: str | None = None


class LlmChatResponse(BaseModel):
    """Typed response from an LLM completion."""

    content: str
    model: str = ""
    usage_tokens: int | None = None


@runtime_checkable
class LlmClientProtocol(Protocol):
    """Low-level protocol for structured text/JSON chat completion."""

    def chat_completion(
        self,
        request: LlmChatRequest,
    ) -> LlmChatResponse:
        ...  # pragma: no cover


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
