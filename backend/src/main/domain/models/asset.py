from dataclasses import dataclass

from domain.models.patent import PatentDocument


@dataclass(frozen=True)
class Asset:
    """An industrial-property asset the product can offer: the publication plus its type and abstract language."""

    patent: PatentDocument
    ip_type: str
    abstract_language: str
