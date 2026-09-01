import pytest
from unittest.mock import MagicMock
from backend.patent_agent.synthesis_engine import InventionSynthesisEngine
from backend.patent_agent.tools.schemas import PatentRecord, DemandSignal, InventionCandidate, AdversarialVerdict, ScoreCard


def test_synthesis_loop_execution():
    mock_client = MagicMock()
    
    # Mock Inventor response
    mock_candidate = InventionCandidate(
        id="INV-C11D-001",
        cluster_id="C11D",
        title="Microencapsulated Cold-Water Enzyme Detergent",
        description="Liquid detergent formulation active at 15C using natural lipid nanocarriers.",
        novelty_claim="Nanocarrier protection of multi-protease complex below 20C."
    )
    # Mock Adversarial response
    mock_verdict = AdversarialVerdict(
        verdict="survives",
        rationale="Prior art ES-2849102-B2 does not disclose nanocarrier encapsulation for protease complexes.",
        cited_patents=["ES-2849102-B2"]
    )
    # Mock Governor response
    mock_scorecard = ScoreCard(
        novelty=0.91,
        prior_art_risk=0.82,
        differentiation=0.88,
        evidence=0.95,
        supporting_evidence=["ES-2849102-B2"]
    )
    
    mock_client.generate_structured.side_effect = [
        mock_candidate, mock_verdict, mock_scorecard
    ]
    
    engine = InventionSynthesisEngine(client=mock_client)
    demand = DemandSignal(source="innoget", id="d1", title="Low temp wash", description="desc", cpc_prefix="C11D", posted_date="2026-01-01", url="http://example.com")
    prior_art = [PatentRecord(publication_number="ES-2849102-B2", title="P1", abstract="A1", assignee="X", filing_date="2020-01-01", cpc_codes=["C11D"], citation_count=5)]
    
    cand, verd, score = engine.run_loop("C11D", demand, prior_art)
    assert cand.title == "Microencapsulated Cold-Water Enzyme Detergent"
    assert verd.verdict == "survives"
    assert "ES-2849102-B2" in verd.cited_patents
    assert score.novelty == 0.91
    assert mock_client.generate_structured.call_count == 3


def test_synthesis_loop_retry_on_rejection():
    mock_client = MagicMock()

    candidate_1 = InventionCandidate(
        id="INV-C11D-001",
        cluster_id="C11D",
        title="Standard Cold-Water Detergent",
        description="Liquid detergent with basic enzymes.",
        novelty_claim="Cold water wash."
    )
    verdict_1 = AdversarialVerdict(
        verdict="rejected",
        rationale="Anticipated by ES-2849102-B2 which already covers basic cold water enzymes.",
        cited_patents=["ES-2849102-B2"]
    )

    candidate_2 = InventionCandidate(
        id="INV-C11D-002",
        cluster_id="C11D",
        title="Lipid Nanocarrier Cold-Water Detergent",
        description="Enzymes encased in lipid nanocarriers active at 10C.",
        novelty_claim="Nanocarrier protection below 15C."
    )
    verdict_2 = AdversarialVerdict(
        verdict="survives",
        rationale="Nanocarrier lipid encapsulation is not disclosed in ES-2849102-B2.",
        cited_patents=["ES-2849102-B2"]
    )

    mock_scorecard = ScoreCard(
        novelty=0.94,
        prior_art_risk=0.85,
        differentiation=0.89,
        evidence=0.93,
        supporting_evidence=["ES-2849102-B2"]
    )

    mock_client.generate_structured.side_effect = [
        candidate_1, verdict_1,
        candidate_2, verdict_2,
        mock_scorecard
    ]

    engine = InventionSynthesisEngine(client=mock_client)
    demand = DemandSignal(source="innoget", id="d1", title="Low temp wash", description="desc", cpc_prefix="C11D", posted_date="2026-01-01", url="http://example.com")
    prior_art = [PatentRecord(publication_number="ES-2849102-B2", title="P1", abstract="A1", assignee="X", filing_date="2020-01-01", cpc_codes=["C11D"], citation_count=5)]

    cand, verd, score = engine.run_loop("C11D", demand, prior_art, max_iterations=2)
    assert cand.title == "Lipid Nanocarrier Cold-Water Detergent"
    assert verd.verdict == "survives"
    assert score.novelty == 0.94
    assert mock_client.generate_structured.call_count == 5


def test_synthesis_loop_max_iterations_exhausted():
    mock_client = MagicMock()

    candidate = InventionCandidate(
        id="INV-C11D-001",
        cluster_id="C11D",
        title="Attempted Detergent",
        description="Detergent formula.",
        novelty_claim="Low temperature enzyme."
    )
    verdict = AdversarialVerdict(
        verdict="rejected",
        rationale="Anticipated by ES-2849102-B2.",
        cited_patents=["ES-2849102-B2"]
    )
    scorecard = ScoreCard(
        novelty=0.30,
        prior_art_risk=0.20,
        differentiation=0.25,
        evidence=0.80,
        supporting_evidence=["ES-2849102-B2"]
    )

    # 2 iterations of reject -> then scored
    mock_client.generate_structured.side_effect = [
        candidate, verdict,
        candidate, verdict,
        scorecard
    ]

    engine = InventionSynthesisEngine(client=mock_client)
    demand = DemandSignal(source="innoget", id="d1", title="Low temp wash", description="desc", cpc_prefix="C11D", posted_date="2026-01-01", url="http://example.com")
    prior_art = [PatentRecord(publication_number="ES-2849102-B2", title="P1", abstract="A1", assignee="X", filing_date="2020-01-01", cpc_codes=["C11D"], citation_count=5)]

    cand, verd, score = engine.run_loop("C11D", demand, prior_art, max_iterations=2)
    assert verd.verdict == "rejected"
    assert mock_client.generate_structured.call_count == 5


def test_synthesis_loop_handles_empty_prior_art():
    mock_client = MagicMock()

    candidate = InventionCandidate(
        id="INV-C11D-001",
        cluster_id="C11D",
        title="Novel Solar Panel",
        description="Perovskite tandem cell.",
        novelty_claim="Tandem efficiency > 30%."
    )
    verdict = AdversarialVerdict(
        verdict="survives",
        rationale="No domestic prior art found in cluster.",
        cited_patents=["NONE"]
    )
    scorecard = ScoreCard(
        novelty=0.98,
        prior_art_risk=0.95,
        differentiation=0.90,
        evidence=0.90,
        supporting_evidence=["NONE"]
    )

    mock_client.generate_structured.side_effect = [
        candidate, verdict, scorecard
    ]

    engine = InventionSynthesisEngine(client=mock_client)
    demand = DemandSignal(source="innoget", id="d1", title="Solar cell", description="desc", cpc_prefix="H02S", posted_date="2026-01-01", url="http://example.com")

    cand, verd, score = engine.run_loop("H02S", demand, prior_art=[])
    assert cand.title == "Novel Solar Panel"
    assert verd.verdict == "survives"
    assert score.novelty == 0.98
