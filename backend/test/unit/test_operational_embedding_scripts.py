import importlib.util
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtractOperationalTextsTest:
    def test_should_keep_parquet_row_order_and_embed_all_demands_when_building_sources(self, tmp_path):
        parquet = tmp_path / "publications.parquet"
        pq.write_table(
            pa.table(
                {
                    "publication_number": ["ES-2-A1", "ES-1-A1"],
                    "title": ["Titulo B", "Titulo A"],
                    "abstract": ["Resumen B", "Resumen A"],
                }
            ),
            parquet,
        )
        demands = tmp_path / "demands.json"
        demands.write_text(
            json.dumps(
                {
                    "demands": [
                        {"demand_id": "D-2", "title": "Two", "description": "second"},
                        {"demand_id": "D-1", "title": "One", "description": "first"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        sources = _load_script("extract_operational_texts").build_sources(parquet, demands)

        assert sources["patent_ids"] == ["ES-2-A1", "ES-1-A1"]
        assert sources["patent_texts"] == ["Titulo B Resumen B", "Titulo A Resumen A"]
        assert sources["demand_ids"] == ["D-2", "D-1"]
        assert sources["demand_texts"] == ["Two second", "One first"]
        assert set(sources["source_sha256"]) == {"publications.parquet", "demand_corpus_n39"}
        assert all(len(v) == 64 for v in sources["source_sha256"].values())
