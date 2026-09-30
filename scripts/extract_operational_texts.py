"""Step 1 of 2 for the operational embeddings: plain-JSON texts for the isolated generation venv.

Runs in the main backend venv (it has pyarrow). The isolated generation environment has neither
pyarrow nor DuckDB, so it reads this JSON instead of the Parquet corpus.

All 39 demands of the n39 corpus are embedded (a superset of the 31 probe demands); excluding the
8 Lab Test demands is the probe's job, not this script's.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

import pyarrow.parquet as pq  # noqa: E402

from infrastructure.embeddings.embedding_texts import demand_embedding_text, patent_embedding_text  # noqa: E402

DEFAULT_PARQUET = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1" / "publications.parquet"
DEFAULT_DEMANDS = (
    REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data" / "dataset_phase2_demand_corpus_n39.json"
)
DEFAULT_OUT = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1" / "embedding_sources_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_sources(parquet_path: Path, demand_corpus_path: Path) -> dict:
    rows = pq.read_table(parquet_path, columns=["publication_number", "title", "abstract"]).to_pylist()
    demands = json.loads(demand_corpus_path.read_text(encoding="utf-8"))["demands"]
    return {
        "patent_ids": [str(r["publication_number"]) for r in rows],
        "patent_texts": [patent_embedding_text(str(r["title"] or ""), str(r["abstract"] or "")) for r in rows],
        "demand_ids": [d["demand_id"] for d in demands],
        "demand_texts": [demand_embedding_text(d["title"], d["description"]) for d in demands],
        "source_sha256": {
            "publications.parquet": _sha256(parquet_path),
            "demand_corpus_n39": _sha256(demand_corpus_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract texts for the operational embedding generation")
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--demands", type=Path, default=DEFAULT_DEMANDS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    sources = build_sources(args.parquet, args.demands)
    args.out.write_text(json.dumps(sources, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out}: {len(sources['patent_ids'])} patents, {len(sources['demand_ids'])} demands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
