"""#104 dense retrieval diagnostic, step 2: run retrieval against the frozen
embedding artifact (docs/phase2-ted-dense-retrieval-diagnostic-contract.md
SS7 checkpoint 4). No new annotation is performed here.

Uses the existing, unmodified DuckDbDenseSemanticRetriever, fed by a
lookup-based TextEmbedder over the frozen artifact's precomputed vectors
(no live embedding computation -- the vectors were already generated and
determinism-checked in checkpoint 3). limit_per_method=20 and
min_threshold=0.0 are the contract's own fixed values (SS3), asserted here
against the frozen artifact and the retriever's own default, not re-decided.

Deliberately runs dense ALONE (not merged with BM25/CPC) -- the contract's
non-goal SS6 explicitly rules out computing a merged pool at this stage.
"""

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import duckdb  # noqa: E402

from application.matching.candidate_pool_builder import CandidatePoolBuilder  # noqa: E402
from domain.models.demand import DemandSignal  # noqa: E402
from infrastructure.matching.dense_semantic import DuckDbDenseSemanticRetriever  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402

LIMIT_PER_METHOD = 20
MIN_THRESHOLD = 0.0
EXPECTED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EXPECTED_MODEL_REVISION = "4328cf26390c98c5e3c738b4460a05b95f4911f5"
EXPECTED_DIMENSION = 768


class FrozenTextEmbedder:
    """TextEmbedder over precomputed vectors -- looks up by exact query text,
    the same `title + ' ' + description` string the frozen artifact was
    generated from. Raises if a text wasn't embedded, rather than silently
    falling back to live computation (there is no live computation available
    here at all -- deliberately, per the contract's isolation)."""

    def __init__(self, text_to_vector: dict[str, list[float]]) -> None:
        self._text_to_vector = text_to_vector

    def embed(self, text: str) -> list[float]:
        if text not in self._text_to_vector:
            raise KeyError(
                f"No frozen embedding for text (first 80 chars): {text[:80]!r}. "
                "This retriever must only see demand text that was already embedded."
            )
        return self._text_to_vector[text]


