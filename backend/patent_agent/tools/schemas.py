"""Shared data contracts passed between agents via session state and returned by tools."""

from pydantic import BaseModel, Field


class PatentRecord(BaseModel):
    """Mirrors the fields we pull from Google Patents Public Datasets on BigQuery."""

    publication_number: str
    title: str
    abstract: str
    assignee: list[str] = Field(default_factory=list)
    inventors: list[str] = Field(default_factory=list)
    filing_date: str
    publication_date: str
    priority_date: str | None = None
    country_code: str
    cpc_codes: list[str] = Field(default_factory=list)
    family_id: str | None = None
    citation_count: int = 0
    similarity_score: float | None = None


class DemandSignal(BaseModel):
    """A market-pull signal: an open technology need/request from a demand-side source
    (e.g. SBIR/STTR solicitations, CORDIS-funded research topics)."""

    source: str  # "sbir" | "cordis"
    id: str
    title: str
    description: str
    cpc_prefix: str | None = None
    posted_date: str
    url: str


class PatentCluster(BaseModel):
    """Output of the Day 4-6 clustering FunctionTool: one technology sub-area."""

    cluster_id: str
    label: str
    representative_patents: list[str]
    patent_count: int
    white_space_score: float
    is_white_space: bool


class InventionCandidate(BaseModel):
    """A candidate invention proposed by the Inventor agent for a given white-space cluster."""

    candidate_id: str
    cluster_id: str
    title: str
    description: str
    claimed_novelty: str


class AdversarialVerdict(BaseModel):
    """The Adversarial agent's verdict on a single InventionCandidate.

    `cited_patents` is required so the verdict is always traceable to concrete
    prior art rather than an unsupported LLM judgment.
    """

    candidate_id: str
    verdict: str  # "survives" | "rejected"
    rationale: str
    cited_patents: list[str] = Field(min_length=1)


class ScoreCard(BaseModel):
    """The Innovation Governor's final score for a surviving candidate.

    Every sub-score must be backed by supporting_evidence citations — never a bare number.
    """

    candidate_id: str
    novelty: float
    prior_art_risk: float
    differentiation: float
    evidence: float
    supporting_evidence: list[str] = Field(min_length=1)
    summary: str
    scope_drift: bool = False
    drift_reason: str = ""
    obviousness_risk: str = "low"
    landscape_quality: str = "RELEVANT"
    evaluation_verdict: str = "REJECTED_ON_PRIOR_ART"


class ScoreCardList(BaseModel):
    """Governor output_schema wrapper: ADK structured output needs a single model."""

    scorecards: list[ScoreCard] = Field(min_length=1)


class AgentEventItem(BaseModel):
    """An observable event emitted during agent pipeline execution."""

    type: str
    timestamp: str
    message: str
    candidateId: str | None = None
    evidence: dict | list | str | None = None

