"""#104 gold-set freeze: 96 exact-agreement pairs (Valentin==Lydia) + 12
adjudicated pairs (data/annotations/ted_at_scale_adjudication.json) = 108
gold relevance judgments on the 0-3 scale.

Adjudicated values are NOT re-derived here -- they were decided in the
adjudication step itself (same 0-3 contract, not recalibrated) and are read
verbatim from the adjudication file. This script only assembles and seals
the final gold set; it makes no judgment calls of its own.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def build_gold_set(
    valentin_path: Path,
    lydia_path: Path,
    adjudication_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    v_rows = _load_csv(valentin_path)
    l_rows = _load_csv(lydia_path)
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))

    adjudicated_by_key = {
        (d["demand_id"], d["publication_id"]): d for d in adjudication["decisions"]
    }

    gold_entries = []
    n_agreed = 0
    n_adjudicated = 0

    for vr, lr in zip(v_rows, l_rows):
        if vr["demand_id"] != lr["demand_id"] or vr["publication_id"] != lr["publication_id"]:
            raise ValueError(f"Row misalignment: {vr} vs {lr}")

        key = (vr["demand_id"], vr["publication_id"])
        v_score = int(vr["judgment"])
        l_score = int(lr["judgment"])

        if v_score == l_score:
            gold_score = v_score
            provenance = "exact_agreement"
            n_agreed += 1
        else:
            if key not in adjudicated_by_key:
                raise ValueError(f"Disagreement at {key} has no adjudication decision")
            decision = adjudicated_by_key[key]
            if decision["valentin"] != v_score or decision["lydia"] != l_score:
                raise ValueError(f"Adjudication record for {key} doesn't match source CSV scores")
            gold_score = decision["adjudicated"]
            provenance = "adjudicated"
            n_adjudicated += 1

        gold_entries.append({
            "demand_id": vr["demand_id"],
            "publication_id": vr["publication_id"],
            "title": vr["title"],
            "abstract": vr["abstract"],
            "classifications_cpc": vr["classifications_cpc"],
            "gold_judgment": gold_score,
            "provenance": provenance,
            "valentin_judgment": v_score,
            "lydia_judgment": l_score,
        })

    if n_agreed + n_adjudicated != len(adjudication["decisions"]) + n_agreed:
        raise AssertionError("Unreachable: sanity check on counts")
    if n_adjudicated != len(adjudication["decisions"]):
        raise ValueError(
            f"Adjudication count mismatch: {n_adjudicated} disagreements resolved "
            f"vs {len(adjudication['decisions'])} decisions on file"
        )

    dist = {str(s): sum(1 for e in gold_entries if e["gold_judgment"] == s) for s in range(4)}

    gold_set = {
        "dataset_id": "nexus-phase2-ted-annotation-gold-v1",
        "purpose": "GOLD_SET -- #104, frozen relevance judgments for BM25+CPC candidate-pool evaluation",
        "source_batch_dataset_id": "nexus-phase2-ted-annotation-at-scale-v1",
        "n_pairs": len(gold_entries),
        "n_exact_agreement": n_agreed,
        "n_adjudicated": n_adjudicated,
        "gold_judgment_distribution": dist,
        "contract_ambiguity_noted": adjudication["contract_ambiguity_noted"],
        "entries": gold_entries,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(gold_set, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    return gold_set


def main(argv: list[str] | None = None) -> int:
    result = build_gold_set(
        valentin_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_annotation_valentin.csv",
        lydia_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_annotation_lydia.csv",
        adjudication_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_adjudication.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_gold_set_v1.json",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "entries"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
