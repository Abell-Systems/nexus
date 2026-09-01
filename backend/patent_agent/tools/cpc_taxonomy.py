"""CPC Taxonomy and Deterministic Concept-to-CPC Mapping Rules."""

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CpcTaxonomyEntry:
    cpc_prefix: str  # e.g., 'C11D'
    section: str     # e.g., 'C' (Chemistry)
    subclass: str    # e.g., 'Detergent Compositions'
    keywords: tuple[str, ...]

# Curated WIPO/EPO concordance dictionary for cross-referencing industry demands
CPC_TAXONOMY_DICTIONARY: dict[str, CpcTaxonomyEntry] = {
    "C11D": CpcTaxonomyEntry("C11D", "C", "Detergent compositions; soap", (
        "detergent", "laundry", "wash", "cleaning", "surfactant", "stain", "biodegradable"
    )),
    "E03C": CpcTaxonomyEntry("E03C", "E", "Sanitary plumbing installations; sinks; basins", (
        "sink", "faucet", "kitchen sink", "basin", "plumbing", "water-saving", "greywater"
    )),
    "A47J": CpcTaxonomyEntry("A47J", "A", "Kitchen equipment; cooking vessels", (
        "kitchen", "appliance", "countertop", "cooking"
    )),
    "G05B": CpcTaxonomyEntry("G05B", "G", "Monitoring, testing and control systems", (
        "monitoring", "control", "sensor", "energy consumption", "industry 4.0", "automation", "efficiency"
    )),
    "G01R": CpcTaxonomyEntry("G01R", "G", "Measuring electric variables", (
        "power monitoring", "electric measurement", "energy management"
    )),
    "H02J": CpcTaxonomyEntry("H02J", "H", "Circuit arrangements for power supply/distribution", (
        "power grid", "energy storage", "smart grid", "power distribution"
    )),
    "C22C": CpcTaxonomyEntry("C22C", "C", "Alloys; ferrous and non-ferrous metallurgy", (
        "alloy", "brass", "lead-free", "machinability", "metallurgy", "bronze"
    )),
    "H01M": CpcTaxonomyEntry("H01M", "H", "Processes/means for electrochemical power generation", (
        "battery", "electrolyte", "solid-state", "cathode", "anode", "cell"
    )),
}

def map_demand_to_cpc(title: str, text: str, min_keyword_matches: int = 1) -> list[str]:
    """Deterministically map text and title concepts to valid CPC subclasses."""
    combined = (title + " " + text).lower()
    matched_scores: list[tuple[str, int]] = []

    for prefix, entry in CPC_TAXONOMY_DICTIONARY.items():
        score = 0
        for kw in entry.keywords:
            if kw in combined:
                # Title matches have higher weight
                weight = 3 if kw in title.lower() else 1
                score += weight
        if score >= min_keyword_matches:
            matched_scores.append((prefix, score))

    matched_scores.sort(key=lambda x: -x[1])
    return [prefix for prefix, _ in matched_scores] if matched_scores else ["G06Q"]

def get_cpc_description(cpc_prefix: str) -> str:
    entry = CPC_TAXONOMY_DICTIONARY.get(cpc_prefix.upper())
    return f"{entry.cpc_prefix} ({entry.subclass})" if entry else f"{cpc_prefix} (General Class)"
