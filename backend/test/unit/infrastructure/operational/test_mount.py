from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.operational.mount import mount_operational_mvp

API_SOURCE = Path(__file__).resolve().parents[5] / "backend" / "src" / "main" / "infrastructure" / "api.py"


class MountOperationalMvpTest:
    def test_should_mount_routes_when_artifacts_verify(self, operational_dir, selection):
        app = FastAPI()
        mount_operational_mvp(app, operational_dir, selection)
        assert TestClient(app).get("/api/matches", params={"demand_id": "D-1"}).status_code == 200

    def test_should_send_hardening_headers_when_serving_the_mvp_routes(self, operational_dir, selection):
        app = FastAPI()
        mount_operational_mvp(app, operational_dir, selection)
        headers = TestClient(app).get("/api/demand-examples").headers
        assert headers["x-content-type-options"] == "nosniff" and headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"

    def test_should_abort_startup_when_the_directory_is_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            mount_operational_mvp(FastAPI(), tmp_path / "missing")


class DemoSelectionFileTest:
    def test_should_partition_all_39_demands_exactly_once_when_reading_the_shipped_selection(self):
        import json

        path = API_SOURCE.parent / "operational" / "demo_selection_v1.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        groups = [set(doc["included"]), set(doc["borderline_excluded_by_default"]), set(doc["excluded"])]
        assert sum(len(g) for g in groups) == 39 == len(set().union(*groups))
        assert all(reason.strip() for key in ("included", "borderline_excluded_by_default", "excluded") for reason in doc[key].values())
        assert doc["rule"].strip() and len(doc["included"]) > 0

    def test_should_list_demo_journeys_only_among_included_demands_when_reading_the_shipped_selection(self):
        import json

        path = API_SOURCE.parent / "operational" / "demo_selection_v1.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        journeys = doc["demo_journeys"]
        assert 3 <= len(journeys["primary"]) <= 3 and 1 <= len(journeys["secondary"]) <= 2
        assert set(journeys["primary"]) | set(journeys["secondary"]) <= set(doc["included"])
        assert not set(journeys["primary"]) & set(journeys["secondary"])
