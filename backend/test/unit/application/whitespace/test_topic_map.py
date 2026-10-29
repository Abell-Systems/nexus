import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.applicant_names import Rule
from application.whitespace.topic_definition import definition_id
from application.whitespace.topic_map import SCHEMA, build_topic_result, check_invariants
from application.whitespace.unobserved_pairs import configuration_id
from domain.models.topic_map import CodeRule, NeighbourName, SubArea, TopicDefinition

REPO_ROOT = Path(__file__).resolve().parents[5]
CORPUS = {"source_id": "synthetic", "files": {"BIBLIO_2000.zip": "a" * 64, "BIBLIO_2001.zip": "b" * 64}}
RULES = (Rule("ACME", "Acme", "same applicant", "2026-10-29"),)
NEIGHBOUR_COUNTS = (  # record order differs from the expected order on purpose
    ("Q06Q", 1),
    ("Q03Q", 2),
    ("Q02Q", 2),
    ("Q01Q", 7),
    ("Q00Q", 2),
    ("Q05Q", 5),
    ("Q04Q", 5),
    ("Q08Q", 3),
    ("Q07Q", 3),
    ("Q12Q", 4),
    ("Q11Q", 6),
    ("Q10Q", 6),
    ("Q09Q", 4),
)


def definition(subarea_reviewed=True, neighbours=None, unreviewed_neighbour=None):
    whole = CodeRule(subclass="T01T", main_group=None, introduced=None, removed=None, verified=True)
    group = CodeRule(subclass="U01U", main_group="5", introduced=None, removed=None, verified=True)
    names = dict(neighbours or {"X01X": "Equis"})
    return TopicDefinition(
        key="t",
        name="Tema",
        noun="tema",
        joined="junto a tema",
        subareas=(
            SubArea(key="a", name="Área A", description="a", reviewed=subarea_reviewed, codes=(whole,)),
            SubArea(key="b", name="Área B", description="b", reviewed=True, codes=(group,)),
        ),
        neighbour_names=tuple(
            NeighbourName(subclass=c, name=n, reviewed=c != unreviewed_neighbour) for c, n in sorted(names.items())
        ),
        own_subclasses=frozenset({"T01T", "U01U"}),
    )


def rec(doc_id, published, subclasses, groups=(), applicants=(), group="patent"):
    return AnalysisRecord(doc_id, published, group, None, tuple(subclasses), "", tuple(groups), tuple(applicants))


def yearly_records():
    return [
        rec("d1", date(2000, 3, 1), ["U01U"], ["U01U 5"], ["ACME S.A.", "Acme SA"]),
        rec("d1", date(2000, 3, 1), ["T01T"], [], ["ACME S.A."]),  # second copy of the same unit
        rec("d2", date(2000, 5, 1), ["T01T", "X01X"], [], ["ACME", "  ", "Beta Corp"]),
        rec("d2", date(2001, 2, 1), ["T01T"], [], ["Late Copy"]),  # later publication: not the unit
        rec("d3", date(2001, 6, 1), ["T01T"], [], ["beta corp"], group="ep_translation"),
        rec("d4", date(2001, 7, 1), ["X01X"], [], ["ACME"]),  # outside the topic
        rec("d5", date(2002, 1, 1), ["Z01Z"]),  # a corpus unit, no topic unit that year
        rec("d6", date(2011, 1, 1), ["T01T"], [], ["Zeta"]),
    ]


def neighbour_records():
    out = []
    for code, count in NEIGHBOUR_COUNTS:
        out += [rec(f"{code}-{i}", date(2000, 1, 1), ["T01T", code], [], [f"Firm {code}"]) for i in range(count)]
    return out


def rare_records():
    """Topic and Y01Y overlap 30 times where independence expects 250 (N=1000, nT=nY=500); a second year adds noise."""
    out = [rec(f"r{i}", date(2005, 1, 1), ["T01T", "Y01Y"]) for i in range(30)]
    out += [rec(f"t{i}", date(2005, 1, 1), ["T01T"]) for i in range(470)]
    out += [rec(f"y{i}", date(2005, 1, 1), ["Y01Y"]) for i in range(470)]
    out += [rec(f"z{i}", date(2005, 1, 1), ["Z01Z"]) for i in range(30)]
    return out


