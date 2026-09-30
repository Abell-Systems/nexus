from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.operational.mount import mount_operational_mvp

API_SOURCE = Path(__file__).resolve().parents[5] / "backend" / "src" / "main" / "infrastructure" / "api.py"


def _paths(app):
    return {getattr(r, "path", None) for r in app.routes}


class MountOperationalMvpTest:
    def test_should_not_mount_routes_when_flag_is_unset(self, monkeypatch):
        monkeypatch.delenv("NEXUS_MVP_ENABLED", raising=False)
        app = FastAPI()
        assert mount_operational_mvp(app) is False
        assert "/api/matches" not in _paths(app)

    def test_should_mount_routes_when_flag_is_set_and_artifacts_verify(self, monkeypatch, operational_dir):
        monkeypatch.setenv("NEXUS_MVP_ENABLED", "1")
        monkeypatch.setenv("NEXUS_OPERATIONAL_DIR", str(operational_dir))
        selection = operational_dir / "selection.json"
        selection.write_text('{"included": {"D-1": "x", "D-2": "x"}}', encoding="utf-8")
        monkeypatch.setenv("NEXUS_DEMO_SELECTION", str(selection))
        app = FastAPI()
        assert mount_operational_mvp(app) is True
        assert TestClient(app).get("/api/matches", params={"demand_id": "D-1"}).status_code == 200

    def test_should_abort_startup_when_flag_is_set_and_directory_is_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NEXUS_MVP_ENABLED", "1")
        monkeypatch.setenv("NEXUS_OPERATIONAL_DIR", str(tmp_path / "missing"))
        with pytest.raises(FileNotFoundError):
            mount_operational_mvp(FastAPI())

    def test_should_mount_before_the_spa_catch_all_route_in_api_module(self):
        source = API_SOURCE.read_text(encoding="utf-8")
        assert "mount_operational_mvp(app)" in source
        assert source.index("mount_operational_mvp(app)") < source.index('@app.get("/{full_path:path}")')


class DemoSelectionFileTest:
    def test_should_partition_all_39_demands_exactly_once_when_reading_the_shipped_selection(self):
        import json

        path = API_SOURCE.parent / "operational" / "demo_selection_v1.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        groups = [set(doc["included"]), set(doc["borderline_excluded_by_default"]), set(doc["excluded"])]
        assert sum(len(g) for g in groups) == 39 == len(set().union(*groups))
        assert all(reason.strip() for key in ("included", "borderline_excluded_by_default", "excluded") for reason in doc[key].values())
        assert doc["rule"].strip() and len(doc["included"]) > 0
