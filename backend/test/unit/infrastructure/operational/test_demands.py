import json

from infrastructure.operational.demands import JsonDemandRepository


def _write(tmp_path):
    path = tmp_path / "demands_v1.json"
    path.write_text(
        json.dumps(
            {
                "source_sha256": "ab" * 32,
                "demands": [
                    {"demand_id": "D-1", "title": "One", "description": "first", "posted_date": None,
                     "origin_country": "Spain", "source_url": "https://x.org/1"},
                    {"demand_id": "D-2", "title": "Two", "description": "second", "posted_date": None,
                     "origin_country": "Spain", "source_url": ""},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


class JsonDemandRepositoryTest:
    def test_should_list_demands_in_file_order_when_loaded(self, tmp_path):
        repository = JsonDemandRepository(_write(tmp_path))
        assert [d.demand_id for d in repository.list_all()] == ["D-1", "D-2"]

    def test_should_return_demand_with_source_url_when_id_is_known(self, tmp_path):
        demand = JsonDemandRepository(_write(tmp_path)).get("D-1")
        assert demand is not None and demand.url == "https://x.org/1" and demand.posted_date is None

    def test_should_return_none_when_id_is_unknown(self, tmp_path):
        assert JsonDemandRepository(_write(tmp_path)).get("D-9") is None

    def test_should_expose_source_hash_when_loaded(self, tmp_path):
        assert JsonDemandRepository(_write(tmp_path)).source_sha256 == "ab" * 32
