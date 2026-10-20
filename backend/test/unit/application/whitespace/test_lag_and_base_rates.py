from datetime import date

import pytest

from application.whitespace.analysis_records import (
    AnalysisRecord,
    distinct_publications,
    filing_year,
    to_analysis_records,
)
from application.whitespace.base_rates import base_rates
from application.whitespace.figure_comparison import compare_published
from application.whitespace.publication_lag import lag_figures
from domain.models.whitespace import IpcEntry, PatentPublication, SourceAnomaly, SourceRecordProvenance


def publication(priorities=(), application=date(2015, 3, 1), anomalies=()) -> PatentPublication:
    return PatentPublication(
        country="ES",
        doc_number="1",
        kind="B1",
        publication_date=date(2020, 1, 1),
        application_date=application,
        priority_dates=priorities,
        anomalies=anomalies,
        ipc_entries=(IpcEntry(section="B", class_number="05", subclass="C"),),
        provenance=SourceRecordProvenance(source_file="f.zip", file_sha256="a" * 64, archive_path="x.xml"),
    )


def record(year: int, subclasses: tuple[str, ...], filed: int | None = None, group="patent", doc="d") -> AnalysisRecord:
    return AnalysisRecord(
        f"{doc}{year}{subclasses}", date(year, 6, 1), group, filed if filed is not None else year, subclasses
    )


def test_shouldUseTheEarliestReadableDateWhenPriorityAndApplicationDiffer():
    assert filing_year(publication(priorities=(date(2012, 5, 1), date(2013, 1, 1)))) == 2012
    assert filing_year(publication(priorities=(date(2017, 1, 1),))) == 2015


def test_shouldFallBackToTheApplicationDateWhenThePriorityDateIsUnreadable():
    unreadable = (SourceAnomaly(field="priority_date", raw_value="101108", reason="not a date"),)
    assert filing_year(publication(anomalies=unreadable)) == 2015


def test_shouldHaveNoFilingYearWhenNoDateIsReadable():
    assert filing_year(publication(application=None)) is None


def test_shouldKeepOneRecordPerIdentifierAndPublicationDateWhenDistinguishingPublications():
    a = record(2020, ("B05C",), doc="x")
    assert distinct_publications([a, a, record(2021, ("B05C",), doc="x")]) == [a, record(2021, ("B05C",), doc="x")]
    assert len(to_analysis_records([publication(), publication()])) == 2


def test_shouldReportNearestRankPercentilesAndCohortCurveWhenComputingLag():
    ep = [record(2012 + i % 4, ("B05C",), filed=2012, group="ep_translation") for i in range(8)]  # lags 0,1,2,3
    national = [record(2013, ("B05C",), filed=2012)]
    old = [record(2005 + lag, ("B05C",), filed=2005, group="ep_translation") for lag in (1, 2, 3, 4)]
    figures = lag_figures(ep + national + old, cohort_years=range(2005, 2006), max_lag=4, completeness_cohorts=(2022,))
    assert figures["lag"]["ep_translation"] == {"records": 8, "mean": 1.5, "median": 1, "p90": 3}
    assert figures["lag"]["national"]["median"] == 1
    assert figures["cumulative_share_percent"] == {"0": 0.0, "1": 25.0, "2": 50.0, "3": 75.0, "4": 100.0}
    assert figures["completeness_percent"] == {"2022": 75.0}  # read at lag 2025 - 2022 = 3


def test_shouldExcludeRecordsWithoutFilingYearFromLagWhenCounting():
    none = AnalysisRecord("d", date(2020, 1, 1), "patent", None, ())
    assert lag_figures([none, record(2020, (), filed=2019)])["records_without_filing_year"] == 1


def test_shouldCountPositivesOnlyForActivePairsNeverSeenWhenComputingBaseRates():
    # A and B co-occur from the start (seen); A, C and B, C only in the horizon (positives); D never reaches 2 documents
    records = (
        [record(2000 + i, ("A", "B"), doc=str(i)) for i in range(2)]
        + [record(2000, ("C",), doc="c0"), record(2001, ("C",), doc="c1")]
        + [record(2002, ("A", "B", "C"), filed=2002, doc="new"), record(2002, ("D", "A"), doc="d")]
    )
    figures = base_rates(records, [2001], min_documents=2, horizon=1)["2001"]
    assert figures["active_subclasses"] == 3
    assert figures["candidate_pairs"] == 2  # A-C and B-C; A-B is seen
    assert figures["positives"] == 2
    assert figures["positive_rate_percent"] == 100.0


def test_shouldNotCountPairsSeenAtTheOriginOrOutsideTheHorizonWhenComputingPositives():
    records = [record(2000, ("A", "B"), doc="1"), record(2000, ("A", "B"), doc="2"), record(2001, ("A", "B"), doc="3")]
    assert base_rates(records, [2000], min_documents=2, horizon=1)["2000"]["positives"] == 0
    late = [
        record(2000, ("A",), doc="a"),
        record(2000, ("B",), doc="b"),
        record(2000, ("A",), doc="a2"),
        record(2000, ("B",), doc="b2"),
        record(2005, ("A", "B"), doc="far"),
    ]
    assert base_rates(late, [2000], min_documents=2, horizon=3)["2000"]["positives"] == 0
    assert base_rates(late, [2000], min_documents=2, horizon=5)["2000"]["positives"] == 1


def test_shouldCountRepeatedPublicationsOnceWhenMeasuringActivity():
    one = record(2000, ("A", "B"), doc="same")
    assert base_rates([one, one], [2000], min_documents=2, horizon=1)["2000"]["active_subclasses"] == 0


