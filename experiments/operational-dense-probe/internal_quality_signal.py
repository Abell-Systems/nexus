"""Internal quality signal from the model's grades alone (spec Amendment A3).

NOT a probe outcome: no RESOLVED/UNRESOLVED label, no human validation, product decisions only.
Opens the provenance file, which ends blindness of sheets v1 (recorded in A3).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402

DEFAULT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM-judged internal quality signal (not a probe outcome)")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    provenance = json.loads((args.dir / "provenance_DO_NOT_OPEN.json").read_text(encoding="utf-8"))
    pair_ids = {pid: tuple(pair) for pid, pair in provenance["pairs"].items()}
    with (args.dir / "model_judgments.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    labels: dict[dp.Pair, dp.Label] = {
        pair_ids[r["pair_id"]]: (None if r["grade"].strip().upper() == "U" else int(r["grade"])) for r in rows
    }
    confidence = {pair_ids[r["pair_id"]]: r["confidence"] for r in rows}

    methods = provenance["methods"]
    p5 = {m: {d: dp.precision_at_5(d, lists[m], labels) for d, lists in methods.items()} for m in ("bm25", "dense")}
    macro = dp.paired_macro(p5["bm25"], p5["dense"])

    def share(method: str, pred) -> float:
        pairs = [(d, pub) for d, lists in methods.items() for pub in lists[method]]
        return sum(1 for p in pairs if pred(p)) / len(pairs)

    by_language = {}
    for language in sorted(set(provenance["demand_language"].values())):
        subset = {d for d, lang in provenance["demand_language"].items() if lang == language}
        sub = dp.paired_macro({d: p5["bm25"][d] for d in subset}, {d: p5["dense"][d] for d in subset})
        by_language[language] = {"n": sub.n_used, "p5_bm25": sub.p5_bm25, "p5_dense": sub.p5_dense}

    result = {
        "label": "LLM-judged internal estimate; no human validation; NOT a probe outcome (Amendment A3)",
        "p5_bm25": macro.p5_bm25,
        "p5_dense": macro.p5_dense,
        "delta": macro.delta,
        "n_demands": macro.n_used,
        "demands_with_at_least_one_relevant_top5": {
            m: sum(1 for v in p5[m].values() if v is not None and v > 0) for m in ("bm25", "dense")
        },
        "low_confidence_share": {
            m: share(m, lambda p: confidence[p] == "low") for m in ("bm25", "dense")
        },
        "by_language_stratum": by_language,
        "bootstrap_informative_only": dp.bootstrap_summary(p5["bm25"], p5["dense"]),
    }
    (args.dir / "internal_quality_signal.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "bootstrap_informative_only"}, indent=2))
    print("bootstrap delta:", result["bootstrap_informative_only"]["delta"] if result["bootstrap_informative_only"] else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
