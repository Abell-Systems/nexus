"""Tests for scripts/publish_scientific_results.py — the first real scientific_results.json
snapshot (ADR 0025). Verifies the snapshot is a faithful publication of a real Head A
landscape execution, not fixture/hand-written data, and that the committed repo-root
artifact itself satisfies the contract.
"""

import inspect
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from application.landscape.clustering import compute_cluster_landscape
from domain.models.scientific_results import DISCOVERY_DISCLAIMER, ScientificResultsDocument, Track
from infrastructure.sources.bigquery_patents import get_patents_datasource
from infrastructure.sources.demand_sources import get_demand_datasource

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from publish_scientific_results import build_document, run_landscape_execution  # noqa: E402


class RealHeadALandscapeExecutionTest:
    """Proves the published clusters are exactly what Nexus's real landscape pipeline
    computes for the same input — not fixture JSON authored to look plausible."""

    def test_should_publish_clusters_matching_the_real_pipeline_output(self) -> None:
        domain = "solid_state_battery"
        query = "solid electrolyte"

        execution, landscape, _status = run_landscape_execution(
            domain=domain,
            query=query,
            max_patents=20,
            execution_id="test-exec-0001",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        patents_datasource = get_patents_datasource()
        demand_datasource = get_demand_datasource()
        expected = compute_cluster_landscape(
            patents=patents_datasource.search_patents(query=query, domain=domain, limit=20),
            demand_signals=demand_datasource.search_demand(query=query, domain=domain),
            domain=domain,
        )

        assert len(landscape.clusters) == len(expected)
        for observation, (expected_cluster, expected_metrics) in zip(landscape.clusters, expected, strict=True):
            assert observation.cluster == expected_cluster
            assert observation.density == expected_metrics["density"]
            assert observation.quadrant == expected_metrics["quadrant"]

        assert execution.track == Track.DISCOVERY

    def test_should_produce_execution_id_traceable_to_the_landscape_record(self) -> None:
        execution, landscape, _status = run_landscape_execution(
            domain="solid_state_battery",
            query="solid electrolyte",
            max_patents=20,
            execution_id="test-exec-0002",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert landscape.execution_id == execution.execution_id == "test-exec-0002"

    def test_should_not_fabricate_dataset_or_policy_metadata(self) -> None:
        execution, _landscape, _status = run_landscape_execution(
            domain="solid_state_battery",
            query="solid electrolyte",
            max_patents=20,
            execution_id="test-exec-0003",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert execution.dataset_id is None
        assert execution.dataset_version is None
        assert execution.policy_id is None
        assert execution.policy_version is None
        assert execution.policy_sha256 is None
        assert execution.engine_commit is None

    def test_should_preserve_representative_patents_as_ids_actually_returned_by_the_datasource(self) -> None:
        domain = "solid_state_battery"
        query = "solid electrolyte"
        patents_datasource = get_patents_datasource()
        real_patent_ids = {p.publication_number for p in patents_datasource.search_patents(query=query, domain=domain, limit=20)}

        _execution, landscape, _status = run_landscape_execution(
            domain=domain, query=query, max_patents=20, execution_id="test-exec-0004", created_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
        for observation in landscape.clusters:
            for rep_id in observation.cluster.representative_patents:
                assert rep_id in real_patent_ids

    def test_should_carry_the_exact_discovery_disclaimer(self) -> None:
        _execution, landscape, _provenance = run_landscape_execution(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            execution_id="test-exec-0005", created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert landscape.disclaimer == DISCOVERY_DISCLAIMER


class DatasourceProvenanceTest:
    """Bloqueante 1 (PR #74 review): a reader of scientific_results.json must be able
    to tell live from fixture data from the artifact itself, not from a CI log."""

    def test_should_publish_provenance_for_both_patents_and_demand_roles(self) -> None:
        execution, _landscape, provenance = run_landscape_execution(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            execution_id="test-exec-0006", created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        roles = {entry.role for entry in provenance}
        assert roles == {"patents", "demand"}
        assert execution.source_provenance == provenance

    def test_should_reuse_the_datasources_own_get_status_type_for_patents(self) -> None:
        patents_datasource = get_patents_datasource()
        expected_kind = patents_datasource.get_status()["type"]

        _execution, _landscape, provenance = run_landscape_execution(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            execution_id="test-exec-0007", created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        patents_entry = next(p for p in provenance if p.role == "patents")
        assert patents_entry.kind == expected_kind == "mock"

    def test_should_report_this_environments_datasources_as_mock_not_live(self) -> None:
        # This environment has no BigQuery/live demand credentials configured — the
        # published provenance must say so plainly, not imply live data.
        _execution, _landscape, provenance = run_landscape_execution(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            execution_id="test-exec-0008", created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        for entry in provenance:
            assert "mock" in entry.kind.lower()


class BuildDocumentDeterminismTest:
    def test_should_produce_equal_documents_for_the_same_input(self) -> None:
        fixed_time = datetime(2026, 1, 1, tzinfo=UTC)
        doc_a, _status_a = build_document(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            generated_at=fixed_time, execution_id="fixed-exec-id",
        )
        doc_b, _status_b = build_document(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            generated_at=fixed_time, execution_id="fixed-exec-id",
        )
        assert doc_a == doc_b

    def test_should_satisfy_the_scientific_results_document_contract(self) -> None:
        doc, _status = build_document(
            domain="solid_state_battery", query="solid electrolyte", max_patents=20,
            generated_at=datetime(2026, 1, 1, tzinfo=UTC), execution_id="contract-check",
        )
        # Constructing it already validated it (frozen pydantic model); re-validating
        # its dump proves round-tripping through JSON keeps it valid too.
        ScientificResultsDocument.model_validate(doc.model_dump(mode="json"))


class PublisherIsTheOnlyWriteBoundaryTest:
    """scripts/publish_scientific_results.py must not write scientific_results.json
    (or anything else) except through infrastructure.storage.scientific_results_publisher.
    publish_scientific_results — no ad hoc json.dump/write_text/open(...'w') calls."""

    def test_should_contain_no_ad_hoc_write_calls_in_the_script_source(self) -> None:
        import publish_scientific_results as script_module

        source = inspect.getsource(script_module)
        assert "publish_scientific_results(" in source
        forbidden = ["json.dump(", ".write_text(", "open(", "with open"]
        for pattern in forbidden:
            assert pattern not in source, f"found ad hoc write pattern {pattern!r} in publish_scientific_results.py"


class CommittedSnapshotTest:
    """Validates the actual scientific_results.json committed at the repo root by this PR."""

    def _snapshot_path(self) -> Path:
        return _REPO_ROOT / "scientific_results.json"

    def test_should_exist_as_a_sibling_of_project_status_json(self) -> None:
        snapshot_path = self._snapshot_path()
        project_status_path = _REPO_ROOT / "project_status.json"
        assert snapshot_path.exists()
        assert project_status_path.exists()
        assert snapshot_path != project_status_path

    def test_should_satisfy_the_scientific_results_document_contract(self) -> None:
        raw = json.loads(self._snapshot_path().read_text(encoding="utf-8"))
        document = ScientificResultsDocument.model_validate(raw)
        assert len(document.executions) == 1
        assert document.executions[0].track == Track.DISCOVERY

    def test_should_contain_exactly_one_discovery_execution_and_no_other_record_kinds(self) -> None:
        raw = json.loads(self._snapshot_path().read_text(encoding="utf-8"))
        document = ScientificResultsDocument.model_validate(raw)
        assert len(document.executions) == 1
        assert len(document.landscapes) == 1
        # No candidates/verifications/matches: this snapshot publishes only the
        # deterministic landscape sub-pipeline, honestly, per the module docstring.
        assert document.candidates == ()
        assert document.verifications == ()
        assert document.matches == ()

    def test_should_carry_the_discovery_disclaimer_on_its_landscape_record(self) -> None:
        raw = json.loads(self._snapshot_path().read_text(encoding="utf-8"))
        document = ScientificResultsDocument.model_validate(raw)
        assert document.landscapes[0].disclaimer == DISCOVERY_DISCLAIMER

    def test_should_not_fabricate_dataset_or_policy_metadata(self) -> None:
        raw = json.loads(self._snapshot_path().read_text(encoding="utf-8"))
        document = ScientificResultsDocument.model_validate(raw)
        execution = document.executions[0]
        assert execution.dataset_id is None
        assert execution.dataset_version is None
        assert execution.policy_id is None
        assert execution.policy_version is None
        assert execution.policy_sha256 is None

    def test_should_leave_project_status_json_carrying_no_scientific_result_fields(self) -> None:
        project_status = json.loads((_REPO_ROOT / "project_status.json").read_text(encoding="utf-8"))
        for forbidden_key in ("executions", "landscapes", "candidates", "verifications", "matches", "track"):
            assert forbidden_key not in project_status

    def test_should_publish_datasource_provenance_readable_without_a_ci_log(self) -> None:
        raw = json.loads(self._snapshot_path().read_text(encoding="utf-8"))
        document = ScientificResultsDocument.model_validate(raw)
        provenance = document.executions[0].source_provenance
        roles = {entry.role for entry in provenance}
        assert roles == {"patents", "demand"}
        assert all("mock" in entry.kind.lower() for entry in provenance)
