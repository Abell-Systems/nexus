import hashlib
import json
from pathlib import Path
from typing import Any

from application.matching.find_assets import RankedAsset, find_assets_for_demand, list_demand_examples
from domain.models.asset import Asset
from domain.models.demand import DemandSignal
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
from infrastructure.operational.links import source_links
from infrastructure.operational.notices import NOTICES
from infrastructure.operational.selection import parse_selection, validate_against_demands

PATENT_INDEX = "embeddings_patents_v1"
DEMAND_INDEX = "embeddings_demands_v1"


def _demand_payload(demand: DemandSignal) -> dict[str, Any]:
    return {
        "demand_id": demand.demand_id,
        "title": demand.title,
        "description": demand.description,
        "origin_country": demand.origin_country,
        "posted_date": demand.posted_date,
        "source_url": demand.url,
    }


class OperationalMatchingService:
    """Answers the two MVP routes from verified, frozen artifacts. Never embeds text at runtime."""

    def __init__(
        self,
        *,
        assets: list[Asset],
        demands: DemandRepository,
        retriever: PatentCandidateRetriever,
        policy: PatentEligibilityPolicy,
        corpus_id: str,
        corpus_sha256: str,
        embedding_index_sha256: str,
        featured_demand_ids: frozenset[str] | None = None,
    ) -> None:
        self._featured = featured_demand_ids
        self._matches_cache: dict[tuple[str, int], dict[str, Any]] = {}
        self._catalog = InMemoryAssetCatalog(assets)
        self._demands = demands
        self._retriever = retriever
        self._policy = policy
        self._meta = {
            "retrieval": "dense",
            "corpus_id": corpus_id,
            "corpus_parquet_sha256": corpus_sha256,
            "embedding_index_sha256": embedding_index_sha256,
            "notices": list(NOTICES),
        }

    @classmethod
    def from_directory(cls, directory: Path, selection_path: Path | None = None) -> "OperationalMatchingService":
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
            vectors[demand_embedding_text(demand.title, demand.description)] = demand_index.matrix[
                row_of[demand.demand_id]
            ]

        featured = cls._read_selection(selection_path, demands) if selection_path is not None else None

        policy = operational_eligibility_policy()
        retriever = NumpyDenseRetriever(
            [a.patent for a in assets], patent_index.matrix, PrecomputedEmbedder(vectors), policy
        )
        return cls(
            assets=assets,
            demands=demands,
            retriever=retriever,
            policy=policy,
            corpus_id=manifest["dataset_id"],
            corpus_sha256=corpus_sha,
            embedding_index_sha256=patent_index.manifest.matrix_sha256,
            featured_demand_ids=featured,
        )

    @staticmethod
    def _read_selection(path: Path, demands: DemandRepository) -> frozenset[str]:
        """Demo view: which demands the screen lists. The full demand set stays intact and answerable."""
        selection = parse_selection(json.loads(path.read_text(encoding="utf-8")))
        validate_against_demands(selection, {d.demand_id for d in demands.list_all()})
        return selection.included

    def examples(self) -> dict[str, Any]:
        listed = list_demand_examples(self._demands, featured=self._featured)
        return {"demands": [_demand_payload(d) for d in listed], "notices": list(NOTICES)}

    def matches(self, demand_id: str, limit: int = 5) -> dict[str, Any]:
        # Artifacts are frozen and verified at startup, so an answer never changes; keys are bounded by demands x limits.
        key = (demand_id, limit)
        if key not in self._matches_cache:
            self._matches_cache[key] = self._compute_matches(demand_id, limit)
        return self._matches_cache[key]

    def _compute_matches(self, demand_id: str, limit: int) -> dict[str, Any]:
        result = find_assets_for_demand(
            demand_id, limit, demands=self._demands, retriever=self._retriever, catalog=self._catalog, policy=self._policy
        )
        payload = _demand_payload(result.demand)
        return {
            "demand": {k: payload[k] for k in ("demand_id", "title", "description", "source_url")},
            "assets": [self._asset_payload(r) for r in result.assets],
            "meta": {**self._meta, "eligible_count": result.eligible_count},
        }

    @staticmethod
    def _asset_payload(ranked: RankedAsset) -> dict[str, Any]:
        asset = ranked.asset
        patent = asset.patent
        return {
            "rank": ranked.rank,
            "publication_id": patent.publication_id,
            "title": patent.title,
            "ip_type": asset.ip_type,
            "country_code": patent.country_code,
            "kind_code": patent.kind_code,
            "assignees": patent.assignees,
            "inventors": patent.inventors,
            "publication_date": patent.publication_date,
            "abstract": patent.abstract,
            "abstract_language": asset.abstract_language,
            "cpc_codes": patent.classifications_cpc,
            "source_links": source_links(patent.publication_id),
        }
