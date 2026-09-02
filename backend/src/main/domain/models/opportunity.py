from pydantic import BaseModel, Field


class OpportunityScore(BaseModel):
    """Deterministic quantitative measurement of innovation gaps and saturation."""

    cluster_id: str
    score: float | None
    score_coverage: float
    components: dict[str, float | None]
    missing_components: list[str] = Field(default_factory=list)
    model_id: str
    model_version: str
    quadrant: str


class OpportunityHypothesis(BaseModel):
    """Qualitative research interpretation and candidate innovation opportunity."""

    hypothesis_id: str
    cluster_id: str
    opportunity_score: OpportunityScore
    rationale: str
    supporting_prior_art: list[str] = Field(default_factory=list)
    target_demand_ids: list[str] = Field(default_factory=list)
    status: str
