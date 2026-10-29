from datetime import date

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.topic_units import Unit, in_subarea, in_topic, o4_units, topic_counts
from domain.models.topic_map import CodeRule, SubArea, TopicDefinition


def rec(doc, year, subclasses, groups=(), group="patent", applicants=(), month=6):
    return AnalysisRecord(
        doc, date(year, month, 1), group, year, tuple(sorted(subclasses)), "", tuple(sorted(groups)), applicants
    )


def rule(subclass, main_group=None):
    return CodeRule(subclass=subclass, main_group=main_group, introduced=None, removed=None, verified=True)


def area(key, *codes):
    return SubArea(key=key, name=key, description=key, reviewed=True, codes=tuple(codes))


def topic(*areas, own=("H01M",)):
    return TopicDefinition(
        key="t",
        name="T",
        noun="t",
        joined="t",
        subareas=tuple(areas),
        neighbour_names=(),
        own_subclasses=frozenset(own),
    )


def corpus():
    return [
        rec("a", 2000, ["H01M", "H02J"], ["H01M 10"], "patent", ("X",)),
        rec("b", 2000, ["H01M"], ["H01M 4"], "ep_translation"),
        rec("c", 2002, ["H02J", "B60L"], ["H02J 7"]),
        rec("d", 2002, ["H01M", "B60L"], ["H01M 10", "H01M 4"], "ep_translation"),
        rec("e", 2002, ["A01B"]),
    ]


TWO = topic(area("one", rule("H01M", "10")), area("two", rule("H01M", "4"), rule("H02J")))


def test_shouldUseTheUnionOfCopiesOfTheEarliestDate():
    units = {
        u.doc_id: u
        for u in o4_units(
            [
                rec("a", 2003, ["Z99Z"], month=1),
                rec("a", 2001, ["H01M"], ["H01M 10"], "patent", ("X",), month=3),
                rec("a", 2001, ["H02J"], ["H02J 7"], "ep_translation", ("Y", "X"), month=3),
            ]
        )
    }
    assert units["a"] == Unit(
        "a", 2001, frozenset({"H01M", "H02J"}), frozenset({"H01M 10", "H02J 7"}), "patent", ("X", "Y")
    )


def test_shouldCountAUnitOnceWhenSeveralCodesMatchTheTopic():
    unit = Unit("d", 2002, frozenset({"H01M"}), frozenset({"H01M 10", "H01M 4"}), "patent", ())
    assert in_topic(unit, TWO)
    assert topic_counts(
        [unit, unit.__class__("e", 2002, frozenset({"A01B"}), frozenset(), "patent", ())], TWO
    ).documents_by_year == {2002: 1}


def test_shouldMatchWholeSubclassOrMainGroup():
    unit = Unit("x", 2000, frozenset({"H01M"}), frozenset({"H01M 4"}), "patent", ())
    assert in_subarea(unit, area("a", rule("H01M")))
    assert in_subarea(unit, area("a", rule("H01M", "4")))
    assert not in_subarea(unit, area("a", rule("H01M", "10")))


def test_shouldKeepSubareaCountsAtOrBelowTheTopicCount():
    counts = topic_counts(o4_units(corpus()), TWO)
    total = sum(counts.documents_by_year.values())
    assert total == 4
    assert counts.subarea_counts == {"one": 2, "two": 4}
    assert all(n <= total for n in counts.subarea_counts.values())


def test_shouldEqualTheTopicWhenUnitingTheSubareas():
    one_area = topic(area("all", rule("H01M", "10"), rule("H01M", "4"), rule("H02J")))
    assert (
        topic_counts(o4_units(corpus()), one_area).documents_by_year
        == topic_counts(o4_units(corpus()), TWO).documents_by_year
    )


def test_shouldGiveTheSameCountsWhateverTheOrderOfCodes():
    flipped = topic(area("one", rule("H01M", "10")), area("two", rule("H02J"), rule("H01M", "4")))
    assert topic_counts(o4_units(corpus()), flipped) == topic_counts(o4_units(corpus()), TWO)


def test_shouldExcludeOwnSubclassesFromNeighbours():
    counts = topic_counts(o4_units(corpus()), TWO)
    assert counts.neighbour_counts == {"H02J": 2, "B60L": 2}
    assert "H01M" not in counts.neighbour_counts


def test_shouldSkipYearsWithoutDocuments():
    counts = topic_counts(o4_units([rec("a", 2000, ["H01M"], ["H01M 10"]), rec("b", 2002, ["H01M"], ["H01M 10"])]), TWO)
    assert counts.corpus_by_year == {2000: 1, 2002: 1}
    assert 2010 not in counts.corpus_by_year and 2001 not in counts.documents_by_year


def test_shouldCountUnitsNotRecordsAndCorpusYearsFromUnits():
    counts = topic_counts(o4_units(corpus() + [rec("a", 2000, ["H01M", "H02J"], ["H01M 10"])]), TWO)
    assert counts.corpus_by_year == {2000: 2, 2002: 3}
    assert counts.documents_by_year == {2000: 2, 2002: 2}


def test_shouldMeasureEpShareOverTheTopicUnitsOfEachYear():
    counts = topic_counts(o4_units(corpus()), TWO)
    assert counts.ep_share_by_year == {2000: 0.5, 2002: 0.5}
