import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _preflight():
    spec = importlib.util.spec_from_file_location("demo_preflight", REPO_ROOT / "scripts" / "demo_preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _server(preflight, *, listed=None, notices=None, assets=5):
    selection = preflight.parse_selection(json.loads(preflight.SELECTION.read_text(encoding="utf-8")))
    listed = sorted(selection.included) if listed is None else listed

    def get_json(path):
        if path.startswith("/api/demand-examples"):
            return {"demands": [{"demand_id": d} for d in listed], "notices": list(preflight.NOTICES) if notices is None else notices}
        return {"assets": [{"rank": i} for i in range(assets)]}

    return get_json


class DemoPreflightTest:
    def test_should_report_ready_when_server_matches_the_current_build(self):
        preflight = _preflight()
        assert preflight.check(_server(preflight)) == []

    def test_should_flag_a_stale_server_when_it_lists_other_demands_or_old_notices(self):
        preflight = _preflight()
        assert any("demands" in p for p in preflight.check(_server(preflight, listed=["X"])))
        assert any("notices" in p for p in preflight.check(_server(preflight, notices=["old"])))

    def test_should_flag_a_journey_that_returns_fewer_than_five_assets(self):
        preflight = _preflight()
        assert any("expected 5" in p for p in preflight.check(_server(preflight, assets=2)))
