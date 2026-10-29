from datetime import date

from application.whitespace.analysis_records import to_analysis_records
from domain.models.whitespace import IpcEntry, PatentPublication, SourceRecordProvenance


def ipc(subclass, main_group=None):
    return IpcEntry(section=subclass[0], class_number=subclass[1:3], subclass=subclass[3], main_group=main_group)


def test_shouldCarryMainGroupsAndApplicantsWhenConvertingAPublication():
    publication = PatentPublication(
        country="ES",
        doc_number="1",
        kind="A1",
        publication_date=date(2020, 1, 1),
        ipc_entries=(ipc("H01M", "10"), ipc("H01M", "4"), ipc("C01B")),
        applicants=("A", "A", "B"),
        provenance=SourceRecordProvenance(source_file="f.zip", file_sha256="a" * 64, archive_path="x.xml"),
    )

    (record,) = to_analysis_records([publication])

    assert record.groups == ("H01M 10", "H01M 4")
    assert record.applicants == ("A", "B")
