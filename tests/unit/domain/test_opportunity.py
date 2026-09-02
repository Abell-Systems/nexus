import pytest
from nexus.domain.models.opportunity import OpportunityScore, OpportunityHypothesis
from nexus.domain.models.demand import DemandSignal


def test_opportunity_measurement_vs_interpretation_separation():
    score = OpportunityScore(
        cluster_id="C11D",
        score=0.42,
        score_coverage=0.75,
        components={"density": 0.10, "recency": 0.60, "traction": None, "demand": 1.00},
        missing_components=["traction"],
        model_id="composite_whitespace_v1",
        model_version="1.0.0",
        quadrant="Quadrant II (Co-developed / Saturated)",
    )
    assert score.score == 0.42
    assert "traction" in score.missing_components
    assert score.components["traction"] is None
    assert score.components["demand"] == 1.00

    hypo = OpportunityHypothesis(
        hypothesis_id="HYP-C11D-001",
        cluster_id="C11D",
        opportunity_score=score,
        rationale="High demand pull with mature domestic IP base",
        supporting_prior_art=["ES-2849102-B2"],
        target_demand_ids=["INNOGET-2292"],
        status="validated",
    )
    assert hypo.hypothesis_id == "HYP-C11D-001"
    assert hypo.cluster_id == "C11D"
    assert hypo.supporting_prior_art == ["ES-2849102-B2"]
    assert hypo.target_demand_ids == ["INNOGET-2292"]
    assert hypo.status == "validated"


def test_demand_signal_model():
    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="Innoget",
        title="Sustainable Surfactants for Industrial Cleaning",
        description="Looking for bio-based surfactant formulations that degrade rapidly.",
        technical_requirements=["Biodegradable", "Non-toxic", "High surfactant efficiency"],
        origin_country="Spain",
        posted_date="2025-01-10",
        deadline_date="2025-06-30",
        classified_cpc_prefixes=["C11D", "C07C"],
    )
    assert demand.demand_id == "INNOGET-2292"
    assert demand.source_network == "Innoget"
    assert len(demand.technical_requirements) == 3
    assert demand.origin_country == "Spain"
    assert demand.classified_cpc_prefixes == ["C11D", "C07C"]


def test_demand_signal_defaults():
    demand = DemandSignal(
        demand_id="DEMAND-001",
        source_network="OpenNetwork",
        title="Title",
        description="Description",
    )
    assert demand.technical_requirements == []
    assert demand.classified_cpc_prefixes == []
    assert demand.origin_country is None
    assert demand.posted_date is None
    assert demand.deadline_date is None
