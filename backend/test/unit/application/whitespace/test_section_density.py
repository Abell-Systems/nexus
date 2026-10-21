from datetime import date

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.section_density import section_density


def record(doc: str, year: int, *subclasses: str) -> AnalysisRecord:
    return AnalysisRecord(doc, date(year, 6, 1), "patent", year, tuple(sorted(subclasses)))


def test_shouldCountSeenAndPossiblePairsBySectionPairWhenDescribingTheCorpus():
    records = [record(f"a{i}", 2000, "A01B") for i in range(2)] + [record(f"b{i}", 2000, "B01B") for i in range(2)]
    records += [record(f"c{i}", 2000, "A01C") for i in range(2)] + [record("ab", 2000, "A01B", "B01B")]
    records += [record("late", 2005, "A01C", "B01B")]  # after the origin: not seen
    result = section_density(records, 2001, min_documents=2)
    assert result["active_subclasses_by_section"] == {"A": 2, "B": 1}
    assert result["cells"]["AB"] == {"possible_pairs": 2, "seen_pairs": 1, "seen_percent": 50.0}
    assert result["cells"]["AA"] == {"possible_pairs": 1, "seen_pairs": 0, "seen_percent": 0.0}
    assert result["seen_pairs"] == 1


def test_shouldIgnoreSubclassesBelowTheActivityThresholdWhenCountingPairs():
    records = [record(f"a{i}", 2000, "A01B") for i in range(2)] + [record("x", 2000, "A01B", "H01L")]
    result = section_density(records, 2001, min_documents=2)
    assert result["active_subclasses"] == 1 and result["seen_pairs"] == 0
