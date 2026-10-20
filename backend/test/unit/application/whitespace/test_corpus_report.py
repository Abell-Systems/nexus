from datetime import date

from application.whitespace.corpus_report import build_figures, compare_figures, kind_group
from domain.models.whitespace import IpcEntry, PatentPublication, RejectedRecord, SourceRecordProvenance


def provenance(source_file: str = "BIBLIO_2020.zip") -> SourceRecordProvenance:
    return SourceRecordProvenance(source_file=source_file, file_sha256="a" * 64, archive_path="x.xml")


def publication(
    kind="B1",
    number="1",
    published=date(2020, 1, 20),
    subclasses=("B05C",),
    priorities=(),
    file="BIBLIO_2020.zip",
    application=date(2018, 1, 1),
) -> PatentPublication:
    return PatentPublication(
        country="ES",
        doc_number=number,
        kind=kind,
        publication_date=published,
        application_date=application,
        priority_dates=priorities,
        ipc_entries=tuple(
            IpcEntry(section=s[0], class_number=s[1:3], subclass=s[3], version="2006.01") for s in subclasses
        ),
        provenance=provenance(file),
    )


def test_shouldGroupKindsLikeThePublishedCharacterizationWhenClassifyingDocuments():
    assert [kind_group(k) for k in ("T3", "T5", "U", "Y1", "B1", "A1", "R1")] == [
        "ep_translation",
        "ep_translation",
        "utility_model",
        "utility_model",
        "patent",
        "patent",
        "patent",
    ]


def test_shouldCountByPublicationYearAndLeaveMissingYearsOutWhenFileNamesDisagree():
    outcomes = [
        publication(published=date(2009, 12, 30), file="BIBLIO_2009.zip"),
        publication(number="2", kind="T3", published=date(2011, 1, 10), file="BIBLIO_2010.zip"),
        publication(number="3", published=date(2011, 2, 1), file="BIBLIO_2011.zip"),
    ]

    figures = build_figures(outcomes)

    assert figures["by_publication_year"] == {
        "2009": {"records": 1, "ep_translations": 0, "national": 1, "distinct_dates": 1},
        "2011": {"records": 2, "ep_translations": 1, "national": 1, "distinct_dates": 2},
    }
    assert figures["years_without_records"] == [2010]
    assert figures["by_file"]["BIBLIO_2010.zip"]["first_publication_date"] == "2011-01-10"


def test_shouldCountRepeatsAndRejectsWithoutRemovingThemWhenIdentifiersRepeat():
    same = publication(number="1")
    outcomes = [
        same,
        same,
        publication(number="1", published=date(2020, 2, 3)),
        RejectedRecord(provenance=provenance(), reason="ParseError"),
    ]

    figures = build_figures(outcomes)

    assert (figures["records"], figures["rejected"]) == (3, 1)
    assert figures["distinct_doc_ids"] == 1
    assert figures["distinct_doc_id_publication_dates"] == 2
    assert figures["exact_repeat_records"] == 1
    assert figures["doc_ids_with_several_publication_dates"] == 1
    assert figures["by_file"]["BIBLIO_2020.zip"]["rejected"] == 1


def test_shouldCountPriorityIpcAndDateGapsWhenRecordsAreIncomplete():
    outcomes = [
        publication(number="1", kind="T3", priorities=(date(2017, 1, 1),), subclasses=("B05C", "B05C", "A01B")),
        publication(number="2", kind="U", subclasses=()),
        publication(number="3", application=None),
        publication(number="4", application=date(2021, 1, 1)),
    ]

    figures = build_figures(outcomes)

    assert figures["without_priority_claim"]["total"] == 3
    assert figures["without_priority_claim"]["by_group_percent"] == {
        "ep_translation": 0.0,
        "patent": 100.0,
        "utility_model": 100.0,
    }
    assert figures["records_without_ipc"] == 1
    assert figures["distinct_ipc_subclasses"] == 2
    assert figures["ipc"]["mean_distinct_subclasses"] == 1.0
    assert figures["ipc"]["two_or_more_subclasses_percent"] == 25.0
    assert figures["ipc"]["most_common_version"] == "2006.01"
    assert figures["records_without_application_date"] == 1
    assert figures["records_with_application_after_publication"] == 1


def test_shouldReportEmptyFiguresWhenTheSourceIsEmpty():
    figures = build_figures([])

    assert figures["records"] == 0
    assert figures["by_publication_year"] == {}
    assert figures["years_without_records"] == []


def test_shouldReturnNoDifferencesWhenFiguresAreIdentical():
    figures = build_figures([publication()])
    assert compare_figures(figures, build_figures([publication()])) == []


def test_shouldNameEachDifferenceWhenPublishedAndReproducedFiguresDisagree():
    published = {
        "records": 10,
        "by_file": {"a.zip": {"records": 5}, "b.zip": {"records": 5}},
        "years_without_records": [2010],
    }
    reproduced = {
        "records": 9,
        "by_file": {"a.zip": {"records": 5}, "c.zip": {"records": 4}},
        "years_without_records": [],
    }

    assert compare_figures(published, reproduced) == [
        "/by_file/b.zip: published {'records': 5}, not reproduced",
        "/by_file/c.zip: reproduced {'records': 4}, not published",
        "/records: published 10, reproduced 9",
        "/years_without_records: published [2010], reproduced []",
    ]
