"""#104 dry-run: independent candidate pools + blind export for a deliberately
selected subset of TED Dev demands (ADR 0029/0030 frozen corpus).

Validates the annotation protocol/instrument only -- NOT an efficacy pool and NOT
a statistical sample, mirroring PR-E's own dry-run scope
(docs/superpowers/specs/2026-09-08-pr-e-candidate-pool-blind-annotation-iaa-design.md).

Runs against the existing 16-patent pilot corpus (data/snapshots/patents_es_snapshot.duckdb),
the only patent corpus materialized in this repo at the time of writing -- a real,
disclosed limitation: this validates blind-export mechanics, guide clarity, and κ
computation, not retrieval quality against a real domestic patent universe. Scaling
beyond this dry-run requires ingesting a production-scale OEPM corpus first (not
done here).

Retrievers: BM25 + CPC only. The Dense/semantic retriever is deliberately excluded
here -- it needs a live TextEmbedder, and the only pinned embedding model
(ADR 0014, sentence-transformers/paraphrase-multilingual-mpnet-base-v2) lives in an
isolated generation-only dependency stack (requirements/evaluation-generation.txt)
this environment does not have installed, and ADR 0014 deliberately forbids the
evaluation runtime from importing that stack. Two of three independent baselines
already exercise the blind-export/annotation mechanics this dry-run exists to
validate.

100% offline (once patent/demand data is loaded), zero new network calls.
"""

import argparse
import hashlib
import json
import logging
import re
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
from infrastructure.annotation.blind_export import AnnotationBatch, build_annotation_batch  # noqa: E402
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever  # noqa: E402
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402

logger = logging.getLogger("experiments.phase2.generate_ted_annotation_dry_run")

_CPV_RE = re.compile(r"code\|name\|cpv\.(\d{8})")

# Deliberately selected for CPV/domain diversity and to include both geographic
# strata present in the frozen corpus -- not a statistical sample (PR-E precedent).
# Rationale for each: docs/annotation/phase2-ted-dry-run-selection.md
DRY_RUN_DEMAND_IDS: tuple[str, ...] = (
    "89204-2025",     # Spain, IT/software procurement-innovation partnership service
    "454027-2024",    # Spain, R&D pilot plant
    "268550-2024",    # Germany, AI-assisted medical robotics platform
    "137639-2024",    # Netherlands, wastewater treatment plant innovation
    "588217-2024",    # Germany, cyanide-free gilding R&D (chemistry-adjacent)
    "22543-2024",     # Poland, electricity meter manufacturing/design
    "566290-2025",    # Netherlands, software platform for register management
    "820594-2025",    # Czechia, AI contactless measurement/automation
)

SEED = 42


def extract_cpv_code(raw_html: str) -> str | None:
    m = _CPV_RE.search(raw_html)
    return m.group(1) if m else None


def _load_demand(demand_id: str, corpus_by_id: dict[str, dict[str, Any]]) -> DemandSignal:
    d = corpus_by_id[demand_id]
    return DemandSignal(
        demand_id=d["demand_id"],
        source_network="ted",
        title=d["title"],
        description=d["description_text"],
        posted_date=d["publication_date_evidence"]["publication_date"],
    )


def generate_dry_run(
    corpus_path: Path,
    patents_db_path: Path,
    out_path: Path,
    demand_ids: tuple[str, ...] = DRY_RUN_DEMAND_IDS,
    seed: int = SEED,
) -> dict[str, Any]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    corpus_sha256 = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    corpus_by_id = {d["demand_id"]: d for d in corpus["demands"]}

    missing = [d for d in demand_ids if d not in corpus_by_id]
    if missing:
        raise ValueError(f"Dry-run demand_ids not found in frozen TED corpus: {missing}")

    con = duckdb.connect(str(patents_db_path), read_only=True)
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
        "SELECT publication_number, title, abstract, publication_date FROM patents"
    ).fetchall()
    # PatentDocument requires doc_number/kind_code -- this table only carries the
    # composite publication_number (format ES-XXXXXXX-A1); derive rather than
    # re-querying a column that doesn't exist here.
    from domain.models.patent import PatentDocument  # noqa: E402

    patents_by_id: dict[str, PatentDocument] = {}
    for row in patents_rows:
        pub_id = str(row[0])
        parts = pub_id.split("-")
        patents_by_id[pub_id] = PatentDocument(
            publication_id=pub_id,
            country_code=parts[0] if len(parts) > 0 else "",
            doc_number=parts[1] if len(parts) > 1 else "",
            kind_code=parts[2] if len(parts) > 2 else "",
            title=str(row[1]) if row[1] is not None else "",
            abstract=str(row[2]) if row[2] is not None else "",
            publication_date=str(row[3]) if row[3] is not None else None,
        )

    batches: list[AnnotationBatch] = []
    pool_sizes: dict[str, int] = {}
    demand_cpv: dict[str, str | None] = {}

    for demand_id in demand_ids:
        demand = _load_demand(demand_id, corpus_by_id)
        result = builder.build(demand, limit_per_method=20)
        pool_sizes[demand_id] = len(result.pool.candidates)
        batch = build_annotation_batch(result.pool, demand, patents_by_id, seed=seed)
        batches.append(batch)

        raw_path = REPO_ROOT / "data" / "raw" / "phase2_candidates_ted" / "ted" / f"{demand_id}.html"
        demand_cpv[demand_id] = extract_cpv_code(raw_path.read_text(encoding="utf-8")) if raw_path.is_file() else None

    con.close()

    dry_run_set = {
        "dataset_id": "nexus-phase2-ted-annotation-dry-run-v1",
        "purpose": "PROTOCOL_VALIDATION_ONLY -- not an efficacy pool, not a statistical sample (PR-E precedent)",
        "source_corpus_dataset_id": corpus["dataset_id"],
        "source_corpus_sha256": corpus_sha256,
        "patent_corpus": "16-patent pilot benchmark (data/snapshots/patents_es_snapshot.duckdb) -- NOT a production-scale OEPM corpus, disclosed limitation",
        "retrievers_used": ["bm25", "cpc"],
        "retrievers_excluded": ["dense_semantic (no live embedder available in this environment, ADR 0014 isolation)"],
        "seed": seed,
        "pool_sizes": pool_sizes,
        "demand_cpv": demand_cpv,
        "demands": [json.loads(b.model_dump_json()) for b in batches],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(dry_run_set, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    logger.info(
        "Dry-run annotation batch generated: %d demands, pool sizes=%s",
        len(batches), pool_sizes,
    )
    return dry_run_set


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="#104 TED annotation dry-run generator.")
    parser.add_argument("--corpus-path", type=Path, default=Path("data/experiments/phase2_v4/ted_independent_corpus_v1.json"))
    parser.add_argument("--patents-db-path", type=Path, default=Path("data/snapshots/patents_es_snapshot.duckdb"))
    parser.add_argument("--out-path", type=Path, default=Path("data/annotations/ted_dry_run_annotation_batch.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    generate_dry_run(corpus_path=args.corpus_path, patents_db_path=args.patents_db_path, out_path=args.out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
