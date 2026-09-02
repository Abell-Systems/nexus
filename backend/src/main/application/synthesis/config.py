"""Synthesis agent configuration constants."""

import os

INVENTION_LOOP_MAX_ITERATIONS = 3


def get_agent_model(role: str) -> str:
    provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
