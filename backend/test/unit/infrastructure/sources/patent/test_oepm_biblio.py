import hashlib
import io
import zipfile
from datetime import date
from pathlib import Path

import pytest

from domain.models.whitespace import PatentPublication, RejectedRecord
from domain.protocols.whitespace import PatentPublicationSource, SourceIntegrityError
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource


def record_xml(
    kind: str = "B1",
    number: str = "2000001",
    published: str = "20200120",
    application: str | None = "20180101",
    priorities: tuple[str, ...] = ("20170101",),
    ipcs: tuple[tuple[str, str, str], ...] = (("B", "05", "C"),),
    title: str = "A title",
    doctype: str = '<!DOCTYPE es-patent-document SYSTEM "../es-patent-document-v1-2.dtd">',
) -> bytes:
    ipc = "".join(
        f"<classification-ipcr sequence='{i}'><ipc-version-indicator><date>2006.01</date></ipc-version-indicator>"
        f"<classification-level>A</classification-level><section>{s}</section><class>{c}</class>"
        f"<subclass>{sc}</subclass><main-group>1</main-group><subgroup>16</subgroup>"
        "<classification-value>I</classification-value></classification-ipcr>"
        for i, (s, c, sc) in enumerate(ipcs, 1)
    )
    app = (
        f"<application-reference><document-id><country>ES</country><doc-number>201931658</doc-number>"
        f"<kind>{kind}</kind><date>{application}</date></document-id></application-reference>"
        if application
        else ""
    )
    prio = "".join(
        f"<priority-claim kind='national' sequence='{i}'><country>US</country><doc-number>1</doc-number>"
        f"<date>{d}</date></priority-claim>"
        for i, d in enumerate(priorities, 1)
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>{doctype}'
        f'<es-patent-document date-publ="{published}" kind="{kind}" doc-number="{number}" country="ES">'
        f"<bibliographic-data><classifications-ipcr>{ipc}</classifications-ipcr>{app}"
        f"<priority-claims>{prio}</priority-claims>"
        "<parties><applicants><applicant><addressbook><name>ACME, S.L.</name></addressbook></applicant></applicants>"
        "<inventors><inventor><addressbook><last-name>GARCIA</last-name><first-name>ANA</first-name>"
        "</addressbook></inventor></inventors></parties>"
        f'<invention-title lang="ES">{title}</invention-title></bibliographic-data></es-patent-document>'
    ).encode()


def zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def write_source(directory: Path, name: str, days: dict[str, dict[str, bytes]]) -> str:
    """Writes `name` as year file -> month archives -> day archives -> xml records; returns its SHA-256."""
    months: dict[str, dict[str, bytes]] = {}
    for day_name, xmls in days.items():
        day = zip_bytes({f"{label}/{label}.xml": xml for label, xml in xmls.items()} | {"authorityFile.txt": b"x"})
        months.setdefault(f"BIBLIO_{day_name[9:15]}.zip", {})[day_name] = day
    data = zip_bytes({month: zip_bytes(entries) for month, entries in months.items()})
    (directory / name).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def source_dir(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    digest = write_source(
        tmp_path,
        "BIBLIO_2010.zip",  # the name says 2010, the record says 2011
        {"BIBLIO_ES20110110.zip": {"a": record_xml(kind="T3", number="1", published="20110110")}},
    )
    return tmp_path, {"BIBLIO_2010.zip": digest}


def test_shouldSatisfyTheSourcePortWhenConstructed(source_dir):
    directory, expected = source_dir
    assert isinstance(OepmBiblioSource(directory, expected), PatentPublicationSource)


def test_shouldReadRawValuesWithProvenanceWhenArchivesAreNested(source_dir):
    directory, expected = source_dir

    (publication,) = OepmBiblioSource(directory, expected).read()

    assert isinstance(publication, PatentPublication)
    assert publication.doc_id == "ES1T3"
    assert publication.title == "A title"
    assert publication.application_date == date(2018, 1, 1)
    assert publication.priority_dates == (date(2017, 1, 1),)
    assert publication.applicants == ("ACME, S.L.",)
    assert publication.inventors == ("GARCIA, ANA",)
    (entry,) = publication.ipc_entries
    assert (entry.subclass_symbol, entry.version, entry.level, entry.value) == ("B05C", "2006.01", "A", "I")
    assert publication.provenance.source_file == "BIBLIO_2010.zip"
    assert publication.provenance.file_sha256 == expected["BIBLIO_2010.zip"]
    assert publication.provenance.archive_path.startswith("BIBLIO_201101.zip/BIBLIO_ES20110110.zip/")


def test_shouldTakeThePublicationDateFromTheRecordWhenTheFileNameSaysAnotherYear(source_dir):
    directory, expected = source_dir

    (publication,) = OepmBiblioSource(directory, expected).read()

    assert publication.publication_date == date(2011, 1, 10)
    assert publication.provenance.source_file == "BIBLIO_2010.zip"


def test_shouldKeepEveryIpcEntryAndEveryPriorityDateWhenARecordHasSeveral(tmp_path):
    xml = record_xml(priorities=("20170101", "20160601"), ipcs=(("B", "05", "C"), ("B", "05", "C"), ("A", "01", "B")))
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert publication.priority_dates == (date(2017, 1, 1), date(2016, 6, 1))
    assert [e.subclass_symbol for e in publication.ipc_entries] == ["B05C", "B05C", "A01B"]


def test_shouldKeepNoneInsteadOfInventingDatesWhenTheSourceHasNoApplicationOrPriority(tmp_path):
    xml = record_xml(application=None, priorities=(), ipcs=())
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert publication.application_date is None
    assert publication.priority_dates == ()
    assert publication.ipc_entries == ()


def test_shouldKeepRepeatedIdentifiersWithoutDeduplicatingWhenTheSourceRepeatsThem(tmp_path):
    xml = record_xml(number="7")
    digest = write_source(
        tmp_path,
        "f.zip",
        {"BIBLIO_ES20200120.zip": {"a": xml, "b": xml}, "BIBLIO_ES20200121.zip": {"a": xml}},
    )

    publications = list(OepmBiblioSource(tmp_path, {"f.zip": digest}).read())

    assert [p.doc_id for p in publications] == ["ES7B1"] * 3


def test_shouldRejectTheRecordWithItsProvenanceWhenTheXmlIsInvalid(tmp_path):
    bad = record_xml() + b"<unclosed"
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"bad": bad, "ok": record_xml(number="2")}})

    outcomes = list(OepmBiblioSource(tmp_path, {"f.zip": digest}).read())

    rejected = [o for o in outcomes if isinstance(o, RejectedRecord)]
    assert len(rejected) == 1 and len(outcomes) == 2
    assert rejected[0].provenance.archive_path.endswith(".xml")
    assert rejected[0].reason.startswith("ParseError")


def test_shouldReadTheRecordWhenItContainsXmlIllegalControlCharacters(tmp_path):
    xml = record_xml(title="Bad \x01 character")
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert isinstance(publication, PatentPublication)
    assert publication.title == "Bad  character"