def full_definition(**kwargs):
    names = {"X01X": "Equis", "Y01Y": "Igriega"} | {c: f"Nombre {c}" for c, _ in NEIGHBOUR_COUNTS}
    return definition(neighbours=names, **kwargs)


def full_result():
    return build_topic_result(yearly_records() + neighbour_records() + rare_records(), full_definition(), RULES, CORPUS)


def result_bytes():
    return json.dumps(full_result(), ensure_ascii=False, separators=(",", ":"))


def test_shouldRefuseUnreviewedNamesWhenBuildingForClients():
    with pytest.raises(ValueError, match="Área A") as error:
        build_topic_result(
            yearly_records(), definition(subarea_reviewed=False, unreviewed_neighbour="X01X"), RULES, CORPUS
        )
    assert "Equis" in str(error.value)


def test_shouldMarkTheResultUnreviewedWhenAllowedAndListTheNames():
    result = build_topic_result(
        yearly_records(),
        definition(subarea_reviewed=False, unreviewed_neighbour="X01X"),
        RULES,
        CORPUS,
        allow_unreviewed=True,
    )
    assert result["names_reviewed"] is False
    assert result["unreviewed"] == ["Equis", "Área A"]


def test_shouldMarkTheResultReviewedWhenEveryNameIsReviewed():
    result = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    assert (result["names_reviewed"], result["unreviewed"]) == (True, [])


def test_shouldChangeTheConfigurationIdWhenANameChanges():
    one = build_topic_result(yearly_records(), definition(neighbours={"X01X": "Equis"}), RULES, CORPUS)
    two = build_topic_result(yearly_records(), definition(neighbours={"X01X": "Equis bis"}), RULES, CORPUS)
    assert one["configuration"]["id"] != two["configuration"]["id"]


def test_shouldChangeTheConfigurationIdWhenAnApplicantRuleChanges():
    one = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    two = build_topic_result(yearly_records(), definition(), (Rule("ACME", "Acme Group", "r", "2026-10-29"),), CORPUS)
    assert one["configuration"]["id"] != two["configuration"]["id"]


def test_shouldFailInvariantsWhenASubareaExceedsTheTopic():
    result = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    check_invariants(result)
    result["subareas"][1]["documents"] = result["total_documents"] + 1
    with pytest.raises(ValueError, match="sub-area"):
        check_invariants(result)


def test_shouldFailInvariantsWhenTheTrendDoesNotAddUpToTheTotal():
    result = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    result["trend"][0]["documents"] += 1
    with pytest.raises(ValueError, match="trend"):
        check_invariants(result)


def test_shouldFailInvariantsWhenARareRowHasFewerThan30Observed():
    result = full_result()
    result["rare"][0]["observed"] = 29
    with pytest.raises(ValueError, match="observed"):
        check_invariants(result)


def test_shouldFailInvariantsWhenRareRowsAreNotAlphabetical():
    result = full_result()
    result["rare"] = [dict(result["rare"][0], name="Zzz"), dict(result["rare"][0], name="Aaa")]
    with pytest.raises(ValueError, match="alphabetical"):
        check_invariants(result)


def test_shouldMatchYearlyTotalsWithTheInputUnits():
    # units: 2000 d1 d2 (topic) ; 2001 d3 (topic, EP) d4 ; 2002 d5 ; 2011 d6 (topic). 2010 has no unit.
    result = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    assert result["years"] == [2000, 2001, 2002, 2011]
    assert result["trend"] == [
        {"year": 2000, "documents": 2, "share": 100.0, "ep_documents": 0},
        {"year": 2001, "documents": 1, "share": 50.0, "ep_documents": 1},
        {"year": 2002, "documents": 0, "share": 0.0, "ep_documents": 0},
        {"year": 2011, "documents": 1, "share": 100.0, "ep_documents": 0},
    ]
    assert (result["total_documents"], result["corpus_documents"], result["ep_share"]) == (4, 6, 0.25)
    assert result["subareas"] == [
        {"key": "a", "name": "Área A", "description": "a", "documents": 4, "series": [2, 1, 0, 1]},
        {"key": "b", "name": "Área B", "description": "b", "documents": 1, "series": [1, 0, 0, 0]},
    ]
    assert result["topic"] == {"key": "t", "name": "Tema", "noun": "tema", "joined": "junto a tema"}


