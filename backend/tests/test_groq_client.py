import json
from unittest.mock import patch
import pytest
from pydantic import BaseModel
from backend.patent_agent.groq_client import GroqLlmClient


class SampleSchema(BaseModel):
    title: str
    confidence: float


def test_groq_client_mock_completion():
    client = GroqLlmClient(api_key="mock_key")
    mock_json_response = '{"title": "Biodegradable Detergent Enzyme", "confidence": 0.95}'

    with patch.object(client, "_call_api", return_value=mock_json_response):
        result = client.generate_structured("Synthesize invention", SampleSchema)
        assert isinstance(result, SampleSchema)
        assert result.title == "Biodegradable Detergent Enzyme"
        assert result.confidence == 0.95


def test_groq_client_generate_text():
    client = GroqLlmClient(api_key="mock_key")
    with patch.object(client, "_call_api", return_value="Patent draft text") as mock_call:
        res = client.generate_text("Draft an abstract", system_prompt="You are a patent attorney.")
        assert res == "Patent draft text"
        mock_call.assert_called_once_with(
            [
                {"role": "system", "content": "You are a patent attorney."},
                {"role": "user", "content": "Draft an abstract"}
            ],
            response_format_json=False
        )


def test_groq_client_generate_structured_with_system_prompt():
    client = GroqLlmClient(api_key="mock_key")
    mock_json_response = '{"title": "Solar Panel Coating", "confidence": 0.88}'
    with patch.object(client, "_call_api", return_value=mock_json_response) as mock_call:
        result = client.generate_structured(
            "Extract features",
            SampleSchema,
            system_prompt="Analyze patent document."
        )
        assert result.title == "Solar Panel Coating"
        assert result.confidence == 0.88
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        messages = args[0]
        assert len(messages) == 2
        assert "Analyze patent document." in messages[0]["content"]
        assert "You MUST output valid JSON conforming strictly to this JSON Schema:" in messages[0]["content"]
        assert messages[1]["content"] == "Extract features"
        assert kwargs["response_format_json"] is True


def test_groq_client_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = GroqLlmClient(api_key=None)
    with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
        client._call_api([{"role": "user", "content": "hello"}])

    mock_client = GroqLlmClient(api_key="mock_key")
    with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
        mock_client._call_api([{"role": "user", "content": "hello"}])


def test_groq_client_init_defaults_and_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "env-secret-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-specdec")
    client = GroqLlmClient()
    assert client.api_key == "env-secret-key"
    assert client.model == "llama-3.3-70b-specdec"
    assert client.base_url == "https://api.groq.com/openai/v1"
    assert client.timeout == 30


def test_groq_client_call_api_urllib():
    client = GroqLlmClient(api_key="real-test-key", model="llama-3.3-70b-versatile")
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": '{"result": "success"}'
                }
            }
        ]
    }
    fake_response_bytes = json.dumps(fake_response).encode("utf-8")

    class MockHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def read(self):
            return fake_response_bytes

    with patch("urllib.request.urlopen", return_value=MockHTTPResponse()) as mock_urlopen:
        messages = [{"role": "user", "content": "ping"}]
        output = client._call_api(messages, response_format_json=True)
        assert output == '{"result": "success"}'

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.groq.com/openai/v1/chat/completions"
        assert req.get_header("Authorization") == "Bearer real-test-key"
        assert req.get_header("Content-type") == "application/json"
        assert req.get_header("User-agent") == "Abell-Nexus-Sovereign/1.0"

        sent_body = json.loads(req.data.decode("utf-8"))
        assert sent_body["model"] == "llama-3.3-70b-versatile"
        assert sent_body["messages"] == messages
        assert sent_body["response_format"] == {"type": "json_object"}


def test_groq_client_generate_structured_markdown_fenced():
    client = GroqLlmClient(api_key="mock_key")
    mock_markdown_response = '```json\n{"title": "Biodegradable Detergent Enzyme", "confidence": 0.95}\n```'

    with patch.object(client, "_call_api", return_value=mock_markdown_response):
        result = client.generate_structured("Synthesize invention", SampleSchema)
        assert isinstance(result, SampleSchema)
        assert result.title == "Biodegradable Detergent Enzyme"
        assert result.confidence == 0.95
