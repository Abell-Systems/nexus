"""#104 dense blind-spot annotation, step 1: blind batch generation.

Per docs/phase2-ted-dense-blindspot-annotation-contract.md -- takes the
exact 220 (demand, patent) pairs already produced by
experiments/phase2/run_dense_retrieval.py for the 11 BM25-zero-pool
demands (no re-retrieval, no re-selection, no score-based filtering: the
candidate list per demand is read verbatim from the frozen dense-retrieval
results) and blind-exports them via the existing
infrastructure.annotation.blind_export.build_annotation_batch (same
deterministic seeded shuffle, same evidence fields, same provenance
stripping used for the original 108-pair gold set).
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import duckdb  # noqa: E402

from domain.models.demand import DemandSignal  # noqa: E402
from domain.models.matching import Candidate, CandidatePool  # noqa: E402
from domain.models.patent import PatentDocument  # noqa: E402
from infrastructure.annotation.blind_export import AnnotationBatch, build_annotation_batch  # noqa: E402

SEED = 42


def generate(
    dense_results_path: Path,
    demand_corpus_path: Path,
    corpus_parquet_glob: str,
    out_path: Path,
    seed: int = SEED,
) -> dict[str, Any]:
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    dense_sha256 = hashlib.sha256(dense_results_path.read_bytes()).hexdigest()

    demand_corpus = json.loads(demand_corpus_path.read_text(encoding="utf-8"))
    corpus_by_id = {d["demand_id"]: d for d in demand_corpus["demands"]}

    blindspot_demand_ids = sorted(
        d_id for d_id, v in dense["per_demand"].items() if v["was_bm25_zero_pool"]
    )
    if len(blindspot_demand_ids) != 11:
        raise ValueError(f"Expected 11 BM25-zero-pool demands, found {len(blindspot_demand_ids)}")

    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE patents AS
        SELECT DISTINCT ON (publication_id)
            publication_id, country_code, doc_number, kind_code, title, abstract,
            publication_date, classifications_cpc AS cpc_codes
        FROM read_parquet('{corpus_parquet_glob}')
        ORDER BY publication_id
    """)
    rows = con.execute(
        "SELECT publication_id, country_code, doc_number, kind_code, title, abstract, "
        "publication_date, cpc_codes FROM patents"
    ).fetchall()
    con.close()

    patents_by_id: dict[str, PatentDocument] = {
        row[0]: PatentDocument(
            publication_id=row[0], country_code=row[1] or "", doc_number=row[2] or "",
            kind_code=row[3] or "", title=row[4] or "", abstract=row[5] or "",
            publication_date=row[6], classifications_cpc=list(row[7]) if row[7] is not None else [],
        )
        for row in rows
    }

    batches: list[AnnotationBatch] = []
    total_pairs = 0
    for demand_id in blindspot_demand_ids:
        d = corpus_by_id[demand_id]
        demand = DemandSignal(
            demand_id=demand_id, source_network="ted", title=d["title"],
            description=d["description_text"],
            posted_date=d["publication_date_evidence"]["publication_date"],
        )
        candidates = dense["per_demand"][demand_id]["candidates"]
        if len(candidates) != 20:
            raise ValueError(f"{demand_id}: expected 20 dense candidates, found {len(candidates)}")
        pool = CandidatePool(
            demand_id=demand_id,
            candidates=[Candidate(publication_id=c["publication_id"], retrieval_scores={}) for c in candidates],
        )
        batch = build_annotation_batch(pool, demand, patents_by_id, seed=seed)
        batches.append(batch)
        total_pairs += len(batch.entries)

    if total_pairs != 220:
        raise ValueError(f"Expected 220 total pairs, got {total_pairs}")

    out = {
        "dataset_id": "nexus-phase2-ted-dense-blindspot-annotation-v1",
        "purpose": "DUAL_ANNOTATION_POOL -- #104 dense blind-spot stratum, docs/phase2-ted-dense-blindspot-annotation-contract.md",
        "source_dense_retrieval_results_path": str(dense_results_path.relative_to(REPO_ROOT)),
        "source_dense_retrieval_results_sha256": dense_sha256,
        "seed": seed,
        "demand_count": len(batches),
        "total_annotation_pairs": total_pairs,
        "demand_ids": blindspot_demand_ids,
        "demands": [json.loads(b.model_dump_json()) for b in batches],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {total_pairs} pairs across {len(batches)} demands to {out_path}")
    return out


def main() -> int:
    generate(
        dense_results_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_retrieval_results.json",
        demand_corpus_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json",
        corpus_parquet_glob=str(REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "*.parquet"),
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_blindspot_annotation_batch.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
