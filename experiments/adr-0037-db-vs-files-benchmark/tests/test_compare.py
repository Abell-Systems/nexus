import pytest
from application.whitespace.analysis_records import AnalysisRecord
from harness.compare import (IncompleteComparison, compare_json, compare_load_checks, compare_pairs, compare_records)
from datetime import date

R = AnalysisRecord("ES1A1", date(2001, 1, 2), "national", 1999, ("A61K", "b01J"), "A1")


def test_shouldBeEqualWhenRecordsIdentical():
    assert compare_records([R], [R]).equal


def test_shouldReportFieldAndExampleWhenOneFieldDiffers():
    other = R._replace(subclasses=("A61K", "b01J", "C11D"))
    diff = compare_records([R], [other])
    assert not diff.equal and diff.differing_fields == {"subclasses": 1} and diff.examples[0]["field"] == "subclasses"


def test_shouldDetectOrderDifferenceInSubclasses():
    assert not compare_records([R], [R._replace(subclasses=("b01J", "A61K"))]).equal


@pytest.mark.parametrize("a,b", [(None, [R]), ([R], None), ([], [R]), ([R], []), ([R], [R, R])])
def test_shouldRefuseToCompareWhenInputIncomplete(a, b):
    with pytest.raises(IncompleteComparison):
        compare_records(a, b)


def test_shouldRefuseWhenAnOriginIsMissingFromThePairsResult():
    with pytest.raises(IncompleteComparison):
        compare_pairs({"2006": {}, "2022": {}}, {"2006": {}})


def test_shouldDetectDifferentPairsAndIgnoreKeyOrder():
    assert compare_pairs({"2006": {"a": 1, "b": 2}}, {"2006": {"b": 2, "a": 1}}) == {"2006": True}
    assert compare_pairs({"2006": {"a": 1}}, {"2006": {"a": 2}}) == {"2006": False}


def test_shouldRefuseWhenAJsonSideIsMissing():
    with pytest.raises(IncompleteComparison):
        compare_json(None, {}, "x")


def test_shouldRefuseIncompleteLoadChecksAndFlagWrongCounts():
    with pytest.raises(IncompleteComparison):
        compare_load_checks({"publications": 711547})
    ok = {"publications": 711547, "rejected": 341, "subclasses": 660, "without_ipc": 2749, "distinct_doc_id": 707985}
    assert all(compare_load_checks(ok).values())
    assert not compare_load_checks({**ok, "rejected": 340})["rejected"]
