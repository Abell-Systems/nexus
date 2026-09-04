"""Unit tests for GroqClient implementing LlmClientProtocol with ProviderConfig."""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.llm.client_protocol import (
    LlmChatMessage,
    LlmChatRequest,
    LlmChatResponse,
    LlmClientProtocol,
)
from infrastructure.llm.groq_client import GroqClient, GroqLlmClient
from infrastructure.llm.provider_config import ProviderConfig


def test_provider_config_from_env_defaults(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_BASE_URL", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("GROQ_TIMEOUT_SECONDS", raising=False)

    config = ProviderConfig.from_env()
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.model == "llama-3.3-70b-versatile"
    assert config.api_key is None
    assert config.timeout_seconds == 30.0


def test_provider_config_from_env_overrides(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "key_xyz")
    monkeypatch.setenv("GROQ_BASE_URL", "https://custom.endpoint/v1")
    monkeypatch.setenv("GROQ_MODEL", "custom-fast-model")
    monkeypatch.setenv("GROQ_TIMEOUT_SECONDS", "15.5")

    config = ProviderConfig.from_env()
    assert config.api_key == "key_xyz"
    assert config.base_url == "https://custom.endpoint/v1"
    assert config.model == "custom-fast-model"
    assert config.timeout_seconds == 15.5


def test_groq_client_protocol_conformance():
    client = GroqClient(api_key="gsk_test")
    assert isinstance(client, LlmClientProtocol)
    assert GroqLlmClient is GroqClient


def test_groq_client_unconfigured_api_key_fails_fast(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = GroqClient()
    request = LlmChatRequest(
        messages=[LlmChatMessage(role="user", content="Hello")],
    )
    with pytest.raises(ValueError, match="GROQ_API_KEY not configured"):
        client.chat_completion(request)


def test_groq_client_with_custom_provider_config():
    config = ProviderConfig(
        base_url="https://custom.llm/v1",
        model="custom-llm-1",
        api_key="sk-test-custom",
        timeout_seconds=45.0,
    )
    client = GroqClient(config=config)
    assert client.api_key == "sk-test-custom"
    assert client.model == "custom-llm-1"
    assert client.base_url == "https://custom.llm/v1"


def test_groq_client_chat_completion_success():
    config = ProviderConfig(
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        api_key="gsk_test",
        timeout_seconds=20.0,
    )
    client = GroqClient(config=config)
    request = LlmChatRequest(
        messages=[
            LlmChatMessage(role="system", content="Act as expert"),
            LlmChatMessage(role="user", content="Describe lithium dendrites"),
        ],
        temperature=0.3,
        response_format="json_object",
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"summary": "Dendrites are needle-like structures"}',
                }
            }
        ],
        "usage": {"total_tokens": 42},
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        result = client.chat_completion(request)

        assert isinstance(result, LlmChatResponse)
        assert result.content == '{"summary": "Dendrites are needle-like structures"}'
        assert result.model == "llama-3.3-70b-versatile"
        assert result.usage_tokens == 42

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer gsk_test"
        payload = call_kwargs["json"]
        assert payload["model"] == "llama-3.3-70b-versatile"
        assert payload["temperature"] == 0.3
        assert payload["response_format"] == {"type": "json_object"}
        assert len(payload["messages"]) == 2
        assert payload["messages"][0] == {"role": "system", "content": "Act as expert"}
