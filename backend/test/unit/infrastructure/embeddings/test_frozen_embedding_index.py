import json

import numpy as np
import pytest

from infrastructure.embeddings.frozen_embedding_index import load_index, save_index

MANIFEST_FIELDS = {
    "model_name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "model_revision": "4328cf26390c98c5e3c738b4460a05b95f4911f5",
    "generation_device": "cpu",
    "batch_size": 1,
    "library_versions": {"torch": "2.5.1+cpu"},
    "source_sha256": {"publications.parquet": "ab" * 32},
    "generation_script_path": "scripts/generate_operational_embeddings.py",
    "generation_script_commit": "deadbeef",
    "truncated_fraction": 0.25,
}


def _unit_matrix() -> np.ndarray:
    return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.6, 0.8, 0.0]], dtype=np.float32)


class FrozenEmbeddingIndexTest:
    def test_should_round_trip_ids_matrix_and_manifest_when_saved_then_loaded(self, tmp_path):
        manifest = save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix(), **MANIFEST_FIELDS)
        index = load_index(tmp_path, "emb")
        assert index.ids == ("P1", "P2", "P3")
        assert np.array_equal(index.matrix, _unit_matrix())
        assert index.manifest == manifest
        assert manifest.n_rows == 3 and manifest.embedding_dimension == 3

    def test_should_fail_load_when_matrix_bytes_changed(self, tmp_path):
        save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix(), **MANIFEST_FIELDS)
        tampered = _unit_matrix()
        tampered[0, 0] = 0.0
        tampered[0, 1] = 1.0
        np.save(tmp_path / "emb.npy", tampered, allow_pickle=False)
        with pytest.raises(ValueError, match="sha256"):
            load_index(tmp_path, "emb")

    def test_should_fail_load_when_ids_file_changed(self, tmp_path):
        save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix(), **MANIFEST_FIELDS)
        (tmp_path / "emb.ids.json").write_text(json.dumps(["P1", "P3", "P2"]), encoding="utf-8")
        with pytest.raises(ValueError, match="sha256"):
            load_index(tmp_path, "emb")

    def test_should_reject_save_when_ids_and_rows_differ_in_count(self, tmp_path):
        with pytest.raises(ValueError, match="rows"):
            save_index(tmp_path, "emb", ["P1", "P2"], _unit_matrix(), **MANIFEST_FIELDS)

    def test_should_reject_save_when_ids_are_not_unique(self, tmp_path):
        with pytest.raises(ValueError, match="unique"):
            save_index(tmp_path, "emb", ["P1", "P1", "P3"], _unit_matrix(), **MANIFEST_FIELDS)

    def test_should_reject_save_when_matrix_is_not_float32(self, tmp_path):
        with pytest.raises(ValueError, match="float32"):
            save_index(tmp_path, "emb", ["P1", "P2", "P3"], _unit_matrix().astype(np.float64), **MANIFEST_FIELDS)

    def test_should_reject_save_when_rows_are_not_unit_norm(self, tmp_path):
        matrix = _unit_matrix() * 2.0
        with pytest.raises(ValueError, match="unit norm"):
            save_index(tmp_path, "emb", ["P1", "P2", "P3"], matrix.astype(np.float32), **MANIFEST_FIELDS)

    def test_should_reject_save_when_matrix_has_non_finite_values(self, tmp_path):
        matrix = _unit_matrix()
        matrix[1, 1] = np.nan
        with pytest.raises(ValueError, match="finite"):
            save_index(tmp_path, "emb", ["P1", "P2", "P3"], matrix, **MANIFEST_FIELDS)
