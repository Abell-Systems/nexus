"""Deterministic concept-to-CPC dictionary for transparent patent taxonomy mapping."""

import re
from dataclasses import dataclass


@dataclass
class CpcTaxonomyEntry:
    cpc_code: str
    subclass_title: str
    description: str


CPC_TAXONOMY_DICTIONARY: dict[str, CpcTaxonomyEntry] = {
    "H01M10/0562": CpcTaxonomyEntry("H01M10/0562", "Solid electrolytes", "Solid state inorganic electrolytes including sulfides and oxides"),
    "H01M10/0525": CpcTaxonomyEntry("H01M10/0525", "Lithium secondary batteries", "Secondary batteries with lithium ion chemistry"),
    "H01M10/0565": CpcTaxonomyEntry("H01M10/0565", "Polymeric electrolytes", "Solid or gel polymer electrolyte membranes"),
    "H01M4/13": CpcTaxonomyEntry("H01M4/13", "Electrodes", "Electrodes for secondary lithium batteries"),
    "C11D1/00": CpcTaxonomyEntry("C11D1/00", "Detergent compositions", "Surface-active agent formulations for cleaning"),
    "C11D3/386": CpcTaxonomyEntry("C11D3/386", "Enzymatic detergents", "Detergent compositions containing enzymes"),
    "E03C1/00": CpcTaxonomyEntry("E03C1/00", "Sanitary plumbing", "Plumbing fixtures, wash-basins, and drainage systems"),
    "G05B19/00": CpcTaxonomyEntry("G05B19/00", "Program-control systems", "Industrial process automation and numerical control"),
    "C22C1/00": CpcTaxonomyEntry("C22C1/00", "Alloys", "Non-ferrous and ferrous metallurgical alloy compositions"),
}

CPC_TAXONOMY_MAP: dict[str, list[str]] = {
    "solid electrolyte": ["H01M10/0562", "H01M10/0525", "H01M4/13"],
    "solid-state battery": ["H01M10/0562", "H01M10/0525", "H01M10/058"],
    "sulfide electrolyte": ["H01M10/0562", "H01M10/0525", "C01B17/00"],
    "oxide electrolyte": ["H01M10/0562", "H01M10/0525", "C04B35/00"],
    "polymer electrolyte": ["H01M10/0565", "H01M10/0525", "C08L1/00"],
    "lithium anode": ["H01M4/134", "H01M4/382", "H01M10/052"],
    "battery separator": ["H01M50/40", "H01M10/0525"],
    "interfacial layer": ["H01M10/0562", "H01M4/02", "H01M4/62"],
    
    # Spanish National Pilot domains
    "detergent": ["C11D1/00", "C11D3/00", "C11D7/00"],
    "cleaning composition": ["C11D1/00", "C11D3/386"],
    "surfactant": ["C11D1/02", "C11D1/66", "B01F17/00"],
    "sanitary": ["E03C1/00", "E03D1/00", "A47K1/00"],
    "sink": ["E03C1/18", "E03C1/33"],
    "drain": ["E03C1/22", "E03C1/26"],
    "control system": ["G05B19/00", "G05B15/02", "G05B13/02"],
    "industrial control": ["G05B19/05", "G05B19/418"],
    "process automation": ["G05B19/418", "G05B17/02"],
    "alloy": ["C22C1/00", "C22C9/00", "C22C19/00"],
    "metallic composition": ["C22C1/02", "C22C5/00"],
    "high-strength steel": ["C22C38/00", "C21D8/00"],
    "composite material": ["C08L1/00", "C08K3/00", "C08J5/00"],
    "biopolymer": ["C08L67/04", "C08L1/02", "C08B37/00"],
    "power grid": ["H02J3/00", "H02J13/00", "H02J7/00"],
    "energy storage system": ["H02J7/00", "H02J15/00", "H01M10/0525"],
}


def get_cpc_description(cpc_code: str) -> str:
    entry = CPC_TAXONOMY_DICTIONARY.get(cpc_code)
    return entry.description if entry else f"CPC Classification {cpc_code}"


def map_concept_to_cpc(concept_or_query: str) -> list[str]:
    normalized = concept_or_query.lower()
    matched_codes: list[str] = []

    for concept, cpc_list in CPC_TAXONOMY_MAP.items():
        pattern = r"\b" + re.escape(concept) + r"\b"
        if re.search(pattern, normalized):
            for cpc in cpc_list:
                if cpc not in matched_codes:
                    matched_codes.append(cpc)

    return matched_codes


def map_demand_to_cpc(demand_title: str, demand_description: str = "") -> list[str]:
    text = f"{demand_title} {demand_description}".lower()
    matched_prefixes: list[str] = []

    for concept, cpc_list in CPC_TAXONOMY_MAP.items():
        pattern = r"\b" + re.escape(concept) + r"\b"
        if re.search(pattern, text):
            for cpc in cpc_list:
                prefix = cpc[:4]
                if prefix not in matched_prefixes:
                    matched_prefixes.append(prefix)

    return matched_prefixes


def map_cpc_prefix(query: str) -> str | None:
    codes = map_concept_to_cpc(query)
    return codes[0][:4] if codes else None
