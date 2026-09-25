"""ADR 0035 SS11.3 step 5: retrieval smoke test.

Runs CandidatePoolBuilder (BM25 + CPC) against the real, frozen OEPM/INVENES
corpus (experiments/oepm/build_oepm_corpus.py) for the same TED Dev demands
#104's original dry-run tried against the 16-patent pilot corpus -- confirms
whether this new, small-but-real corpus yields non-trivial pools before
declaring it usable (ADR 0035 SS11.3 step 5's explicit empirical requirement,
not a re-assertion that ingestion "should" work).
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.matching.candidate_pool_builder import CandidatePoolBuilder  # noqa: E402
from domain.models.demand import DemandSignal  # noqa: E402
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever  # noqa: E402
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402

logger = logging.getLogger("experiments.oepm.retrieval_smoke_test")

# Same 8 demands #104's original dry-run selected (generate_ted_annotation_dry_run.py)
DRY_RUN_DEMAND_IDS: tuple[str, ...] = (
    "89204-2025", "454027-2024", "268550-2024", "137639-2024",
    "588217-2024", "22543-2024", "566290-2025", "820594-2025",
)


def run_smoke_test(
    ted_corpus_path: Path = REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json",
    patents_parquet: Path = REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "part_0000.parquet",
    out_path: Path = REPO_ROOT / "data" / "experiments" / "oepm_v1" / "retrieval_smoke_test.json",
) -> dict[str, Any]:
    ted_corpus = json.loads(ted_corpus_path.read_text(encoding="utf-8"))
    demands_by_id = {d["demand_id"]: d for d in ted_corpus["demands"]}

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW patents AS SELECT * FROM read_parquet('{patents_parquet.resolve().as_posix()}')")

    eligibility_policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    builder = CandidatePoolBuilder(
        retrievers=[
            DuckDbBM25Retriever(con, eligibility_policy=eligibility_policy),
            DuckDbCPCRetriever(con, eligibility_policy=eligibility_policy),
        ],
        eligibility_policy=eligibility_policy,
        connection=con,
    )

    pool_sizes: dict[str, int] = {}
    pool_members: dict[str, list[str]] = {}
    for demand_id in DRY_RUN_DEMAND_IDS:
        d = demands_by_id.get(demand_id)
        if d is None:
            pool_sizes[demand_id] = -1
            continue
        demand = DemandSignal(
            demand_id=d["demand_id"],
            source_network="ted",
            title=d["title"],
            description=d["description_text"],
            posted_date=d["publication_date_evidence"]["publication_date"],
        )
        result = builder.build(demand, limit_per_method=20)
        pool_sizes[demand_id] = len(result.pool.candidates)
        pool_members[demand_id] = [c.publication_id for c in result.pool.candidates]

    con.close()

    non_empty = sum(1 for n in pool_sizes.values() if n > 0)
    report = {
        "purpose": "ADR 0035 SS11.3 step 5 retrieval smoke test -- empirical check, not a claim of usability",
        "patent_corpus": str(patents_parquet),
        "patent_corpus_size": 8,
        "demands_attempted": len(DRY_RUN_DEMAND_IDS),
        "non_empty_pools": non_empty,
        "pool_sizes": pool_sizes,
        "pool_members": pool_members,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Smoke test report: %s", json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_smoke_test()
