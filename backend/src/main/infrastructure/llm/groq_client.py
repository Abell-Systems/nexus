"""Lightweight OpenAI-compatible client for Groq API."""

from typing import Any

import httpx

from infrastructure.llm.client_protocol import (
    LlmChatRequest,
    LlmChatResponse,
    LlmClientProtocol,
)
from infrastructure.llm.provider_config import ProviderConfig


class GroqClient(LlmClientProtocol):
    """Client implementing LlmClientProtocol for Groq's OpenAI-compatible endpoint."""

    def __init__(
        self,
        config: ProviderConfig | None = None,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            base_config = ProviderConfig.from_env()
            self.config = ProviderConfig(
                base_url=base_config.base_url,
                model=model or base_config.model,
                api_key=api_key or base_config.api_key,
                timeout_seconds=base_config.timeout_seconds,
            )

    @property
    def api_key(self) -> str | None:
        return self.config.api_key

    @property
    def model(self) -> str:
        return self.config.model

    @property
    def base_url(self) -> str:
        return self.config.base_url

    def chat_completion(
        self,
        request: LlmChatRequest,
    ) -> LlmChatResponse:
        if not self.config.api_key:
            raise ValueError("GROQ_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.response_format:
            payload["response_format"] = {"type": request.response_format}

        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            resp = client.post(f"{self.config.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {}).get("total_tokens")
            return LlmChatResponse(content=content, model=self.config.model, usage_tokens=usage)


GroqLlmClient = GroqClient
