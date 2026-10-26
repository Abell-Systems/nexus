import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from application.whitespace.completeness_gate import completeness_gate

ROOT = Path(__file__).resolve().parents[5]
EXPOSURE = ROOT / "docs" / "whitespace" / "oepm-corpus-exposure-results.json"


def cell(inventory: int, absent: int) -> dict:
    return {"inventory": inventory, "present": inventory - absent, "absent": absent}


def result(**groups: dict) -> dict:
    cells = {"ep_translation": cell(1000, 0), "kind_y": cell(1000, 0), "other": cell(1000, 0)} | groups
    return {"authority_file": {"name": "A.zip", "sha256": "ab" * 32}, "exposure": {"by_year": {"2025": cells}}}


def test_shouldAllowWhenEveryGroupIsWithinTheThreshold():
    decision = completeness_gate(result(other=cell(1000, 5)))
    assert decision["allowed"] is True
    assert decision["reasons"] == []
    assert decision["groups"]["other"]["within_threshold"] is True


GROUPS = ("ep_translation", "kind_y", "other")


@pytest.mark.parametrize("group", GROUPS)
def test_shouldAllowAtExactlyOnePercentInEachGroupWhenTheThresholdIsAtMost(group):
    assert completeness_gate(result(**{group: cell(1000, 10)}))["allowed"] is True


@pytest.mark.parametrize("group", GROUPS)
def test_shouldBlockJustAboveOnePercentInEachGroupEvenIfItRoundsToOne(group):
    decision = completeness_gate(result(**{group: cell(100000, 1001)}))  # 1.001 % would display as 1.0
    assert decision["allowed"] is False
    assert f"threshold exceeded: {group}" in decision["reasons"][0]


@pytest.mark.parametrize("group", GROUPS)
def test_shouldBlockWhenOnlyThatGroupExceedsTheThreshold(group):
    decision = completeness_gate(result(**{group: cell(1000, 11)}))
    assert decision["allowed"] is False
    others = [g for g in GROUPS if g != group]
    assert all(decision["groups"][g]["within_threshold"] for g in others)


@pytest.mark.parametrize("field", ["absent", "present", "inventory"])
@pytest.mark.parametrize(
    ("bad", "complement"),
    [(True, 999), (1.0, 999.0), (-1, 1001), ("1", 999)],
    ids=["bool", "float", "negative", "string"],
)
def test_shouldRejectTheTypeOfACountEvenWhenTheArithmeticStillAddsUp(field, bad, complement):
    """present + absent == inventory holds numerically, so only the type check can reject these."""
    inventory = 1000
    cells = {"inventory": inventory, "present": 999, "absent": 1}
    if field == "inventory":
        cells = {"inventory": bad, "present": 999, "absent": 1}
    else:
        other = "present" if field == "absent" else "absent"
        cells[field], cells[other] = bad, complement
    decision = completeness_gate(result(other=cells))
    assert decision["allowed"] is False
    assert "other has no valid counts" in decision["reasons"][0]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["exposure"]["by_year"].pop("2025"),
        lambda r: r["exposure"]["by_year"]["2025"].pop("kind_y"),
        lambda r: r["exposure"]["by_year"]["2025"]["other"].pop("absent"),
        lambda r: r["exposure"]["by_year"]["2025"]["other"].update(inventory=0, present=0, absent=0),
        lambda r: r["exposure"]["by_year"]["2025"]["other"].update(present=1),
        lambda r: r.pop("authority_file"),
        lambda r: r["authority_file"].pop("sha256"),
        lambda r: r["authority_file"].update(name="   "),
        lambda r: r["authority_file"].update(sha256=""),
        lambda r: r["authority_file"].update(name=1),
        lambda r: r["authority_file"].update(sha256=True),
        lambda r: r.update(authority_file=["A.zip"]),
        lambda r: r.pop("exposure"),
    ],
)
def test_shouldBlockWhenTheMeasurementIsMissingInvalidOrInconsistent(mutate):
    data = copy.deepcopy(result())
    mutate(data)
    decision = completeness_gate(data)
    assert decision["allowed"] is False
    assert decision["reasons"]
    assert all(reason.startswith(("not measurable", "threshold exceeded")) for reason in decision["reasons"])


def test_shouldBlockWithoutAnyFigureWhenTheResultIsEmpty():
    assert completeness_gate({})["allowed"] is False


def test_shouldBlockAnotherYearThatIsNotInTheResult():
    assert completeness_gate(result(), year=2030)["allowed"] is False


def test_shouldNeverTreatAMissingValueAsFavourable():
    data = result()
    data["exposure"]["by_year"]["2025"]["other"] = {}
    assert completeness_gate(data)["allowed"] is False


def test_shouldStateTheCaveatAndTheInventoryInTheDecision():
    decision = completeness_gate(result())
    assert "OEPM inventory" in decision["caveat"]
    assert decision["inventory"]["sha256"] == "ab" * 32


def test_shouldAllowWithTheVersionedExposureResultAtTheReferenceYear():
    decision = completeness_gate(json.loads(EXPOSURE.read_text(encoding="utf-8")))
    assert decision["allowed"] is True
    assert set(decision["groups"]) == {"ep_translation", "kind_y", "other"}


def test_shouldExitNonZeroFromTheScriptWhenTheFileIsMissing(tmp_path):
    script = ROOT / "scripts" / "check_vertical3_completeness.py"
    run = subprocess.run(
        [sys.executable, str(script), "--exposure", str(tmp_path / "missing.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1
    assert '"allowed": false' in run.stdout


def test_shouldExitZeroFromTheScriptWithTheVersionedResult():
    script = ROOT / "scripts" / "check_vertical3_completeness.py"
    run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
    assert run.returncode == 0


def test_shouldBlockWithADiagnosticAndNoTracebackWhenTheJsonIsNestedBeyondTheParser(tmp_path):
    script = ROOT / "scripts" / "check_vertical3_completeness.py"
    nested = tmp_path / "nested.json"
    nested.write_text("[" * 200000, encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(script), "--exposure", str(nested)], capture_output=True, text=True, check=False
    )
    assert run.returncode == 1
    assert '"allowed": false' in run.stdout
    assert "blocked:" in run.stderr
    assert "Traceback" not in run.stderr


def test_shouldBlockWhenTheJsonRootIsNotAnObject(tmp_path):
    script = ROOT / "scripts" / "check_vertical3_completeness.py"
    root = tmp_path / "list.json"
    root.write_text("[]", encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(script), "--exposure", str(root)], capture_output=True, text=True, check=False
    )
    assert run.returncode == 1
