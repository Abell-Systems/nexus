"""Infrastructure protocols and contracts for low-level LLM transport clients."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


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
