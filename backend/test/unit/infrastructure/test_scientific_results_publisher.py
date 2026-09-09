import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.scientific_results import ScientificResultsDocument, ScientificResultsExecution, Track
from infrastructure.storage.scientific_results_publisher import (
    ScientificResultsPublicationError,
    canonical_scientific_results_json,
    publish_scientific_results,
)


def _execution(**overrides) -> ScientificResultsExecution:
    defaults = {
        "execution_id": "exec-0001",
        "track": Track.DISCOVERY,
        "domain": "solid_state_battery",
        "query": "improve dendrite suppression",
        "created_at": datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return ScientificResultsExecution(**defaults)


def _document(**overrides) -> ScientificResultsDocument:
    defaults = {
        "schema_version": "0.1.0",
        "generated_at": datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
        "executions": (_execution(),),
    }
    defaults.update(overrides)
    return ScientificResultsDocument(**defaults)


class CanonicalSerializationTest:
    def test_should_produce_utf8_json_bytes_when_document_is_valid(self) -> None:
        encoded = canonical_scientific_results_json(_document())
        assert isinstance(encoded, bytes)
        decoded = json.loads(encoded.decode("utf-8"))
        assert decoded["schema_version"] == "0.1.0"

    def test_should_sort_keys_when_serializing(self) -> None:
        encoded = canonical_scientific_results_json(_document()).decode("utf-8")
        # "executions" < "generated_at" < "schema_version" alphabetically at the top level.
        assert encoded.index('"executions"') < encoded.index('"generated_at"') < encoded.index('"schema_version"')

    def test_should_produce_byte_identical_output_for_equivalent_documents_built_differently(self) -> None:
        doc_a = ScientificResultsDocument(
            schema_version="0.1.0",
            generated_at=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
            executions=(_execution(execution_id="e1"), _execution(execution_id="e2")),
        )
        # Same content, executions supplied in reversed construction order.
        doc_b = ScientificResultsDocument(
            executions=(_execution(execution_id="e1"), _execution(execution_id="e2")),
            generated_at=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
            schema_version="0.1.0",
        )
        assert canonical_scientific_results_json(doc_a) == canonical_scientific_results_json(doc_b)


class PublishScientificResultsTest:
    def test_should_publish_valid_document_producing_exact_expected_json(self, tmp_path: Path) -> None:
        document = _document()
        target = tmp_path / "scientific_results.json"

        result_path = publish_scientific_results(document, target)

        assert result_path == target
        assert target.exists()
        assert target.read_bytes() == canonical_scientific_results_json(document)

    def test_should_publish_when_given_a_raw_mapping_instead_of_a_document_instance(self, tmp_path: Path) -> None:
        raw_payload = {
            "schema_version": "0.1.0",
            "generated_at": "2026-09-09T12:00:00Z",
            "executions": [
                {
                    "execution_id": "exec-0001",
                    "track": "discovery",
                    "domain": "solid_state_battery",
                    "query": "improve dendrite suppression",
                    "created_at": "2026-09-09T12:00:00Z",
                }
            ],
        }
        target = tmp_path / "scientific_results.json"

        publish_scientific_results(raw_payload, target)

        published = json.loads(target.read_text(encoding="utf-8"))
        assert published["executions"][0]["execution_id"] == "exec-0001"
        assert published["executions"][0]["track"] == "discovery"

    def test_should_reject_invalid_mapping_payload_without_writing_anything(self, tmp_path: Path) -> None:
        invalid_payload = {"generated_at": "2026-09-09T12:00:00Z"}  # missing schema_version
        target = tmp_path / "scientific_results.json"

        with pytest.raises(ScientificResultsPublicationError):
            publish_scientific_results(invalid_payload, target)

        assert not target.exists()
        assert list(tmp_path.iterdir()) == []

    def test_should_reject_invalid_payload_when_track_is_not_discovery_or_verification(self, tmp_path: Path) -> None:
        invalid_payload = {
            "schema_version": "0.1.0",
            "generated_at": "2026-09-09T12:00:00Z",
            "executions": [
                {
                    "execution_id": "exec-0001",
                    "track": "synthesis",
                    "domain": "solid_state_battery",
                    "query": "q",
                    "created_at": "2026-09-09T12:00:00Z",
                }
            ],
        }
        target = tmp_path / "scientific_results.json"

        with pytest.raises(ScientificResultsPublicationError):
            publish_scientific_results(invalid_payload, target)
        assert not target.exists()

    def test_should_leave_existing_target_unchanged_when_write_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "scientific_results.json"
        original_document = _document(executions=(_execution(execution_id="original"),))
        publish_scientific_results(original_document, target)
        original_bytes = target.read_bytes()

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("simulated atomic-replace failure")

        monkeypatch.setattr(os, "replace", _boom)

        new_document = _document(executions=(_execution(execution_id="should-not-land"),))
        with pytest.raises(OSError, match="simulated atomic-replace failure"):
            publish_scientific_results(new_document, target)

        assert target.read_bytes() == original_bytes

    def test_should_not_leave_a_temporary_file_behind_when_write_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "scientific_results.json"

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("simulated atomic-replace failure")

        monkeypatch.setattr(os, "replace", _boom)

        with pytest.raises(OSError):
            publish_scientific_results(_document(), target)

        assert not target.exists()
        leftover = list(tmp_path.iterdir())
        assert leftover == [], f"expected no leftover temp files, found: {leftover}"

    def test_should_not_mutate_supplied_document(self, tmp_path: Path) -> None:
        document = _document()
        before = document.model_dump(mode="json")

        publish_scientific_results(document, tmp_path / "scientific_results.json")

        assert document.model_dump(mode="json") == before

    def test_should_write_target_as_sibling_never_touching_project_status_json(self, tmp_path: Path) -> None:
        project_status_path = tmp_path / "project_status.json"
        project_status_path.write_text('{"untouched": true}', encoding="utf-8")

        target = tmp_path / "scientific_results.json"
        publish_scientific_results(_document(), target)

        assert project_status_path.read_text(encoding="utf-8") == '{"untouched": true}'
        assert target.exists()
        assert target != project_status_path

    def test_should_raise_scientific_results_publication_error_not_bare_validation_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(ScientificResultsPublicationError) as exc_info:
            publish_scientific_results({}, tmp_path / "scientific_results.json")
        assert not isinstance(exc_info.value, ValidationError)
