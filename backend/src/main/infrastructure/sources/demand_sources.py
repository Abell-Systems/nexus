"""Demand data sources (Innoget, SBIR, CORDIS, and Mock signals)."""

import json
import os
from pathlib import Path
from typing import Any

from domain.models.runtime_schemas import DemandSignalItem


class InnogetDemandDataSource:
    """Innoget open innovation challenges data source."""

    def __init__(self, snapshot_path: str = "data/snapshots/innoget_challenges.json"):
        self.snapshot_path = snapshot_path
        self._demands = self._load()

    def _load(self) -> list[DemandSignalItem]:
        p = Path(self.snapshot_path)
        if not p.exists():
            return [
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
                    source="innoget",
                    id="INNOGET-2415",
                    title="Optimized sink and sanitary plumbing drainage systems",
                    description="Seeking durable high-flow sanitary drainage and sink fixtures",
                    cpc_prefix="E03C",
                    posted_date="2023-09-20",
                    url="https://innoget.com/challenge/2415",
                ),
                DemandSignalItem(
                    source="innoget",
                    id="INNOGET-2501",
                    title="Industrial process automation numerical control software",
                    description="Seeking program-control algorithms for factory robotics",
                    cpc_prefix="G05B",
                    posted_date="2024-01-10",
                    url="https://innoget.com/challenge/2501",
                ),
            ]
        try:
            with open(p, encoding="utf-8") as f:
                items = json.load(f)
                return [
                    DemandSignalItem(
                        source="innoget",
                        id=d.get("id", f"INNOGET-{i}"),
                        title=d.get("title", ""),
                        description=d.get("description", ""),
                        cpc_prefix=d.get("cpc_prefix", "H01M"),
                        posted_date=d.get("posted_date", ""),
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
        d = domain.lower()
        matched = [
            item for item in self._demands
            if (not q or q in item.title.lower() or q in item.description.lower())
            and (not d or d in item.title.lower() or d in item.description.lower() or (item.cpc_prefix and d in item.cpc_prefix.lower()))
        ]
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
        q = query.lower()
        d = domain.lower()
        matched = [
            item for item in self.demands
            if (not q or q in item.title.lower() or q in item.description.lower())
            and (not d or d in item.title.lower() or d in item.description.lower() or (item.cpc_prefix and d in item.cpc_prefix.lower()))
        ]
        return matched or self.demands


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
        q = query.lower()
        d = domain.lower()
        matched = [
            item for item in self.demands
            if (not q or q in item.title.lower() or q in item.description.lower())
            and (not d or d in item.title.lower() or d in item.description.lower() or (item.cpc_prefix and d in item.cpc_prefix.lower()))
        ]
        return matched or self.demands


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
        d = domain.lower()
        matched = [
            item for item in self.demands
            if (not q or q in item.title.lower() or q in item.description.lower())
            and (not d or d in item.title.lower() or d in item.description.lower() or (item.cpc_prefix and d in item.cpc_prefix.lower()))
        ]
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
