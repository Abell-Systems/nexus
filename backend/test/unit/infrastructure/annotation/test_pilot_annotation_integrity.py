import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from domain.models.annotation import AnnotationJudgment


class TestPilotAnnotationIntegrity:
    """Scientific integrity and traceability tests for PR-E.1 pilot annotations (Annotator A)."""

    def _root_path(self) -> Path:
        # tests live in backend/test/unit/infrastructure/annotation/
        return Path(__file__).resolve().parents[5]

    def _load_canonical_json(self) -> list[dict]:
        path = self._root_path() / "data" / "annotations" / "judgments-A.json"
        assert path.exists(), f"Canonical JSON artifact missing at {path}"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_csv_rows(self) -> list[dict]:
        path = self._root_path() / "data" / "annotations" / "pilot_strict_annotation_valentin.csv"
        assert path.exists(), f"Working CSV sheet missing at {path}"
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _load_batch_json(self) -> dict:
        path = self._root_path() / "data" / "annotations" / "pilot_strict_annotation_batch.json"
        assert path.exists(), f"Frozen pilot batch missing at {path}"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_should_have_exactly_38_unique_pairs_in_canonical_json(self) -> None:
        judgments = self._load_canonical_json()
        assert len(judgments) == 38

        pairs = [(j["demand_id"], j["publication_id"]) for j in judgments]
        assert len(set(pairs)) == 38, "Duplicate (demand_id, publication_id) found in canonical JSON"

    def test_should_align_exactly_between_csv_and_canonical_json(self) -> None:
        csv_rows = self._load_csv_rows()
        json_judgments = self._load_canonical_json()

        assert len(csv_rows) == 38
        assert len(json_judgments) == 38

        for i, (row, j) in enumerate(zip(csv_rows, json_judgments, strict=True)):
            assert row["demand_id"] == j["demand_id"], f"Mismatch at index {i}: demand_id"
            assert row["publication_id"] == j["publication_id"], f"Mismatch at index {i}: publication_id"
            assert int(row["judgment"]) == j["grade"], f"Mismatch at index {i}: grade"

    def test_should_preserve_exact_batch_pair_order_and_identity(self) -> None:
        batch = self._load_batch_json()
        expected_pairs: list[tuple[str, str]] = []
        for demand in batch["demands"]:
            for entry in demand["entries"]:
                expected_pairs.append((demand["demand_id"], entry["publication_id"]))

        assert len(expected_pairs) == 38

        json_judgments = self._load_canonical_json()
        observed_pairs = [(j["demand_id"], j["publication_id"]) for j in json_judgments]

        assert observed_pairs == expected_pairs, "Canonical judgments do not match frozen batch order"

    def test_should_match_declared_grade_distribution(self) -> None:
        json_judgments = self._load_canonical_json()
        counts = Counter(j["grade"] for j in json_judgments)

        assert counts[0] == 31, f"Expected 31 grade 0, got {counts[0]}"
        assert counts[1] == 2, f"Expected 2 grade 1, got {counts[1]}"
        assert counts[2] == 4, f"Expected 4 grade 2, got {counts[2]}"
        assert counts[3] == 1, f"Expected 1 grade 3, got {counts[3]}"

    def test_should_have_matching_sha256_sidecar(self) -> None:
        json_path = self._root_path() / "data" / "annotations" / "judgments-A.json"
        sha_path = self._root_path() / "data" / "annotations" / "judgments-A.json.sha256"

        assert sha_path.exists(), f"SHA-256 sidecar missing at {sha_path}"

        computed = hashlib.sha256(json_path.read_bytes()).hexdigest()
        expected = sha_path.read_text(encoding="utf-8").strip().split()[0]

        assert computed == expected, f"SHA-256 mismatch: {computed} != {expected}"

    def test_should_have_audit_rationales_for_all_non_zero_grades(self) -> None:
        json_judgments = self._load_canonical_json()

        for j in json_judgments:
            grade = j["grade"]
            notes = j.get("notes", "")
            if grade in (1, 2, 3):
                assert len(notes) >= 20, (
                    f"Pair ({j['demand_id']}, {j['publication_id']}) with grade {grade} "
                    f"must include substantive audit notes (got '{notes}')"
                )

    def test_all_judgments_validate_against_domain_model(self) -> None:
        json_judgments = self._load_canonical_json()

        for j in json_judgments:
            validated = AnnotationJudgment(**j)
            assert validated.annotator_id == "valentin"
            assert validated.grade in (0, 1, 2, 3)
