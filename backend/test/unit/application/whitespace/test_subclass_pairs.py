from datetime import date

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.section_density import section_density
from application.whitespace.subclass_pairs import subclass_pairs


def record(doc: str, year: int, *subclasses: str) -> AnalysisRecord:
    return AnalysisRecord(doc, date(year, 6, 1), "patent", year, tuple(sorted(subclasses)))


def corpus() -> list[AnalysisRecord]:
    records = [record(f"a{i}", 2000, "A01B") for i in range(2)] + [record(f"b{i}", 2000, "B01B") for i in range(2)]
    records += [record(f"c{i}", 2000, "A01C") for i in range(2)]
    records += [record("ab1", 2000, "A01B", "B01B"), record("ab2", 2001, "A01B", "B01B")]
    records += [record("late", 2005, "A01C", "B01B"), record("tiny", 2000, "H01L", "A01B")]
    return records


def test_shouldListActiveSubclassesWithTheirDocumentsWhenDescribingAnOrigin():
    result = subclass_pairs(corpus(), 2001, min_documents=2)
    assert result["active"] == {"A01B": 5, "A01C": 2, "B01B": 4}


def test_shouldCountDocumentsWithBothByYearAndFirstYearWhenThePairIsObserved():
    pair = subclass_pairs(corpus(), 2001, min_documents=2)["pairs"]["A01B|B01B"]
    assert pair == {"documents": 2, "by_year": {"2000": 1, "2001": 1}, "first_year": 2000}


def test_shouldNotStorePairsThatAreNotObservedOrAreAfterTheOriginOrHaveAnInactiveSide():
    pairs = subclass_pairs(corpus(), 2001, min_documents=2)["pairs"]
    assert set(pairs) == {"A01B|B01B"}  # A01C|B01B is after the origin, H01L is inactive


def test_shouldCountADocumentOnceWhenSeveralRecordsCarryTheSamePair():
    records = [record(f"x{i}", 2000, "A01B") for i in range(2)] + [record(f"y{i}", 2000, "B01B") for i in range(2)]
    records += [record("d", 2000, "A01B", "B01B"), record("d", 2001, "A01B", "B01B")]
    pair = subclass_pairs(records, 2001, min_documents=2)["pairs"]["A01B|B01B"]
    assert pair == {"documents": 1, "by_year": {"2000": 1}, "first_year": 2000}


def test_shouldMatchSectionDensityInvariantsWhenBothDescribeTheSameOrigin():
    for origin in (2000, 2001, 2005):
        result = subclass_pairs(corpus(), origin, min_documents=2)
        density = section_density(corpus(), origin, min_documents=2)
        assert len(result["active"]) == density["active_subclasses"]
        assert len(result["pairs"]) == density["seen_pairs"]
        for cell, figures in density["cells"].items():
            seen = sum(1 for key in result["pairs"] if {key[0], key.split("|")[1][0]} == set(cell))
            assert seen == figures["seen_pairs"]


def test_shouldAddUpByYearToTheTotalOfEveryPair():
    for pair in subclass_pairs(corpus(), 2005, min_documents=2)["pairs"].values():
        assert sum(pair["by_year"].values()) == pair["documents"]
        assert pair["first_year"] == min(int(y) for y in pair["by_year"])


def test_shouldGiveEachActiveSubclassTheEarliestPublicationYearOfItsDocumentsWhenDescribingAnOrigin():
    records = [
        record("a1", 2003, "A01B"),
        record("a2", 2001, "A01B"),
        record("c1", 2002, "A01C"),
        record("c2", 2002, "A01C"),
    ]
    records += [record("late", 1999 + 8, "A01C")]  # after the origin: ignored
    result = subclass_pairs(records, 2005, min_documents=2)
    assert result["first_years"] == {"A01B": 2001, "A01C": 2002}


def test_shouldKeepFirstYearsInTheSameSetAsActiveSubclassesAndNeverAfterTheOrigin():
    for origin in (2000, 2001, 2005):
        result = subclass_pairs(corpus(), origin, min_documents=2)
        assert set(result["first_years"]) == set(result["active"])
        assert all(year <= origin for year in result["first_years"].values())
