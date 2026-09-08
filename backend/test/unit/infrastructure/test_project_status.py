"""Unit tests and invariant assertions for Project Status Auditor (ADR 0022).

Enforces:
1. Formal conservative aggregation rule across required and optional dimensions.
2. Symmetrical status vocabulary (PASS, FAIL, SKIPPED, UNVERIFIED, N/A).
3. JSON schema v1.0.0 conformance (docs/schemas/project-status-v1.json).
4. Separation of evidence availability from evaluation result.
5. Deterministic markdown report generation.
"""

import json
import sys
from pathlib import Path

import jsonschema
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from audit_project_status import (  # noqa: E402
    REQ_OPTIONAL,
    REQ_REQUIRED,
    STATUS_FAIL,
    STATUS_NA,
    STATUS_PASS,
    STATUS_UNVERIFIED,
    CheckResult,
    DimensionResult,
    aggregate_overall_status,
    build_project_status,
    evaluate_coverage_xml,
    generate_markdown_report,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _REPO_ROOT / "docs" / "schemas" / "project-status-v1.json"


@pytest.fixture
def status_schema() -> dict:
    assert _SCHEMA_PATH.exists(), f"Schema missing at {_SCHEMA_PATH}"
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _make_dummy_dimension(
    status: str,
    req_level: str = REQ_REQUIRED,
    evidence_available: bool = True,
    evidence_source: str = "test/source",
) -> DimensionResult:
    return DimensionResult(
        status=status,
        requirement_level=req_level,
        evidence_source=evidence_source,
        evidence_available=evidence_available,
        message=f"Status is {status}",
        metrics={"count": 1},
        checks=[CheckResult(name="check1", status=status, value=1, detail="ok")],
    )


class TestConservativeAggregation:
    def test_all_required_pass_yields_overall_pass(self) -> None:
        dimensions = {
            "dim1": _make_dummy_dimension(STATUS_PASS, req_level=REQ_REQUIRED),
            "dim2": _make_dummy_dimension(STATUS_PASS, req_level=REQ_REQUIRED),
            "opt": _make_dummy_dimension(STATUS_UNVERIFIED, req_level=REQ_OPTIONAL),
        }
        overall, rule = aggregate_overall_status(dimensions)
        assert overall == STATUS_PASS
        assert "all required" in rule.lower()

    def test_any_required_fail_yields_overall_fail(self) -> None:
        dimensions = {
            "dim1": _make_dummy_dimension(STATUS_PASS, req_level=REQ_REQUIRED),
            "dim2": _make_dummy_dimension(STATUS_FAIL, req_level=REQ_REQUIRED),
            "dim3": _make_dummy_dimension(STATUS_UNVERIFIED, req_level=REQ_REQUIRED),
        }
        overall, rule = aggregate_overall_status(dimensions)
        assert overall == STATUS_FAIL
        assert "fail" in rule.lower()

    def test_unverified_required_yields_overall_unverified_when_no_fail(self) -> None:
        dimensions = {
            "dim1": _make_dummy_dimension(STATUS_PASS, req_level=REQ_REQUIRED),
            "dim2": _make_dummy_dimension(STATUS_UNVERIFIED, req_level=REQ_REQUIRED),
        }
        overall, rule = aggregate_overall_status(dimensions)
        assert overall == STATUS_UNVERIFIED
        assert "unverified" in rule.lower()

    def test_optional_unverified_does_not_block_overall_pass(self) -> None:
        dimensions = {
            "backend": _make_dummy_dimension(STATUS_PASS, req_level=REQ_REQUIRED),
            "sonar": _make_dummy_dimension(
                STATUS_UNVERIFIED, req_level=REQ_OPTIONAL, evidence_available=False
            ),
        }
        overall, _ = aggregate_overall_status(dimensions)
        assert overall == STATUS_PASS

    def test_na_does_not_participate_in_aggregation(self) -> None:
        dimensions = {
            "dim1": _make_dummy_dimension(STATUS_PASS, req_level=REQ_REQUIRED),
            "dim_na": _make_dummy_dimension(STATUS_NA, req_level=REQ_REQUIRED),
        }
        overall, _ = aggregate_overall_status(dimensions)
        assert overall == STATUS_PASS

    def test_empty_required_dimensions_yields_unverified(self) -> None:
        dimensions = {
            "opt": _make_dummy_dimension(STATUS_PASS, req_level=REQ_OPTIONAL),
        }
        overall, _ = aggregate_overall_status(dimensions)
        assert overall == STATUS_UNVERIFIED


class TestEvidenceEvaluation:
    def test_evaluate_coverage_xml_pass(self, tmp_path: Path) -> None:
        coverage_file = tmp_path / "coverage.xml"
        coverage_file.write_text(
            '<?xml version="1.0" ?><coverage line-rate="0.8542" branch-rate="0.75" />',
            encoding="utf-8",
        )
        res = evaluate_coverage_xml(coverage_file, threshold=0.80)
        assert res.status == STATUS_PASS
        assert res.evidence_available is True
        assert res.metrics["line_coverage"] == 85.42

    def test_evaluate_coverage_xml_fail(self, tmp_path: Path) -> None:
        coverage_file = tmp_path / "coverage.xml"
        coverage_file.write_text(
            '<?xml version="1.0" ?><coverage line-rate="0.7490" branch-rate="0.60" />',
            encoding="utf-8",
        )
        res = evaluate_coverage_xml(coverage_file, threshold=0.80)
        assert res.status == STATUS_FAIL
        assert res.evidence_available is True
        assert res.metrics["line_coverage"] == 74.9

    def test_evaluate_coverage_xml_missing(self, tmp_path: Path) -> None:
        missing_file = tmp_path / "nonexistent.xml"
        res = evaluate_coverage_xml(missing_file, threshold=0.80)
        assert res.status == STATUS_UNVERIFIED
        assert res.evidence_available is False


class TestSchemaValidationAndSerialization:
    def test_build_project_status_conforms_to_schema(self, status_schema: dict) -> None:
        payload = build_project_status(
            repo_root=_REPO_ROOT,
            commit_sha="db714eee6b79b7b767ac07e6abd4225b2220eadc",
            evaluated_at="2026-09-08T18:20:00Z",
        )
        jsonschema.validate(instance=payload, schema=status_schema)
        assert payload["schema_version"] == "1.0.0"
        assert payload["commit_sha"] == "db714eee6b79b7b767ac07e6abd4225b2220eadc"
        assert payload["overall_status"] in (STATUS_PASS, STATUS_FAIL, STATUS_UNVERIFIED)

    def test_generate_markdown_report_structure(self) -> None:
        payload = build_project_status(
            repo_root=_REPO_ROOT,
            commit_sha="db714eee6b79b7b767ac07e6abd4225b2220eadc",
            evaluated_at="2026-09-08T18:20:00Z",
        )
        md = generate_markdown_report(payload)
        assert "# Nexus Project Status" in md
        assert payload["commit_sha"] in md
        assert "## Dimensions Summary" in md
        assert "| Dimension |" in md
        assert "UNVERIFIED != PASS" in md
