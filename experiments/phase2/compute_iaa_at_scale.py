"""#104 at-scale IAA: aligns the two independent annotator CSVs, computes the
0-3 judgment distribution per annotator, a 4x4 confusion matrix, Cohen's kappa
(unweighted and quadratic-weighted, since the scale is ordinal), and the list
of disagreements for adjudication.

Does not adjudicate anything itself -- that is a separate, later step once
disagreements are reviewed. Read-only with respect to both annotators' CSVs;
never modifies primary annotation data.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

SCALE = (0, 1, 2, 3)


def _load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _cohen_kappa(a: list[int], b: list[int], weighted: str | None = None) -> float:
    """weighted: None (unweighted), or 'quadratic'."""
    n = len(a)
    labels = SCALE
    k = len(labels)
    idx = {v: i for i, v in enumerate(labels)}

    confusion = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        confusion[idx[x]][idx[y]] += 1

    row_marg = [sum(row) for row in confusion]
    col_marg = [sum(confusion[i][j] for i in range(k)) for j in range(k)]

    if weighted is None:
        weights = [[0 if i == j else 1 for j in range(k)] for i in range(k)]
    elif weighted == "quadratic":
        weights = [[((i - j) ** 2) for j in range(k)] for i in range(k)]
    else:
        raise ValueError(weighted)

    max_w = max(max(row) for row in weights) or 1

    po = sum(
        (1 - weights[i][j] / max_w) * confusion[i][j]
        for i in range(k) for j in range(k)
    ) / n
    pe = sum(
        (1 - weights[i][j] / max_w) * row_marg[i] * col_marg[j] / (n * n)
        for i in range(k) for j in range(k)
    )

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def compute_iaa(
    valentin_path: Path,
    lydia_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    v_rows = _load(valentin_path)
    l_rows = _load(lydia_path)

    if len(v_rows) != len(l_rows):
        raise ValueError(f"Row count mismatch: valentin={len(v_rows)}, lydia={len(l_rows)}")

    for i, (vr, lr) in enumerate(zip(v_rows, l_rows)):
        if vr["demand_id"] != lr["demand_id"] or vr["publication_id"] != lr["publication_id"]:
            raise ValueError(
                f"Row {i} misaligned: valentin=({vr['demand_id']},{vr['publication_id']}) "
                f"lydia=({lr['demand_id']},{lr['publication_id']})"
            )
        if vr["judgment"] == "" or lr["judgment"] == "":
            raise ValueError(f"Row {i} ({vr['demand_id']},{vr['publication_id']}) has a blank judgment")

    v_scores = [int(r["judgment"]) for r in v_rows]
    l_scores = [int(r["judgment"]) for r in l_rows]

    def dist(scores: list[int]) -> dict[str, int]:
        return {str(s): scores.count(s) for s in SCALE}

    k = len(SCALE)
    confusion: list[list[int]] = [[0] * k for _ in range(k)]
    idx = {v: i for i, v in enumerate(SCALE)}
    for vs, ls in zip(v_scores, l_scores):
        confusion[idx[vs]][idx[ls]] += 1

    exact_agreement = sum(1 for vs, ls in zip(v_scores, l_scores) if vs == ls)
    within_one = sum(1 for vs, ls in zip(v_scores, l_scores) if abs(vs - ls) <= 1)

    disagreements = []
    for vr, lr, vs, ls in zip(v_rows, l_rows, v_scores, l_scores):
        if vs != ls:
            disagreements.append({
                "demand_id": vr["demand_id"],
                "publication_id": vr["publication_id"],
                "title": vr["title"],
                "valentin_judgment": vs,
                "lydia_judgment": ls,
                "abs_diff": abs(vs - ls),
            })
    disagreements.sort(key=lambda d: (-d["abs_diff"], d["demand_id"], d["publication_id"]))

    result = {
        "n_pairs": len(v_rows),
        "valentin_distribution": dist(v_scores),
        "lydia_distribution": dist(l_scores),
        "confusion_matrix": {
            "rows_are": "valentin",
            "cols_are": "lydia",
            "labels": list(SCALE),
            "matrix": confusion,
        },
        "exact_agreement_count": exact_agreement,
        "exact_agreement_rate": round(exact_agreement / len(v_rows), 4),
        "within_one_agreement_rate": round(within_one / len(v_rows), 4),
        "cohens_kappa_unweighted": round(_cohen_kappa(v_scores, l_scores, weighted=None), 4),
        "cohens_kappa_quadratic_weighted": round(_cohen_kappa(v_scores, l_scores, weighted="quadratic"), 4),
        "n_disagreements": len(disagreements),
        "disagreements": disagreements,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    result = compute_iaa(
        valentin_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_annotation_valentin.csv",
        lydia_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_annotation_lydia.csv",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_at_scale_iaa_report.json",
    )
    print(json.dumps(
        {k: v for k, v in result.items() if k != "disagreements"},
        indent=2, ensure_ascii=False,
    ))
    print(f"\n{result['n_disagreements']} disagreements -- see data/annotations/ted_at_scale_iaa_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
