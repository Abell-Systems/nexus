import ast
from datetime import date
from pathlib import Path

import pytest

from application.whitespace import expected_count as module
from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.expected_count import documents_per_year, expected_count, unobserved_pairs_expected


def record(doc: str, year: int, *subclasses: str) -> AnalysisRecord:
    return AnalysisRecord(doc, date(year, 6, 1), "patent", year, tuple(sorted(subclasses)))


def corpus() -> list[AnalysisRecord]:
    """Hand-computed. 2000: 4 documents (A in 2, B in 2). 2002: 2 documents (A in 1, B in 1, C in 2). 2001 has none."""
    return [
        record("a1", 2000, "A01B"),
        record("a2", 2000, "A01B"),
        record("b1", 2000, "B01B"),
        record("b2", 2000, "B01B"),
        record("a3", 2002, "A01B"),
        record("b3", 2002, "B01B"),
        record("c1", 2002, "A01C"),
        record("c2", 2002, "A01C"),
    ]


def test_shouldCountDocumentsOncePerEarliestYearWhenACopyIsPublishedLater():
    records = [record("x", 2000, "A01B"), record("x", 2003, "A01B"), record("y", 2003, "B01B")]
    assert documents_per_year(records) == {2000: 1, 2003: 1}


def test_shouldSumTheContributionOfEachObservedYearWhenComputingTheExpectedCount():
    totals = {2000: 4, 2002: 4}  # 2001 has no documents
    a, b = {2000: 2, 2002: 1}, {2000: 2, 2002: 1}
    assert expected_count(a, b, totals) == pytest.approx(2 * 2 / 4 + 1 * 1 / 4)


def test_shouldSkipAYearWithoutDocumentsAndNeverCountItAsZeroWhenItIsMissingFromTheTotals():
    totals = {2000: 4, 2002: 4}  # 2001 absent: not a key, not a division, not a term
    assert expected_count({2000: 2, 2002: 1}, {2000: 2, 2002: 1}, totals) == pytest.approx(1.25)
    assert expected_count({2000: 2}, {2000: 2}, {2000: 4, 2001: 0}) == pytest.approx(1.0)


def test_shouldContributeZeroWhenASubclassHasNoDocumentsInAnObservedYear():
    assert expected_count({2000: 2}, {2002: 1}, {2000: 4, 2002: 4}) == 0


def test_shouldListEveryPairOfActiveSubclassesThatNoRecordStatesTogetherWithItsExpectedCount():
    # 2000: N=4 (A01B 2, B01B 2); 2002: N=4 (A01B 1, B01B 1, A01C 2)... A01C has 2 docs, active with min_documents=2
    result = {(a, b): e for a, b, e in unobserved_pairs_expected(corpus(), 2002, min_documents=2)}
    assert set(result) == {("A01B", "A01C"), ("A01B", "B01B"), ("A01C", "B01B")}
    assert result[("A01B", "B01B")] == pytest.approx(2 * 2 / 4 + 1 * 1 / 4)
    assert result[("A01B", "A01C")] == pytest.approx(0 * 0 / 4 + 1 * 2 / 4)  # A01C has no documents in 2000
    assert result[("A01C", "B01B")] == pytest.approx(2 * 1 / 4)


def test_shouldExcludeObservedPairsAndPairsWithAnInactiveSide():
    records = corpus() + [record("ab", 2002, "A01B", "B01B"), record("tiny", 2002, "H01L", "A01B")]
    pairs = {(a, b) for a, b, _ in unobserved_pairs_expected(records, 2002, min_documents=2)}
    assert ("A01B", "B01B") not in pairs  # observed by "ab"
    assert not any("H01L" in pair for pair in pairs)  # one document: inactive


def test_shouldUseOnlyDocumentsPublishedUpToTheOrigin():
    late = corpus() + [record("l1", 2005, "A01B", "A01C")]
    before = {(a, b): e for a, b, e in unobserved_pairs_expected(corpus(), 2002, min_documents=2)}
    after = {(a, b): e for a, b, e in unobserved_pairs_expected(late, 2002, min_documents=2)}
    assert before == after


def test_shouldCountObservedAndUnobservedPairsAsAllPairsBetweenActiveSubclasses():
    from application.whitespace.subclass_pairs import subclass_pairs

    records = corpus() + [record("ab", 2002, "A01B", "B01B")]
    result = subclass_pairs(records, 2002, min_documents=2)
    n = len(result["active"])
    unobserved = list(unobserved_pairs_expected(records, 2002, min_documents=2))
    assert len(unobserved) + len(result["pairs"]) == n * (n - 1) // 2


def test_shouldNotImportTheStudyDetectorNullModelOrBaselineNorNameItself_f1():
    tree = ast.parse(Path(module.__file__).read_text())
    imported = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [None])
        if (node.module if isinstance(node, ast.ImportFrom) else alias.name)
    }
    assert not any(part in name for name in imported for part in ("detector", "null_model", "baseline", "evaluation"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))
    }
    assert not any(name.lower() in ("f1", "null_model", "baseline") for name in names)
