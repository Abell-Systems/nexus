import json

import pyarrow.parquet as pq
import pytest

from application.matching.find_assets import UnknownDemandError
from infrastructure.operational.notices import NOTICES
from infrastructure.operational.service import OperationalMatchingService

from .conftest import DEMANDS, ROWS, build_operational_dir

_SCORE_KEYS = {"score", "scores", "retrieval_scores", "similarity", "band", "relevance_band", "distance"}


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


class OperationalMatchingServiceTest:
    def test_should_rank_assets_by_dense_similarity_when_demand_is_known(self, operational_dir):
        result = OperationalMatchingService.from_directory(operational_dir).matches("D-1")
        assert [a["publication_id"] for a in result["assets"]] == ["ES-1000002-U", "ES-1000003-A1", "ES-1000001-A1"]
        assert [a["rank"] for a in result["assets"]] == [1, 2, 3]

    def test_should_return_results_when_demand_has_no_posted_date(self, operational_dir):
        result = OperationalMatchingService.from_directory(operational_dir).matches("D-2")
        assert result["demand"]["demand_id"] == "D-2" and len(result["assets"]) == 3

    def test_should_not_pad_when_limit_exceeds_eligible_assets(self, operational_dir):
        result = OperationalMatchingService.from_directory(operational_dir).matches("D-1", limit=10)
        assert len(result["assets"]) == 3 and result["meta"]["eligible_count"] == 3

    def test_should_respect_limit_when_fewer_requested(self, operational_dir):
        assert len(OperationalMatchingService.from_directory(operational_dir).matches("D-1", limit=2)["assets"]) == 2

    def test_should_exclude_ep_asset_when_jurisdiction_is_not_es(self, operational_dir):
        ids = [a["publication_id"] for a in OperationalMatchingService.from_directory(operational_dir).matches("D-1")["assets"]]
        assert "EP-1000004-B1" not in ids

    def test_should_expose_holders_type_abstract_cpc_and_links_when_asset_is_returned(self, operational_dir):
        asset = OperationalMatchingService.from_directory(operational_dir).matches("D-1")["assets"][0]
        assert asset["ip_type"] == "utility_model" and asset["assignees"] == ["BETA SL"]
        assert asset["abstract"] == "Abstract two" and asset["abstract_language"] == "es"
        assert asset["source_links"]["google_patents"].endswith("ES1000002U")
        assert asset["cpc_codes"] == [] and asset["publication_date"] == "2020-02-01"

    def test_should_not_expose_any_score_like_key_when_serialising_matches_and_examples(self, operational_dir):
        service = OperationalMatchingService.from_directory(operational_dir)
        keys = set(_keys(service.matches("D-1"))) | set(_keys(service.examples()))
        assert not keys & _SCORE_KEYS

    def test_should_serve_four_fixed_notices_when_listing_examples_and_matches(self, operational_dir):
        service = OperationalMatchingService.from_directory(operational_dir)
        assert len(NOTICES) == 4
        assert service.examples()["notices"] == list(NOTICES)
        assert service.matches("D-1")["meta"]["notices"] == list(NOTICES)

    def test_should_list_example_demands_in_corpus_order_when_asked(self, operational_dir):
        demands = OperationalMatchingService.from_directory(operational_dir).examples()["demands"]
        assert [d["demand_id"] for d in demands] == ["D-1", "D-2"] and demands[0]["source_url"] == "https://example.org/d1"

    def test_should_raise_unknown_demand_when_id_is_not_offered(self, operational_dir):
        with pytest.raises(UnknownDemandError):
            OperationalMatchingService.from_directory(operational_dir).matches("D-9")

    def test_should_report_corpus_identity_when_serving_matches(self, operational_dir):
        meta = OperationalMatchingService.from_directory(operational_dir).matches("D-1")["meta"]
        assert meta["retrieval"] == "dense" and meta["corpus_id"] == "NEXUS-OPERATIONAL-CORPUS-V1"
        assert len(meta["corpus_parquet_sha256"]) == 64 and len(meta["embedding_index_sha256"]) == 64


class OperationalMatchingStartupTest:
    def test_should_abort_when_corpus_parquet_changed_after_manifest(self, operational_dir):
        pq.write_table(pq.read_table(operational_dir / "publications.parquet").slice(0, 2), operational_dir / "publications.parquet")
        with pytest.raises(ValueError, match="sha256"):
            OperationalMatchingService.from_directory(operational_dir)

    def test_should_abort_when_embeddings_were_generated_for_another_corpus(self, tmp_path):
        directory = build_operational_dir(tmp_path / "op")
        manifest_path = directory / "embeddings_patents_v1.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_sha256"]["publications.parquet"] = "00" * 32
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="corpus"):
            OperationalMatchingService.from_directory(directory)

    def test_should_abort_when_demand_snapshot_differs_from_the_embedded_demand_corpus(self, operational_dir):
        path = operational_dir / "demands_v1.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["source_sha256"] = "11" * 32
        path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ValueError, match="demand"):
            OperationalMatchingService.from_directory(operational_dir)

    def test_should_abort_when_a_served_demand_has_no_embedding(self, tmp_path):
        extra = DEMANDS + [{"demand_id": "D-3", "title": "Extra", "description": "Not embedded", "posted_date": None,
                            "origin_country": "Spain", "source_url": ""}]
        directory = build_operational_dir(tmp_path / "op", rows=ROWS, demands=extra)
        with pytest.raises(ValueError, match="D-3"):
            OperationalMatchingService.from_directory(directory)

    def test_should_abort_when_embedding_matrix_bytes_changed(self, operational_dir):
        npy = operational_dir / "embeddings_patents_v1.npy"
        npy.write_bytes(npy.read_bytes()[:-1] + b"\x01")
        with pytest.raises(ValueError, match="sha256"):
            OperationalMatchingService.from_directory(operational_dir)
