"""Canonical CPC Taxonomy and Deterministic Concept-to-CPC Mapping Rules.

Unified mapping engine combining regex patterns and WIPO/EPO concordance dictionary.
Used across all demand signal sources, landscape clusterers, and empirical experiments.
"""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class CpcTaxonomyEntry:
    cpc_prefix: str  # e.g., 'C11D'
    section: str     # e.g., 'C' (Chemistry)
    subclass: str    # e.g., 'Detergent Compositions'
    keywords: tuple[str, ...]
    regex_pattern: Optional[re.Pattern[str]] = None


# Curated WIPO/EPO concordance dictionary for cross-referencing industry demands
CPC_TAXONOMY_DICTIONARY: dict[str, CpcTaxonomyEntry] = {
    # Section A: Human Necessities
    "A47J": CpcTaxonomyEntry(
        "A47J", "A", "Kitchen equipment; cooking vessels",
        ("kitchen", "appliance", "countertop", "cooking", "sink accessories"),
        re.compile(r"\b(kitchen appliance|kitchen equipment|cooking vessel|culinary)\b", re.IGNORECASE)
    ),
    "A61K": CpcTaxonomyEntry(
        "A61K", "A", "Preparations for medical, dental, or toilet purposes",
        ("antibiotic", "pharma", "dermatological", "cellular agriculture", "biological sciences", "gene therapy", "drug delivery"),
        re.compile(r"\b(antibiotic|pharma|dermatological|cellular agriculture|gene therapy|drug delivery)\b", re.IGNORECASE)
    ),
    "A23L": CpcTaxonomyEntry(
        "A23L", "A", "Foods, foodstuffs, or non-alcoholic beverages",
        ("food", "beverage", "beverages", "natural color", "preservative", "frozen food", "methyl cellulose", "bivalves", "mussels"),
        re.compile(r"\b(food|beverage|beverages|natural color|preservative|frozen food|methyl cellulose|bivalves|mussels)\b", re.IGNORECASE)
    ),

    # Section B: Performing Operations; Transporting
    "B01J": CpcTaxonomyEntry(
        "B01J", "B", "Chemical or physical processes, e.g. catalysis, colloid chemistry",
        ("catalyst", "catalysts", "catalytic", "adsorbent", "chemical reactor", "fermentation reactor", "microencapsulation"),
        re.compile(r"\b(catalyst|catalysts|catalytic|adsorbent|chemical reactor|fermentation reactor)\b", re.IGNORECASE)
    ),
    "B23B": CpcTaxonomyEntry(
        "B23B", "B", "Turning; boring; machining",
        ("machining", "microdrilling", "microturning", "chip evacuation", "cutting tool", "lathe"),
        re.compile(r"\b(microdrilling|microturning|chip evacuation|lathe|turning tool)\b", re.IGNORECASE)
    ),

    # Section C: Chemistry; Metallurgy
    "C11D": CpcTaxonomyEntry(
        "C11D", "C", "Detergent compositions; soap",
        ("detergent", "laundry", "wash", "cleaning", "surfactant", "stain", "biodegradable", "soap"),
        re.compile(r"\b(detergent|laundry|surfactant|stain removal|low-temperature wash|cleaning composition)\b", re.IGNORECASE)
    ),
    "C01B": CpcTaxonomyEntry(
        "C01B", "C", "Non-metallic elements; compounds thereof",
        ("inorganic", "borate", "silicon", "halogenation", "non-metallic", "carbon nanotube", "graphene"),
        re.compile(r"\b(inorganic|borate|silicon|halogenation|non-metallic|carbon nanotube|graphene)\b", re.IGNORECASE)
    ),
    "C08L": CpcTaxonomyEntry(
        "C08L", "C", "Compositions of macromolecular compounds",
        ("polymer", "polymers", "polypropylene", "polyethylene", "resin", "plastics", "coating", "silicone", "pdms", "ptfe"),
        re.compile(r"\b(polymer|polymers|polypropylene|polyethylene|resin|plastics|coating|silicone|pdms|ptfe)\b", re.IGNORECASE)
    ),
    "C22C": CpcTaxonomyEntry(
        "C22C", "C", "Alloys; ferrous and non-ferrous metallurgy",
        ("alloy", "brass", "lead-free", "machinability", "metallurgy", "bronze", "copper", "nickel silver"),
        re.compile(r"\b(lead-free brass|metallurgy|nickel silver|bronze alloy)\b", re.IGNORECASE)
    ),

    # Section E: Fixed Constructions
    "E03C": CpcTaxonomyEntry(
        "E03C", "E", "Sanitary plumbing installations; sinks; basins",
        ("sink", "faucet", "kitchen sink", "basin", "plumbing", "water-saving", "greywater", "sanitary"),
        re.compile(r"\b(sanitary plumbing|faucet|greywater recycling|sanitary basin)\b", re.IGNORECASE)
    ),

    # Section G: Physics; Electricity; Control
    "G05B": CpcTaxonomyEntry(
        "G05B", "G", "Monitoring, testing and control systems",
        ("monitoring", "control", "sensor", "energy consumption", "industry 4.0", "automation", "efficiency", "machine performance"),
        re.compile(r"\b(energy consumption monitoring|industry 4\.0|cyber-physical|process control|automation system)\b", re.IGNORECASE)
    ),
    "G01R": CpcTaxonomyEntry(
        "G01R", "G", "Measuring electric variables",
        ("power monitoring", "electric measurement", "energy management", "nilm", "smart meter"),
        re.compile(r"\b(power monitoring|electric measurement|energy management|nilm|smart meter)\b", re.IGNORECASE)
    ),
    "G01N": CpcTaxonomyEntry(
        "G01N", "G", "Investigating or analyzing materials by determining their chemical or physical properties",
        ("substance detection", "spectroscopy", "sensor", "interstitial fluid", "sampling", "biomarker", "detection device"),
        re.compile(r"\b(substance detection|spectroscopy|sensor|interstitial fluid|sampling|biomarker|detection device)\b", re.IGNORECASE)
    ),

    # Section H: Electricity
    "H01M": CpcTaxonomyEntry(
        "H01M", "H", "Processes/means for electrochemical power generation",
        ("battery", "electrolyte", "solid-state", "cathode", "anode", "cell", "fuel cell", "energy storage"),
        re.compile(r"\b(battery|batteries|electrolyte|solid-state|fuel cell|cathode|anode|energy storage)\b", re.IGNORECASE)
    ),
    "H01L": CpcTaxonomyEntry(
        "H01L", "H", "Semiconductor devices; electric solid state devices",
        ("semiconductor", "semiconductors", "photovoltaic", "microelectronic", "wafer"),
        re.compile(r"\b(semiconductor|semiconductors|photovoltaic|microelectronic|wafer)\b", re.IGNORECASE)
    ),
    "H02J": CpcTaxonomyEntry(
        "H02J", "H", "Circuit arrangements for power supply/distribution",
        ("power grid", "energy storage", "smart grid", "power distribution", "load management"),
        re.compile(r"\b(power grid|smart grid|power distribution|load management)\b", re.IGNORECASE)
    ),
}


