"""Universal Groq / OpenAI-Compatible LLM Provider Client."""

import os
import json
import re
from typing import TypeVar, Type
import urllib.request
import urllib.error
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class GroqLlmClient:
    """Lightweight OpenAI-compatible client for Groq API without external heavy SDKs."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: int = 30
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _call_api(self, messages: list[dict[str, str]], response_format_json: bool = True) -> str:
        if not self.api_key or self.api_key == "mock_key":
            raise ValueError("GROQ_API_KEY is not set.")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Abell-Nexus-Sovereign/1.0"
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8")
            res_json = json.loads(body)
            return res_json["choices"][0]["message"]["content"]

    def generate_text(self, prompt: str, system_prompt: str = "You are a specialized patent AI agent.") -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        return self._call_api(messages, response_format_json=False)

    def generate_structured(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        sys_msg = (
            (system_prompt + "\n\n" if system_prompt else "") +
            f"You MUST output valid JSON conforming strictly to this JSON Schema:\n{schema_json}"
        )
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt}
        ]
        raw_output = self._call_api(messages, response_format_json=True)
        # Parse JSON
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        return schema.model_validate(parsed)
