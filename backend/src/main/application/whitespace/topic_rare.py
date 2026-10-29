"""'Menos de lo esperado' rows: ADR 0038 E3 within years, over O4 units (topic map, spec section 7)."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from application.whitespace.topic_units import Unit, in_topic
from domain.models.topic_map import TopicDefinition

MIN_OBSERVED = 30
MIN_EXPECTED = 30.0
MAX_RATIO = 0.8


@dataclass(frozen=True)
class RareRow:
    subclass: str
    name: str
    observed: int
    expected: float
    ratio: float


def rare_combinations(units: Iterable[Unit], definition: TopicDefinition) -> list[RareRow]:
    units = list(units)
    total = Counter(u.year for u in units)
    members = [u for u in units if in_topic(u, definition)]
    in_year = Counter(u.year for u in members)
    carrying: Counter[tuple[int, str]] = Counter((u.year, s) for u in units for s in u.subclasses)
    observed = Counter(s for u in members for s in u.subclasses)
    names = {n.subclass: n.name for n in definition.neighbour_names}
    min_expected, max_ratio = Fraction(str(MIN_EXPECTED)), Fraction(str(MAX_RATIO))  # decimal literals, not binary floats
    rows = []
    for subclass, o in observed.items():
        if subclass in definition.own_subclasses or o < MIN_OBSERVED:
            continue
        expected = sum(Fraction(n_t * carrying[(y, subclass)], total[y]) for y, n_t in in_year.items())
        if expected < min_expected or Fraction(o) / expected >= max_ratio:
            continue
        rows.append(
            RareRow(subclass, names.get(subclass, subclass), o, round(float(expected), 9), round(float(o / expected), 9))
        )
    return sorted(rows, key=lambda r: (r.name, r.subclass))
