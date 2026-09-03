"""Policy-driven concept-to-CPC dictionary for transparent patent taxonomy mapping.

In accordance with Section 3 of AGENTS.md, ADR 0004, and ADR 0005:
- Zero hardcoded dictionaries in code.
- Zero implicit filesystem loading or repository-relative paths.
- All taxonomy mappings and descriptions require an explicitly injected MatchingPolicyConfig.
"""

import re

from domain.models.matching import MatchingPolicyConfig


def get_cpc_description(
    cpc_code: str,
    policy: MatchingPolicyConfig,
) -> str:
    """Returns canonical description for a CPC code from the explicitly injected policy."""
    entry = policy.cpc_taxonomy_descriptions.get(cpc_code)
    if entry and "description" in entry:
        return entry["description"]
    return f"CPC Classification {cpc_code}"


def map_concept_to_cpc(
    concept_or_query: str,
    policy: MatchingPolicyConfig,
) -> list[str]:
    """Maps a concept or text query to matching CPC codes defined by the injected policy taxonomy."""
    normalized = concept_or_query.lower()
    matched_codes: list[str] = []

    for concept, cpc_list in policy.concept_to_cpc_taxonomy.items():
        pattern = r"\b" + re.escape(concept) + r"\b"
        if re.search(pattern, normalized):
            for cpc in cpc_list:
                if cpc not in matched_codes:
                    matched_codes.append(cpc)

    return matched_codes


def map_demand_to_cpc(
    demand_title: str,
    demand_description: str,
    policy: MatchingPolicyConfig,
) -> list[str]:
    """Extracts 4-character CPC subclass prefixes from demand text based on the injected policy taxonomy."""
    text = f"{demand_title} {demand_description}".lower()
    matched_prefixes: list[str] = []

    for concept, cpc_list in policy.concept_to_cpc_taxonomy.items():
        pattern = r"\b" + re.escape(concept) + r"\b"
        if re.search(pattern, text):
            for cpc in cpc_list:
                prefix = cpc[:4]
                if prefix not in matched_prefixes:
                    matched_prefixes.append(prefix)

    return matched_prefixes


def map_cpc_prefix(
    query: str,
    policy: MatchingPolicyConfig,
) -> str | None:
    """Maps query to the primary 4-character CPC prefix using the injected policy."""
    codes = map_concept_to_cpc(query, policy=policy)
    return codes[0][:4] if codes else None
