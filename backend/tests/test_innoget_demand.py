from patent_agent.tools.innoget_datasource import InnogetDemandDataSource, MatchProvenance
from patent_agent.tools.schemas import DemandSignal


def test_innoget_demand_source_returns_valid_signals():
    ds = InnogetDemandDataSource()
    signals = ds.search_demand(query="coating", domain="materials", max_results=5)

    assert isinstance(signals, list)
    assert len(signals) > 0
    for s in signals:
        assert isinstance(s, DemandSignal)
        assert s.source == "innoget"
        assert s.id.startswith("innoget-")
        assert s.url.startswith("https://")


def test_innoget_demand_source_ranking_is_deterministic():
    ds = InnogetDemandDataSource()
    res1 = ds.search_demand(query="coating", domain="materials", max_results=5)
    res2 = ds.search_demand(query="coating", domain="materials", max_results=5)

    assert [s.id for s in res1] == [s.id for s in res2]


def test_innoget_demand_source_match_provenance():
    ds = InnogetDemandDataSource()
    results_with_provenance = ds.search_demand_with_provenance(query="cellular agriculture", domain="food", max_results=5)

    assert len(results_with_provenance) > 0
    signal, provenance = results_with_provenance[0]
    assert isinstance(signal, DemandSignal)
    assert isinstance(provenance, MatchProvenance)
    assert provenance.score > 0
    assert len(provenance.matched_fields) > 0


def test_innoget_demand_source_searches_text_field():
    ds = InnogetDemandDataSource()
    # Search for terms present in the body text of Innoget calls
    results = ds.search_demand_with_provenance(query="depuration decontamination", domain="marine", max_results=5)

    assert len(results) > 0
    signal, provenance = results[0]
    assert "text" in provenance.matched_fields

