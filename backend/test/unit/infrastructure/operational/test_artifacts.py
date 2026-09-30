import json

import numpy as np
import pyarrow.parquet as pq
import pytest

from infrastructure.embeddings.frozen_embedding_index import save_index
from infrastructure.operational.artifacts import load_operational_artifacts

from .conftest import DEMANDS, ROWS, _fields, build_operational_dir


class LoadOperationalArtifactsIdentityTest:
    def test_should_report_corpus_and_index_identity_when_artifacts_verify(self, operational_dir):
        identity = load_operational_artifacts(operational_dir).identity
        assert identity["corpus_id"] == "NEXUS-OPERATIONAL-CORPUS-V1"
        assert len(identity["corpus_parquet_sha256"]) == 64 and len(identity["embedding_index_sha256"]) == 64


class LoadOperationalArtifactsStartupTest:
    def test_should_abort_when_corpus_parquet_changed_after_manifest(self, operational_dir):
        pq.write_table(pq.read_table(operational_dir / "publications.parquet").slice(0, 2), operational_dir / "publications.parquet")
        with pytest.raises(ValueError, match="sha256"):
            load_operational_artifacts(operational_dir)

    def test_should_abort_when_embeddings_were_generated_for_another_corpus(self, tmp_path):
        directory = build_operational_dir(tmp_path / "op")
        manifest_path = directory / "embeddings_patents_v1.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_sha256"]["publications.parquet"] = "00" * 32
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="corpus"):
            load_operational_artifacts(directory)

    def test_should_abort_when_demand_snapshot_differs_from_the_embedded_demand_corpus(self, operational_dir):
        path = operational_dir / "demands_v1.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["source_sha256"] = "11" * 32
        path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ValueError, match="demand"):
            load_operational_artifacts(operational_dir)

    def test_should_abort_when_a_served_demand_has_no_embedding(self, tmp_path):
        extra = DEMANDS + [{"demand_id": "D-3", "title": "Extra", "description": "Not embedded", "posted_date": None,
                            "origin_country": "Spain", "source_url": ""}]
        directory = build_operational_dir(tmp_path / "op", rows=ROWS, demands=extra)
        with pytest.raises(ValueError, match="D-3"):
            load_operational_artifacts(directory)

    def test_should_abort_when_embedding_matrix_bytes_changed(self, operational_dir):
        npy = operational_dir / "embeddings_patents_v1.npy"
        npy.write_bytes(npy.read_bytes()[:-1] + b"\x01")
        with pytest.raises(ValueError, match="sha256"):
            load_operational_artifacts(operational_dir)


class LoadOperationalArtifactsConsistencyTest:
    def test_should_abort_when_a_demand_text_was_edited_after_the_snapshot_was_built(self, operational_dir):
        path = operational_dir / "demands_v1.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["demands"][0]["title"] = raw["demands"][0]["title"] + " (edited)"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ValueError, match="texts"):
            load_operational_artifacts(operational_dir)

    def test_should_abort_when_snapshot_has_no_texts_hash(self, operational_dir):
        path = operational_dir / "demands_v1.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        del raw["texts_sha256"]
        path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ValueError, match="texts"):
            load_operational_artifacts(operational_dir)

    def test_should_abort_when_patent_and_demand_indexes_come_from_different_models(self, operational_dir):
        path = operational_dir / "embeddings_demands_v1.manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["model_revision"] = "other-revision"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="model"):
            load_operational_artifacts(operational_dir)

    def test_should_abort_at_startup_when_index_dimensions_differ(self, operational_dir):
        parquet_sha = json.loads((operational_dir / "manifest.json").read_text(encoding="utf-8"))["parquet_sha256"]
        three_d = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float32)
        save_index(operational_dir, "embeddings_demands_v1", ["D-1", "D-2"], three_d, **_fields(parquet_sha))
        with pytest.raises(ValueError, match="dimension"):
            load_operational_artifacts(operational_dir)
