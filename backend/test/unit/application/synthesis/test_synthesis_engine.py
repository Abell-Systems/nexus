"""Unit tests for SynthesisEngine under ADR 0009."""

import json
from unittest.mock import MagicMock

import pytest

from application.synthesis.synthesis_engine import (
    InventionSynthesisEngine,
    SynthesisEngine,
    validate_grounded_citations,
)
from domain.models.runtime_schemas import DemandSignal, InventionCandidate, PatentRecord
from domain.protocols.agents import (
    AdversarialAgentProtocol,
    InventorAgentProtocol,
    LlmChatRequest,
    LlmChatResponse,
    LlmClientProtocol,
)


@pytest.fixture
def mock_patents() -> list[PatentRecord]:
    return [
        PatentRecord(
            publication_number="ES-2849102-B2",
            title="Sulfide solid electrolyte",
            abstract="Lithium phosphorus sulfur compound with high ionic conductivity.",
            filing_date="2020-01-01",
        ),
        PatentRecord(
            publication_number="ES-1234567-A1",
            title="Cathode material",
            abstract="Coated active material for solid state cells.",
            filing_date="2021-02-02",
        ),
    ]


@pytest.fixture
def mock_demands() -> list[DemandSignal]:
    return [
        DemandSignal(
            source="innoget",
            id="DEM-1",
            title="High conductivity solid electrolyte",
            description="Seeking >10 mS/cm at room temperature with moisture stability.",
        )
    ]


@pytest.fixture
def mock_candidate() -> InventionCandidate:
    return InventionCandidate(
        candidate_id="cand_test_001",
        cluster_id="cluster_battery",
        title="Doped Halide-Sulfide Composite Electrolyte",
        description="A moisture-resistant composite electrolyte with 15 mS/cm conductivity.",
        claimed_novelty="Synergistic halogenation preventing H2S release.",
    )


def test_validate_grounded_citations(mock_patents):
    # Matches valid patents
    cites = ["ES-2849102-B2", "NON_EXISTENT_999"]
    grounded = validate_grounded_citations(cites, mock_patents)
    assert grounded == ["ES-2849102-B2"]

    # None match
    assert validate_grounded_citations(["UNKNOWN_1"], mock_patents) == []
    # Empty input
    assert validate_grounded_citations([], mock_patents) == []


def test_protocol_conformance():
    engine = SynthesisEngine()
    assert isinstance(engine, InventorAgentProtocol)
    assert isinstance(engine, AdversarialAgentProtocol)
    assert InventionSynthesisEngine is SynthesisEngine


def test_propose_candidate_unconfigured_client_fails_fast(mock_demands, mock_patents):
    engine = SynthesisEngine(llm_client=None)
    with pytest.raises(ValueError, match="LLM client not configured"):
        engine.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_propose_candidate_success(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "title": "Novel Argyrodite Electrolyte",
            "description": "Bromine-doped argyrodite with ionic conductivity >12 mS/cm.",
            "claimed_novelty": "Dual-halide substitution suppressing dendritic growth.",
        })
    )

    engine = SynthesisEngine(llm_client=client)
    candidate = engine.propose_candidate("cluster_battery", mock_demands, mock_patents)

    assert candidate.cluster_id == "cluster_battery"
    assert candidate.title == "Novel Argyrodite Electrolyte"
    assert "Dual-halide" in candidate.claimed_novelty
    assert client.chat_completion.called

    # Verify typed request was passed
    args, kwargs = client.chat_completion.call_args
    req = args[0]
    assert isinstance(req, LlmChatRequest)
    assert req.response_format == "json_object"
    assert len(req.messages) == 2


def test_propose_candidate_malformed_json_fails_fast(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(content="not valid json")

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(json.JSONDecodeError):
        engine.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_propose_candidate_missing_schema_keys_fails_fast(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({"description": "Missing title and novelty"})
    )

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(ValueError, match="LLM response failed schema validation"):
        engine.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_propose_candidate_non_dict_json_fails_fast(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(content="[1, 2, 3]")

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(ValueError, match="LLM response failed schema validation"):
        engine.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_critique_candidate_empty_prior_art(mock_candidate):
    engine = SynthesisEngine(llm_client=None)
    verdict = engine.critique_candidate(mock_candidate, prior_art=[])
    assert verdict.verdict == "survives"
    assert verdict.cited_patents == ["NONE"]


def test_critique_candidate_unconfigured_client_fails_fast(mock_candidate, mock_patents):
    engine = SynthesisEngine(llm_client=None)
    with pytest.raises(ValueError, match="LLM client not configured"):
        engine.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_success(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "verdict": "survives",
            "rationale": "Candidate exhibits distinct stoichiometry over ES-2849102-B2.",
            "cited_patents": ["ES-2849102-B2"],
        })
    )

    engine = SynthesisEngine(llm_client=client)
    verdict = engine.critique_candidate(mock_candidate, mock_patents)

    assert verdict.verdict == "survives"
    assert verdict.cited_patents == ["ES-2849102-B2"]
    assert "ES-2849102-B2" in verdict.rationale


def test_evaluate_adversarial_alias(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "verdict": "rejected",
            "rationale": "Anticipated by ES-1234567-A1.",
            "cited_patents": ["ES-1234567-A1"],
        })
    )

    engine = SynthesisEngine(llm_client=client)
    verdict = engine.evaluate_adversarial(mock_candidate, mock_patents)

    assert verdict.verdict == "rejected"
    assert verdict.cited_patents == ["ES-1234567-A1"]


def test_critique_candidate_malformed_json_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(content="invalid json output")

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(json.JSONDecodeError):
        engine.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_missing_schema_keys_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({"rationale": "Missing verdict and cited_patents"})
    )

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(ValueError, match="LLM response failed schema validation"):
        engine.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_invalid_cited_patents_type_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({"verdict": "survives", "cited_patents": "not-a-list"})
    )

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(ValueError, match="Expected cited_patents to be a list"):
        engine.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_ungrounded_citations_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "verdict": "rejected",
            "rationale": "Anticipated by hallucinated patent.",
            "cited_patents": ["US-9999999-B2"],
        })
    )

    engine = SynthesisEngine(llm_client=client)
    with pytest.raises(ValueError, match="Adversarial critique cited no valid prior art"):
        engine.critique_candidate(mock_candidate, mock_patents)
