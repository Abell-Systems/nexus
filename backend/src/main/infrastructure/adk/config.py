"""Synthesis agent configuration constants."""

import os

INVENTION_LOOP_MAX_ITERATIONS = 3


def get_agent_model(role: str = "default") -> str:
    provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
    role_env_var = f"{provider.upper()}_{role.upper()}_MODEL"
    if role_env_var in os.environ:
        return os.environ[role_env_var]
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
