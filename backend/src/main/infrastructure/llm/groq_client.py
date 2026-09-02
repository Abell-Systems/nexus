"""Lightweight OpenAI-compatible client for Groq API."""

import json
import os
from typing import Any
import httpx


class GroqClient:
    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"content": content, "raw_response": data}


GroqLlmClient = GroqClient