def test_shouldKeepThePairsOfEveryCopyWhenRecordsShareIdentifierAndDate():
    history = [AnalysisRecord(f"{s}{y}", date(y, 1, 1), "patent", y, (s,)) for y in (2000, 2001) for s in "AB"]
    copy_1 = AnalysisRecord("ES9A1", date(2002, 1, 1), "patent", 2002, ("A",))
    copy_2 = copy_1._replace(subclasses=("A", "B"))
    assert base_rates([*history, copy_1, copy_2], [2001], min_documents=2, horizon=1)["2001"]["positives"] == 1


def test_shouldCountADocumentOnceWhenItIsPublishedAgainAndMeasuringActivity():
    first = AnalysisRecord("ES1A1", date(2000, 6, 1), "patent", 2000, ("A", "B"))
    again = first._replace(published=date(2001, 6, 1))  # same identifier, later publication date
    assert base_rates([first, again], [2001], min_documents=2, horizon=1)["2001"]["active_subclasses"] == 0
    other = AnalysisRecord("ES2A1", date(2001, 1, 1), "patent", 2001, ("A", "B"))
    assert base_rates([first, again, other], [2001], min_documents=2, horizon=1)["2001"]["active_subclasses"] == 2


def test_shouldLetTheCopyPolicyDecideActivityWhenCopiesOfADocumentDiffer():
    copy_a = AnalysisRecord("ES1A1", date(2000, 6, 1), "patent", 2000, ("A",))
    copy_b = copy_a._replace(subclasses=("B",))
    other = AnalysisRecord("ES2A1", date(2001, 1, 1), "patent", 2001, ("A", "B"))

    def active(policy):
        return base_rates([copy_a, copy_b, other], [2001], min_documents=2, horizon=1, copy_policy=policy)["2001"][
            "active_subclasses"
        ]

    assert (active("first"), active("last"), active("union")) == (1, 1, 2)


def test_shouldRejectAnUnknownCopyPolicyWhenComputingBaseRates():
    with pytest.raises(ValueError, match="Unknown copy policy 'frist'"):
        base_rates([record(2000, ("A",))], [2000], copy_policy="frist")  # type: ignore[arg-type]


def test_shouldUseEveryCopyForPairsWhateverTheCopyPolicy():
    history = [AnalysisRecord(f"{s}{y}", date(y, 1, 1), "patent", y, (s,)) for y in (2000, 2001) for s in "AB"]
    copy_1 = AnalysisRecord("ES9A1", date(2002, 1, 1), "patent", 2002, ("A",))
    copy_2 = copy_1._replace(subclasses=("A", "B"))
    for policy in ("first", "last", "union"):
        result = base_rates([*history, copy_1, copy_2], [2001], min_documents=2, horizon=1, copy_policy=policy)
        assert result["2001"]["positives"] == 1


def test_shouldSeparateFiledByOriginFromFiledLaterWhenDiagnosingPositives():
    history = [record(y, (s,), doc=f"{s}{y}") for y in (2000, 2001) for s in "ABCD"]
    horizon = [
        record(2002, ("A", "B"), filed=2000, group="ep_translation", doc="p1"),  # filed by origin
        record(2002, ("C", "D"), filed=2002, doc="p2"),  # filed after the origin
    ]
    diagnostic = base_rates(history + horizon, [2001], min_documents=2, horizon=1)["2001"]["filing_diagnostic"]
    assert diagnostic["positives"] == 2
    assert diagnostic["filed_by_origin_percent"] == 50.0
    assert diagnostic["every_contributor_ep_translation_percent"] == 50.0
    assert diagnostic["no_contributor_ep_translation_percent"] == 50.0


def test_shouldCountFilingYearOutcomeOnlyWhenTheHorizonIsComplete():
    history = [record(y, (s,), doc=f"{s}{y}") for y in (2000, 2001) for s in "AB"]
    later = [record(2005, ("A", "B"), filed=2002, doc="x")]
    done = base_rates(history + later, [2001], min_documents=2, horizon=1, filing_outcome_until=2002)
    assert done["2001"]["positives_filing_year_outcome"] == 1
    pending = base_rates(history + later, [2001], min_documents=2, horizon=1, filing_outcome_until=2001)
    assert pending["2001"]["positives_filing_year_outcome"] is None


def test_shouldCountPairsSeenOnlyInTheHiddenYearAndRepeatedInTheHorizonWhenEstimatingTheGap():
    records = (
        [record(y, (s,), doc=f"{s}{y}") for y in (2000, 2001) for s in "ABCD"]
        + [record(2000, ("A", "B"), doc="ab"), record(2001, ("C", "D"), doc="cd"), record(2001, ("C", "D"), doc="cd2")]
        + [record(2002, ("A", "B"), doc="ab2"), record(2002, ("C", "D"), doc="cd3")]
    )
    hidden = base_rates(
        records, [2001], min_documents=2, horizon=1, hidden_year_origins=[2001], hidden_years=[2000, 2001]
    )
    assert hidden["2001"]["hidden_year"]["by_hidden_year"] == {"2000": 1, "2001": 1}


def test_shouldRoundToPublishedPrecisionAndListOnlyPublishedDifferencesWhenComparing():
    published = {"a": 6.9, "b": 93, "c": {"d": 5}}
    assert compare_published(published, {"a": 6.94, "b": 92.6, "c": {"d": 5}, "extra": 1}) == []
    assert compare_published(published, {"a": 7.0, "b": 92.2, "c": {}}) == [
        "/a: published 6.9, reproduced 7.0",
        "/b: published 93, reproduced 92.2",
        "/c/d: published 5, not reproduced",
    ]
