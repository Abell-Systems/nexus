from datetime import date

from application.whitespace.application_links import link_report, resolve_filing_numbers
from domain.models.whitespace import (
    ApplicationKey,
    ApplicationReference,
    AuthorityEntry,
    PatentPublication,
    SourceRecordProvenance,
    application_key_candidates,
    application_key_from_authority,
    application_key_from_reference,
)


def reference(country="ES", number="201000660", kind="U") -> ApplicationReference:
    return ApplicationReference(country=country, number=number, kind=kind)


def publication(number="1072888", kind="U8", published=date(2013, 8, 7), ref=None, filed=date(2010, 6, 22)):
    return PatentPublication(
        country="ES",
        doc_number=number,
        kind=kind,
        publication_date=published,
        application_reference=ref,
        application_date=filed,
        provenance=SourceRecordProvenance(source_file="f.zip", file_sha256="a" * 64, archive_path="x.xml"),
    )


def entry(number="1072888", kind="U8", published="20130807", office="ES", text="U201000660", filed="20100622"):
    return AuthorityEntry(
        publication_number=number,
        kind=kind,
        publication_date=published,
        application_office=office,
        application_text=text,
        filing_date=filed,
    )


def test_shouldUseTheApplicationKindAsSeriesWhenBuildingAKeyFromAReference():
    assert application_key_from_reference(reference()) == ApplicationKey(series="U", number="201000660")
    assert application_key_from_reference(reference(country="EP", number="06743854", kind="E")) == ApplicationKey(
        series="E", number="06743854"
    )


def test_shouldNotBuildAKeyWhenTheReferenceIsAbsentOrAnomalous():
    assert application_key_from_reference(None) is None
    assert application_key_from_reference(reference(number="P98924378", kind="E")) is None  # a letter inside the number
    assert application_key_from_reference(reference(kind="")) is None
    assert application_key_from_reference(reference(kind="X")) is None


def test_shouldReadTheSeriesFromTheLetterOfANationalNumberAndFromTheOfficeOfAnEuropeanOne():
    assert application_key_from_authority("ES", "U200502626") == ApplicationKey(series="U", number="200502626")
    assert application_key_from_authority("ES", "P9650031") == ApplicationKey(series="P", number="9650031")
    assert application_key_from_authority("EP", "06743854") == ApplicationKey(series="E", number="06743854")


def test_shouldNotBuildAKeyFromAnUnexpectedAuthorityNumber():
    for office, text in (
        ("ES", "200502626"),
        ("ES", "E200502626"),
        ("EP", "E06743854"),
        ("WO", "PCT/ES2005/000123"),
        ("ES", ""),
    ):
        assert application_key_from_authority(office, text) is None


def test_shouldOfferCandidatesNotAKeyWhenTheSeriesIsOmitted():
    assert [k.series for k in application_key_candidates("ES", "201000660")] == ["P", "U"]
    assert [k.series for k in application_key_candidates("EP", "06743854")] == ["E"]
    assert application_key_candidates("ES", "U201000660") == ()
    assert application_key_candidates("WO", "123") == ()


def test_shouldCountMatchesAgreementsAndDifferencesWhenLinkingTheCorpusToTheInventory():
    corpus = [
        publication("1", "U8", date(2013, 1, 1), reference()),
        publication("2", "B1", date(2013, 1, 1), reference(number="200000001", kind="P")),
        publication("3", "B1", date(2013, 1, 1), reference(number="200000002", kind="P")),
        publication("4", "B1", date(2013, 1, 1), None),
        publication("5", "B1", date(2013, 1, 1), reference(number="200000005", kind="P")),
    ]
    authority = [
        entry("1", "U8", "20130101", text="U201000660"),
        entry("2", "B1", "20130101", text="P200000001", filed="20100101"),  # same key, different filing date
        entry("3", "B1", "20130101", text="P200000099"),  # different key
        entry("4", "B1", "20130101", text="P200000004"),  # the corpus has no reference
        entry("5", "B1", "20130101", office="WO", text="PCT/ES/1"),  # not parsed
        entry("6", "B1", "20130101", text="P200000006"),  # not in the corpus
    ]
    report = link_report(corpus, authority)
    assert report["corpus_keys_in_authority"] == 5 and report["corpus_keys_not_in_authority"] == 0
    assert report["application_key_agreement"] == {
        "same_key": 1,
        "same_key_filing_date_differs": 1,
        "different_keys": 1,
        "corpus_key_missing": 1,
        "authority_key_missing": 1,
    }
    assert report["authority_application_numbers_not_parsed"] == {"WO|aaa/aa/9": 1}
    assert report["by_year"][2013]["other_entries"] == 6 and report["by_year"][2013]["other_with_application_key"] == 5


def test_shouldReportCollisionsAmongTheInventorysApplicationKeys():
    authority = [
        entry("1", text="P200000001", filed="20100101"),
        entry("2", text="P200000001", filed="20110101"),  # the same key with another filing date
        entry("3", text="U200000001", filed="20100101"),  # the same digits in the other series
        entry("4", office="EP", text="06743854", kind="T3"),
    ]
    report = link_report([], authority)
    assert report["authority_application_keys"] == 3  # P1, U1 and E: three distinct keys
    assert report["authority_keys_with_several_filing_dates"] == 1
    assert report["national_digit_strings"] == 1 and report["national_digit_strings_shared_by_P_and_U"] == 1


def test_shouldFlagCopiesOfAKeyThatDisagreeOnTheApplicationWhenBuildingTheCorpusIndex():
    copies = [publication(ref=reference()), publication(ref=reference(number="201000661"))]
    assert link_report(copies, [])["corpus_keys_with_copies_that_disagree_on_the_application"] == 1


def test_shouldSeparateUniqueAmbiguousAndUnmatchedFilingNumbersWhenResolvingThem():
    known = {
        ApplicationKey(series="P", number="200000001"),
        ApplicationKey(series="U", number="200000001"),
        ApplicationKey(series="U", number="200000002"),
        ApplicationKey(series="E", number="06743854"),
    }
    numbers = [
        ("ES", "200000001"),
        ("ES", "200000002"),
        ("ES", "200000003"),
        ("EP", "06743854"),
        ("EP", "99"),
        ("WO", "1"),
        ("ES", "200000001"),
    ]
    assert resolve_filing_numbers(numbers, known) == {
        "ambiguous_between_series": 1,
        "matched_uniquely": 2,
        "no_application_in_the_inventory": 2,
        "not_a_digit_number_or_unknown_office": 1,
    }
