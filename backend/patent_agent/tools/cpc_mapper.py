"""Deterministic CPC Mapper for technology call records.

Prioritizes precision over recall: assigns a CPC prefix only when high-confidence
keyword evidence exists across title, category, or description. Defaults to None when
evidence is ambiguous or absent to avoid white-space score contamination.
"""

import re

# High-precision keyword to CPC mapping rules
_CPC_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "H01M",
        re.compile(
            r"\b(battery|batteries|electrolyte|solid-state|fuel cell|cathode|anode|energy storage)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "C01B",
        re.compile(
            r"\b(inorganic|borate|silicon|halogenation|non-metallic|carbon nanotube|graphene)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "B01J",
        re.compile(
            r"\b(catalyst|catalysts|catalytic|adsorbent|chemical reactor|fermentation reactor)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "H01L",
        re.compile(
            r"\b(semiconductor|semiconductors|photovoltaic|microelectronic|wafer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "C08L",
        re.compile(
            r"\b(polymer|polymers|polypropylene|polyethylene|resin|plastics|coating|silicone|pdms|ptfe)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "G01N",
        re.compile(
            r"\b(substance detection|spectroscopy|sensor|interstitial fluid|sampling|biomarker|detection device)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "A61K",
        re.compile(
            r"\b(antibiotic|pharma|dermatological|cellular agriculture|biological sciences|gene therapy|drug delivery)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "A23L",
        re.compile(
            r"\b(food|beverage|beverages|natural color|preservative|frozen food|methyl cellulose|bivalves|mussels)\b",
            re.IGNORECASE,
        ),
    ),
]


def map_cpc_prefix(text_fields: list[str]) -> str | None:
    """Evaluate combined text fields against CPC rules.

    Returns:
        The matched CPC 4-character prefix (e.g. 'H01M'), or None if evidence is ambiguous/insufficient.
    """
    combined_text = " ".join(field for field in text_fields if field)
    if not combined_text.strip():
        return None

    matches: list[str] = []
    for cpc_prefix, pattern in _CPC_RULES:
        if pattern.search(combined_text):
            matches.append(cpc_prefix)

    # Return matched CPC prefix only if exactly one rule matched (unambiguous)
    # or return the first rule match if distinct rule categories don't conflict
    if len(matches) == 1:
        return matches[0]

    return None
