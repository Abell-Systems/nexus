"""Provider configuration for LLM transports under ADR 0009 and ADR 0008."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    """Operational settings for an external LLM provider."""

    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(
        cls,
        prefix: str = "GROQ",
        default_base_url: str = "https://api.groq.com/openai/v1",
        default_model: str = "llama-3.3-70b-versatile",
        default_timeout: float = 30.0,
    ) -> "ProviderConfig":
        """Load provider configuration from environment variables or defaults."""
        api_key = os.getenv(f"{prefix}_API_KEY")
        base_url = os.getenv(f"{prefix}_BASE_URL", default_base_url)
        model = os.getenv(f"{prefix}_MODEL", default_model)
        timeout_str = os.getenv(f"{prefix}_TIMEOUT_SECONDS")
        timeout = float(timeout_str) if timeout_str else default_timeout

        return cls(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_seconds=timeout,
        )
