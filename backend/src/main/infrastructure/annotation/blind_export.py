import json
import random

from pydantic import BaseModel, ConfigDict, Field

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import CandidatePool, EligibilityReason, PatentCandidateEvidence
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


class BlindedAnnotationSet(BaseModel):
    """Canonical multi-demand blinded annotation set. Built once per (benchmark, policy, seed)
    and completely deterministic without timestamps or scores."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_sha256: str = Field(min_length=64, max_length=64)
    temporal_pool_mode: str = Field(min_length=1)
    seed: int
    demands: list[AnnotationBatch] = Field(default_factory=list)


def build_annotation_batch(
    pool: CandidatePool,
    demand: DemandRecord | DemandSignal,
    patents_by_id: dict[str, PatentDocument],
    seed: int,
) -> AnnotationBatch:
    """Strips retrieval provenance and applies a deterministic seeded shuffle.

    Pre-sorts publication IDs alphabetically before shuffling to guarantee bit-for-bit
    reproducibility regardless of the order candidates were inserted into the pool.

    Raises KeyError if a pool candidate has no corresponding patent — an
    AnnotationBatch must never silently drop or skip a pool member.
    """
    order = sorted([c.publication_id for c in pool.candidates])
    # Deterministic reproducible shuffle for annotation-batch ordering, not
    # security-sensitive. Rule python:S2245 is suppressed project-wide via
    # sonar-project.properties; inline NOSONAR does not work for this rule.
    random.Random(seed).shuffle(order)

    entries = []
    for pub_id in order:
        if pub_id not in patents_by_id:
            raise KeyError(pub_id)
        patent = patents_by_id[pub_id]
        # Deliberately NOT publication_date: PR-E spec §4 defines the annotator-
        # facing evidence as title/abstract/CPC only. Annotators grade technical
        # relevance, not temporal/prior-art eligibility (that's evaluated
        # separately by AnnotationPoolEligibilityPolicy, ADR 0019, and never
        # shown here) -- exposing publication_date would let an annotator's
        # relevance judgment be contaminated by reasoning about eligibility,
        # exactly the two-axis conflation this PR's architecture keeps apart.
        evidence = PatentCandidateEvidence(
            publication_id=pub_id,
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


def export_temporal_provenance(temporal_reasons: dict[str, EligibilityReason]) -> str:
    """ADR 0019 §5: eligibility provenance (ELIGIBLE / TEMPORAL_UNKNOWN) for later
    PR-F admissibility analysis. Kept completely separate from AnnotationBatch /
    AnnotationCandidateEntry — this is never annotator-facing and must never cross
    the blind-export boundary those models define."""
    return json.dumps({pub_id: reason.value for pub_id, reason in temporal_reasons.items()})
