import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from domain.protocols.asset_catalog import AssetCatalog
from domain.protocols.demand_repository import DemandRepository
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy
from infrastructure.embeddings.embedding_texts import demand_embedding_text, texts_sha256
from infrastructure.embeddings.frozen_embedding_index import load_index
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder
from infrastructure.matching.numpy_dense import NumpyDenseRetriever
from infrastructure.matching.operational_corpus import (
    InMemoryAssetCatalog,
    load_operational_assets,
    operational_eligibility_policy,
)
from infrastructure.operational.demands import JsonDemandRepository

PATENT_INDEX = "embeddings_patents_v1"
DEMAND_INDEX = "embeddings_demands_v1"


@dataclass(frozen=True)
class OperationalArtifacts:
    """The verified, frozen artifacts behind the MVP, wired to the ports the use cases need."""

    catalog: AssetCatalog
    demands: DemandRepository
    retriever: PatentCandidateRetriever
    policy: PatentEligibilityPolicy
    identity: dict[str, str]


def load_operational_artifacts(directory: Path) -> OperationalArtifacts:
    """Loads the artifacts, aborting with ValueError on any hash or consistency mismatch."""
    parquet = directory / "publications.parquet"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    corpus_sha = hashlib.sha256(parquet.read_bytes()).hexdigest()
    if corpus_sha != manifest["parquet_sha256"]:
        raise ValueError("publications.parquet sha256 does not match manifest.json")

    assets = load_operational_assets(parquet)
    patent_index = load_index(directory, PATENT_INDEX)
    demand_index = load_index(directory, DEMAND_INDEX)
    if patent_index.ids != tuple(a.patent.publication_id for a in assets):
        raise ValueError("Patent embedding ids are not aligned with the corpus row order")
    if patent_index.manifest.source_sha256.get("publications.parquet") != corpus_sha:
        raise ValueError("Patent embeddings were generated for a different corpus")

    demands = JsonDemandRepository(directory / "demands_v1.json")
    if demand_index.manifest.source_sha256.get("demand_corpus_n39") != demands.source_sha256:
        raise ValueError("Demand snapshot does not match the demand corpus the embeddings were built from")

    texts = [demand_embedding_text(d.title, d.description) for d in demands.list_all()]
    if demands.texts_sha256 is None or texts_sha256(texts) != demands.texts_sha256:
        raise ValueError("Demand texts do not match the texts hash recorded in the demand snapshot")

    patent_manifest, demand_manifest = patent_index.manifest, demand_index.manifest
    if (patent_manifest.model_name, patent_manifest.model_revision) != (
        demand_manifest.model_name,
        demand_manifest.model_revision,
    ):
        raise ValueError("Patent and demand embeddings come from different models")
    if patent_manifest.embedding_dimension != demand_manifest.embedding_dimension:
        raise ValueError("Patent and demand embeddings have different dimension")

    row_of = {demand_id: row for row, demand_id in enumerate(demand_index.ids)}
    vectors: dict[str, Any] = {}
    for demand in demands.list_all():
        if demand.demand_id not in row_of:
            raise ValueError(f"Demand {demand.demand_id} has no frozen embedding")
        vectors[demand_embedding_text(demand.title, demand.description)] = demand_index.matrix[row_of[demand.demand_id]]

    policy = operational_eligibility_policy()
    retriever = NumpyDenseRetriever([a.patent for a in assets], patent_index.matrix, PrecomputedEmbedder(vectors), policy)
    return OperationalArtifacts(
        catalog=InMemoryAssetCatalog(assets),
        demands=demands,
        retriever=retriever,
        policy=policy,
        identity={
            "corpus_id": manifest["dataset_id"],
            "corpus_parquet_sha256": corpus_sha,
            "embedding_index_sha256": patent_manifest.matrix_sha256,
        },
    )
