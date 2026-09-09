import hashlib
import json
import random
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import Candidate, CandidatePool, EligibilityReason, PatentCandidateEvidence
from domain.models.patent import PatentDocument
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy

# ADR 0018 pilot benchmark fixture. Declared verbatim: computed via
# sha256sum data/evaluation/dataset_pilot_benchmark.json (verified against the
# real file, not guessed).
EXPECTED_PILOT_BENCHMARK_SHA256 = "bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453"


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


def generate_blinded_annotation_set(
    benchmark_path: Path,
    temporal_pool_mode: str = "strict",
    seed: int = 42,
    expected_sha256: str | None = EXPECTED_PILOT_BENCHMARK_SHA256,
) -> BlindedAnnotationSet:
    """Loads the benchmark dataset, enforces fail-fast validations on SHA-256 and temporal policy,
    evaluates candidates under strict eligibility (ADR 0018), and produces the canonical BlindedAnnotationSet.

    Temporal eligibility (t_pub < t_demand) is decided exclusively by
    DefaultPatentEligibilityPolicy.evaluate() -- never re-implemented here.
    """
    if temporal_pool_mode != "strict":
        raise ValueError(
            f"PR-E.1 contract requires temporal_pool_mode must be 'strict', got '{temporal_pool_mode}'"
        )

    path = Path(benchmark_path)
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark dataset file not found: {path}")

    content_bytes = path.read_bytes()
    computed_sha256 = hashlib.sha256(content_bytes).hexdigest()
    if expected_sha256 and computed_sha256 != expected_sha256:
        raise ValueError(
            f"Benchmark SHA-256 digest mismatch. Expected {expected_sha256}, got {computed_sha256}"
        )

    data = json.loads(content_bytes.decode("utf-8"))
    dataset_id = data.get("dataset_id")
    if not dataset_id:
        raise ValueError("Benchmark JSON is missing 'dataset_id'")

    policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")

    patents_by_id: dict[str, PatentDocument] = {}
    for p_raw in data.get("patents", []):
        doc = PatentDocument(
            publication_id=p_raw["publication_id"],
            country_code=p_raw.get("country_code", p_raw["publication_id"].split("-")[0]),
            doc_number=p_raw.get("doc_number", p_raw["publication_id"].split("-")[1]),
            kind_code=p_raw.get("kind_code", p_raw["publication_id"].split("-")[2]),
            title=p_raw.get("title", ""),
            abstract=p_raw.get("abstract", ""),
            publication_date=p_raw.get("publication_date"),
            classifications_cpc=p_raw.get("classifications_cpc", []),
        )
        patents_by_id[doc.publication_id] = doc

    demands_batches: list[AnnotationBatch] = []
    for d_raw in data.get("demands", []):
        demand = DemandSignal(
            demand_id=d_raw["demand_id"],
            title=d_raw["title"],
            description=d_raw["description"],
            posted_date=d_raw.get("posted_date"),
        )

        eligible_candidates: list[Candidate] = []
        for pub_id, patent in patents_by_id.items():
            eligibility = policy.evaluate(patent, demand)
            if eligibility.is_eligible and eligibility.reason == EligibilityReason.ELIGIBLE:
                eligible_candidates.append(Candidate(publication_id=pub_id, retrieval_scores={}))

        pool = CandidatePool(demand_id=demand.demand_id, candidates=eligible_candidates)
        batch = build_annotation_batch(pool, demand, patents_by_id, seed=seed)
        demands_batches.append(batch)

    return BlindedAnnotationSet(
        schema_version="1.0.0",
        dataset_id=dataset_id,
        dataset_sha256=computed_sha256,
        temporal_pool_mode=temporal_pool_mode,
        seed=seed,
        demands=demands_batches,
    )


def export_temporal_provenance(temporal_reasons: dict[str, EligibilityReason]) -> str:
    """ADR 0019 §5: eligibility provenance (ELIGIBLE / TEMPORAL_UNKNOWN) for later
    PR-F admissibility analysis. Kept completely separate from AnnotationBatch /
    AnnotationCandidateEntry — this is never annotator-facing and must never cross
    the blind-export boundary those models define."""
    return json.dumps({pub_id: reason.value for pub_id, reason in temporal_reasons.items()})
