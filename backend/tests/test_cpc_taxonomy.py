import pytest
from backend.patent_agent.tools.cpc_taxonomy import map_demand_to_cpc, get_cpc_description, CpcTaxonomyEntry, CPC_TAXONOMY_DICTIONARY
from backend.patent_agent.tools.innoget_datasource import InnogetDemandDataSource
from backend.patent_agent.tools.schemas import DemandSignal


def test_spanish_demands_filter():
    ds = InnogetDemandDataSource()
    spanish_calls = ds.get_spanish_demands()
    assert len(spanish_calls) >= 3
    for call in spanish_calls:
        assert isinstance(call, DemandSignal)
        assert call.source == "innoget"
        assert len(call.cpc_prefix) >= 3


def test_concept_to_cpc_mapping():
    # Detergent demand -> C11D
    detergent_text = "low-temperature wash liquid detergent formulation stain removal biodegradable"
    cpcs = map_demand_to_cpc(title="Liquid Detergent", text=detergent_text)
    assert "C11D" in cpcs

    # Sink / kitchen fixture demand -> E03C / A47J
    sink_text = "kitchen sink smart touchless faucet water-saving greywater recycling"
    cpcs = map_demand_to_cpc(title="Smart Kitchen Sink", text=sink_text)
    assert any(c in cpcs for c in ["E03C", "A47J", "A47K"])

    # Energy monitoring / IoT demand -> G05B / G01R / H02J
    iot_text = "machine performance monitoring energy consumption optimization industry 4.0 IoT sensors"
    cpcs = map_demand_to_cpc(title="Energy Monitoring", text=iot_text)
    assert any(c in cpcs for c in ["G05B", "G01R", "H02J", "G06Q"])


def test_cpc_description_and_fallback():
    desc_c11d = get_cpc_description("C11D")
    assert "C11D" in desc_c11d
    assert "Detergent compositions; soap" in desc_c11d

    desc_unknown = get_cpc_description("Z99X")
    assert desc_unknown == "Z99X (General Class)"

    # Fallback to G06Q when no keywords match
    fallback_cpcs = map_demand_to_cpc(title="xyz", text="abc unrelated tokens")
    assert fallback_cpcs == ["G06Q"]
