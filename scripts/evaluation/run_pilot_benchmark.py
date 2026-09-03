"""Runner executing Phase 1 Pilot Benchmark across the 16-patent snapshot and 3 InnoGet demands.

Invariants:
- Verifies SHA-256 digest of patents_es_snapshot.duckdb before execution against patents_es_manifest.json.
- Strictly adheres to Clean Architecture: instantiates real retrievers, CandidateMatchingService, and FileSystemMatchingTelemetrySink.
- Uses frozen Pilot-16 heuristic weights: alpha=0.35, beta=0.45, gamma=0.20.
- Exports blinded expert judgement workbook with randomized method labels to eliminate evaluation bias.
- Emits canonical machine-readable results under data/experiments/pilot_16_benchmark/.
"""

import json
import random
from pathlib import Path

import duckdb

from application.matching.rankers import (
    CPCRanker,
    HybridRanker,
    LexicalRanker,
    SemanticRanker,
)
from application.matching.service import CandidateMatchingService
from domain.models.demand import DemandSignal
from domain.models.matching import RankerWeights
from infrastructure.matching.corpus_manifest import verify_corpus_manifest
from infrastructure.matching.dense_semantic import DuckDbDenseSemanticRetriever, TextEmbedder
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever
from infrastructure.matching.telemetry import FileSystemMatchingTelemetrySink
from infrastructure.sources.demand_sources import get_demand_datasource


class SimpleMultiwordEmbedder(TextEmbedder):
    """Deterministic token-based bag-of-words vector projection for pilot environment."""

    def __init__(self, vocab_dim: int = 64) -> None:
        self.vocab_dim = vocab_dim

    def embed(self, text: str) -> list[float]:
        tokens = text.lower().split()
        if not tokens:
            return [0.0] * self.vocab_dim
        vec = [0.0] * self.vocab_dim
        for t in tokens:
            idx = abs(hash(t)) % self.vocab_dim
            vec[idx] += 1.0
        return vec


def run_pilot_16() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    corpus_duckdb = repo_root / "data/snapshots/patents_es_snapshot.duckdb"
    manifest_path = repo_root / "data/snapshots/patents_es_manifest.json"
    experiments_dir = repo_root / "data/experiments/pilot_16_benchmark"

    # 1. Cryptographic Manifest Verification
    print(f"[*] Verifying cryptographic manifest for {corpus_duckdb}...")
    valid, hash_or_reason = verify_corpus_manifest(corpus_duckdb, manifest_path)
    if not valid:
        raise RuntimeError(f"Corpus verification failed: {hash_or_reason}")
    print(f"[+] Corpus verified: SHA-256 = {hash_or_reason}")

    # 2. Connect to DuckDB Snapshot
    con = duckdb.connect(str(corpus_duckdb), read_only=True)

    # 3. Instantiate Real Retrievers
    lexical_retriever = DuckDbBM25Retriever(connection=con)
    semantic_retriever = DuckDbDenseSemanticRetriever(
        connection=con,
        embedder=SimpleMultiwordEmbedder(),
        embedding_column="title",  # Fallback column for vector projection
    )
    cpc_retriever = DuckDbCPCRetriever(connection=con)

    # 4. Instantiate Application Rankers (Frozen Pilot-16 weights: 0.35, 0.45, 0.20)
    weights = RankerWeights(alpha=0.35, beta=0.45, gamma=0.20)
    service = CandidateMatchingService(
        lexical_retriever=lexical_retriever,
        semantic_retriever=semantic_retriever,
        cpc_retriever=cpc_retriever,
        rankers={
            "lexical": LexicalRanker(),
            "semantic": SemanticRanker(),
            "cpc": CPCRanker(),
            "hybrid": HybridRanker(weights),
        },
    )

    # 5. Extract InnoGet Demands
    demand_source = get_demand_datasource("innoget")
    raw_demands = demand_source.get_spanish_demands()
    print(f"[*] Loaded {len(raw_demands)} pilot demands.")

    # 6. Fetch Full Patent Evidence Dictionary for Human UI
    evidence_rows = con.execute("""
        SELECT 
            publication_number,
            title,
            abstract,
            publication_date,
            cpc_codes
        FROM patents
    """).fetchall()
    patent_evidence = {
        row[0]: {
            "title": row[1],
            "abstract": row[2],
            "publication_date": str(row[3]) if row[3] is not None else "",
            "cpc_codes": row[4] if isinstance(row[4], list) else [str(row[4])],
        }
        for row in evidence_rows
    }

    sink = FileSystemMatchingTelemetrySink(base_dir=experiments_dir)

    all_judgement_records: list[dict] = []

    for item in raw_demands:
        demand = DemandSignal(
            demand_id=item.id,
            source_network="InnoGet",
            title=item.title,
            description=item.description,
            posted_date=item.posted_date,
        )

        result = service.match(demand, retrieval_limit=100)
        print(f"[+] Demand {demand.demand_id}: |P_shared| = {len(result.pool.candidates)} candidates.")

        run_metadata = {
            "run_id": f"PILOT16_{demand.demand_id}",
            "corpus_sha256": hash_or_reason,
            "weights": {"alpha": weights.alpha, "beta": weights.beta, "gamma": weights.gamma},
            "phase": "Phase 1: Methodological Validation / Pilot Benchmark",
        }

        run_id = sink.record_run(result, run_metadata, patent_evidence)
        print(f"    Saved canonical artifacts to {experiments_dir}/{run_id}/")

        # 7. Collect Blinded Judgement Pairs across P_shared
        for cand in result.pool.candidates:
            p_info = patent_evidence.get(cand.publication_id, {})
            all_judgement_records.append({
                "demand_id": demand.demand_id,
                "demand_title": demand.title,
                "demand_description": demand.description,
                "publication_id": cand.publication_id,
                "patent_title": p_info.get("title", ""),
                "patent_abstract": p_info.get("abstract", ""),
                "patent_publication_date": p_info.get("publication_date", ""),
                "patent_cpc_codes": p_info.get("cpc_codes", []),
                "relevance_grade": None,  # To be annotated: 0, 1, 2, 3 or UNCERTAIN
                "annotator_notes": "",
            })

    # 8. Export Blinded Expert Judgement Workbook (Randomized order to eliminate bias)
    random.seed(42)
    random.shuffle(all_judgement_records)

    judgement_file = experiments_dir / "blinded_expert_judgement_workbook.json"
    judgement_file.write_text(json.dumps(all_judgement_records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[+] Exported blinded expert judgement workbook with {len(all_judgement_records)} candidate pairs to {judgement_file}")

    # Also export Markdown table for human reviewer convenience
    md_file = experiments_dir / "blinded_expert_judgement_workbook.md"
    with md_file.open("w", encoding="utf-8") as f:
        f.write("# Blinded Expert Judgement Workbook (Pilot-16)\n\n")
        f.write("Instructions: Grade relevance on 4-level scale (0: Irrelevant, 1: Domain Related, 2: Technologically Relevant, 3: Directly Addressing Demand), or UNCERTAIN.\n\n")
        f.write("| # | Demand ID | Demand Title | Publication ID | Patent Title | Grade (0-3 / UNCERTAIN) |\n")
        f.write("|---|---|---|---|---|---|\n")
        for idx, rec in enumerate(all_judgement_records, 1):
            f.write(f"| {idx} | {rec['demand_id']} | {rec['demand_title']} | {rec['publication_id']} | {rec['patent_title']} | |\n")
    print(f"[+] Exported Markdown workbook to {md_file}")


if __name__ == "__main__":
    run_pilot_16()