def test_shouldMergeApplicantsByRulesCountingEachUnitOnceAndDroppingBlankNames():
    result = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    assert result["applicants"] == [
        {"name": "Acme", "documents": 2, "originals": ["ACME", "ACME S.A.", "Acme SA"]},
        {"name": "Beta Corp", "documents": 2, "originals": ["Beta Corp", "beta corp"]},
        {"name": "Zeta", "documents": 1, "originals": ["Zeta"]},
    ]
    # last two years are 2002 (no applicant) and 2011 (Zeta): the recent leader is not the overall leader Acme
    assert result["top_applicant_recent"] == {"name": "Zeta", "by_year": [0, 0, 0, 1]}


def applicant_units(spec):
    """spec: (applicant or None, year, count); every unit is in the topic."""
    out = []
    for name, year, count in spec:
        applicants = [name] if name else []
        out += [rec(f"{name}-{year}-{i}", date(year, 1, 1), ["T01T"], [], applicants) for i in range(count)]
    return out


def test_shouldPickTheLeaderOfTheLastTwoYearsWhenItDiffersFromTheOverallLeader():
    # OldCo: 10 in 2020, 1 in 2024 -> 11 overall, 1 recent ; NewCo: 3 in 2024, 2 in 2025 -> 5 overall, 5 recent
    records = applicant_units([("OldCo", 2020, 10), ("OldCo", 2024, 1), ("NewCo", 2024, 3), ("NewCo", 2025, 2)])
    result = build_topic_result(records, definition(), RULES, CORPUS)
    assert result["applicants"][0]["name"] == "Oldco"
    assert result["top_applicant_recent"] == {"name": "Newco", "by_year": [0, 3, 2]}


def test_shouldBreakARecentTieByNameWhenTwoApplicantsHaveTheSameRecentDocuments():
    # Zed: 5 in 2020 + 2 in 2025 (7 overall, 2 recent) ; Abe: 2 in 2024 (2 overall, 2 recent) -> Abe by name
    records = applicant_units([("Zed", 2020, 5), ("Zed", 2025, 2), ("Abe", 2024, 2)])
    result = build_topic_result(records, definition(), RULES, CORPUS)
    assert result["top_applicant_recent"] == {"name": "Abe", "by_year": [0, 2, 0]}


def test_shouldGiveNoRecentLeaderWhenNobodyHasDocumentsInTheLastTwoYears():
    records = applicant_units([("OldCo", 2000, 3), (None, 2024, 1), (None, 2025, 1)])
    result = build_topic_result(records, definition(), RULES, CORPUS)
    assert result["applicants"][0]["name"] == "Oldco"
    assert result["top_applicant_recent"] is None


def test_shouldKeepTwelveApplicantsWhenThereAreMore():
    result = full_result()
    assert len(result["applicants"]) == 12
    assert result["applicants"][0] == {"name": "Firm Q01Q", "documents": 7, "originals": ["Firm Q01Q"]}


def test_shouldListTheTwelveLargestNeighboursSortedByDocumentsThenSubclass():
    result = full_result()
    assert [(n["subclass"], n["documents"]) for n in result["neighbours"]] == [
        ("Y01Y", 30),
        ("Q01Q", 7),
        ("Q10Q", 6),
        ("Q11Q", 6),
        ("Q04Q", 5),
        ("Q05Q", 5),
        ("Q09Q", 4),
        ("Q12Q", 4),
        ("Q07Q", 3),
        ("Q08Q", 3),
        ("Q00Q", 2),
        ("Q02Q", 2),
    ]
    assert result["neighbours"][0]["name"] == "Igriega"


