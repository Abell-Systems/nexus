"""Shared data contracts passed between agents and returned by API endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PatentRecord(BaseModel):
    """Mirrors the fields pulled from Patent Datasources (BigQuery, DuckDB, OEPM, EPO)."""
    model_config = ConfigDict(extra="allow")

    publication_number: str
    title: str
    abstract: str
    assignee: list[str] | str = Field(default_factory=list)
    inventors: list[str] = Field(default_factory=list)
    filing_date: str
    publication_date: str = ""
    priority_date: str | None = None
    country_code: str = "ES"
    cpc_codes: list[str] = Field(default_factory=list)
    citation_count: int | None = None
    backward_citation_count: int | None = None
    similarity_score: float | None = None


class PatentCluster(BaseModel):
    """One technology sub-area cluster with white space metrics."""
    cluster_id: str
    label: str
    representative_patents: list[str]
    patent_count: int
    white_space_score: float
    is_white_space: bool


class InventionCandidate(BaseModel):
    """A candidate invention proposed for a given white-space cluster."""
    candidate_id: str = ""
    id: str | None = None
    cluster_id: str
    title: str
    description: str
    claimed_novelty: str = ""
    novelty_claim: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            c_id = data.get("candidate_id") or data.get("id") or ""
            data.setdefault("candidate_id", c_id)
            data.setdefault("id", c_id)
            nov = data.get("novelty_claim") or data.get("claimed_novelty") or ""
            data.setdefault("claimed_novelty", nov)
            data.setdefault("novelty_claim", nov)
        return data


class AdversarialVerdict(BaseModel):
    """Adversarial agent's verdict on an InventionCandidate."""
    candidate_id: str = ""
    verdict: str  # "survives" | "rejected"
    rationale: str
    cited_patents: list[str] = Field(min_length=1)


class ScoreCard(BaseModel):
    """Innovation Governor scorecard for a candidate."""
    candidate_id: str = ""
    novelty: float
    prior_art_risk: float
    differentiation: float
    evidence: float
    supporting_evidence: list[str] = Field(min_length=1)


class AgentEventItem(BaseModel):
    """Structured progress event emitted by agents during execution."""
    agent: str
    stage: str
    status: str
    title: str
    timestamp: str
    detail: str | None = None
    items: list[dict[str, Any]] | None = None
