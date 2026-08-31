"""LLM Provider abstraction layer.

Resolves model instances and configuration for Google ADK agents based on environment settings.
Supports standard environment trio: MODEL_PROVIDER, MODEL_NAME, MODEL_KEY.
Fails fast on unknown or unsupported providers.
"""

import os
from typing import Any, Dict, List, Set, Union

SUPPORTED_PROVIDERS: Set[str] = {"gemini", "groq", "openrouter", "openai", "anthropic"}

DEFAULT_MODELS: Dict[str, str] = {
    "gemini": "gemini-3.5-flash",
    "groq": "qwen/qwen3.8-27b",
    "openrouter": "minimax/minimax-m2.7:free",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
}

API_KEY_ENV_VARS: Dict[str, List[str]] = {
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
}

# Groq models documented (console.groq.com/docs/structured-outputs) as
# supporting native strict JSON schema output. LiteLLM's own model registry
# doesn't know this yet for the newer/preview ones — without this,
# litellm.supports_response_schema() silently returns False and Groq's
# transformation layer falls back to a tool-call-forcing workaround
# ("json_tool_call") instead of constrained decoding, which is exactly what
# let qwen3.8-27b emit a malformed ScoreCardList (missing the 'scorecards'
# wrapper) despite Groq's docs saying it supports strict mode. Registering
# the capability with litellm restores the native, reliable path.
GROQ_STRUCTURED_OUTPUT_MODELS: Set[str] = {
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-safeguard-20b",
}


def _register_litellm_capabilities() -> None:
    """Registers structured output support in LiteLLM for known Groq models."""
    try:
        import litellm

        for model in GROQ_STRUCTURED_OUTPUT_MODELS:
            keys = [model, f"groq/{model}" if not model.startswith("groq/") else model]
            for k in keys:
                if k not in litellm.model_cost:
                    litellm.model_cost[k] = {}
                litellm.model_cost[k]["supports_response_schema"] = True
                litellm.model_cost[k]["supports_function_calling"] = True
    except ImportError:
        pass


_register_litellm_capabilities()


class LLMProvider:
    """Single source of truth for resolving LLM models across the application."""

    @classmethod
    def get_provider_name(cls) -> str:
        """Returns the normalized provider name from environment, failing fast if unsupported."""
        provider = os.getenv("MODEL_PROVIDER", "gemini").lower().strip()
        if provider not in SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported MODEL_PROVIDER: '{provider}'. Supported providers are: {supported}.")
        return provider

    @classmethod
    def get_model_name(cls) -> str:
        """Returns the model name for the current provider."""
        provider = cls.get_provider_name()
        model_name = (
            os.getenv("MODEL_NAME")
            or os.getenv(f"{provider.upper()}_MODEL")
            or DEFAULT_MODELS.get(provider)
        )
        if not model_name:
            raise ValueError(f"No model configured for provider '{provider}'.")
        return model_name

    @classmethod
    def sync_model_key(cls) -> None:
        """Propagates generic MODEL_KEY env var to provider-specific SDK env vars if set."""
        model_key = os.getenv("MODEL_KEY")
        if not model_key:
            return

        provider = cls.get_provider_name()
        target_vars = API_KEY_ENV_VARS.get(provider, [f"{provider.upper()}_API_KEY"])
        for var in target_vars:
            if not os.getenv(var):
                os.environ[var] = model_key

    @classmethod
    def get_agent_model(cls) -> Union[str, Any]:
        """Resolves the model object expected by ADK LlmAgent.

        Returns:
            str for Gemini (native ADK format)
            LiteLlm instance for all other providers (groq, openrouter, openai, etc.)
        """
        cls.sync_model_key()
        _register_litellm_capabilities()
        provider = cls.get_provider_name()
        model_name = cls.get_model_name()

        if provider == "gemini":
            return model_name

        from google.adk.models.lite_llm import LiteLlm

        if model_name.startswith(f"{provider}/"):
            model_id = model_name
        else:
            model_id = f"{provider}/{model_name}"

        return LiteLlm(model=model_id)

    @classmethod
    def is_api_key_configured(cls) -> bool:
        """Checks if credentials are present for the active provider.

        Gemini via Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true) authenticates with
        the runtime's Application Default Credentials, not an API key -- reporting
        `false` there would be a false negative on Cloud Run, which always runs
        in that mode.
        """
        if bool(os.getenv("MODEL_KEY")):
            return True
        provider = cls.get_provider_name()
        if (
            provider == "gemini"
            and os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
            and os.getenv("GOOGLE_CLOUD_PROJECT")
        ):
            return True
        env_vars = API_KEY_ENV_VARS.get(provider, [f"{provider.upper()}_API_KEY"])
        return any(bool(os.getenv(var)) for var in env_vars)

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns provider, model, and configuration metadata for health/monitoring endpoints."""
        return {
            "model_provider": cls.get_provider_name(),
            "model": cls.get_model_name(),
            "api_key_configured": cls.is_api_key_configured(),
        }
