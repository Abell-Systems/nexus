"""Unit tests for GroqClient implementing LlmClientProtocol."""

from unittest.mock import MagicMock, patch

import pytest

from domain.protocols.agents import (
    LlmChatMessage,
    LlmChatRequest,
    LlmChatResponse,
    LlmClientProtocol,
)
from infrastructure.llm.groq_client import GroqClient, GroqLlmClient


def test_groq_client_protocol_conformance():
    client = GroqClient(api_key="gsk_test")
    assert isinstance(client, LlmClientProtocol)
    assert GroqLlmClient is GroqClient


def test_groq_client_unconfigured_api_key_fails_fast(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = GroqClient(api_key=None)
    request = LlmChatRequest(
        messages=[LlmChatMessage(role="user", content="Hello")],
    )
    with pytest.raises(ValueError, match="GROQ_API_KEY not configured"):
        client.chat_completion(request)


def test_groq_client_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "env_key_123")
    client = GroqClient()
    assert client.api_key == "env_key_123"
    assert client.model == "llama-3.3-70b-versatile"


def test_groq_client_chat_completion_success():
    client = GroqClient(api_key="gsk_test", model="custom-model")
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
        assert result.model == "custom-model"
        assert result.usage_tokens == 42

        # Verify call payload
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer gsk_test"
        payload = call_kwargs["json"]
        assert payload["model"] == "custom-model"
        assert payload["temperature"] == 0.3
        assert payload["response_format"] == {"type": "json_object"}
        assert len(payload["messages"]) == 2
        assert payload["messages"][0] == {"role": "system", "content": "Act as expert"}
