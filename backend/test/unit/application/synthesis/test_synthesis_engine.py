"""Unit tests for SynthesisEngine application orchestrator under ADR 0009."""

from unittest.mock import MagicMock

import pytest

from application.synthesis.synthesis_engine import SynthesisEngine
from domain.models.demand import DemandSignal
from domain.models.runtime_schemas import (
    AdversarialVerdict,
    InventionCandidate,
    PatentRecord,
)
from domain.protocols.agents import (
    AdversarialAgentProtocol,
    InventorAgentProtocol,
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
    ]


@pytest.fixture
def mock_demands() -> list[DemandSignal]:
    return [
        DemandSignal(
            source_network="innoget",
            demand_id="DEM-1",
            title="High conductivity solid electrolyte",
            description="Seeking >10 mS/cm at room temperature.",
        )
    ]


@pytest.fixture
def mock_candidate() -> InventionCandidate:
    return InventionCandidate(
        candidate_id="cand_battery_001",
        cluster_id="cluster_battery",
        title="Doped Halide-Sulfide Composite Electrolyte",
        description="A moisture-resistant composite electrolyte.",
        claimed_novelty="Synergistic halogenation.",
    )


def test_propose_candidate_unconfigured_inventor_fails_fast(mock_demands, mock_patents):
    engine = SynthesisEngine(inventor=None)
    with pytest.raises(ValueError, match="Inventor agent not configured"):
        engine.propose_candidate("cluster_battery", mock_demands, mock_patents)


def test_evaluate_adversarial_unconfigured_adversarial_fails_fast(mock_candidate, mock_patents):
    engine = SynthesisEngine(adversarial=None)
    with pytest.raises(ValueError, match="Adversarial agent not configured"):
        engine.evaluate_adversarial(mock_candidate, mock_patents)


def test_propose_candidate_delegates_to_inventor_port(mock_demands, mock_patents, mock_candidate):
    mock_inventor = MagicMock(spec=InventorAgentProtocol)
    mock_inventor.propose_candidate.return_value = mock_candidate

    engine = SynthesisEngine(inventor=mock_inventor)
    result = engine.propose_candidate("cluster_battery", mock_demands, mock_patents)

    assert result == mock_candidate
    mock_inventor.propose_candidate.assert_called_once_with(
        "cluster_battery", mock_demands, mock_patents
    )


def test_evaluate_adversarial_delegates_to_adversarial_port(mock_candidate, mock_patents):
    mock_adversarial = MagicMock(spec=AdversarialAgentProtocol)
    expected_verdict = AdversarialVerdict(
        candidate_id=mock_candidate.candidate_id,
        verdict="survives",
        rationale="Novel composition.",
        cited_patents=["ES-2849102-B2"],
    )
    mock_adversarial.critique_candidate.return_value = expected_verdict

    engine = SynthesisEngine(adversarial=mock_adversarial)
    result = engine.evaluate_adversarial(mock_candidate, mock_patents)

    assert result == expected_verdict
    mock_adversarial.critique_candidate.assert_called_once_with(mock_candidate, mock_patents)


def test_critique_candidate_alias(mock_candidate, mock_patents):
    mock_adversarial = MagicMock(spec=AdversarialAgentProtocol)
    expected_verdict = AdversarialVerdict(
        candidate_id=mock_candidate.candidate_id,
        verdict="rejected",
        rationale="Prior art anticipates.",
        cited_patents=["ES-2849102-B2"],
    )
    mock_adversarial.critique_candidate.return_value = expected_verdict

    engine = SynthesisEngine(adversarial=mock_adversarial)
    result = engine.critique_candidate(mock_candidate, mock_patents)

    assert result == expected_verdict
    mock_adversarial.critique_candidate.assert_called_once_with(mock_candidate, mock_patents)


def test_constructor_explicit_injection(mock_demands, mock_patents, mock_candidate):
    mock_inventor = MagicMock(spec=InventorAgentProtocol)
    mock_adversarial = MagicMock(spec=AdversarialAgentProtocol)

    engine = SynthesisEngine(inventor=mock_inventor, adversarial=mock_adversarial)
    assert engine.inventor is mock_inventor
    assert engine.adversarial is mock_adversarial


def test_constructor_does_not_silently_adopt_duck_typed_adversarial(mock_demands, mock_patents, mock_candidate):
    """P1 invariant test: constructor does not silently adopt an object as adversarial based on hasattr."""
    class ImpostorInventor:
        def propose_candidate(self, cluster_id, demands, prior_art):
            return mock_candidate

        # Has an attribute with the same name, but isn't explicitly injected as adversarial
        critique_candidate = "not a valid adversarial agent"

    impostor = ImpostorInventor()
    engine = SynthesisEngine(inventor=impostor)  # type: ignore[arg-type]

    assert engine.inventor is impostor
    assert engine.adversarial is None
    with pytest.raises(ValueError, match="Adversarial agent not configured"):
        engine.evaluate_adversarial(mock_candidate, mock_patents)
