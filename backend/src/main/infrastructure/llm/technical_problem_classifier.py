"""LLM-backed implementation of TechnicalProblemClassifierProtocol, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md SS7."""

import json

from domain.models.corpus_expansion import TechnicalProblemClassification
from infrastructure.llm.client_protocol import LlmChatMessage, LlmChatRequest, LlmClientProtocol

_CLASS_DEFINITIONS_PROMPT = """Classify the following public tender description into exactly one of three categories:

TECHNICAL_PROBLEM: the description articulates a specific technical, scientific, or engineering challenge, need, or capability gap that a solution is being sought for -- it describes what is technically difficult or unsolved.

GENERIC_PROCUREMENT: the description specifies a scope of work, deliverable, standard/certification to follow, quantity, or administrative/contractual term, without articulating an underlying technical problem -- it reads as "what to buy/deliver," not "what technical difficulty needs solving."

EMPTY_INSUFFICIENT: the description is empty, near-empty, or so minimal/boilerplate that no meaningful judgment can be made either way.

Respond ONLY in valid JSON matching: {"classification": "TECHNICAL_PROBLEM" | "GENERIC_PROCUREMENT" | "EMPTY_INSUFFICIENT"}"""

_LABEL_TO_CLASSIFICATION = {
    "TECHNICAL_PROBLEM": TechnicalProblemClassification.TECHNICAL_PROBLEM,
    "GENERIC_PROCUREMENT": TechnicalProblemClassification.GENERIC_PROCUREMENT,
    "EMPTY_INSUFFICIENT": TechnicalProblemClassification.EMPTY_INSUFFICIENT,
}


class LlmTechnicalProblemClassifier:
    """Deterministic (temperature=0) classifier per spec SS7. Implements
    TechnicalProblemClassifierProtocol structurally (no explicit inheritance needed --
    the protocol is runtime_checkable)."""

    def __init__(self, llm_client: LlmClientProtocol) -> None:
        self.client = llm_client

    def classify(self, description_text: str) -> TechnicalProblemClassification:
        request = LlmChatRequest(
            messages=[
                LlmChatMessage(role="system", content=_CLASS_DEFINITIONS_PROMPT),
                LlmChatMessage(role="user", content=description_text),
            ],
            temperature=0.0,
            response_format="json_object",
        )
        response = self.client.chat_completion(request)
        try:
            payload = json.loads(response.content)
            label = str(payload["classification"]).strip().upper()
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"Malformed classifier response: {response.content!r}") from exc

        if label not in _LABEL_TO_CLASSIFICATION:
            raise ValueError(f"Unknown classification label from LLM: {label!r}")
        return _LABEL_TO_CLASSIFICATION[label]
