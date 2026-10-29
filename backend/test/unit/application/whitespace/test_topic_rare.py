from application.whitespace.topic_rare import MAX_RATIO, MIN_EXPECTED, MIN_OBSERVED, RareRow, rare_combinations
from application.whitespace.topic_units import Unit
from domain.models.topic_map import CodeRule, NeighbourName, SubArea, TopicDefinition


def definition(names=None):
    rule = CodeRule(subclass="T01T", main_group=None, introduced=None, removed=None, verified=True)
    return TopicDefinition(
        key="t",
        name="T",
        noun="t",
        joined="t",
        subareas=(SubArea(key="a", name="a", description="a", reviewed=True, codes=(rule,)),),
        neighbour_names=tuple(NeighbourName(subclass=c, name=n, reviewed=True) for c, n in (names or {}).items()),
        own_subclasses=frozenset({"T01T"}),
    )


def units(year, *spec):
    """spec: (subclasses, count) pairs; a unit is in the topic when it carries T01T."""
    out = []
    for subclasses, count in spec:
        out += [Unit(f"{year}-{len(out)}", year, frozenset(subclasses), frozenset(), "patent", ()) for _ in range(count)]
    return out


def single_x(a, b, c, d, year=2000):
    """a: topic+X, b: topic only, c: X only (outside), d: neither."""
    return units(year, ({"T01T", "X01X"}, a), ({"T01T"}, b), ({"X01X"}, c), ({"Z01Z"}, d))


def rows(a, b, c, d):
    return rare_combinations(single_x(a, b, c, d), definition())


def test_shouldExposeTheProvisionalParametersInOnePlace():
    assert (MIN_OBSERVED, MIN_EXPECTED, MAX_RATIO) == (30, 30.0, 0.8)


def test_shouldComputeExpectedWithinYearsWhenTwoYearsDiffer():
    # y1: N=1000 nT=100 nX=900 -> 90 ; y2: N=1000 nT=900 nX=100 -> 90 ; E=180 (corpus-wide would be 500)
    # O = 50 + 50 = 100 ; ratio = 100/180 = 0.555555556
    data = single_x(50, 50, 850, 50, 2000) + single_x(50, 850, 50, 50, 2001)
    assert rare_combinations(data, definition({"X01X": "Equis"})) == [RareRow("X01X", "Equis", 100, 180.0, 0.555555556)]


def test_shouldSkipTheYearWithoutDocumentsWhenSumming():
    data = single_x(50, 50, 850, 50, 2009) + single_x(50, 850, 50, 50, 2011)
    assert [r.expected for r in rare_combinations(data, definition())] == [180.0]


def test_shouldIncludeARowOnlyWhenObservedAndExpectedAreAtLeast30AndRatioBelow0Point8():
    # nT=500 nX=200 N=1000 -> E=100, O=30 -> 0.3
    assert rows(30, 470, 170, 330) == [RareRow("X01X", "X01X", 30, 100.0, 0.3)]


def test_shouldExcludeWhenObservedIs29():
    assert rows(29, 471, 171, 329) == []


def test_shouldIncludeWhenObservedIs30():
    assert [r.observed for r in rows(30, 470, 170, 330)] == [30]


def test_shouldExcludeWhenExpectedIs29Point9():
    # nT=299 nX=100 N=1000 -> 29.9
    assert rows(30, 269, 70, 631) == []


def test_shouldExcludeWhenRatioIs0Point8():
    # nT=500 nX=200 N=1000 -> E=100, O=80
    assert rows(80, 420, 120, 380) == []


def test_shouldIncludeWhenRatioIs0Point79():
    assert [r.ratio for r in rows(79, 421, 121, 379)] == [0.79]


def test_shouldNeverReturnARowWithZeroObserved():
    # X only outside the topic: E = 500*200/1000 = 100, O = 0
    assert rows(0, 500, 200, 300) == []


def test_shouldReturnAnEmptyListWhenNothingQualifies():
    assert rare_combinations([], definition()) == []


def test_shouldOrderAlphabeticallyByNameNotByRatio():
    # N=1000 nT=500; B01B: nX=200 O=30 (ratio .3) ; C01C: nX=200 O=70 (ratio .7) ; each E=100
    data = units(
        2000,
        ({"T01T", "B01B"}, 30),
        ({"T01T", "C01C"}, 70),
        ({"T01T"}, 400),
        ({"B01B"}, 170),
        ({"C01C"}, 130),
        ({"Z01Z"}, 200),
    )
    result = rare_combinations(data, definition({"B01B": "Zeta", "C01C": "Alfa"}))
    assert [(r.name, r.subclass) for r in result] == [("Alfa", "C01C"), ("Zeta", "B01B")]
    assert result[0].ratio > result[1].ratio


def test_shouldFallBackToTheSubclassCodeWhenThereIsNoName():
    assert rows(30, 470, 170, 330)[0].name == "X01X"
