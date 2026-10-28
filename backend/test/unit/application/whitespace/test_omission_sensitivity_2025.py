from datetime import date

import pytest

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.omission_sensitivity_2025 import (
    check_manifest_counts,
    compare,
    o4_years,
    remove_units,
    spearman,
    stratified_sample,
    units_of_year,
    units_per_year,
)
from application.whitespace.unobserved_pairs import unobserved_pairs


def record(doc: str, year: int, *subclasses: str) -> AnalysisRecord:
    return AnalysisRecord(doc, date(year, 6, 1), "patent", year, tuple(sorted(subclasses)))


def corpus() -> list[AnalysisRecord]:
    return [
        record("a1", 2000, "A01B"), record("a2", 2000, "A01B"), record("b1", 2000, "B01B"), record("b2", 2000, "B01B"),
        record("a3", 2002, "A01B"), record("b3", 2002, "B01B"), record("c1", 2002, "A01C"), record("c2", 2002, "A01C"),
        record("ab", 2002, "A01B", "B01B"),
    ]


def test_shouldUseTheEarliestYearOfEachUnitAndDropEveryCopyWhenRemoved():
    records = [*corpus(), record("a1", 2005, "A01B")]  # later copy of a1
    assert o4_years(records)["a1"] == 2000
    assert units_per_year(o4_years(records)) == {2000: 4, 2002: 5}
    assert all(r.doc_id != "a1" for r in remove_units(records, units_of_year(o4_years(records), 2000)))


def test_shouldSampleFloorTenPercentPerYearAndBeDeterministicPerSeed():
    units = {f"d{i}": 2000 + i % 2 for i in range(45)}  # 23 in 2000, 22 in 2001; k = 2 and 2
    first = stratified_sample(units, 7)
    assert first == stratified_sample(units, 7)
    assert sum(1 for d in first if units[d] == 2000) == 2 and sum(1 for d in first if units[d] == 2001) == 2
    assert stratified_sample({f"d{i}": 2000 for i in range(9)}, 7) == set()  # n_y < 10 loses none


def test_shouldGiveAverageRanksOnTiesAndNoneWhenUndefined():
    assert spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 1, 2], [1, 1, 2]) == pytest.approx(1.0)
    assert spearman([1, 1, 1], [1, 2, 3]) is None
    assert spearman([1], [1]) is None


def test_shouldFindNoPairBecomingObservedWhenDocumentsAreRemoved():
    base = unobserved_pairs(corpus(), 2002, min_documents=2)
    reduced = unobserved_pairs(remove_units(corpus(), {"ab"}), 2002, min_documents=2)
    stats = compare(base, reduced)
    assert stats["became_observed"] == 0
    assert stats["became_unobserved"] == 1  # A01B|B01B was observed only through "ab"
    assert stats["share_became_unobserved"] == 1.0
    assert stats["unobserved"] == base["counts"]["unobserved"] + 1


def test_shouldCountPairsOfSubclassesThatStopBeingActiveApartFromTheCommonUniverse():
    base = unobserved_pairs(corpus(), 2002, min_documents=2)
    stricter = unobserved_pairs(corpus(), 2002, min_documents=3)  # A01C has 2 documents and leaves
    stats = compare(base, stricter)
    assert stats["common_active"] == 2 and stats["active"] == 2
    assert stats["dropped_unobserved_pairs_of_S_A"] == 2  # the two pairs that involve A01C


MANIFEST = {"records": 711547, "rejected": 341, "distinct_doc_ids": 707985}


def test_shouldAcceptTheManifestCountsIncludingTheNumberOfRecordsRead():
    check_manifest_counts(711888, 341, 711547, 707985, MANIFEST)


@pytest.mark.parametrize("figures", [(711887, 341, 711547, 707985), (711888, 340, 711547, 707985), (711888, 341, 711546, 707985), (711888, 341, 711547, 707984)])
def test_shouldRaiseWhenAnyOfTheFourCountsDiffersFromTheManifest(figures):
    with pytest.raises(ValueError):
        check_manifest_counts(*figures, MANIFEST)
