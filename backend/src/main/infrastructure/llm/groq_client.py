"""Lightweight OpenAI-compatible client for Groq API."""

import os
from typing import Any

import httpx

from domain.protocols.agents import LlmChatRequest, LlmChatResponse, LlmClientProtocol


class GroqClient(LlmClientProtocol):
    """Client implementing LlmClientProtocol for Groq's OpenAI-compatible endpoint."""

    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile") -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

    def chat_completion(
        self,
        request: LlmChatRequest,
    ) -> LlmChatResponse:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.response_format:
            payload["response_format"] = {"type": request.response_format}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {}).get("total_tokens")
            return LlmChatResponse(content=content, model=self.model, usage_tokens=usage)


GroqLlmClient = GroqClient
