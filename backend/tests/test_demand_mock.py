import os

os.environ.setdefault("USE_MOCK_DEMAND", "true")

from patent_agent.tools.demand_sources import MockDemandDataSource
from patent_agent.tools.schemas import DemandSignal


def test_search_demand_returns_valid_signals():
    source = MockDemandDataSource()
    signals = source.search_demand("solid electrolyte", "EV batteries", max_results=5)

    assert len(signals) == 5
    for signal in signals:
        assert isinstance(signal, DemandSignal)
        assert signal.source in ("sbir", "cordis")
        assert signal.title
        assert signal.cpc_prefix


def test_search_demand_is_deterministic():
    source = MockDemandDataSource()
    first = source.search_demand("solid electrolyte", "EV batteries", max_results=3)
    second = source.search_demand("solid electrolyte", "EV batteries", max_results=3)

    assert [s.id for s in first] == [s.id for s in second]
