from dataclasses import dataclass

from domain.models.patent import PatentDocument


@dataclass(frozen=True)
class Asset:
    patent: PatentDocument
    ip_type: str
    abstract_language: str
