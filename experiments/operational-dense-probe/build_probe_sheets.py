"""Builds the blinded judging sheets for the pre-registered probe. Spec sections 7.1-7.5.

Usage: python experiments/operational-dense-probe/build_probe_sheets.py [--out-dir outputs]
Requires the operational embeddings (Task 7) and the operational corpus snapshot.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402

from domain.models.demand import DemandSignal  # noqa: E402
from infrastructure.embeddings.embedding_texts import demand_embedding_text  # noqa: E402
from infrastructure.embeddings.frozen_embedding_index import load_index  # noqa: E402
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder  # noqa: E402
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402
from infrastructure.matching.numpy_dense import NumpyDenseRetriever  # noqa: E402
from infrastructure.matching.operational_corpus import load_operational_patents  # noqa: E402

CORPUS_DIR = dp.REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1"
LAB_DATA = dp.REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data"
DEFAULT_OUT = Path(__file__).resolve().parent / "outputs"
SHEET_COLUMNS = ["pair_id", "demand_title", "demand_description", "patent_title", "patent_abstract",
                 "abstract_language", "grade", "note"]


def probe_demands() -> list[DemandSignal]:
    corpus = json.loads((LAB_DATA / "dataset_phase2_demand_corpus_n39.json").read_text(encoding="utf-8"))["demands"]
    test_ids = set(json.loads((LAB_DATA / "devtest_split_n18_v2.json").read_text(encoding="utf-8"))["test"])
    selected = [d for d in corpus if d["demand_id"] not in test_ids]
    if len(corpus) - len(selected) != len(test_ids):
        raise ValueError("Not all Lab Test demand ids were found in the n39 corpus")
    return [
        DemandSignal(
            demand_id=d["demand_id"], title=d["title"], description=d["description"],
            posted_date=d.get("posted_date"), origin_country=d.get("origin_country"),
        )
        for d in selected
    ]


def _write_sheet(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build blinded judging sheets for the dense probe")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    parquet = CORPUS_DIR / "publications.parquet"
    patents = load_operational_patents(parquet)
    language_by_id = {
        r["publication_number"]: r["abstract_language"]
        for r in pq.read_table(parquet, columns=["publication_number", "abstract_language"]).to_pylist()
    }
    patent_index = load_index(CORPUS_DIR, "embeddings_patents_v1")
    demand_index = load_index(CORPUS_DIR, "embeddings_demands_v1")
    if patent_index.ids != tuple(p.publication_id for p in patents):
        raise ValueError("Embedding ids are not aligned with the corpus parquet row order")

    demands = probe_demands()
    demand_vectors = {
        demand_embedding_text(d.title, d.description): demand_index.matrix[demand_index.ids.index(d.demand_id)]
        for d in demands
    }
    policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    dense = NumpyDenseRetriever(patents, patent_index.matrix, PrecomputedEmbedder(demand_vectors), policy)

    con = duckdb.connect()
    con.execute(
        "CREATE TABLE patents AS SELECT publication_number, country_code, kind_code, title, abstract, "
        f"publication_date FROM read_parquet('{parquet}')"
    )
    bm25 = DuckDbBM25Retriever(con, eligibility_policy=policy)

    methods: dict[str, dict[str, list[str]]] = {}
    eligible_sizes: dict[str, int] = {}
    for demand in demands:
        methods[demand.demand_id] = {
            "bm25": [c.publication_id for c in bm25.retrieve(demand, limit=dp.TOP_K)],
            "dense": [c.publication_id for c in dense.retrieve(demand, limit=dp.TOP_K)],
        }
        eligible_sizes[demand.demand_id] = sum(1 for p in patents if policy.evaluate(p, demand).is_eligible)

    ordered = dp.blind_order(dp.union_pairs(
        {d: m["bm25"] for d, m in methods.items()}, {d: m["dense"] for d, m in methods.items()}
    ))
    pair_ids = {f"P{i:03d}": pair for i, pair in enumerate(ordered, start=1)}
    common = set(dp.draw_common_sample(ordered))

    demand_by_id = {d.demand_id: d for d in demands}
    patent_by_id = {p.publication_id: p for p in patents}
    rows = []
    for pair_id, (demand_id, publication_id) in pair_ids.items():
        demand, patent = demand_by_id[demand_id], patent_by_id[publication_id]
        rows.append({
            "pair_id": pair_id, "demand_title": demand.title, "demand_description": demand.description,
            "patent_title": patent.title, "patent_abstract": patent.abstract,
            "abstract_language": language_by_id[publication_id], "grade": "", "note": "",
        })
    _write_sheet(args.out_dir / "judging_sheet_A.csv", rows)
    _write_sheet(args.out_dir / "judging_sheet_B_common.csv",
                 [r for r in rows if pair_ids[r["pair_id"]] in common])

    provenance = {
        "pairs": {pid: list(pair) for pid, pair in pair_ids.items()},
        "methods": methods,
        "eligible_sizes": eligible_sizes,
        "demand_language": {d.demand_id: dp.guess_language(f"{d.title} {d.description}") for d in demands},
        "demand_language_method": "stopword heuristic (dense_probe.guess_language)",
        "common_sample": [pid for pid, pair in pair_ids.items() if pair in common],
    }
    (args.out_dir / "provenance_DO_NOT_OPEN.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"{len(demands)} demands, {len(rows)} pairs to judge, {len(common)} in the common sample")
    return 0


if __name__ == "__main__":
    sys.exit(main())
