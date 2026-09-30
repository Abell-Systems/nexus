"""Builds the human escalation sheet after the model has judged (spec Amendment A2).

Usage: python experiments/operational-dense-probe/build_escalation_sheet.py [--dir outputs]
Reads judging_sheet_A.csv (blinded content), judging_sheet_B_common.csv (which pairs are common) and
model_judgments.csv; writes escalation_sheet.csv with the pairs the human must grade beyond the common
sample. The sheet carries no model grade or confidence, and this script never opens the provenance file.
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402
from score_probe import parse_grade  # noqa: E402

DEFAULT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the human escalation sheet")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    with (args.dir / "judging_sheet_A.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = {row["pair_id"]: row for row in reader}
    with (args.dir / "judging_sheet_B_common.csv").open(newline="", encoding="utf-8") as handle:
        common_ids = {row["pair_id"] for row in csv.DictReader(handle)}
    judgments: dict[str, tuple[dp.Label, str]] = {}
    with (args.dir / "model_judgments.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            judgments[row["pair_id"]] = (parse_grade(row["grade"]), row["confidence"].strip().lower())
    missing = sorted(set(rows) - set(judgments))
    if missing:
        raise KeyError(f"No model judgment for {missing[0]} (and {len(missing) - 1} more)")

    escalated = dp.escalation_pair_ids(judgments, common_ids)
    with (args.dir / "escalation_sheet.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for pair_id in escalated:
            writer.writerow({**rows[pair_id], "grade": "", "note": ""})
    print(f"{len(escalated)} pairs escalated to the human (outside the {len(common_ids)}-pair common sample)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
