"""#104 dense retrieval diagnostic, step 1a: extracts the plain (id, text)
pairs generate_dense_embeddings.py needs, from the frozen corpora -- runs in
the MAIN backend venv (has duckdb), so the isolated
.venv-embedding-generation stack (verified in
docs/phase2-ted-dense-retrieval-diagnostic-contract.md SS7 checkpoint 2)
never needs duckdb/pandas/pyarrow added to it.

Same 30 Dev demand_ids + same 63-patent corpus already used by BM25/CPC/
CPV -- no new text sources, no filtering, no curation.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

import duckdb  # noqa: E402


def extract(
    devtest_split_path: Path,
    demand_corpus_path: Path,
    corpus_parquet_glob: str,
    corpus_sha256_path: Path,
    out_path: Path,
) -> None:
    split = json.loads(devtest_split_path.read_text(encoding="utf-8"))
    dev_ids: list[str] = split["dev"]

    demand_corpus_bytes = demand_corpus_path.read_bytes()
    demand_corpus_sha256 = hashlib.sha256(demand_corpus_bytes).hexdigest()
    demand_corpus = json.loads(demand_corpus_bytes)
    by_id = {d["demand_id"]: d for d in demand_corpus["demands"]}

    missing = [d for d in dev_ids if d not in by_id]
    if missing:
        raise ValueError(f"Dev demand_ids not found in demand corpus: {missing}")

    demand_texts = [f"{by_id[d]['title']} {by_id[d]['description_text']}" for d in dev_ids]

    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE patents AS
        SELECT DISTINCT ON (publication_id) publication_id, title, abstract
        FROM read_parquet('{corpus_parquet_glob}')
        ORDER BY publication_id
    """)
    rows = con.execute("SELECT publication_id, title, abstract FROM patents").fetchall()
    con.close()

    patent_ids = [r[0] for r in rows]
    patent_texts = [f"{r[1] or ''} {r[2] or ''}" for r in rows]

    patent_corpus_sha256 = corpus_sha256_path.read_text(encoding="utf-8").strip().split()[0]

    payload = {
        "purpose": "Plain (id, text) source for experiments/phase2/generate_dense_embeddings.py -- no embeddings computed here.",
        "n_demands": len(dev_ids),
        "n_patents": len(patent_ids),
        "demand_corpus_sha256": demand_corpus_sha256,
        "patent_corpus_sha256": patent_corpus_sha256,
        "demand_ids": dev_ids,
        "demand_texts": demand_texts,
        "patent_ids": patent_ids,
        "patent_texts": patent_texts,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}: {len(dev_ids)} demands, {len(patent_ids)} patents")


def main() -> int:
    extract(
        devtest_split_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_devtest_split_v1.json",
        demand_corpus_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json",
        corpus_parquet_glob=str(REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "*.parquet"),
        corpus_sha256_path=REPO_ROOT / "data" / "raw" / "oepm_invenes_corpus_v1.sha256",
        out_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_source_texts.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
