import json
from pathlib import Path

from domain.models.demand import DemandSignal
from domain.protocols.demand_repository import DemandRepository


class JsonDemandRepository(DemandRepository):
    """Reads the product demand snapshot written by scripts/build_demands_snapshot.py."""

    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.source_sha256: str = raw["source_sha256"]
        self._demands = [
            DemandSignal(
                demand_id=d["demand_id"],
                title=d["title"],
                description=d["description"],
                posted_date=d.get("posted_date"),
                origin_country=d.get("origin_country"),
                url=d.get("source_url", ""),
            )
            for d in raw["demands"]
        ]
        self._by_id = {d.demand_id: d for d in self._demands}

    def get(self, demand_id: str) -> DemandSignal | None:
        return self._by_id.get(demand_id)

    def list_all(self) -> list[DemandSignal]:
        return list(self._demands)
