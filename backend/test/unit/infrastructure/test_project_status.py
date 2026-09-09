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

import pytest

try:
    import jsonschema
except ImportError:
    jsonschema = None

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from audit_project_status import (  # noqa: E402
    ALLOWED_SOURCE_EVENTS,
    README_STATUS_END,
    README_STATUS_START,
    REQ_OPTIONAL,
    REQ_REQUIRED,
    STATUS_FAIL,
    STATUS_NA,
    STATUS_PASS,
    STATUS_SKIPPED,
    STATUS_UNVERIFIED,
    CheckResult,
    DimensionResult,
    aggregate_overall_status,
    append_history_entry,
    build_history_entry,
    build_project_status,
    evaluate_backend_testing,
    evaluate_coverage_xml,
    evaluate_frontend_testing,
    evaluate_scientific_integrity,
    generate_markdown_report,
    generate_readme_status_snippet,
    parse_junit_xml,
    status_badge_color,
    update_readme_status,
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

    def test_parse_junit_xml_valid(self, tmp_path: Path) -> None:
        report = tmp_path / "sample-junit.xml"
        report.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuites name="test">\n'
            '  <testsuite name="suite1" tests="10" failures="1" errors="0" skipped="2" />\n'
            '  <testsuite name="suite2" tests="5" failures="0" errors="0" skipped="0" />\n'
            '</testsuites>',
            encoding="utf-8",
        )
        metrics = parse_junit_xml(report)
        assert metrics["total"] == 15
        assert metrics["failed"] == 1
        assert metrics["errors"] == 0
        assert metrics["skipped"] == 2
        assert metrics["passed"] == 12

    def test_evaluate_backend_testing_pass(self, tmp_path: Path) -> None:
        test_dir = tmp_path / "test-results"
        test_dir.mkdir()
        (test_dir / "unit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuite name="unit" tests="100" failures="0" errors="0" skipped="2" />',
            encoding="utf-8",
        )
        (test_dir / "integration.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuite name="integration" tests="50" failures="0" errors="0" skipped="0" />',
            encoding="utf-8",
        )
        res = evaluate_backend_testing(tmp_path)
        assert res.status == STATUS_PASS
        assert res.evidence_available is True
        assert res.metrics["total"] == 150
        assert res.metrics["passed"] == 148
        assert res.metrics["failed"] == 0
        assert res.metrics["errors"] == 0
        assert res.metrics["skipped"] == 2

    def test_evaluate_backend_testing_fail_when_failures_exist(self, tmp_path: Path) -> None:
        test_dir = tmp_path / "test-results"
        test_dir.mkdir()
        (test_dir / "unit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuite name="unit" tests="100" failures="2" errors="1" skipped="0" />',
            encoding="utf-8",
        )
        res = evaluate_backend_testing(tmp_path)
        assert res.status == STATUS_FAIL
        assert res.evidence_available is True
        assert res.metrics["failed"] == 2
        assert res.metrics["errors"] == 1
        assert "3 failures, 1 errors" not in res.message  # Check exact message format
        assert "failed: 2 failures, 1 errors" in res.message

    def test_evaluate_backend_testing_unverified_when_only_coverage_exists(self, tmp_path: Path) -> None:
        """Blocker 1 Invariant: coverage.xml alone is NOT affirmative evidence of test completion."""
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0" ?><coverage line-rate="0.85" />', encoding="utf-8"
        )
        res = evaluate_backend_testing(tmp_path)
        assert res.status == STATUS_UNVERIFIED
        assert res.evidence_available is False
        assert "unverified" in res.message.lower()

    def test_evaluate_backend_testing_fails_when_zero_tests(self, tmp_path: Path) -> None:
        test_dir = tmp_path / "test-results"
        test_dir.mkdir()
        (test_dir / "unit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuite name="unit" tests="0" failures="0" errors="0" skipped="0" />',
            encoding="utf-8",
        )
        res = evaluate_backend_testing(tmp_path)
        assert res.status == STATUS_FAIL
        assert "0 executed tests" in res.message

    def test_evaluate_frontend_testing_pass(self, tmp_path: Path) -> None:
        cov_dir = tmp_path / "frontend" / "coverage"
        cov_dir.mkdir(parents=True)
        (cov_dir / "junit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuites name="vitest tests" tests="40" failures="0" errors="0">\n'
            '  <testsuite name="suite" tests="40" failures="0" errors="0" skipped="0" />\n'
            '</testsuites>',
            encoding="utf-8",
        )
        res = evaluate_frontend_testing(tmp_path)
        assert res.status == STATUS_PASS
        assert res.evidence_available is True
        assert res.metrics["total"] == 40
        assert res.metrics["passed"] == 40
        assert res.metrics["failed"] == 0

    def test_evaluate_frontend_testing_unverified_when_only_lcov_exists(self, tmp_path: Path) -> None:
        """Blocker 1 Invariant: lcov.info alone is NOT affirmative evidence of test completion."""
        cov_dir = tmp_path / "frontend" / "coverage"
        cov_dir.mkdir(parents=True)
        (cov_dir / "lcov.info").write_text("TN:\nSF:test.ts\nLF:10\nLH:10\nend_of_record\n", encoding="utf-8")
        res = evaluate_frontend_testing(tmp_path)
        assert res.status == STATUS_UNVERIFIED
        assert res.evidence_available is False

    def test_evaluate_frontend_testing_fail(self, tmp_path: Path) -> None:
        cov_dir = tmp_path / "frontend" / "coverage"
        cov_dir.mkdir(parents=True)
        (cov_dir / "junit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuites name="vitest tests" tests="40" failures="3" errors="0">\n'
            '  <testsuite name="suite" tests="40" failures="3" errors="0" skipped="0" />\n'
            '</testsuites>',
            encoding="utf-8",
        )
        res = evaluate_frontend_testing(tmp_path)
        assert res.status == STATUS_FAIL
        assert res.evidence_available is True
        assert res.metrics["failed"] == 3

    def test_evaluate_scientific_integrity_pass_with_frozen_exceptions(self) -> None:
        """Scientific integrity evaluates to PASS when manifests match and temporal violations are frozen exceptions."""
        res = evaluate_scientific_integrity(_REPO_ROOT)
        assert res.status == STATUS_PASS
        assert res.evidence_available is True
        # Check that temporal_eligibility is explicitly marked SKIPPED (not FAIL, not undocumented PASS)
        temporal_checks = [c for c in res.checks if c.name == "temporal_eligibility"]
        assert len(temporal_checks) == 1
        assert temporal_checks[0].status == STATUS_SKIPPED
        assert "ADR-0018" in temporal_checks[0].detail or "ADR 0018" in temporal_checks[0].detail
        # Invariant: NO check within a PASS dimension may have status FAIL
        assert all(c.status != STATUS_FAIL for c in res.checks), "Found FAIL check within PASS scientific_integrity!"

    def test_evaluate_scientific_integrity_fails_when_unexpected_violations_exist(
        self, tmp_path: Path
    ) -> None:
        """Scientific integrity evaluates to FAIL if an unknown/unexempted violation is present."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        mock_audit = scripts_dir / "audit_dataset_identity.py"
        mock_audit.write_text(
            'import json, sys, argparse\n'
            'p = argparse.ArgumentParser()\n'
            'p.add_argument("--output", type=str)\n'
            'args = p.parse_args()\n'
            'report = {\n'
            '    "temporal_violations": [\n'
            '        {"demand_id": "NEW-DEMAND", "publication_id": "NEW-PATENT"}\n'
            '    ],\n'
            '    "checks": [\n'
            '        {"check": "dataset_sha_manifest", "status": "PASS", "detail": "ok"},\n'
            '        {"check": "temporal_eligibility", "status": "FAIL", "detail": "1 violation"}\n'
            '    ]\n'
            '}\n'
            'with open(args.output, "w") as f: json.dump(report, f)\n',
            encoding="utf-8",
        )
        res = evaluate_scientific_integrity(tmp_path)
        assert res.status == STATUS_FAIL
        temporal_checks = [c for c in res.checks if c.name == "temporal_eligibility"]
        assert len(temporal_checks) == 1
        assert temporal_checks[0].status == STATUS_FAIL

    def test_evaluate_scientific_integrity_missing_script(self, tmp_path: Path) -> None:
        res = evaluate_scientific_integrity(tmp_path)
        assert res.status == STATUS_UNVERIFIED
        assert res.evidence_available is False


class TestSchemaValidationAndSerialization:
    def test_build_project_status_conforms_to_schema(self, status_schema: dict) -> None:
        if jsonschema is None:
            pytest.skip("jsonschema not installed in current environment")
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


class TestHistoricalTelemetry:
    @pytest.fixture
    def sample_payload(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "commit_sha": "e6dccbe123456789abcdef0123456789abcdef01",
            "evaluated_at": "2026-09-08T18:25:00Z",
            "overall_status": STATUS_PASS,
            "aggregation_rule": "all required pass",
            "summary": "Sample summary",
            "dimensions": {
                "backend_coverage": {
                    "status": STATUS_PASS,
                    "requirement_level": REQ_REQUIRED,
                    "evidence_source": "coverage.xml",
                    "evidence_available": True,
                    "metrics": {"line_coverage": 85.0},
                    "checks": [],
                },
                "sonar_cloud": {
                    "status": STATUS_UNVERIFIED,
                    "requirement_level": REQ_OPTIONAL,
                    "evidence_source": "environment",
                    "evidence_available": False,
                    "metrics": {},
                    "checks": [],
                },
            },
        }

    def test_build_history_entry_conforms_to_spec(self, sample_payload: dict) -> None:
        entry = build_history_entry(sample_payload, source_event="ci_audit")
        assert entry["schema_version"] == "1.0.0"
        assert entry["commit_sha"] == "e6dccbe123456789abcdef0123456789abcdef01"
        assert entry["evaluated_at"] == "2026-09-08T18:25:00Z"
        assert entry["overall_status"] == STATUS_PASS
        assert entry["aggregation_rule"] == "all required pass"
        assert entry["source_event"] == "ci_audit"
        assert entry["dimension_statuses"] == {
            "backend_coverage": STATUS_PASS,
            "sonar_cloud": STATUS_UNVERIFIED,
        }
        assert entry["metrics"] == {"backend_coverage.line_coverage": 85.0}

    def test_build_history_entry_rejects_uncontrolled_source_event(self, sample_payload: dict) -> None:
        with pytest.raises(ValueError, match="Invalid source_event"):
            build_history_entry(sample_payload, source_event="unauthorized_random_trigger")

    def test_allowed_source_events_set(self) -> None:
        assert "manual_audit" in ALLOWED_SOURCE_EVENTS
        assert "ci_audit" in ALLOWED_SOURCE_EVENTS
        assert "release_audit" in ALLOWED_SOURCE_EVENTS

    def test_append_history_entry_appends_and_preserves_previous(
        self, tmp_path: Path, sample_payload: dict
    ) -> None:
        history_file = tmp_path / "telemetry" / "history.jsonl"

        entry1 = build_history_entry(sample_payload, source_event="manual_audit")
        appended1 = append_history_entry(history_file, entry1)
        assert appended1 is True
        assert history_file.exists()

        payload2 = dict(sample_payload)
        payload2["commit_sha"] = "ffffffffffffffffffffffffffffffffffffffff"
        entry2 = build_history_entry(payload2, source_event="manual_audit")
        appended2 = append_history_entry(history_file, entry2)
        assert appended2 is True

        lines = history_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        record1 = json.loads(lines[0])
        record2 = json.loads(lines[1])
        assert record1["commit_sha"] == sample_payload["commit_sha"]
        assert record2["commit_sha"] == "ffffffffffffffffffffffffffffffffffffffff"

    def test_append_history_entry_idempotency(
        self, tmp_path: Path, sample_payload: dict
    ) -> None:
        history_file = tmp_path / "telemetry" / "history.jsonl"

        entry = build_history_entry(sample_payload, source_event="ci_audit")
        assert append_history_entry(history_file, entry) is True
        # Second identical append must be skipped
        assert append_history_entry(history_file, entry) is False

        lines = history_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_append_history_entry_force_allows_duplicate(
        self, tmp_path: Path, sample_payload: dict
    ) -> None:
        history_file = tmp_path / "telemetry" / "history.jsonl"

        entry = build_history_entry(sample_payload, source_event="ci_audit")
        assert append_history_entry(history_file, entry) is True
        assert append_history_entry(history_file, entry, force=True) is True

        lines = history_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_history_does_not_alter_overall_status(
        self, tmp_path: Path, sample_payload: dict
    ) -> None:
        history_file = tmp_path / "telemetry" / "history.jsonl"
        original_status = sample_payload["overall_status"]

        entry = build_history_entry(sample_payload, source_event="manual_audit")
        append_history_entry(history_file, entry)

        # Invariant 1: history is secondary output, overall_status cannot be changed
        assert sample_payload["overall_status"] == original_status


class TestReadmeObservatory:
    def test_generate_readme_status_snippet(self) -> None:
        payload = {
            "schema_version": "1.0.0",
            "commit_sha": "abcdef1234567890abcdef1234567890abcdef12",
            "evaluated_at": "2026-09-08T18:30:00Z",
            "overall_status": STATUS_PASS,
            "aggregation_rule": "all required pass",
            "dimensions": {
                "architecture": {"status": STATUS_PASS},
                "backend_testing": {
                    "status": STATUS_PASS,
                    "checks": [{"value": 566}],
                },
                "backend_coverage": {
                    "status": STATUS_PASS,
                    "metrics": {"line_coverage": 80.24},
                },
                "documentation": {"status": STATUS_PASS},
                "scientific_integrity": {"status": STATUS_PASS},
                "sonar_cloud": {"status": STATUS_UNVERIFIED},
            },
        }

        snippet = generate_readme_status_snippet(payload)
        assert README_STATUS_START in snippet
        assert README_STATUS_END in snippet
        assert "Project_Status-PASS" in snippet
        assert "Tests-566_passed" in snippet
        assert "Coverage-80.24%25" in snippet
        assert "SonarCloud-UNVERIFIED-yellow" in snippet
        assert "Scientific_Dashboard-Live-blue" in snippet
        assert "Verified against:** `abcdef1234` · `2026-09-08T18:30:00Z`" in snippet
        assert "https://abell-systems.github.io/nexus/" in snippet

    def test_update_readme_status_success(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Title\n\n"
            f"{README_STATUS_START}\nOld content\n{README_STATUS_END}\n\n"
            "## Section\nContent",
            encoding="utf-8",
        )
        payload = {
            "schema_version": "1.0.0",
            "commit_sha": "abcdef1234567890",
            "evaluated_at": "2026-09-08T18:30:00Z",
            "overall_status": STATUS_PASS,
            "dimensions": {},
        }
        res = update_readme_status(readme, payload)
        assert res is True
        content = readme.read_text(encoding="utf-8")
        assert "Old content" not in content
        assert "Project_Status-PASS" in content
        assert "## Section\nContent" in content

    def test_update_readme_status_missing_delimiters(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# Title\nNo delimiters", encoding="utf-8")
        res = update_readme_status(readme, {"overall_status": STATUS_PASS})
        assert res is False
        assert readme.read_text(encoding="utf-8") == "# Title\nNo delimiters"

    def test_status_badge_color_mapping(self) -> None:
        assert status_badge_color(STATUS_PASS) == "brightgreen"
        assert status_badge_color(STATUS_FAIL) == "red"
        assert status_badge_color(STATUS_UNVERIFIED) == "yellow"
        assert status_badge_color(STATUS_NA) == "lightgrey"

    def test_generate_readme_status_snippet_zero_green_fallbacks_on_empty_payload(self) -> None:
        """Blocker 3 Invariant: Empty payload MUST NEVER render default green, 566, or 80.0%."""
        payload = {
            "schema_version": "1.0.0",
            "commit_sha": "0123456789abcdef",
            "evaluated_at": "2026-09-08T18:30:00Z",
            "overall_status": STATUS_UNVERIFIED,
            "dimensions": {},
        }
        snippet = generate_readme_status_snippet(payload)
        assert "brightgreen" not in snippet, "Snippet leaked brightgreen with empty dimensions!"
        assert "566" not in snippet, "Snippet leaked hardcoded 566 test count!"
        assert "80.0" not in snippet, "Snippet leaked hardcoded 80.0 coverage!"
        assert "Project_Status-UNVERIFIED-yellow" in snippet
        assert "CI_Gates-UNVERIFIED-yellow" in snippet
        assert "Architecture-UNVERIFIED-yellow" in snippet
        assert "Tests-UNVERIFIED-yellow" in snippet
        assert "Coverage-UNVERIFIED-yellow" in snippet
        assert "Docs-UNVERIFIED-yellow" in snippet
        assert "Scientific_Integrity-UNVERIFIED-yellow" in snippet
        assert "SonarCloud-UNVERIFIED-yellow" in snippet

    def test_generate_readme_status_snippet_renders_fail_accurately(self) -> None:
        """Verifies failed dimensions render as red with explicit failed status/metrics."""
        payload = {
            "schema_version": "1.0.0",
            "commit_sha": "0123456789abcdef",
            "evaluated_at": "2026-09-08T18:30:00Z",
            "overall_status": STATUS_FAIL,
            "dimensions": {
                "backend_testing": {"status": STATUS_FAIL},
                "backend_coverage": {"status": STATUS_FAIL, "metrics": {"line_coverage": 73.5}},
                "architecture": {"status": STATUS_FAIL},
            },
        }
        snippet = generate_readme_status_snippet(payload)
        assert "Project_Status-FAIL-red" in snippet
        assert "CI_Gates-FAIL-red" in snippet
        assert "Architecture-FAIL-red" in snippet
        assert "Tests-FAIL-red" in snippet
        assert "Coverage-73.5%25-red" in snippet
