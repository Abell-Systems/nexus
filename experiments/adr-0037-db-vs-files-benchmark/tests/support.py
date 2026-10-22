import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "backend" / "src" / "main"))

from domain.models.whitespace import (  # noqa: E402
    ApplicationReference, IpcEntry, PatentPublication, RejectedRecord, SourceAnomaly, SourceRecordProvenance)

SHA = "a" * 64
FILES = {"BIBLIO_2000.zip": {"sha256": SHA, "bytes": 10}}


def _prov(path):
    return SourceRecordProvenance(source_file="BIBLIO_2000.zip", file_sha256=SHA, archive_path=path)


def _ipc(subclass):
    return IpcEntry(section=subclass[0], class_number=subclass[1:3], subclass=subclass[3], main_group="1", subgroup="00",
                    version="2006.01", level="A", value="I")


def outcomes():
    """Synthetic corpus: mixed-case symbols (b01J, A61k as in the real data), a repeated doc_id, an anomaly, a rejected record."""
    return [
        PatentPublication(country="ES", doc_number="1", kind="A1", publication_date=date(2001, 1, 2),
                          application_reference=ApplicationReference(country="ES", number="99", kind="P"),
                          application_date=date(2000, 5, 5), priority_dates=(date(1999, 3, 1),), title="uno",
                          applicants=("Ana",), inventors=("Luis", "Eva"),
                          ipc_entries=tuple(_ipc(s) for s in ("A61K", "A61Q", "C11D", "D06M", "B01J")) + (_ipc("B01J"),),
                          provenance=_prov("a.zip/1.xml")),
        PatentPublication(country="ES", doc_number="2", kind="T3", publication_date=date(2005, 6, 7), title="dos",
                          ipc_entries=(_ipc("A61K"), _ipc("A61k")), provenance=_prov("a.zip/2.xml"),
                          anomalies=(SourceAnomaly(field="priority_date", raw_value="00000000", reason="invalid"),)),
        PatentPublication(country="ES", doc_number="2", kind="T3", publication_date=date(2005, 6, 7), title="dos repetido",
                          ipc_entries=(), provenance=_prov("a.zip/3.xml")),
        RejectedRecord(provenance=_prov("a.zip/4.xml"), reason="ParseError: x"),
    ]
