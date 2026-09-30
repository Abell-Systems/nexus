from typing import Any

from fastapi import APIRouter, HTTPException, Query

from application.matching.find_assets import UnknownDemandError
from infrastructure.operational.service import OperationalMatchingService


def build_router(service: OperationalMatchingService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/demand-examples")
    def demand_examples() -> dict[str, Any]:
        return service.examples()

    @router.get("/api/matches")
    def matches(
        demand_id: str = Query(..., min_length=1),
        limit: int = Query(5, ge=1, le=10),
    ) -> dict[str, Any]:
        try:
            return service.matches(demand_id, limit)
        except UnknownDemandError as err:
            raise HTTPException(status_code=404, detail=f"Demand '{demand_id}' not found.") from err

    return router
