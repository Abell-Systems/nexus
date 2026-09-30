import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_probe as sp  # noqa: E402


class ParseGradeTest:
    @pytest.mark.parametrize("cell,expected", [("0", 0), ("1", 1), ("2", 2), ("3", 3), (" 3 ", 3)])
    def test_should_parse_integer_grade_when_cell_is_zero_to_three(self, cell, expected):
        assert sp.parse_grade(cell) == expected

    @pytest.mark.parametrize("cell", ["U", "u", " U "])
    def test_should_return_none_when_cell_marks_uncertain(self, cell):
        assert sp.parse_grade(cell) is None

    @pytest.mark.parametrize("cell", ["", "4", "-1", "2.5", "yes"])
    def test_should_raise_when_cell_is_empty_or_invalid(self, cell):
        with pytest.raises(ValueError):
            sp.parse_grade(cell)


class ReadSheetGradesTest:
    def test_should_map_pair_ids_to_pairs_and_grades_when_sheet_is_complete(self, tmp_path):
        path = tmp_path / "sheet.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade"])
            writer.writeheader()
            writer.writerow({"pair_id": "P001", "grade": "3"})
            writer.writerow({"pair_id": "P002", "grade": "U"})
        pairs = {"P001": ("D1", "ES-1-A1"), "P002": ("D1", "ES-2-A1")}
        assert sp.read_sheet_grades(path, pairs) == {("D1", "ES-1-A1"): 3, ("D1", "ES-2-A1"): None}

    def test_should_raise_when_any_grade_cell_is_left_empty(self, tmp_path):
        path = tmp_path / "sheet.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade"])
            writer.writeheader()
            writer.writerow({"pair_id": "P001", "grade": ""})
        with pytest.raises(ValueError, match="P001"):
            sp.read_sheet_grades(path, {"P001": ("D1", "ES-1-A1")})

    def test_should_raise_when_sheet_contains_unknown_pair_id(self, tmp_path):
        path = tmp_path / "sheet.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade"])
            writer.writeheader()
            writer.writerow({"pair_id": "P999", "grade": "2"})
        with pytest.raises(KeyError):
            sp.read_sheet_grades(path, {"P001": ("D1", "ES-1-A1")})


class ProbeEligibilityPolicyTest:
    def test_should_obtain_policy_from_the_single_factory_when_building_probe_sheets(self):
        source = (Path(__file__).resolve().parent / "build_probe_sheets.py").read_text(encoding="utf-8")
        assert "operational_eligibility_policy()" in source
        assert "DefaultPatentEligibilityPolicy" not in source


class ReadModelJudgmentsTest:
    def _write(self, tmp_path, rows):
        path = tmp_path / "model_judgments.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["pair_id", "grade", "confidence", "rationale"])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_should_map_grade_and_confidence_when_file_is_complete(self, tmp_path):
        path = self._write(tmp_path, [
            {"pair_id": "P001", "grade": "3", "confidence": "high", "rationale": "x"},
            {"pair_id": "P002", "grade": "U", "confidence": "low", "rationale": "y"},
        ])
        pairs = {"P001": ("D1", "ES-1-A1"), "P002": ("D1", "ES-2-A1")}
        assert sp.read_model_judgments(path, pairs) == {"P001": (3, "high"), "P002": (None, "low")}

    def test_should_raise_when_confidence_is_not_high_or_low(self, tmp_path):
        path = self._write(tmp_path, [{"pair_id": "P001", "grade": "2", "confidence": "medium", "rationale": ""}])
        with pytest.raises(ValueError, match="confidence"):
            sp.read_model_judgments(path, {"P001": ("D1", "ES-1-A1")})

    def test_should_raise_when_a_sheet_pair_has_no_model_judgment(self, tmp_path):
        path = self._write(tmp_path, [{"pair_id": "P001", "grade": "2", "confidence": "high", "rationale": ""}])
        with pytest.raises(KeyError, match="P002"):
            sp.read_model_judgments(path, {"P001": ("D1", "a"), "P002": ("D1", "b")})
