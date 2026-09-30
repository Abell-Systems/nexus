import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildDemandsSnapshotTest:
    def test_should_keep_corpus_order_and_copy_text_verbatim_when_building_snapshot(self, tmp_path):
        corpus = tmp_path / "demands.json"
        corpus.write_text(
            json.dumps(
                {
                    "demands": [
                        {"demand_id": "D-2", "title": "Two", "description": "second\nline", "posted_date": None,
                         "origin_country": "Spain", "provenance": {"source_uri": "https://x.org/2"}},
                        {"demand_id": "D-1", "title": "One", "description": "first", "posted_date": None,
                         "origin_country": "ES", "provenance": {}},
                    ]
                }
            ),
            encoding="utf-8",
        )

        snapshot = _load_script("build_demands_snapshot").build_snapshot(corpus)

        assert [d["demand_id"] for d in snapshot["demands"]] == ["D-2", "D-1"]
        assert snapshot["demands"][0]["description"] == "second\nline"
        assert snapshot["demands"][0]["source_url"] == "https://x.org/2"
        assert snapshot["demands"][1]["source_url"] == ""
        assert len(snapshot["source_sha256"]) == 64
