"""Domain taxonomy context and validation."""

from typing import Any

from domain.models.runtime_schemas import PatentCluster, PatentRecord

SUPPORTED_DOMAINS = [
    "solid_state_battery",
    "solid_state_batteries",
    "solid-state battery",
    "solid-state batteries",
    "ev_battery",
    "battery_electrolyte",
    "spanish_patents_pilot",
    "spanish_patents",
    "oepm",
    "general",
]

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "solid_state_battery": [
        "solid electrolyte",
        "sulfide",
        "garnet",
        "llzo",
        "nasicon",
        "polymer electrolyte",
        "composite electrolyte",
        "dendrite",
        "interfacial resistance",
        "critical current density",
    ],
    "spanish_patents_pilot": [
        "detergent",
        "cleaning composition",
        "sanitary",
        "sink",
        "drain",
        "control system",
        "process automation",
        "alloy",
        "composite material",
        "biopolymer",
    ],
}


def is_supported_domain(domain: str) -> bool:
    if not domain or not domain.strip():
        return False
    norm = domain.strip().lower()
    return any(norm == d or norm in d for d in SUPPORTED_DOMAINS)


def get_domain_keywords(domain: str) -> list[str]:
    norm = domain.strip().lower()
    for d_key, kws in DOMAIN_KEYWORDS.items():
        if norm == d_key or norm in d_key:
            return kws
    return DOMAIN_KEYWORDS.get("solid_state_battery", [])


def build_cluster_context(
    cluster: PatentCluster,
    patents: list[PatentRecord],
    demands: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "cluster_id": cluster.cluster_id,
        "label": cluster.label,
        "white_space_score": cluster.white_space_score,
        "is_white_space": cluster.is_white_space,
        "patent_count": len(patents),
        "patents": [p.model_dump() for p in patents],
        "demands": [d.model_dump() if hasattr(d, "model_dump") else d for d in (demands or [])],
    }
