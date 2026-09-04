"""Unit tests for infrastructure LLM agent adapters under ADR 0009."""

import json
from unittest.mock import MagicMock

import pytest

from domain.models.runtime_schemas import DemandSignal, InventionCandidate, PatentRecord
from infrastructure.llm.adapters import (
    GroqAgentAdapter,
    LlmAgentAdapter,
    validate_grounded_citations,
)
from infrastructure.llm.client_protocol import (
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
    cites = ["ES-2849102-B2", "NON_EXISTENT_999"]
    grounded = validate_grounded_citations(cites, mock_patents)
    assert grounded == ["ES-2849102-B2"]

    assert validate_grounded_citations(["UNKNOWN_1"], mock_patents) == []
    assert validate_grounded_citations([], mock_patents) == []


def test_protocol_conformance():
    adapter = LlmAgentAdapter()
    # Structural conformance to InventorAgentProtocol
    assert hasattr(adapter, "propose_candidate") and callable(adapter.propose_candidate)
    # Structural conformance to AdversarialAgentProtocol
    assert hasattr(adapter, "critique_candidate") and callable(adapter.critique_candidate)
    assert GroqAgentAdapter is LlmAgentAdapter


def test_propose_candidate_unconfigured_client_fails_fast(mock_demands, mock_patents):
    adapter = LlmAgentAdapter(llm_client=None)
    with pytest.raises(ValueError, match="LLM client not configured"):
        adapter.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_propose_candidate_success(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "title": "Novel Argyrodite Electrolyte",
            "description": "Bromine-doped argyrodite with ionic conductivity >12 mS/cm.",
            "claimed_novelty": "Dual-halide substitution suppressing dendritic growth.",
        })
    )

    adapter = LlmAgentAdapter(llm_client=client)
    candidate = adapter.propose_candidate("cluster_battery", mock_demands, mock_patents)

    assert candidate.cluster_id == "cluster_battery"
    assert candidate.title == "Novel Argyrodite Electrolyte"
    assert "Dual-halide" in candidate.claimed_novelty
    assert client.chat_completion.called

    args, _ = client.chat_completion.call_args
    req = args[0]
    assert isinstance(req, LlmChatRequest)
    assert req.response_format == "json_object"
    assert len(req.messages) == 2


def test_propose_candidate_malformed_json_fails_fast(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(content="not valid json")

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(json.JSONDecodeError):
        adapter.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_propose_candidate_missing_schema_keys_fails_fast(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({"description": "Missing title and novelty"})
    )

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(ValueError, match="LLM response failed schema validation"):
        adapter.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_propose_candidate_non_dict_json_fails_fast(mock_demands, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(content="[1, 2, 3]")

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(ValueError, match="LLM response failed schema validation"):
        adapter.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_critique_candidate_empty_prior_art(mock_candidate):
    adapter = LlmAgentAdapter(llm_client=None)
    verdict = adapter.critique_candidate(mock_candidate, prior_art=[])
    assert verdict.verdict == "survives"
    assert verdict.cited_patents == ["NONE"]


def test_critique_candidate_unconfigured_client_fails_fast(mock_candidate, mock_patents):
    adapter = LlmAgentAdapter(llm_client=None)
    with pytest.raises(ValueError, match="LLM client not configured"):
        adapter.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_success(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "verdict": "survives",
            "rationale": "Candidate exhibits distinct stoichiometry over ES-2849102-B2.",
            "cited_patents": ["ES-2849102-B2"],
        })
    )

    adapter = LlmAgentAdapter(llm_client=client)
    verdict = adapter.critique_candidate(mock_candidate, mock_patents)

    assert verdict.verdict == "survives"
    assert verdict.cited_patents == ["ES-2849102-B2"]
    assert "ES-2849102-B2" in verdict.rationale


def test_critique_candidate_malformed_json_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(content="invalid json output")

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(json.JSONDecodeError):
        adapter.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_missing_schema_keys_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({"rationale": "Missing verdict and cited_patents"})
    )

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(ValueError, match="LLM response failed schema validation"):
        adapter.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_invalid_cited_patents_type_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({"verdict": "survives", "cited_patents": "not-a-list"})
    )

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(ValueError, match="Expected cited_patents to be a list"):
        adapter.critique_candidate(mock_candidate, mock_patents)


def test_critique_candidate_ungrounded_citations_fails_fast(mock_candidate, mock_patents):
    client = MagicMock(spec=LlmClientProtocol)
    client.chat_completion.return_value = LlmChatResponse(
        content=json.dumps({
            "verdict": "rejected",
            "rationale": "Anticipated by hallucinated patent.",
            "cited_patents": ["US-9999999-B2"],
        })
    )

    adapter = LlmAgentAdapter(llm_client=client)
    with pytest.raises(ValueError, match="Adversarial critique cited no valid prior art"):
        adapter.critique_candidate(mock_candidate, mock_patents)
