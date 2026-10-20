from datetime import date

import pytest
from pydantic import ValidationError

from domain.models.whitespace import (
    IpcEntry,
    PatentPublication,
    RejectedRecord,
    SourceAnomaly,
    SourceRecordProvenance,
)

PROVENANCE = SourceRecordProvenance(
    source_file="BIBLIO_2020.zip", file_sha256="a" * 64, archive_path="m.zip/d.zip/x.xml"
)


def publication(**overrides) -> PatentPublication:
    values = {"country": "ES", "doc_number": "2738048", "kind": "T3", "publication_date": date(2020, 1, 20)}
    return PatentPublication(**values, provenance=PROVENANCE, **overrides)


def test_shouldBuildTheIdentifierFromCountryNumberAndKindWhenAskedForTheDocId():
    assert publication().doc_id == "ES2738048T3"


def test_shouldDeriveTheFourCharacterSubclassFromTheEntryWhenAskedForTheSymbol():
    entry = IpcEntry(section="B", class_number="05", subclass="C", main_group="1", subgroup="16")
    assert entry.subclass_symbol == "B05C"


def test_shouldKeepMissingValuesAsNoneWhenTheSourceDoesNotStateThem():
    record = publication()
    assert record.application_date is None
    assert record.priority_dates == ()
    assert record.ipc_entries == ()


def test_shouldRejectAnythingButASha256DigestWhenBuildingProvenance():
    with pytest.raises(ValidationError):
        SourceRecordProvenance(source_file="f.zip", file_sha256="not-a-digest", archive_path="x.xml")


def test_shouldNotChangeWhenAFieldIsAssignedAfterConstruction():
    with pytest.raises(ValidationError):
        publication().kind = "B1"


def test_shouldCarryProvenanceAndReasonWhenARecordIsRejected():
    rejected = RejectedRecord(provenance=PROVENANCE, reason="ParseError: boom")
    assert rejected.provenance.archive_path == "m.zip/d.zip/x.xml"


def test_shouldStillSayThereIsAPriorityClaimWhenItsDateWasUnreadable():
    anomaly = SourceAnomaly(field="priority_date", raw_value="101108", reason="invalid priority date: '101108'")

    assert publication(anomalies=(anomaly,)).has_priority_claim is True
    assert publication().has_priority_claim is False
    assert publication(priority_dates=(date(2017, 1, 1),)).has_priority_claim is True


def test_shouldNotCountAnUnreadableApplicationDateAsAPriorityClaim():
    anomaly = SourceAnomaly(field="application_date", raw_value="x", reason="invalid application date: 'x'")

    assert publication(anomalies=(anomaly,)).has_priority_claim is False
