"""Scores the pre-registered probe. Spec section 7 as amended by A2 (model-first, human tie-break).

Usage: python experiments/operational-dense-probe/score_probe.py [--dir outputs]
Reads model_judgments.csv, judging_sheet_B_common.csv (human, common sample), escalation_sheet.csv (human,
escalated pairs) and provenance_DO_NOT_OPEN.json from --dir, writes probe_result.json there.
"""

import argparse
import csv
import json
import sys
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402

DEFAULT_DIR = Path(__file__).resolve().parent / "outputs"


def parse_grade(cell: str) -> int | None:
    value = cell.strip()
    if value.upper() == "U":
        return None
    if value in {"0", "1", "2", "3"}:
        return int(value)
    raise ValueError(f"Invalid grade {cell!r}: expected 0-3 or U")


def read_sheet_grades(path: Path, pair_ids: Mapping[str, dp.Pair], grade_column: str = "grade") -> dict[dp.Pair, dp.Label]:
    grades: dict[dp.Pair, dp.Label] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pair_id = row["pair_id"]
            if pair_id not in pair_ids:
                raise KeyError(f"{path.name}: unknown pair_id {pair_id!r}")
            try:
                grades[pair_ids[pair_id]] = parse_grade(row[grade_column])
            except ValueError as err:
                raise ValueError(f"{path.name}: pair {pair_id}: {err}") from err
    return grades


def read_model_judgments(path: Path, pair_ids: Mapping[str, dp.Pair]) -> dict[str, tuple[dp.Label, str]]:
    judgments: dict[str, tuple[dp.Label, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pair_id = row["pair_id"]
            if pair_id not in pair_ids:
                raise KeyError(f"{path.name}: unknown pair_id {pair_id!r}")
            confidence = row["confidence"].strip().lower()
            if confidence not in {"high", "low"}:
                raise ValueError(f"{path.name}: pair {pair_id}: invalid confidence {row['confidence']!r}")
            try:
                judgments[pair_id] = (parse_grade(row["grade"]), confidence)
            except ValueError as err:
                raise ValueError(f"{path.name}: pair {pair_id}: {err}") from err
    missing = sorted(set(pair_ids) - set(judgments))
    if missing:
        raise KeyError(f"{path.name}: no model judgment for {missing[0]} (and {len(missing) - 1} more)")
    return judgments


def main() -> int:
    parser = argparse.ArgumentParser(description="Score the operational dense-retrieval probe (Amendment A2)")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    provenance = json.loads((args.dir / "provenance_DO_NOT_OPEN.json").read_text(encoding="utf-8"))
    pair_ids = {pid: (d, p) for pid, (d, p) in provenance["pairs"].items()}
    common_ids = set(provenance["common_sample"])
    common = {pair_ids[pid] for pid in common_ids}

    judgments = read_model_judgments(args.dir / "model_judgments.csv", pair_ids)
    model = {pair_ids[pid]: grade for pid, (grade, _) in judgments.items()}
    escalated_ids = dp.escalation_pair_ids(judgments, common_ids)
    escalated = {pair_ids[pid] for pid in escalated_ids}

    human_common = read_sheet_grades(args.dir / "judging_sheet_B_common.csv", pair_ids)
    human_escalated = read_sheet_grades(args.dir / "escalation_sheet.csv", pair_ids)
    if set(human_escalated) != escalated:
        raise ValueError("escalation_sheet.csv does not cover exactly the escalated pairs")
    human = {**human_common, **human_escalated}
    labels = dp.final_labels(model, human, common | escalated)
    model_only = {pair: grade for pair, grade in model.items()}

    methods = provenance["methods"]

    def p5_for(label_map: Mapping[dp.Pair, dp.Label]) -> dict[str, dict[str, float | None]]:
        return {
            method: {d: dp.precision_at_5(d, lists[method], label_map) for d, lists in methods.items()}
            for method in ("bm25", "dense")
        }

    p5 = p5_for(labels)
    macro = dp.paired_macro(p5["bm25"], p5["dense"])
    kappa = dp.common_sample_kappa(model, human_common, common)
    outcome = dp.classify_outcome(macro.p5_dense, macro.p5_bm25, kappa.weighted_kappa)
    try:
        model_only_macro = dp.paired_macro(*p5_for(model_only).values())
        model_only_summary = {"p5_bm25": model_only_macro.p5_bm25, "p5_dense": model_only_macro.p5_dense}
    except (ValueError, KeyError):
        model_only_summary = None

    by_language: dict[str, dict[str, float]] = {}
    for language in sorted(set(provenance["demand_language"].values())):
        subset = {d for d, lang in provenance["demand_language"].items() if lang == language}
        try:
            sub = dp.paired_macro({d: p5["bm25"][d] for d in subset}, {d: p5["dense"][d] for d in subset})
            by_language[language] = {"p5_bm25": sub.p5_bm25, "p5_dense": sub.p5_dense, "n": sub.n_used}
        except ValueError:
            by_language[language] = {"n": 0}

    disagreements = sum(1 for p in common if model.get(p) is not None and human_common.get(p) is not None
                        and model[p] != human_common[p])
    result = {
        "judging_mode": "Amendment A2: model-first, human tie-break, agreement on 62-pair random common sample",
        "outcome": outcome.value,
        "p5_bm25": macro.p5_bm25,
        "p5_dense": macro.p5_dense,
        "delta": macro.delta,
        "n_demands_used": macro.n_used,
        "n_demands_dropped": macro.n_dropped,
        "weighted_kappa": kappa.weighted_kappa,
        "binary_kappa": kappa.binary_kappa,
        "kappa_pairs_used": kappa.n_used,
        "kappa_pairs_excluded": kappa.n_excluded,
        "common_sample_disagreements": disagreements,
        "pairs_total": len(pair_ids),
        "pairs_escalated_outside_common": len(escalated),
        "pairs_model_only": len(pair_ids) - len(common | escalated),
        "excluded_pairs_total": sum(1 for v in labels.values() if v is None),
        "model_only_labels_informative": model_only_summary,
        "short_lists": {m: sum(1 for lst in (methods[d][m] for d in methods) if len(lst) < dp.TOP_K) for m in ("bm25", "dense")},
        "by_language_stratum": by_language,
        "per_demand_p5": p5,
        "bootstrap_informative_only": dp.bootstrap_summary(p5["bm25"], p5["dense"]),
        "eligible_sizes": provenance["eligible_sizes"],
    }
    (args.dir / "probe_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"OUTCOME {outcome.value}: P@5 dense={macro.p5_dense:.3f} bm25={macro.p5_bm25:.3f} "
          f"delta={macro.delta:.3f} kappa_w={kappa.weighted_kappa:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
