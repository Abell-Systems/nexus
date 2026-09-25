"""#104 CPC channel-activation diagnostic, per
docs/phase2-ted-cpc-channel-diagnostic-contract.md. Runs BM25 (unchanged) +
CPC (now configured with a real, corpus-grounded taxonomy,
config/policies/matching/ted_at_scale_cpc_taxonomy_v1.json) over the same 30
Dev demands / same frozen corpus / same eligibility policy, and reports:

1. CPC activation: which demands match >=1 concept phrase, which don't.
2. Incremental retrieval: CPC-exclusive candidates, split into already
   gold-scored (coincidence with the existing 108-pair gold set) vs. new
   and unscored. No judgment is invented for the unscored ones.

Analysis-only with respect to the frozen gold set -- never writes to it.
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
from domain.models.matching import MatchingPolicyConfig  # noqa: E402
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever  # noqa: E402
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever, extract_demand_cpc_auto  # noqa: E402
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402


def run_diagnostic(
    policy_path: Path,
    corpus_parquet_glob: str,
    demand_corpus_path: Path,
    devtest_split_path: Path,
    gold_set_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    policy = MatchingPolicyConfig.load_from_json(str(policy_path))

    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE patents AS
        SELECT DISTINCT ON (publication_id)
            publication_id, country_code, doc_number, kind_code, title, abstract,
            publication_date, classifications_cpc AS cpc_codes
        FROM read_parquet('{corpus_parquet_glob}')
        ORDER BY publication_id
    """)

    corpus = json.loads(demand_corpus_path.read_text(encoding="utf-8"))
    corpus_by_id = {d["demand_id"]: d for d in corpus["demands"]}
    split = json.loads(devtest_split_path.read_text(encoding="utf-8"))
    dev_ids: list[str] = split["dev"]

    gold = json.loads(gold_set_path.read_text(encoding="utf-8"))
    original_pool_keys = {(e["demand_id"], e["publication_id"]) for e in gold["entries"]}

    eligibility_policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    builder = CandidatePoolBuilder(
        retrievers=[
            DuckDbBM25Retriever(con, eligibility_policy=eligibility_policy),
            DuckDbCPCRetriever(con, eligibility_policy=eligibility_policy, policy=policy),
        ],
        eligibility_policy=eligibility_policy,
        connection=con,
    )

    activation: dict[str, Any] = {}
    cpc_exclusive_already_scored: list[dict[str, str]] = []
    cpc_exclusive_new: list[dict[str, str]] = []

    for demand_id in dev_ids:
        d = corpus_by_id[demand_id]
        demand = DemandSignal(
            demand_id=d["demand_id"], source_network="ted", title=d["title"],
            description=d["description_text"],
            posted_date=d["publication_date_evidence"]["publication_date"],
        )
        demand_cpc = extract_demand_cpc_auto(demand, policy=policy)
        activation[demand_id] = {
            "language_code": d["language_code"],
            "symbols": demand_cpc.symbols,
            "activated": bool(demand_cpc.symbols),
        }

        result = builder.build(demand, limit_per_method=20)
        for c in result.pool.candidates:
            methods = {m.value for m in c.retrieval_scores.keys()}
            if methods == {"cpc"}:
                key = (demand_id, c.publication_id)
                target = cpc_exclusive_already_scored if key in original_pool_keys else cpc_exclusive_new
                target.append({"demand_id": demand_id, "publication_id": c.publication_id})

    n_activated = sum(1 for v in activation.values() if v["activated"])
    result_summary = {
        "estimand_contract": "docs/phase2-ted-cpc-channel-diagnostic-contract.md",
        "policy_path": str(policy_path),
        "policy_sha256": policy.policy_sha256,
        "n_concept_entries": len(policy.concept_to_cpc_taxonomy),
        "n_dev_demands": len(dev_ids),
        "n_activated_demands": n_activated,
        "activation_rate": round(n_activated / len(dev_ids), 4),
        "activation_by_demand": activation,
        "cpc_exclusive_already_scored_count": len(cpc_exclusive_already_scored),
        "cpc_exclusive_already_scored": cpc_exclusive_already_scored,
        "cpc_exclusive_new_count": len(cpc_exclusive_new),
        "cpc_exclusive_new": cpc_exclusive_new,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result_summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return result_summary


def main(argv: list[str] | None = None) -> int:
    result = run_diagnostic(
        policy_path=REPO_ROOT / "config" / "policies" / "matching" / "ted_at_scale_cpc_taxonomy_v1.json",
        corpus_parquet_glob=str(REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "*.parquet"),
        demand_corpus_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json",
        devtest_split_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_devtest_split_v1.json",
        gold_set_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_gold_set_v1.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_cpc_channel_diagnostic.json",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "activation_by_demand"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
