import random

from pydantic import BaseModel, ConfigDict, Field

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import CandidatePool, PatentCandidateEvidence
from domain.models.patent import PatentDocument


class AnnotationCandidateEntry(BaseModel):
    """One candidate as shown to an annotator: observed evidence only. Never
    carries retrieval_scores, RetrievalMethod, or ranking position (PR-E spec
    §5 contract 2 — the blind-export boundary)."""

    model_config = ConfigDict(frozen=True)

    publication_id: str
    evidence: PatentCandidateEvidence


class AnnotationBatch(BaseModel):
    """A frozen, blinded set of candidates for one demand, ready for independent
    annotation. Built once per (pool, seed) and never mutated by annotation
    (PR-E spec §9 non-negotiable statement 2)."""

    model_config = ConfigDict(frozen=True)

    demand_id: str
    demand_title: str
    demand_description: str
    seed: int
    entries: tuple[AnnotationCandidateEntry, ...] = Field(default_factory=tuple)


def build_annotation_batch(
    pool: CandidatePool,
    demand: DemandRecord | DemandSignal,
    patents_by_id: dict[str, PatentDocument],
    seed: int,
) -> AnnotationBatch:
    """Strips retrieval provenance and applies a deterministic seeded shuffle.

    Raises KeyError if a pool candidate has no corresponding patent — an
    AnnotationBatch must never silently drop or skip a pool member.
    """
    publication_ids = [c.publication_id for c in pool.candidates]
    order = list(publication_ids)
    random.Random(seed).shuffle(order)

    entries = []
    for pub_id in order:
        if pub_id not in patents_by_id:
            raise KeyError(pub_id)
        patent = patents_by_id[pub_id]
        evidence = PatentCandidateEvidence(
            publication_id=pub_id,
            publication_date=patent.publication_date,
            classifications_cpc=list(patent.classifications_cpc),
            title=patent.title,
            abstract=patent.abstract,
        )
        entries.append(AnnotationCandidateEntry(publication_id=pub_id, evidence=evidence))

    return AnnotationBatch(
        demand_id=demand.demand_id,
        demand_title=demand.title,
        demand_description=demand.description,
        seed=seed,
        entries=tuple(entries),
    )