def map_demand_to_cpc(title: str, text: str, min_keyword_matches: int = 1) -> list[str]:
    """Deterministically map text and title concepts to valid CPC subclasses.
    
    Returns ranked list of CPC subclass prefixes by match confidence.
    """
    combined = (title + " " + text).lower()
    matched_scores: list[tuple[str, int]] = []

    for prefix, entry in CPC_TAXONOMY_DICTIONARY.items():
        score = 0
        
        # 1. Regex high-precision match (weight = 5)
        if entry.regex_pattern and entry.regex_pattern.search(combined):
            score += 5
            
        # 2. Keyword matches
        for kw in entry.keywords:
            if kw in combined:
                weight = 3 if kw in title.lower() else 1
                score += weight
                
        if score >= min_keyword_matches:
            matched_scores.append((prefix, score))

    matched_scores.sort(key=lambda x: -x[1])
    return [prefix for prefix, _ in matched_scores] if matched_scores else ["G06Q"]


def map_cpc_prefix(text_fields: list[str]) -> str | None:
    """Canonical single-prefix high-precision mapper.
    
    Returns:
        The unambiguous matched CPC 4-character prefix (e.g. 'H01M'),
        or None if evidence is ambiguous, absent, or conflicting.
    """
    combined_text = " ".join(field for field in text_fields if field)
    if not combined_text.strip():
        return None

    matches: list[str] = []
    for prefix, entry in CPC_TAXONOMY_DICTIONARY.items():
        if entry.regex_pattern and entry.regex_pattern.search(combined_text):
            matches.append(prefix)

    # Return matched prefix only if exactly one rule matched (unambiguous)
    if len(matches) == 1:
        return matches[0]

    return None


def get_cpc_description(cpc_prefix: str) -> str:
    """Return human-readable title for a CPC subclass."""
    entry = CPC_TAXONOMY_DICTIONARY.get(cpc_prefix.upper())
    return f"{entry.cpc_prefix} ({entry.subclass})" if entry else f"{cpc_prefix} (General Class)"
