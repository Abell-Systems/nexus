"""#104 dense-exclusive stratified sample, step 2: blind batch generation.

Per docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md
SS10. Takes the exact (demand, patent) pairs already selected by
sample_dense_exclusive_stratified.py (no re-sampling, no re-selection here)
and blind-exports them via the existing
infrastructure.annotation.blind_export.build_annotation_batch -- same
deterministic seeded shuffle, same evidence fields, same provenance
stripping used for the original 108-pair gold set and the parked
220-pair batch.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import duckdb  # noqa: E402

from dense_exclusive_sampling import BLIND_EXPORT_SEED  # noqa: E402
from domain.models.demand import DemandSignal  # noqa: E402
from domain.models.matching import Candidate, CandidatePool  # noqa: E402
from domain.models.patent import PatentDocument  # noqa: E402
from infrastructure.annotation.blind_export import AnnotationBatch, build_annotation_batch  # noqa: E402


def generate(
    manifest_path: Path,
    demand_corpus_path: Path,
    corpus_parquet_glob: str,
    out_path: Path,
    seed: int = BLIND_EXPORT_SEED,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    demand_corpus = json.loads(demand_corpus_path.read_text(encoding="utf-8"))
    corpus_by_id = {d["demand_id"]: d for d in demand_corpus["demands"]}

    pairs_by_demand: dict[str, list[str]] = {}
    for row in manifest["selected"]:
        pairs_by_demand.setdefault(row["demand_id"], []).append(row["publication_id"])

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
    for demand_id in sorted(pairs_by_demand):
        d = corpus_by_id[demand_id]
        demand = DemandSignal(
            demand_id=demand_id, source_network="ted", title=d["title"],
            description=d["description_text"],
            posted_date=d["publication_date_evidence"]["publication_date"],
        )
        publication_ids = pairs_by_demand[demand_id]
        pool = CandidatePool(
            demand_id=demand_id,
            candidates=[Candidate(publication_id=pid, retrieval_scores={}) for pid in publication_ids],
        )
        batch = build_annotation_batch(pool, demand, patents_by_id, seed=seed)
        batches.append(batch)
        total_pairs += len(batch.entries)

    if total_pairs != manifest["n_total"]:
        raise ValueError(f"Expected {manifest['n_total']} total pairs, got {total_pairs}")

    out = {
        "dataset_id": "nexus-phase2-ted-dense-exclusive-stratified-annotation-v1",
        "purpose": "DUAL_ANNOTATION_POOL -- #104 dense-exclusive stratified sample, "
                   "docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md",
        "source_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "source_manifest_sha256": manifest_sha256,
        "seed": seed,
        "demand_count": len(batches),
        "total_annotation_pairs": total_pairs,
        "demand_ids": sorted(pairs_by_demand),
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
        manifest_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_sample_manifest.json",
        demand_corpus_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json",
        corpus_parquet_glob=str(REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "*.parquet"),
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_annotation_batch.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