def test_shouldEmitOnlyQualifyingRareRowsWithTheirPlainName():
    # Y01Y only in 2005: N=1000 nT=500 nY=500 -> E=250 ; O=30 ; ratio 0.12. Q01Q (O=7) and X01X (O=1) are below 30.
    rare = full_result()["rare"]
    assert rare == [{"subclass": "Y01Y", "name": "Igriega", "observed": 30, "expected": 250.0, "ratio": 0.12}]


def test_shouldRefuseANeighbourWithoutPlainNameWhenBuilding():
    with pytest.raises(ValueError, match="Y01Y"):
        build_topic_result(rare_records(), definition(), RULES, CORPUS, allow_unreviewed=True)


def test_shouldRecordTheCorpusHashesAndTheDefinitionId():
    result = build_topic_result(yearly_records(), definition(), RULES, CORPUS)
    parameters = result["configuration"]["parameters"]
    assert result["schema"] == SCHEMA == "topic-map/1"
    assert result["corpus"] == CORPUS
    assert parameters["definition_id"] == definition_id(definition())
    assert (parameters["min_observed"], parameters["min_expected"], parameters["max_ratio"], parameters["unit"]) == (
        30,
        30.0,
        0.8,
        "O4",
    )
    assert result["configuration"]["id"] == configuration_id(parameters)


def test_shouldNotContainAnyRecordOrPerDocumentIdentifier():
    records = yearly_records() + neighbour_records() + rare_records()
    ids = {r.doc_id for r in records}
    seen = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                seen.append(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        else:
            seen.append(value)

    walk(full_result())
    assert not ids & {s for s in seen if isinstance(s, str)}


def test_shouldReproduceTheSameBytesWhenRunTwice():
    assert result_bytes() == result_bytes()
    snippet = f"import runpy; print(runpy.run_path({str(Path(__file__))!r})['result_bytes']())"
    outputs = {
        subprocess.run(
            [sys.executable, "-c", snippet],
            env=os.environ | {"PYTHONHASHSEED": seed, "PYTHONPATH": str(REPO_ROOT / "backend" / "src" / "main")},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("0", "1", "2")
    }
    assert outputs == {result_bytes() + "\n"}


def load_script():
    spec = importlib.util.spec_from_file_location("report_topic_map", REPO_ROOT / "scripts" / "report_topic_map.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shouldRequireTopicCorpusAndOutputWhenParsingArguments():
    script = load_script()
    args = script.parse_args(["--topic", "baterias", "--corpus-dir", "c", "--write", "out.json"])
    assert (args.topic, args.corpus_dir, args.write, args.allow_unreviewed) == (
        "baterias",
        Path("c"),
        Path("out.json"),
        False,
    )
    assert script.parse_args(
        ["--topic", "t", "--corpus-dir", "c", "--write", "o", "--allow-unreviewed"]
    ).allow_unreviewed
    with pytest.raises(SystemExit):
        script.parse_args(["--topic", "baterias", "--corpus-dir", "c"])


def test_shouldRefuseTheVersionedTopicWhenItsNamesAreUnreviewed():
    records = [rec("b1", date(2020, 1, 1), ["H01M"], ["H01M 10"])]
    with pytest.raises(ValueError, match="unreviewed"):
        load_script().build_for_topic("baterias", records, CORPUS, allow_unreviewed=False)


def test_shouldWriteTheBuiltResultWhenRunWithASyntheticCorpus(tmp_path, monkeypatch):
    script = load_script()
    records = [rec("b1", date(2020, 1, 1), ["H01M"], ["H01M 10"]), rec("b2", date(2020, 1, 1), ["A01B"])]
    seen = []
    monkeypatch.setattr(script, "read_corpus", lambda corpus_dir: seen.append(corpus_dir) or (records, CORPUS))
    out = tmp_path / "baterias.json"
    assert (
        script.main(["--topic", "baterias", "--corpus-dir", "synthetic", "--write", str(out), "--allow-unreviewed"])
        == 0
    )
    written = json.loads(out.read_text(encoding="utf-8"))
    assert seen == [Path("synthetic")]
    assert written == script.build_for_topic("baterias", records, CORPUS, allow_unreviewed=True)
    assert (written["topic"]["key"], written["total_documents"], written["names_reviewed"]) == ("baterias", 1, False)
