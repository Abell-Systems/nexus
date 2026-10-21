from datetime import date

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import base_rates
from application.whitespace.omission_sensitivity import omission_sensitivity


def record(doc: str, year: int, subclasses: tuple[str, ...], kind: str = "B1") -> AnalysisRecord:
    return AnalysisRecord(doc, date(year, 6, 1), "patent", year, subclasses, kind)


def corpus() -> list[AnalysisRecord]:
    """Subclasses A, B, C active in 2000-2001; A-B seen in 2000 only; A-B and A-C appear in the horizon (2002)."""
    history = [record(f"{s}{y}{i}", y, (s,)) for y in (2000, 2001) for s in "ABC" for i in range(2)]
    history.append(record("ab", 2000, ("A", "B")))
    horizon = [record("ab2", 2002, ("A", "B")), record("ac", 2002, ("A", "C"))]
    return history + horizon


KW = {"min_documents": 2, "horizon": 1}


def test_shouldReproduceTheBaseRatesWhenTheScenarioIsTheObservedCorpus():
    result = omission_sensitivity(corpus(), [2001], {}, replications=2, **KW)["2001"]["S-A"]
    direct = base_rates(corpus(), [2001], min_documents=2, horizon=1, filing_diagnostic=False, copy_policy="union")[
        "2001"
    ]
    assert result == {q: direct[q] for q in result}
    assert (result["active_subclasses"], result["candidate_pairs"], result["positives"]) == (
        3,
        2,
        1,
    )  # A-C only: A-B is seen


def test_shouldSeparateThePairsSeenOnlyInTheRemovedYearWhenRemovingAHistoryYear():
    b1 = omission_sensitivity(corpus(), [2001], {}, replications=1, **KW)["2001"]["S-B1"]
    assert b1["2000"]["positives"] == 2  # A-B is unseen without 2000 and reappears in 2002, besides A-C
    assert b1["2000"]["positives_whose_pair_was_seen_only_in_the_removed_year"] == 1
    assert b1["2000"]["positives_change_not_explained_by_that"] == 0
    assert b1["2001"]["positives"] == 1
    assert b1["2001"]["positives_whose_pair_was_seen_only_in_the_removed_year"] == 0


def test_shouldKeepOnlyTheLastYearsOfHistoryWhenShorteningTheWindow():
    b2 = omission_sensitivity(corpus(), [2001], {}, replications=1, window=1, **KW)["2001"]["S-B2"]
    assert (b2["active_subclasses"], b2["candidate_pairs"], b2["positives"]) == (
        3,
        3,
        2,
    )  # nothing is seen in 2001 alone


def test_shouldGiveTheObservedCountsInEveryReplicationWhenNothingIsDeleted():
    s_c = omission_sensitivity(corpus(), [2001], {}, replications=5, **KW)["2001"]["S-C"]
    assert s_c["positives"] == {"mean": 1.0, "p2.5": 1, "p97.5": 1}
    assert s_c["seeds"] == [1, 5]


def test_shouldDeleteEverythingOfAGroupWhenItsAbsenceIsTotal():
    kept_only_b1 = omission_sensitivity(
        corpus(), [2001], {(y, "other"): 100.0 for y in range(2000, 2003)}, replications=3, **KW
    )
    assert kept_only_b1["2001"]["S-C"]["active_subclasses"]["mean"] == 0.0


def test_shouldGiveTheSameResultsForTheSameSeedsAndDifferentOnesForOtherSeeds():
    shares = {(y, "other"): 40.0 for y in range(2000, 2003)}
    first = omission_sensitivity(corpus(), [2001], shares, replications=20, seed_base=7, **KW)
    again = omission_sensitivity(corpus(), [2001], shares, replications=20, seed_base=7, **KW)
    other = omission_sensitivity(corpus(), [2001], shares, replications=20, seed_base=700, **KW)
    assert first == again
    assert (
        first["2001"]["S-C"]["positives"] != other["2001"]["S-C"]["positives"]
        or first["2001"]["S-C"]["candidate_pairs"] != other["2001"]["S-C"]["candidate_pairs"]
    )
