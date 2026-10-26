import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.unobserved_pairs import unobserved_pairs

ROOT = Path(__file__).resolve().parents[5]
RESULT = ROOT / "docs" / "whitespace" / "oepm-unobserved-pairs-results.json"
FIGURES = ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"


def record(doc: str, year: int, *subclasses: str) -> AnalysisRecord:
    return AnalysisRecord(doc, date(year, 6, 1), "patent", year, tuple(sorted(subclasses)))


def corpus() -> list[AnalysisRecord]:
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


def test_shouldStoreEachUnobservedPairOnceWithItsExpectedCountAndTheTotalsBehindIt():
    result = unobserved_pairs(corpus(), 2002, min_documents=2)
    assert result["pairs"] == {"A01B": {"A01C": 0.5, "B01B": 1.25}, "A01C": {"B01B": 0.5}}
    assert result["documents_per_year"] == {"2000": 4, "2002": 4}  # 2001 has no documents and is not a key
    assert result["active"] == {"A01B": 3, "A01C": 2, "B01B": 3}
    assert result["counts"] == {"active": 3, "pairs": 3, "unobserved": 3}


def test_shouldNotListAnObservedPairAndShouldCountItInTheUniverse():
    records = corpus() + [record("ab", 2002, "A01B", "B01B")]
    result = unobserved_pairs(records, 2002, min_documents=2)
    assert "B01B" not in result["pairs"].get("A01B", {})
    assert result["counts"]["pairs"] == 3
    assert result["counts"]["unobserved"] == 2


def test_shouldStateTheQuantityAndTheFixedParametersWithoutAnyScoreOrRankField():
    result = unobserved_pairs(corpus(), 2002, min_documents=2)
    assert result["e_min"] == 1.0
    assert "independence" in result["quantity"]
    assert not {"rank", "score", "f1", "probability"} & set(result)


def report_script():
    spec = importlib.util.spec_from_file_location(
        "report_oepm_unobserved_pairs", ROOT / "scripts" / "report_oepm_unobserved_pairs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shouldFailWhenTheActiveSubclassesDifferEvenIfTheyAreAsManyAsTheObservedOnes():
    result = unobserved_pairs(corpus(), 2002, min_documents=2)
    observed = {"active": {"A01B": 3, "A01C": 2, "Z99Z": 3}, "pairs": {}}  # same size, one identifier differs
    with pytest.raises(AssertionError, match="active subclasses differ"):
        report_script().check_against_observed(result, observed)


def test_shouldFailWhenTheDocumentsOfAnActiveSubclassDiffer():
    result = unobserved_pairs(corpus(), 2002, min_documents=2)
    observed = {"active": {"A01B": 3, "A01C": 2, "B01B": 4}, "pairs": {}}
    with pytest.raises(AssertionError, match="active subclasses differ"):
        report_script().check_against_observed(result, observed)


def test_shouldAcceptTheSameActiveSubclassesWithTheSameDocuments():
    result = unobserved_pairs(corpus(), 2002, min_documents=2)
    observed = {"active": {"A01B": 3, "A01C": 2, "B01B": 3}, "pairs": {}}
    report_script().check_against_observed(result, observed)


@pytest.fixture(scope="module")
def versioned() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_shouldHaveTheCountsOfTheVersionedResultAgreeWithItsOwnPairs(versioned):
    counts = versioned["counts"]
    assert counts["active"] == len(versioned["active"])
    assert counts["pairs"] == counts["active"] * (counts["active"] - 1) // 2
    assert counts["unobserved"] == sum(len(row) for row in versioned["pairs"].values())
    assert versioned["origin"] == 2025
    assert versioned["min_documents"] == 20
    assert versioned["e_min"] == 1.0


def test_shouldListOnlyOrderedPairsOfActiveSubclassesWithNonNegativeValuesInTheVersionedResult(versioned):
    active = versioned["active"]
    for a, row in versioned["pairs"].items():
        assert a in active
        for b, value in row.items():
            assert a < b
            assert b in active
            assert value >= 0


def test_shouldSkipTheMissingYearAndKeepEveryOtherYearInTheVersionedResult(versioned):
    years = versioned["documents_per_year"]
    assert "2010" not in years
    assert "2025" in years
    assert all(n > 0 for n in years.values())


def test_shouldCarryTheCorpusHashesOfTheConfigurationInTheVersionedResult(versioned):
    figures = json.loads(FIGURES.read_text(encoding="utf-8"))
    assert versioned["corpus"]["files"] == {n: f["sha256"] for n, f in figures["files"].items()}
    assert versioned["corpus"]["source_id"] == figures["source_id"]
