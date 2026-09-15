"""#104 at-scale candidate pools + blind export against the frozen production OEPM
corpus (ADR 0035, 63 domestic patents, data/snapshots/oepm_invenes_corpus_v1).

Supersedes generate_ted_annotation_dry_run.py's protocol-validation scope: this runs
against the *real* frozen corpus and the *full* Dev partition of the frozen TED
demand corpus (data/experiments/phase2_v4/ted_devtest_split_v1.json), not a
deliberately hand-picked 8-demand subset. The dry-run's own limitation note --
"scaling beyond this dry-run requires ingesting a production-scale OEPM corpus
first (not done here)" -- is what this script resolves.

Retrievers: BM25 + CPC only, same as the dry-run and for the same reason (Dense/
semantic retriever needs a live TextEmbedder from an isolated dependency stack,
ADR 0014). limit_per_method=20, matching the dry-run's own setting so results are
comparable.

Disclosed finding, not routed around: with only 63 patents in the frozen corpus,
11 of the 30 Dev demands produce an empty eligible candidate pool (no BM25 or CPC
match survives DefaultPatentEligibilityPolicy). Those 11 are excluded from the
annotation batch (there is nothing to annotate) but are recorded by demand_id in
the output's `zero_pool_demand_ids`, not silently dropped from the record.

100% offline (once patent/demand data is loaded), zero new network calls.
"""

import argparse
import hashlib
import json
import logging
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
from domain.models.patent import PatentDocument  # noqa: E402
from infrastructure.annotation.blind_export import AnnotationBatch, build_annotation_batch  # noqa: E402
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever  # noqa: E402
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402

logger = logging.getLogger("experiments.phase2.generate_ted_annotation_at_scale")

SEED = 42
LIMIT_PER_METHOD = 20


def _load_demand(demand_id: str, corpus_by_id: dict[str, dict[str, Any]]) -> DemandSignal:
    d = corpus_by_id[demand_id]
    return DemandSignal(
        demand_id=d["demand_id"],
        source_network="ted",
        title=d["title"],
        description=d["description_text"],
        posted_date=d["publication_date_evidence"]["publication_date"],
    )


def _materialize_patents_table(con: duckdb.DuckDBPyConnection, corpus_parquet_glob: str) -> None:
    """The frozen canonical store accumulates one full-snapshot Parquet part per
    acquisition session (each session's build_corpus() re-ingests the complete
    cumulative included set, not just new records) -- so raw parts contain
    duplicate rows per publication_id across parts. DISTINCT ON collapses to the
    63 real records; content is identical across duplicates (same source HTML),
    so which duplicate survives is immaterial."""
    con.execute(f"""
        CREATE TABLE patents AS
        SELECT DISTINCT ON (publication_id)
            publication_id, country_code, doc_number, kind_code, title, abstract,
            publication_date, classifications_cpc AS cpc_codes
        FROM read_parquet('{corpus_parquet_glob}')
        ORDER BY publication_id
    """)


