"""LLM provider abstraction resolving Gemini, Groq, or OpenRouter."""

import os
from typing import Any


class LLMProvider:
    @classmethod
    def get_provider_name(cls) -> str:
        return os.getenv("MODEL_PROVIDER", "gemini").lower()

    @classmethod
    def get_model_name(cls) -> str:
        provider = cls.get_provider_name()
        if provider == "groq":
            return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        return {
            "model_provider": cls.get_provider_name(),
            "model": cls.get_model_name(),
            "has_api_key": bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        }
