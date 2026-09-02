"""Unit tests for concept-to-CPC taxonomy mapping."""

from nexus.application.landscape.cpc_taxonomy import (
    map_concept_to_cpc,
    map_demand_to_cpc,
    map_cpc_prefix,
    get_cpc_description,
)


def test_map_concept_to_cpc():
    cpc_codes = map_concept_to_cpc("solid electrolyte interphase")
    assert "H01M10/0562" in cpc_codes
    assert "H01M10/0525" in cpc_codes


def test_map_demand_to_cpc():
    prefixes = map_demand_to_cpc("Concentrated industrial detergent formulation", "Biodegradable surfactants")
    assert "C11D" in prefixes


def test_get_cpc_description():
    desc = get_cpc_description("H01M10/0562")
    assert "Solid electrolytes" in desc or "inorganic" in desc
