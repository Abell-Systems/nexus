from functools import cache
from typing import Any

from fastapi import APIRouter, Query

from application.matching.find_assets import (
    AssetsForDemand,
    RankedAsset,
    find_assets_for_demand,
    list_demand_examples,
)
from domain.models.demand import DemandSignal
from infrastructure.operational.artifacts import OperationalArtifacts
from infrastructure.operational.links import source_links
from infrastructure.operational.notices import NOTICES

MVP_PATHS = ("/api/demand-examples", "/api/matches")


def _demand_json(demand: DemandSignal) -> dict[str, Any]:
    return {
        "demand_id": demand.demand_id,
        "title": demand.title,
        "description": demand.description,
        "origin_country": demand.origin_country,
        "posted_date": demand.posted_date,
        "source_url": demand.url,
    }


def _asset_json(ranked: RankedAsset) -> dict[str, Any]:
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


def build_router(artifacts: OperationalArtifacts, featured: frozenset[str] | None = None) -> APIRouter:
    router = APIRouter()

    # Artifacts are frozen and verified at startup, so an answer never changes; keys are bounded by demands x limits.
    @cache
    def find(demand_id: str, limit: int) -> AssetsForDemand:
        return find_assets_for_demand(
            demand_id,
            limit,
            demands=artifacts.demands,
            retriever=artifacts.retriever,
            catalog=artifacts.catalog,
            policy=artifacts.policy,
        )

    @router.get("/api/demand-examples")
    def demand_examples() -> dict[str, Any]:
        listed = list_demand_examples(artifacts.demands, featured=featured)
        return {"demands": [_demand_json(d) for d in listed], "notices": list(NOTICES)}

    @router.get("/api/matches")
    def matches(
        demand_id: str = Query(..., min_length=1, max_length=64),
        limit: int = Query(5, ge=1, le=10),
    ) -> dict[str, Any]:
        result = find(demand_id, limit)
        demand = _demand_json(result.demand)
        return {
            "demand": {k: demand[k] for k in ("demand_id", "title", "description", "source_url")},
            "assets": [_asset_json(r) for r in result.assets],
            "meta": {
                "retrieval": "dense",
                **artifacts.identity,
                "eligible_count": result.eligible_count,
                "notices": list(NOTICES),
            },
        }

    return router
