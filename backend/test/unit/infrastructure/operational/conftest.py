import hashlib
import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from infrastructure.embeddings.embedding_texts import demand_embedding_text, texts_sha256
from infrastructure.embeddings.frozen_embedding_index import save_index

DEMANDS = [
    {"demand_id": "D-1", "title": "Lighter vehicles", "description": "Seeking new materials", "posted_date": None,
     "origin_country": "Spain", "source_url": "https://example.org/d1"},
    {"demand_id": "D-2", "title": "Water sensors", "description": "Cheap sensing", "posted_date": None,
     "origin_country": "Spain", "source_url": "https://example.org/d2"},
]
DEMAND_SOURCE_SHA = "cd" * 32
# id, country, kind, ip_type, title, abstract, language, assignees, inventors, cpc, filing, publication, family
ROWS = [
    ("ES-1000001-A1", "ES", "A1", "patent", "Title one", "Abstract one", "es", ["ACME SA"], ["ANA"], ["B60K1/00"], "2019-01-01", "2020-01-01", "F1"),
    ("ES-1000002-U", "ES", "U", "utility_model", "Title two", "Abstract two", "es", ["BETA SL"], [], [], "2019-02-01", "2020-02-01", "F2"),
    ("ES-1000003-A1", "ES", "A1", "patent", "Title three", "Abstract three", "en", ["GAMMA SA"], ["LUIS"], ["G01N1/00"], "2019-03-01", "2030-03-01", "F3"),
    ("EP-1000004-B1", "EP", "B1", "patent", "Title four", "Abstract four", "en", ["DELTA SA"], [], [], "2019-04-01", "2020-04-01", "F4"),
]
PATENT_VECTORS = [[1.0, 0.0], [0.0, 1.0], [0.6, 0.8], [1.0, 0.0]]
DEMAND_VECTORS = {"D-1": [0.0, 1.0], "D-2": [1.0, 0.0]}


def _table(rows):
    cols = ["publication_number", "country_code", "kind_code", "ip_type", "title", "abstract",
            "abstract_language", "assignees", "inventors", "cpc_codes", "filing_date", "publication_date", "family_id"]
    return pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)})


def _fields(parquet_sha):
    return {
        "model_name": "test-model", "model_revision": "rev", "generation_device": "cpu", "batch_size": 1,
        "library_versions": {}, "generation_script_path": "scripts/x.py", "generation_script_commit": "abc",
        "truncated_fraction": 0.0,
        "source_sha256": {"publications.parquet": parquet_sha, "demand_corpus_n39": DEMAND_SOURCE_SHA},
    }


def build_operational_dir(directory, *, rows=ROWS, demands=DEMANDS):
    directory.mkdir(parents=True, exist_ok=True)
    parquet = directory / "publications.parquet"
    pq.write_table(_table(rows), parquet)
    sha = hashlib.sha256(parquet.read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(
        json.dumps({"dataset_id": "NEXUS-OPERATIONAL-CORPUS-V1", "parquet_sha256": sha}), encoding="utf-8"
    )
    (directory / "demands_v1.json").write_text(
        json.dumps({
            "source_sha256": DEMAND_SOURCE_SHA,
            "texts_sha256": texts_sha256([demand_embedding_text(d["title"], d["description"]) for d in demands]),
            "demands": demands,
        }), encoding="utf-8"
    )
    save_index(directory, "embeddings_patents_v1", [r[0] for r in rows],
               np.array(PATENT_VECTORS, dtype=np.float32), **_fields(sha))
    save_index(directory, "embeddings_demands_v1", list(DEMAND_VECTORS),
               np.array(list(DEMAND_VECTORS.values()), dtype=np.float32), **_fields(sha))
    return directory


@pytest.fixture
def operational_dir(tmp_path):
    return build_operational_dir(tmp_path / "operational")


@pytest.fixture
def selection(operational_dir):
    path = operational_dir / "selection.json"
    path.write_text('{"rule": "r", "included": {"D-1": "x", "D-2": "x"}}', encoding="utf-8")
    return path
