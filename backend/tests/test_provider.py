import os
import pytest
from google.adk.models.lite_llm import LiteLlm
from patent_agent.provider import LLMProvider


def test_default_provider_is_gemini(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert LLMProvider.get_provider_name() == "gemini"
    assert LLMProvider.get_model_name() == "gemini-3.5-flash"
    # Gemini uses native string path
    assert LLMProvider.get_agent_model() == "gemini-3.5-flash"


def test_gemini_custom_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("MODEL_NAME", "gemini-2.5-pro")

    assert LLMProvider.get_agent_model() == "gemini-2.5-pro"


def test_groq_provider_resolution(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "groq")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    assert LLMProvider.get_provider_name() == "groq"
    assert LLMProvider.get_model_name() == "qwen/qwen3.8-27b"

    model_obj = LLMProvider.get_agent_model()
    assert isinstance(model_obj, LiteLlm)
    assert model_obj.model == "groq/qwen/qwen3.8-27b"


def test_groq_with_custom_model_name(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "groq")
    monkeypatch.setenv("MODEL_NAME", "llama-3.1-8b-instant")

    model_obj = LLMProvider.get_agent_model()
    assert isinstance(model_obj, LiteLlm)
    assert model_obj.model == "groq/llama-3.1-8b-instant"


def test_openrouter_provider_resolution(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "minimax/minimax-m2.7:free")

    assert LLMProvider.get_provider_name() == "openrouter"
    model_obj = LLMProvider.get_agent_model()
    assert isinstance(model_obj, LiteLlm)
    assert model_obj.model == "openrouter/minimax/minimax-m2.7:free"


def test_model_key_synchronization(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "groq")
    monkeypatch.setenv("MODEL_KEY", "gsk_test_key_12345")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assert LLMProvider.is_api_key_configured() is True
    _ = LLMProvider.get_agent_model()
    assert os.getenv("GROQ_API_KEY") == "gsk_test_key_12345"


def test_vertex_mode_counts_as_api_key_configured(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "ip-matchmaker-506820")
    monkeypatch.delenv("MODEL_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert LLMProvider.is_api_key_configured() is True


def test_unsupported_provider_fails_fast(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "unsupported_provider_xyz")

    with pytest.raises(ValueError, match="Unsupported MODEL_PROVIDER: 'unsupported_provider_xyz'"):
        LLMProvider.get_provider_name()


def test_groq_structured_output_capabilities_registered():
    import litellm

    assert litellm.supports_response_schema("groq/qwen/qwen3.8-27b", "groq") is True
    assert litellm.supports_response_schema("qwen/qwen3.8-27b", "groq") is True
    assert litellm.supports_response_schema("groq/openai/gpt-oss-120b", "groq") is True