def generate_at_scale(
    demand_corpus_path: Path,
    devtest_split_path: Path,
    corpus_parquet_glob: str,
    out_path: Path,
    seed: int = SEED,
    limit_per_method: int = LIMIT_PER_METHOD,
) -> dict[str, Any]:
    demand_corpus = json.loads(demand_corpus_path.read_text(encoding="utf-8"))
    demand_corpus_sha256 = hashlib.sha256(demand_corpus_path.read_bytes()).hexdigest()
    corpus_by_id = {d["demand_id"]: d for d in demand_corpus["demands"]}

    split = json.loads(devtest_split_path.read_text(encoding="utf-8"))
    split_sha256 = hashlib.sha256(devtest_split_path.read_bytes()).hexdigest()
    dev_ids: list[str] = split["dev"]

    missing = [d for d in dev_ids if d not in corpus_by_id]
    if missing:
        raise ValueError(f"Dev-split demand_ids not found in frozen TED corpus: {missing}")

    con = duckdb.connect()
    _materialize_patents_table(con, corpus_parquet_glob)
    patent_count = con.execute("SELECT count(*) FROM patents").fetchone()[0]

    eligibility_policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    builder = CandidatePoolBuilder(
        retrievers=[
            DuckDbBM25Retriever(con, eligibility_policy=eligibility_policy),
            DuckDbCPCRetriever(con, eligibility_policy=eligibility_policy),
        ],
        eligibility_policy=eligibility_policy,
        connection=con,
    )

    patents_rows = con.execute(
        "SELECT publication_id, country_code, doc_number, kind_code, title, abstract, "
        "publication_date, cpc_codes FROM patents"
    ).fetchall()
    patents_by_id: dict[str, PatentDocument] = {}
    for row in patents_rows:
        patents_by_id[row[0]] = PatentDocument(
            publication_id=row[0],
            country_code=row[1] or "",
            doc_number=row[2] or "",
            kind_code=row[3] or "",
            title=row[4] or "",
            abstract=row[5] or "",
            publication_date=row[6],
            classifications_cpc=list(row[7]) if row[7] is not None else [],
        )

    batches: list[AnnotationBatch] = []
    pool_sizes: dict[str, int] = {}
    zero_pool_demand_ids: list[str] = []

    for demand_id in dev_ids:
        demand = _load_demand(demand_id, corpus_by_id)
        result = builder.build(demand, limit_per_method=limit_per_method)
        pool_sizes[demand_id] = len(result.pool.candidates)
        if len(result.pool.candidates) == 0:
            zero_pool_demand_ids.append(demand_id)
            continue
        batch = build_annotation_batch(result.pool, demand, patents_by_id, seed=seed)
        batches.append(batch)

    con.close()

    total_pairs = sum(len(b.entries) for b in batches)
    at_scale_set = {
        "dataset_id": "nexus-phase2-ted-annotation-at-scale-v1",
        "purpose": "DUAL_ANNOTATION_POOL -- #104, real frozen OEPM corpus and full Dev partition",
        "source_demand_corpus_dataset_id": demand_corpus["dataset_id"],
        "source_demand_corpus_sha256": demand_corpus_sha256,
        "source_devtest_split_dataset_id": split["dataset_id"],
        "source_devtest_split_sha256": split_sha256,
        "patent_corpus": "OEPM-INVENES-CORPUS-2026-V1 (ADR 0035, frozen 2026-09-15, 63 domestic patents)",
        "patent_count": patent_count,
        "retrievers_used": ["bm25", "cpc"],
        "retrievers_excluded": ["dense_semantic (no live embedder available in this environment, ADR 0014 isolation)"],
        "seed": seed,
        "limit_per_method": limit_per_method,
        "dev_demand_count": len(dev_ids),
        "annotated_demand_count": len(batches),
        "zero_pool_demand_count": len(zero_pool_demand_ids),
        "zero_pool_demand_ids": sorted(zero_pool_demand_ids),
        "pool_sizes": pool_sizes,
        "total_annotation_pairs": total_pairs,
        "demands": [json.loads(b.model_dump_json()) for b in batches],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(at_scale_set, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    logger.info(
        "At-scale annotation batch generated: %d/%d Dev demands annotated (%d zero-pool), %d total pairs",
        len(batches), len(dev_ids), len(zero_pool_demand_ids), total_pairs,
    )
    return at_scale_set


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="#104 TED at-scale annotation batch generator.")
    parser.add_argument("--demand-corpus-path", type=Path, default=Path("data/experiments/phase2_v4/ted_independent_corpus_v1.json"))
    parser.add_argument("--devtest-split-path", type=Path, default=Path("data/experiments/phase2_v4/ted_devtest_split_v1.json"))
    parser.add_argument(
        "--corpus-parquet-glob", type=str,
        default="data/snapshots/oepm_invenes_corpus_v1/OEPM-INVENES-CORPUS-2026-V1/patents/*.parquet",
    )
    parser.add_argument("--out-path", type=Path, default=Path("data/annotations/ted_at_scale_annotation_batch.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    generate_at_scale(
        demand_corpus_path=args.demand_corpus_path,
        devtest_split_path=args.devtest_split_path,
        corpus_parquet_glob=args.corpus_parquet_glob,
        out_path=args.out_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
