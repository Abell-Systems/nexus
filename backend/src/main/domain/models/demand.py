from pydantic import BaseModel, Field


class DemandSignal(BaseModel):
    """External technological demand or market challenge signal."""

    demand_id: str
    source_network: str
    title: str
    description: str
    technical_requirements: list[str] = Field(default_factory=list)
    origin_country: str | None = None
    posted_date: str | None = None
    deadline_date: str | None = None
    classified_cpc_prefixes: list[str] = Field(default_factory=list)
