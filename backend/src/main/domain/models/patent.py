from pydantic import BaseModel, Field

from domain.models.evidence import FieldObservation


class PatentDocument(BaseModel):
    """Publication-level patent document representing a specific gazette publication."""

    publication_id: str
    country_code: str
    doc_number: str
    kind_code: str
    application_number: str | None = None
    title: str
    abstract: str
    assignees: list[str] = Field(default_factory=list)
    inventors: list[str] = Field(default_factory=list)
    filing_date: str | None = None
    publication_date: str | None = None
    priority_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    classifications_ipc: list[str] = Field(default_factory=list)
    forward_citation_count: int | None = None
    backward_citation_count: int | None = None
    family_id: str | None = None


class PatentFamily(BaseModel):
    """Metadata for a family of related patent documents sharing priority claims."""

    family_id: str
    earliest_priority_date: str | None = None
    title_consensus: str | None = None
    family_cpc_codes: list[str] = Field(default_factory=list)


class FamilyMembership(BaseModel):
    """Relational mapping linking a publication document to its family."""

    family_id: str
    publication_id: str
    membership_source: str
    evidence: FieldObservation
