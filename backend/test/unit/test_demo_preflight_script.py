import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY = {"corpus_id": "C-1", "corpus_parquet_sha256": "aaa", "embedding_index_sha256": "bbb"}


def _preflight():
    spec = importlib.util.spec_from_file_location("demo_preflight", REPO_ROOT / "scripts" / "demo_preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def artifacts(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"dataset_id": "C-1", "parquet_sha256": "aaa"}), encoding="utf-8")
    (tmp_path / "embeddings_patents_v1.manifest.json").write_text(json.dumps({"matrix_sha256": "bbb"}), encoding="utf-8")
    return tmp_path


def _server(preflight, *, listed=None, notices=None, assets=5, meta=None, extra=None):
    selection = preflight.parse_selection(json.loads(preflight.SELECTION.read_text(encoding="utf-8")))
    listed = sorted(selection.included) if listed is None else listed

    def get_json(path):
        if path.startswith("/api/demand-examples"):
            return {"demands": [{"demand_id": d} for d in listed], "notices": list(preflight.NOTICES) if notices is None else notices}
        return {"assets": [{"rank": i, **(extra or {})} for i in range(assets)], "meta": IDENTITY if meta is None else meta}

    return get_json


class DemoPreflightTest:
    def test_should_report_ready_when_server_matches_the_current_build(self, artifacts):
        preflight = _preflight()
        assert preflight.check(_server(preflight), artifacts) == []

    def test_should_flag_a_stale_server_when_it_lists_other_demands_or_old_notices(self, artifacts):
        preflight = _preflight()
        assert any("demands" in p for p in preflight.check(_server(preflight, listed=["X"]), artifacts))
        assert any("notices" in p for p in preflight.check(_server(preflight, notices=["old"]), artifacts))

    def test_should_flag_a_journey_that_returns_fewer_than_five_assets(self, artifacts):
        preflight = _preflight()
        assert any("expected 5" in p for p in preflight.check(_server(preflight, assets=2), artifacts))

    @pytest.mark.parametrize("field", list(IDENTITY))
    def test_should_flag_a_server_built_from_other_artifacts_even_when_everything_visible_matches(self, artifacts, field):
        preflight = _preflight()
        meta = {**IDENTITY, field: "other"}
        assert any("another build" in p for p in preflight.check(_server(preflight, meta=meta), artifacts))

    def test_should_flag_a_score_field_but_not_the_word_in_text(self, artifacts):
        preflight = _preflight()
        assert any("score" in p for p in preflight.check(_server(preflight, extra={"score": 0.9}), artifacts))
        assert preflight.check(_server(preflight, extra={"title": "score keeping device"}), artifacts) == []
