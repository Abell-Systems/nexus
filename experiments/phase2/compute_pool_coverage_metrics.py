"""#104 pool-coverage metrics, computed exactly per
docs/phase2-ted-pool-coverage-estimand-contract.md -- three distinct
estimands, none of them called "recall":

1. Demand-level pool coverage rate (denominator=30, includes zero-pool demands).
2. Pool relevance yield (precision-flavored; explicitly not recall).
3. Relevance distribution among retrieved candidates, pooled and per-demand.
"""

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

THRESHOLDS = (1, 2)


def compute_metrics(
    gold_set_path: Path,
    at_scale_batch_path: Path,
    devtest_split_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    gold = json.loads(gold_set_path.read_text(encoding="utf-8"))
    batch = json.loads(at_scale_batch_path.read_text(encoding="utf-8"))
    split = json.loads(devtest_split_path.read_text(encoding="utf-8"))

    dev_ids: list[str] = split["dev"]
    zero_pool_ids: set[str] = set(batch["zero_pool_demand_ids"])
    annotated_ids = {d["demand_id"] for d in batch["demands"]}

    if set(dev_ids) != zero_pool_ids | annotated_ids:
        raise ValueError("Dev split does not partition cleanly into zero-pool + annotated demand_ids")

    # gold judgments grouped by demand_id
    by_demand: dict[str, list[dict[str, Any]]] = {}
    for e in gold["entries"]:
        by_demand.setdefault(e["demand_id"], []).append(e)

    # --- 1. Demand-level pool coverage rate ---
    coverage: dict[str, Any] = {}
    for threshold in THRESHOLDS:
        covered = []
        for demand_id in dev_ids:
            entries = by_demand.get(demand_id, [])
            is_covered = any(e["gold_judgment"] >= threshold for e in entries)
            covered.append(is_covered)
        n_covered = sum(covered)
        coverage[f"threshold_gold_gte_{threshold}"] = {
            "n_covered": n_covered,
            "n_total_dev_demands": len(dev_ids),
            "coverage_rate": round(n_covered / len(dev_ids), 4),
        }

    # --- 2. Pool relevance yield (NOT recall) ---
    yield_stats: dict[str, Any] = {}
    all_scores = [e["gold_judgment"] for e in gold["entries"]]
    n_pairs = len(all_scores)
    for threshold in THRESHOLDS:
        n_relevant = sum(1 for s in all_scores if s >= threshold)
        yield_stats[f"threshold_gold_gte_{threshold}"] = {
            "n_relevant_pairs": n_relevant,
            "n_total_pool_pairs": n_pairs,
            "pool_relevance_yield": round(n_relevant / n_pairs, 4),
        }

    # --- 3. Relevance distribution ---
    def dist(entries: list[dict[str, Any]]) -> dict[str, int]:
        return {str(s): sum(1 for e in entries if e["gold_judgment"] == s) for s in range(4)}

    pooled_distribution = dist(gold["entries"])
    per_demand_distribution = {
        demand_id: {
            "n_pool": len(entries),
            "distribution": dist(entries),
            "max_gold_judgment": max((e["gold_judgment"] for e in entries), default=None),
        }
        for demand_id, entries in by_demand.items()
    }
    # zero-pool demands: explicit entries with n_pool=0
    for demand_id in zero_pool_ids:
        per_demand_distribution[demand_id] = {
            "n_pool": 0,
            "distribution": {str(s): 0 for s in range(4)},
            "max_gold_judgment": None,
        }

    result = {
        "estimand_contract": "docs/phase2-ted-pool-coverage-estimand-contract.md",
        "dev_demand_count": len(dev_ids),
        "zero_pool_demand_count": len(zero_pool_ids),
        "annotated_demand_count": len(annotated_ids),
        "demand_level_pool_coverage_rate": coverage,
        "pool_relevance_yield": yield_stats,
        "pooled_relevance_distribution": pooled_distribution,
        "per_demand_relevance_distribution": per_demand_distribution,
        "recall_note": (
            "No 'recall' metric is reported. The gold set covers only the 108 "
            "retrieved pairs; there is no independent judgment of patents outside "
            "the pool, so relevant-total (the recall denominator) is unknown. "
            "See docs/phase2-ted-pool-coverage-estimand-contract.md SS3."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    result = compute_metrics(
        gold_set_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_gold_set_v1.json",
        at_scale_batch_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_annotation_batch.json",
        devtest_split_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_devtest_split_v1.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_pool_coverage_metrics.json",
    )
    print(json.dumps(
        {k: v for k, v in result.items() if k != "per_demand_relevance_distribution"},
        indent=2, ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
