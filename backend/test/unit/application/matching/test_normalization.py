from application.matching.normalization import min_max_normalize


def test_min_max_normalize_typical():
    scores = {"A": 10.0, "B": 20.0, "C": 30.0}
    norm = min_max_normalize(scores)
    assert norm["A"] == 0.0
    assert norm["B"] == 0.5
    assert norm["C"] == 1.0


def test_min_max_normalize_identical_values():
    scores = {"A": 15.0, "B": 15.0, "C": 15.0}
    norm = min_max_normalize(scores)
    assert norm == {"A": 0.0, "B": 0.0, "C": 0.0}


def test_min_max_normalize_single_value():
    scores = {"A": 42.0}
    norm = min_max_normalize(scores)
    assert norm == {"A": 0.0}


def test_min_max_normalize_empty():
    assert min_max_normalize({}) == {}
