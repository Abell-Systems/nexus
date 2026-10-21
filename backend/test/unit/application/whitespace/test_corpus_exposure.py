from datetime import date

from application.whitespace.corpus_exposure import exposure_group, exposure_table
from domain.models.whitespace import AuthorityEntry, PatentPublication, SourceRecordProvenance


def publication(number: str, kind: str, published: date) -> PatentPublication:
    return PatentPublication(
        country="ES",
        doc_number=number,
        kind=kind,
        publication_date=published,
        provenance=SourceRecordProvenance(source_file="f.zip", file_sha256="a" * 64, archive_path="x.xml"),
    )


def entry(number: str, kind: str, published: str) -> AuthorityEntry:
    return AuthorityEntry(
        publication_number=number,
        kind=kind,
        publication_date=published,
        application_office="ES",
        application_text="P1",
        filing_date="20000101",
    )


def test_shouldGroupKindCodesByFamilyWithoutNamingWhatYDenotes():
    assert [exposure_group(k) for k in ("T3", "T5", "Y", "A1", "U", "B1")] == [
        "ep_translation",
        "ep_translation",
        "kind_y",
        "other",
        "other",
        "other",
    ]


def test_shouldCountPresentAbsentAndCorpusOnlyKeysByYearAndGroupWhenBuildingTheTable():
    corpus = [publication("1", "B1", date(2001, 5, 1)), publication("9", "B1", date(2001, 6, 1))]
    authority = [
        entry("1", "B1", "20010501"),  # present
        entry("2", "Y", "20010502"),  # absent, kind Y
        entry("3", "T3", "20010503"),  # absent, EP translation
        entry("3", "T3", "20010503"),  # listed twice: counted once
        entry("4", "B1", "20020101"),  # absent, next year
        entry("5", "B1", "19991231"),  # outside the range
    ]
    table = exposure_table(corpus, authority, origins=[2001, 2002], first_year=2000, last_year=2002)
    y2001 = table["by_year"]["2001"]
    assert y2001["other"] == {"inventory": 1, "present": 1, "absent": 0, "absent_share_percent": 0.0}
    assert y2001["kind_y"]["absent"] == 1 and y2001["ep_translation"]["absent"] == 1
    assert y2001["corpus_keys_not_in_inventory"] == 1
    assert table["by_year"]["2002"]["other"]["absent_share_percent"] == 100.0
    assert table["inventory_publications"] == 4


def test_shouldAccumulateAbsencesFromTheFirstYearUpToEachOriginWhenBuildingTheTable():
    corpus = [publication("1", "B1", date(2000, 1, 1))]
    authority = [
        entry("1", "B1", "20000101"),
        entry("2", "Y", "20000102"),
        entry("3", "Y", "20010101"),
        entry("4", "A1", "20010102"),
    ]
    table = exposure_table(corpus, authority, origins=[2000, 2001], first_year=2000, last_year=2001)
    first, second = table["accumulated_up_to_origin"]["2000"], table["accumulated_up_to_origin"]["2001"]
    assert (
        first["calendar_years_in_window"] == 1
        and first["years_with_corpus_publications"] == 1
        and first["all_groups"]
        == {
            "inventory": 2,
            "absent": 1,
            "absent_share_percent": 50.0,
        }
    )
    assert (
        second["calendar_years_in_window"] == 2
        and second["years_with_corpus_publications"] == 1
        and second["kind_y"]
        == {
            "inventory": 2,
            "absent": 2,
            "absent_share_percent": 100.0,
        }
    )
    assert second["all_groups"]["absent"] == 3


def test_shouldCountOnlyYearsWithCorpusPublicationsWhenAYearIsMissingFromTheCorpus():
    corpus = [publication("1", "B1", date(2000, 1, 1)), publication("2", "B1", date(2002, 1, 1))]
    authority = [entry("1", "B1", "20000101"), entry("3", "B1", "20010101"), entry("2", "B1", "20020101")]
    third = exposure_table(corpus, authority, origins=[2002], first_year=2000, last_year=2002)[
        "accumulated_up_to_origin"
    ]["2002"]
    assert third["calendar_years_in_window"] == 3 and third["years_with_corpus_publications"] == 2
