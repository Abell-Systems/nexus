import json
from unittest.mock import MagicMock

import pytest

from domain.models.corpus_expansion import TechnicalProblemClassification
from domain.protocols.corpus import TechnicalProblemClassifierProtocol
from infrastructure.llm.client_protocol import LlmChatResponse
from infrastructure.llm.technical_problem_classifier import (
    _CLASS_DEFINITIONS_PROMPT,
    LlmTechnicalProblemClassifier,
)


def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat_completion.return_value = LlmChatResponse(content=content, model="test")
    return client


def test_classify_returns_technical_problem():
    client = _mock_client(json.dumps({"classification": "TECHNICAL_PROBLEM"}))
    classifier = LlmTechnicalProblemClassifier(client)
    assert classifier.classify("some description") == TechnicalProblemClassification.TECHNICAL_PROBLEM


def test_classify_returns_generic_procurement():
    client = _mock_client(json.dumps({"classification": "GENERIC_PROCUREMENT"}))
    classifier = LlmTechnicalProblemClassifier(client)
    assert classifier.classify("some description") == TechnicalProblemClassification.GENERIC_PROCUREMENT


def test_classify_uses_temperature_zero():
    client = _mock_client(json.dumps({"classification": "EMPTY_INSUFFICIENT"}))
    classifier = LlmTechnicalProblemClassifier(client)
    classifier.classify("x")
    request = client.chat_completion.call_args[0][0]
    assert request.temperature == 0.0


def test_classify_raises_on_malformed_json():
    client = _mock_client("not json")
    classifier = LlmTechnicalProblemClassifier(client)
    with pytest.raises(ValueError):
        classifier.classify("x")


def test_classify_raises_on_unknown_label():
    client = _mock_client(json.dumps({"classification": "MAYBE"}))
    classifier = LlmTechnicalProblemClassifier(client)
    with pytest.raises(ValueError):
        classifier.classify("x")


def test_classifier_conforms_to_protocol():
    client = _mock_client(json.dumps({"classification": "TECHNICAL_PROBLEM"}))
    classifier = LlmTechnicalProblemClassifier(client)
    assert isinstance(classifier, TechnicalProblemClassifierProtocol)


def test_class_definitions_prompt_includes_frozen_spec_clauses():
    assert "AENA failure mode" in _CLASS_DEFINITIONS_PROMPT
    assert "Distinct from GENERIC_PROCUREMENT" in _CLASS_DEFINITIONS_PROMPT
