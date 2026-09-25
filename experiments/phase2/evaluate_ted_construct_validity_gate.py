# experiments/phase2/evaluate_ted_construct_validity_gate.py
"""TED construct-validity classifier, step 4: validation-gate check.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS6/SS8. Reads the human labeling CSVs (valentin, lydia), adjudicates
disagreements, reads the LLM classification run, and evaluates the two-gate
decision rule. Refuses to run (raises) if any human labeling CSV still has
blank judgment cells -- this script must not silently treat "not yet labeled"
as a valid input."""

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.corpus.validation_gate import evaluate_validation_gate  # noqa: E402
from domain.models.corpus_expansion import TechnicalProblemClassification  # noqa: E402


def _read_labels(csv_path: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            labels[row["demand_id"]] = row["judgment"].strip()
    return labels


def _to_classification(raw: str, demand_id: str, annotator: str) -> TechnicalProblemClassification:
    key = raw.strip().upper()
    if not key:
        raise ValueError(
            f"BLOCKED: {annotator}'s labeling CSV has a blank judgment for {demand_id}. "
            "This script refuses to run against incomplete human labels."
        )
    for c in TechnicalProblemClassification:
        if key in (c.value.upper(), c.name):
            return c
    raise ValueError(f"{annotator}: unrecognized judgment {raw!r} for {demand_id}")


def evaluate(
    manifest_path: Path,
    valentin_csv: Path,
    lydia_csv: Path,
    llm_path: Path,
    adjudication_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    boundary_ids = frozenset(manifest["boundary_ids"])
    all_ids = set(manifest["all_ids"])
    actual_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    valentin_raw = _read_labels(valentin_csv)
    lydia_raw = _read_labels(lydia_csv)
    if set(valentin_raw) != all_ids or set(lydia_raw) != all_ids:
        raise ValueError("Labeling CSVs must cover exactly the control sample's demand_ids")

    valentin = {d: _to_classification(v, d, "valentin") for d, v in valentin_raw.items()}
    lydia = {d: _to_classification(v, d, "lydia") for d, v in lydia_raw.items()}

    disagreements = sorted(d for d in all_ids if valentin[d] != lydia[d])
    adjudication: dict[str, str] = {}
    if disagreements:
        if not adjudication_path.is_file():
            raise ValueError(
                f"BLOCKED: {len(disagreements)} disagreement(s) between valentin and lydia "
                f"({disagreements}) require an adjudication file at {adjudication_path}, none found."
            )
        adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
        missing = [d for d in disagreements if d not in adjudication]
        if missing:
            raise ValueError(f"Adjudication file is missing entries for: {missing}")

    reference: dict[str, TechnicalProblemClassification] = {}
    for d in all_ids:
        if d in adjudication:
            reference[d] = _to_classification(adjudication[d], d, "adjudication")
        else:
            reference[d] = valentin[d]

    llm_data = json.loads(llm_path.read_text(encoding="utf-8"))
    if llm_data["source_manifest_sha256"] != actual_manifest_sha256:
        raise ValueError(
            "LLM classification file was run against a different manifest than the one being evaluated "
            f"(expected sha256 {actual_manifest_sha256}, LLM file recorded {llm_data['source_manifest_sha256']})"
        )
    llm_labels = {d: _to_classification(v, d, "llm") for d, v in llm_data["classifications"].items()}
    if set(llm_labels) != all_ids:
        raise ValueError("LLM classification file must cover exactly the control sample's demand_ids")

    result = evaluate_validation_gate(reference, llm_labels, boundary_ids=boundary_ids)

    out = {
        "dataset_id": "nexus-ted-construct-validity-gate-decision-v1",
        "purpose": "TED construct-validity classifier validation-gate decision -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md SS8",
        "n_control_sample": len(all_ids),
        "n_disagreements_human": len(disagreements),
        "disagreement_ids": disagreements,
        "passed": result.passed,
        "recall_technical_problem": result.recall_technical_problem,
        "specificity_generic_procurement": result.specificity_generic_procurement,
        "boundary_false_positives": list(result.boundary_false_positives),
        "reason": result.reason,
        "note": (
            "This n=30 control sample is an acceptance gate for allowing automated "
            "classification, not a powered estimate of population-level classifier "
            "sensitivity or specificity (spec SS5/SS10)."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Gate decision: {'PASS' if result.passed else 'FAIL'} -- {result.reason}")
    return out


def main() -> int:
    evaluate(
        manifest_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json",
        valentin_csv=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_labeling_valentin.csv",
        lydia_csv=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_labeling_lydia.csv",
        llm_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_llm_classification.json",
        adjudication_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_adjudication.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_gate_decision.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