@pytest.mark.parametrize(
    ("xml", "reason"),
    [
        (record_xml(published="20201340"), "invalid publication date"),
        (record_xml(ipcs=(("B", "05", ""),)), "incomplete IPC entry"),
        (record_xml().replace(b"es-patent-document", b"other"), "unexpected root element"),
    ],
)
def test_shouldRejectTheRecordWithAReasonWhenAFieldIsMalformed(tmp_path, xml, reason):
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (outcome,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert isinstance(outcome, RejectedRecord)
    assert reason in outcome.reason


def test_shouldKeepTheRecordAndTheRawValueAsAnAnomalyWhenThePriorityDateIsUnreadable(tmp_path):
    xml = record_xml(priorities=("101108", "20170101"))
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert isinstance(publication, PatentPublication)
    assert publication.priority_dates == (date(2017, 1, 1),)
    (anomaly,) = publication.anomalies
    assert (anomaly.field, anomaly.raw_value) == ("priority_date", "101108")
    assert "invalid priority_date" in anomaly.reason
    assert publication.provenance.archive_path.endswith(".xml")


def test_shouldKeepTheRecordWithoutAnApplicationDateWhenTheSourceValueIsUnreadable(tmp_path):
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": record_xml(application="2018-01-01")}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert publication.application_date is None
    assert [(a.field, a.raw_value) for a in publication.anomalies] == [("application_date", "2018-01-01")]


def test_shouldReportNoAnomaliesWhenEveryOptionalFieldIsReadable(source_dir):
    directory, expected = source_dir

    (publication,) = OepmBiblioSource(directory, expected).read()

    assert publication.anomalies == ()


def test_shouldRejectWithTheEntityNamesInTheReasonWhenNamedEntitiesAreNotDefinedInTheRecord(tmp_path):
    # The record points to an external DTD (the default DOCTYPE) that is never loaded: nothing is resolved.
    xml = record_xml(title="Ger&OSLASH;n &SCARONON; &amp; co")
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (outcome,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert isinstance(outcome, RejectedRecord)
    assert "undefined entity" in outcome.reason
    assert "&OSLASH;, &SCARONON;" in outcome.reason
    assert "&amp;" not in outcome.reason


def test_shouldKeepTheRecordAndAnAnomalyWhenTheBytesAreNotValidUtf8(tmp_path):
    xml = record_xml(title="Name X end").replace(b"X", b"\xc3(")
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert isinstance(publication, PatentPublication)
    assert "\ufffd" in publication.title
    (anomaly,) = publication.anomalies
    assert (anomaly.field, anomaly.raw_value) == ("encoding", "c3")


def test_shouldReportNoAnomalyWhenAccentedTextIsValidUtf8(tmp_path):
    xml = record_xml(title="Ñandú ß Ø €")
    digest = write_source(tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": xml}})

    (publication,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert publication.title == "Ñandú ß Ø €"
    assert publication.anomalies == ()


def test_shouldNotExpandEntitiesWhenTheDocumentDeclaresThem(tmp_path):
    doctype = '<!DOCTYPE es-patent-document [<!ENTITY boom "expanded">]>'
    digest = write_source(
        tmp_path, "f.zip", {"BIBLIO_ES20200120.zip": {"a": record_xml(title="&boom;", doctype=doctype)}}
    )

    (outcome,) = OepmBiblioSource(tmp_path, {"f.zip": digest}).read()

    assert isinstance(outcome, RejectedRecord)


def test_shouldRejectTheArchiveWhenANestedArchiveIsCorrupt(tmp_path):
    month = zip_bytes(
        {"BIBLIO_ES20200120.zip": b"not a zip", "BIBLIO_ES20200121.zip": zip_bytes({"a/a.xml": record_xml()})}
    )
    data = zip_bytes({"BIBLIO_202001.zip": month})
    (tmp_path / "f.zip").write_bytes(data)

    outcomes = list(OepmBiblioSource(tmp_path, {"f.zip": hashlib.sha256(data).hexdigest()}).read())

    assert [type(o) for o in outcomes] == [RejectedRecord, PatentPublication]
    assert "BadZipFile" in outcomes[0].reason


def test_shouldRaiseBeforeYieldingAnythingWhenAFileDoesNotMatchItsHash(source_dir):
    directory, expected = source_dir
    other = write_source(
        directory, "BIBLIO_2011.zip", {"BIBLIO_ES20110111.zip": {"a": record_xml(published="20110111")}}
    )

    reader = OepmBiblioSource(directory, {**expected, "BIBLIO_2011.zip": "0" * 64}).read()

    with pytest.raises(SourceIntegrityError, match=f"BIBLIO_2011.zip: SHA-256 is {other}"):
        next(reader)


def test_shouldRaiseWhenAnExpectedFileIsMissing(source_dir):
    directory, expected = source_dir

    with pytest.raises(SourceIntegrityError, match="BIBLIO_2012.zip: file is missing"):
        next(OepmBiblioSource(directory, {**expected, "BIBLIO_2012.zip": "0" * 64}).read())


def test_shouldIgnoreFilesThatAreNotExpectedWhenTheDirectoryHoldsOthers(source_dir):
    directory, expected = source_dir
    (directory / "manifest.json").write_text("{}")
    (directory / "BIBLIO_2099.zip").write_bytes(b"unlisted")

    assert len(list(OepmBiblioSource(directory, expected).read())) == 1


def test_shouldReadTheSameRecordsInTheSameOrderWhenReadTwiceOrArchivedInAnotherOrder(tmp_path):
    day = {"a": record_xml(number="1"), "b": record_xml(number="2")}
    d1 = tmp_path / "one"
    d2 = tmp_path / "two"
    d1.mkdir()
    d2.mkdir()
    h1 = write_source(d1, "f.zip", {"BIBLIO_ES20200120.zip": day, "BIBLIO_ES20200121.zip": day})
    h2 = write_source(d2, "f.zip", {"BIBLIO_ES20200121.zip": day, "BIBLIO_ES20200120.zip": day})

    first = [p.model_dump() for p in OepmBiblioSource(d1, {"f.zip": h1}).read() if isinstance(p, PatentPublication)]
    again = [p.model_dump() for p in OepmBiblioSource(d1, {"f.zip": h1}).read() if isinstance(p, PatentPublication)]
    other = [p.model_dump() for p in OepmBiblioSource(d2, {"f.zip": h2}).read() if isinstance(p, PatentPublication)]

    def without_hash(rows):
        return [
            {k: v for k, v in r.items() if k != "provenance"} | {"path": r["provenance"]["archive_path"]} for r in rows
        ]

    assert first == again
    assert without_hash(first) == without_hash(other)
