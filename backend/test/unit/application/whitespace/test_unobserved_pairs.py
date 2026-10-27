import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.unobserved_pairs import configuration, configuration_id, unobserved_pairs

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


def test_shouldStoreTheDocumentsByYearOfEachActiveSubclassWithoutTheYearsItDoesNotHave():
    result = unobserved_pairs(corpus(), 2002, min_documents=2)
    assert result["documents_by_year"] == {
        "A01B": {"2000": 2, "2002": 1},
        "A01C": {"2002": 2},
        "B01B": {"2000": 2, "2002": 1},
    }  # A01C has no key for 2000: a year without documents is absent, never zero
    assert {s: sum(v.values()) for s, v in result["documents_by_year"].items()} == result["active"]


def test_shouldNotStoreTheDocumentsByYearOfASubclassThatIsNotActive():
    records = corpus() + [record("z1", 2002, "Z99Z")]
    result = unobserved_pairs(records, 2002, min_documents=2)
    assert "Z99Z" not in result["documents_by_year"]
    assert set(result["documents_by_year"]) == set(result["active"])


def test_shouldGiveTheConfigurationIdOfTheContractTestVector():
    config = configuration(2025, 20, 1.0)
    assert config["parameters"] == {
        "e_min": "1",
        "min_documents": 20,
        "origin": 2025,
        "quantity": "ADR 0038 E3",
        "schema": "vertical3-unobserved-pairs/1",
        "unit": "O4",
    }
    assert config["id"] == "456858bd653d792244206f9ef5a531524279c4f5d2402b1f016ebf435f883bd8"


@pytest.mark.parametrize("e_min", [1, 1.0, 1.00])
def test_shouldGiveTheSameIdWhenEMinIsWrittenAsOneOrOnePointZero(e_min):
    assert configuration(2025, 20, e_min)["id"] == "456858bd653d792244206f9ef5a531524279c4f5d2402b1f016ebf435f883bd8"


def test_shouldChangeTheIdWhenAParameterChanges():
    base = configuration(2025, 20, 1.0)["id"]
    assert configuration(2022, 20, 1.0)["id"] != base
    assert configuration(2025, 21, 1.0)["id"] != base
    assert configuration(2025, 20, 1.5)["id"] != base


def test_shouldNotDependOnTheOrderOfTheKeysWhenComputingTheId():
    parameters = configuration(2025, 20, 1.0)["parameters"]
    assert configuration_id(dict(reversed(list(parameters.items())))) == configuration_id(parameters)


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


def test_shouldRecordAConfigurationWhoseIdIsTheHashOfItsOwnParametersInTheVersionedResult(versioned):
    config = versioned["configuration"]
    assert config["id"] == configuration_id(config["parameters"])
    assert config["parameters"] == configuration(versioned["origin"], versioned["min_documents"], versioned["e_min"])["parameters"]


def test_shouldHaveTheDocumentsByYearAddUpToTheDocumentsOfEveryActiveSubclassInTheVersionedResult(versioned):
    by_year = versioned["documents_by_year"]
    assert set(by_year) == set(versioned["active"])
    assert {s: sum(v.values()) for s, v in by_year.items()} == versioned["active"]


def test_shouldHaveNoYearWithoutDocumentsAndNoZeroCountInTheDocumentsByYearOfTheVersionedResult(versioned):
    years = set(versioned["documents_per_year"])
    for by_year in versioned["documents_by_year"].values():
        assert set(by_year) <= years
        assert "2010" not in by_year
        assert all(n > 0 for n in by_year.values())