def run(
    embeddings_artifact_path: Path,
    source_texts_path: Path,
    corpus_parquet_glob: str,
    gold_set_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    artifact = json.loads(embeddings_artifact_path.read_text(encoding="utf-8"))

    # Contract assertion (SS7 stopping rule): any discrepancy with the frozen
    # contract stops execution, is not corrected on the fly.
    if artifact["model_name"] != EXPECTED_MODEL_NAME or artifact["model_revision"] != EXPECTED_MODEL_REVISION:
        raise RuntimeError(
            f"BLOCKED: embedding artifact model/revision "
            f"({artifact['model_name']}@{artifact['model_revision']}) does not match "
            f"the contract's pinned model ({EXPECTED_MODEL_NAME}@{EXPECTED_MODEL_REVISION})."
        )
    if artifact["embedding_dimension"] != EXPECTED_DIMENSION:
        raise RuntimeError(
            f"BLOCKED: embedding artifact dimension {artifact['embedding_dimension']} "
            f"!= expected {EXPECTED_DIMENSION}."
        )

    source = json.loads(source_texts_path.read_text(encoding="utf-8"))
    demand_ids = source["demand_ids"]
    demand_texts = source["demand_texts"]

    if len(demand_ids) != 30 or set(demand_ids) != set(artifact["demand_embeddings"].keys()):
        raise RuntimeError("BLOCKED: demand_ids in source texts do not match the frozen embedding artifact's keys.")

    text_to_vector = {
        text: artifact["demand_embeddings"][d_id]
        for d_id, text in zip(demand_ids, demand_texts, strict=True)
    }
    embedder = FrozenTextEmbedder(text_to_vector)

    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE patents AS
        SELECT DISTINCT ON (publication_id)
            publication_id, country_code, doc_number, kind_code, title, abstract, publication_date
        FROM read_parquet('{corpus_parquet_glob}')
        ORDER BY publication_id
    """)
    n_patents = con.execute("SELECT count(*) FROM patents").fetchone()[0]
    if n_patents != artifact["n_patents"]:
        raise RuntimeError(
            f"BLOCKED: corpus has {n_patents} distinct patents, but the frozen embedding "
            f"artifact declares n_patents={artifact['n_patents']}."
        )

    con.execute("ALTER TABLE patents ADD COLUMN embedding VARCHAR")
    for pub_id, vec in artifact["patent_embeddings"].items():
        con.execute("UPDATE patents SET embedding = ? WHERE publication_id = ?", [json.dumps(vec), pub_id])
    missing_embedding = con.execute("SELECT count(*) FROM patents WHERE embedding IS NULL").fetchone()[0]
    if missing_embedding:
        raise RuntimeError(f"BLOCKED: {missing_embedding} patents have no embedding after load.")

    eligibility_policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    retriever = DuckDbDenseSemanticRetriever(
        con, embedder=embedder, eligibility_policy=eligibility_policy, min_threshold=MIN_THRESHOLD,
    )
    builder = CandidatePoolBuilder(retrievers=[retriever], eligibility_policy=eligibility_policy, connection=con)

    # Contract assertions on the retriever's own fixed values (not re-decided here).
    if retriever._min_threshold != MIN_THRESHOLD:  # noqa: SLF001 -- asserting the contract's own fixed value
        raise RuntimeError("BLOCKED: retriever min_threshold does not match the contract's fixed value.")

    demand_corpus = json.loads((REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json").read_text())
    demand_corpus_by_id = {d["demand_id"]: d for d in demand_corpus["demands"]}

    gold = json.loads(gold_set_path.read_text(encoding="utf-8"))
    bm25_pool_keys = {(e["demand_id"], e["publication_id"]) for e in gold["entries"]}
    bm25_zero_pool_ids = set(json.loads((REPO_ROOT / "data" / "annotations" / "ted_at_scale_annotation_batch.json").read_text())["zero_pool_demand_ids"])

    per_demand: dict[str, Any] = {}
    all_dense_pairs: list[dict[str, Any]] = []
    n_nonempty = 0

    for demand_id in demand_ids:
        d = demand_corpus_by_id[demand_id]
        demand = DemandSignal(
            demand_id=demand_id, source_network="ted", title=d["title"],
            description=d["description_text"],
            posted_date=d["publication_date_evidence"]["publication_date"],
        )
        result = builder.build(demand, limit_per_method=LIMIT_PER_METHOD)
        candidates = result.pool.candidates
        if candidates:
            n_nonempty += 1

        candidate_list = []
        for c in candidates:
            score = c.retrieval_scores.get(next(iter(c.retrieval_scores.keys())))
            key = (demand_id, c.publication_id)
            provenance = (
                "shared_with_bm25_gold_scored" if key in bm25_pool_keys
                else "dense_exclusive_new_unscored"
            )
            candidate_list.append({
                "publication_id": c.publication_id,
                "score": round(score, 6),
                "provenance": provenance,
            })
            all_dense_pairs.append({"demand_id": demand_id, **candidate_list[-1]})

        per_demand[demand_id] = {
            "pool_size": len(candidates),
            "was_bm25_zero_pool": demand_id in bm25_zero_pool_ids,
            "candidates": candidate_list,
        }

    con.close()

    n_shared = sum(1 for p in all_dense_pairs if p["provenance"] == "shared_with_bm25_gold_scored")
    n_new_unscored = sum(1 for p in all_dense_pairs if p["provenance"] == "dense_exclusive_new_unscored")

    # BM25's own structure, for side-by-side reporting only -- not recomputed, read from frozen results.
    bm25_zero_pool_count = len(bm25_zero_pool_ids)
    bm25_nonempty_count = 30 - bm25_zero_pool_count

    result_summary = {
        "estimand_contract": "docs/phase2-ted-dense-retrieval-diagnostic-contract.md",
        "embedding_artifact_sha256": artifact["artifact_sha256"],
        "embedding_artifact_path": str(embeddings_artifact_path.relative_to(REPO_ROOT)),
        "limit_per_method": LIMIT_PER_METHOD,
        "min_threshold": MIN_THRESHOLD,
        "n_dev_demands": len(demand_ids),
        "n_demands_nonempty_pool": n_nonempty,
        "n_demands_empty_pool": len(demand_ids) - n_nonempty,
        "n_total_dense_pairs": len(all_dense_pairs),
        "n_shared_with_bm25_gold_scored": n_shared,
        "n_dense_exclusive_new_unscored": n_new_unscored,
        "bm25_comparison_structure": {
            "bm25_nonempty_pool_demands": bm25_nonempty_count,
            "bm25_empty_pool_demands": bm25_zero_pool_count,
            "note": "BM25's own 9/30 gold>=1 coverage is not recomputed here -- see docs/phase2-ted-pool-coverage-results.md. This block only restates BM25's pool-emptiness structure for side-by-side comparison.",
        },
        "per_demand": per_demand,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result_summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return result_summary


def main() -> int:
    result = run(
        embeddings_artifact_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_embeddings_v1.json",
        source_texts_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_source_texts.json",
        corpus_parquet_glob=str(REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "*.parquet"),
        gold_set_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_gold_set_v1.json",
        out_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_retrieval_results.json",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "per_demand"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
