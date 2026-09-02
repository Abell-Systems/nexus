"""Demand sources provider (Innoget, SBIR, CORDIS, Mock)."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any
from domain.models.runtime_schemas import DemandSignalItem


@dataclass
class MatchProvenance:
    matched_keyword: str
    target_cpc: str
    confidence: float


class InnogetDemandDataSource:
    def __init__(self, json_path: str | Path | None = None):
        if json_path is None:
            json_path = Path(__file__).parent / "innoget_demands.json"
            if not json_path.exists():
                json_path = Path("data/raw/innoget_demands.json")
        self.json_path = Path(json_path)
        self._demands = self._load_demands()

    def _load_demands(self) -> list[DemandSignalItem]:
        if not self.json_path.exists():
            return [
                DemandSignalItem(
                    source="innoget",
                    id="INNOGET-2292",
                    title="Industrial formulation for concentrated detergent",
                    description="Seeking enzymatic biodegradable surfactant formulations",
                    cpc_prefix="C11D",
                    posted_date="2023-05-15",
                    url="https://innoget.com/challenge/2292",
                )
            ]
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("demands", data) if isinstance(data, dict) else data
                return [
                    DemandSignalItem(
                        source="innoget",
                        id=d.get("id", f"INNOGET-{i}"),
                        title=d.get("title", ""),
                        description=d.get("description", ""),
                        cpc_prefix=d.get("cpc_prefix") or d.get("target_cpc_prefix", "C11D"),
                        posted_date=d.get("posted_date", "2023-01-01"),
                        url=d.get("url", ""),
                    )
                    for i, d in enumerate(items)
                ]
        except Exception:
            return []

    def get_spanish_demands(self) -> list[DemandSignalItem]:
        return self._demands

    def get_demands_for_cluster(self, cluster_id: str) -> list[DemandSignalItem]:
        return [d for d in self._demands if (d.cpc_prefix or "")[:4] == cluster_id[:4]]

    def search_demand(self, query: str = "", domain: str = "") -> list[DemandSignalItem]:
        q = query.lower()
        matched = [d for d in self._demands if q in d.title.lower() or q in d.description.lower()]
        return matched or self._demands


class SBIRDemandDataSource:
    def __init__(self):
        self.demands = [
            DemandSignalItem(
                source="sbir",
                id="SBIR-2022-001",
                title="Solid electrolyte interphase stability in solid-state lithium metal batteries",
                description="DoE solicitation for interfacial stabilization between solid electrolyte and Li anode",
                cpc_prefix="H01M",
                posted_date="2022-04-10",
                url="https://sbir.gov/node/12345",
            )
        ]

    def search_demand(self, query: str = "", domain: str = "") -> list[DemandSignalItem]:
        return self.demands


class CORDISDemandDataSource:
    def __init__(self):
        self.demands = [
            DemandSignalItem(
                source="cordis",
                id="CORDIS-958284",
                title="European Solid-State Lithium Battery Initiative",
                description="Horizon Europe grant for next-generation solid electrolyte interfaces",
                cpc_prefix="H01M",
                posted_date="2021-09-01",
                url="https://cordis.europa.eu/project/id/958284",
            )
        ]

    def search_demand(self, query: str = "", domain: str = "") -> list[DemandSignalItem]:
        return self.demands


class MockDemandDataSource:
    def __init__(self):
        self.demands = [
            DemandSignalItem(
                source="innoget",
                id="INNOGET-2292",
                title="Industrial formulation for concentrated detergent",
                description="Seeking enzymatic biodegradable surfactant formulations",
                cpc_prefix="C11D",
                posted_date="2023-05-15",
                url="https://innoget.com/challenge/2292",
            ),
            DemandSignalItem(
                source="sbir",
                id="SBIR-2022-001",
                title="Solid electrolyte interphase stability in solid-state lithium metal batteries",
                description="DoE solicitation for interfacial stabilization between solid electrolyte and Li anode",
                cpc_prefix="H01M",
                posted_date="2022-04-10",
                url="https://sbir.gov/node/12345",
            ),
        ]

    def search_demand(self, query: str = "", domain: str = "") -> list[DemandSignalItem]:
        q = query.lower()
        matched = [d for d in self.demands if q in d.title.lower() or q in d.description.lower()]
        return matched or self.demands


_DEMAND_INSTANCE = MockDemandDataSource()


def get_demand_datasource(source_type: str = "auto") -> Any:
    if source_type == "innoget" or os.getenv("DEMAND_SOURCE", "").lower() == "innoget":
        return InnogetDemandDataSource()
    if source_type == "cordis":
        return CORDISDemandDataSource()
    if source_type == "sbir":
        return SBIRDemandDataSource()
    return _DEMAND_INSTANCE
