"""Deterministic concept-to-CPC dictionary for transparent patent taxonomy mapping."""

import re
from dataclasses import dataclass

CPC_H01M10_0562 = "H01M10/0562"
CPC_H01M10_0525 = "H01M10/0525"
CPC_H01M10_0565 = "H01M10/0565"
CPC_H01M4_13 = "H01M4/13"
CPC_C11D1_00 = "C11D1/00"
CPC_C11D3_386 = "C11D3/386"
CPC_E03C1_00 = "E03C1/00"
CPC_G05B19_00 = "G05B19/00"
CPC_C22C1_00 = "C22C1/00"


@dataclass
class CpcTaxonomyEntry:
    cpc_code: str
    subclass_title: str
    description: str


CPC_TAXONOMY_DICTIONARY: dict[str, CpcTaxonomyEntry] = {
    CPC_H01M10_0562: CpcTaxonomyEntry(CPC_H01M10_0562, "Solid electrolytes", "Solid state inorganic electrolytes including sulfides and oxides"),
    CPC_H01M10_0525: CpcTaxonomyEntry(CPC_H01M10_0525, "Lithium secondary batteries", "Secondary batteries with lithium ion chemistry"),
    CPC_H01M10_0565: CpcTaxonomyEntry(CPC_H01M10_0565, "Polymeric electrolytes", "Solid or gel polymer electrolyte membranes"),
    CPC_H01M4_13: CpcTaxonomyEntry(CPC_H01M4_13, "Electrodes", "Electrodes for secondary lithium batteries"),
    CPC_C11D1_00: CpcTaxonomyEntry(CPC_C11D1_00, "Detergent compositions", "Surface-active agent formulations for cleaning"),
    CPC_C11D3_386: CpcTaxonomyEntry(CPC_C11D3_386, "Enzymatic detergents", "Detergent compositions containing enzymes"),
    CPC_E03C1_00: CpcTaxonomyEntry(CPC_E03C1_00, "Sanitary plumbing", "Plumbing fixtures, wash-basins, and drainage systems"),
    CPC_G05B19_00: CpcTaxonomyEntry(CPC_G05B19_00, "Program-control systems", "Industrial process automation and numerical control"),
    CPC_C22C1_00: CpcTaxonomyEntry(CPC_C22C1_00, "Alloys", "Non-ferrous and ferrous metallurgical alloy compositions"),
}

CPC_TAXONOMY_MAP: dict[str, list[str]] = {
    "solid electrolyte": [CPC_H01M10_0562, CPC_H01M10_0525, CPC_H01M4_13],
    "solid-state battery": [CPC_H01M10_0562, CPC_H01M10_0525, "H01M10/058"],
    "sulfide electrolyte": [CPC_H01M10_0562, CPC_H01M10_0525, "C01B17/00"],
    "oxide electrolyte": [CPC_H01M10_0562, CPC_H01M10_0525, "C04B35/00"],
    "polymer electrolyte": [CPC_H01M10_0565, CPC_H01M10_0525, "C08L1/00"],
    "lithium anode": ["H01M4/134", "H01M4/382", "H01M10/052"],
    "battery separator": ["H01M50/40", CPC_H01M10_0525],
    "interfacial layer": [CPC_H01M10_0562, "H01M4/02", "H01M4/62"],
    
    # Spanish National Pilot domains
    "detergent": [CPC_C11D1_00, "C11D3/00", "C11D7/00"],
    "cleaning composition": [CPC_C11D1_00, CPC_C11D3_386],
    "surfactant": ["C11D1/02", "C11D1/66", "B01F17/00"],
    "sanitary": [CPC_E03C1_00, "E03D1/00", "A47K1/00"],
    "sink": ["E03C1/18", "E03C1/33"],
    "drain": ["E03C1/22", "E03C1/26"],
    "control system": [CPC_G05B19_00, "G05B15/02", "G05B13/02"],
    "industrial control": ["G05B19/05", "G05B19/418"],
    "process automation": ["G05B19/418", "G05B17/02"],
    "alloy": [CPC_C22C1_00, "C22C9/00", "C22C19/00"],
    "metallic composition": ["C22C1/02", "C22C5/00"],
    "high-strength steel": ["C22C38/00", "C21D8/00"],
    "composite material": ["C08L1/00", "C08K3/00", "C08J5/00"],
    "biopolymer": ["C08L67/04", "C08L1/02", "C08B37/00"],
    "power grid": ["H02J3/00", "H02J13/00", "H02J7/00"],
    "energy storage system": ["H02J7/00", "H02J15/00", CPC_H01M10_0525],
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
