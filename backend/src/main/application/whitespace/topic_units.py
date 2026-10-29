"""O4 units and topic membership counts (topic map, spec section 6)."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from application.whitespace.analysis_records import AnalysisRecord
from domain.models.topic_map import SubArea, TopicDefinition


@dataclass(frozen=True)
class Unit:
    doc_id: str
    year: int
    subclasses: frozenset[str]
    groups: frozenset[str]
    kind_group: str
    applicants: tuple[str, ...]


@dataclass(frozen=True)
class TopicCounts:
    documents_by_year: dict[int, int]
    corpus_by_year: dict[int, int]
    subarea_counts: dict[str, int]
    neighbour_counts: dict[str, int]
    ep_share_by_year: dict[int, float]


def o4_units(records: Iterable[AnalysisRecord]) -> list[Unit]:
    """One unit per identifier: the union of the copies that share its earliest publication date."""
    earliest: dict[str, tuple[date, list[AnalysisRecord]]] = {}
    for record in records:
        current = earliest.get(record.doc_id)
        if current is None or record.published < current[0]:
            earliest[record.doc_id] = (record.published, [record])
        elif record.published == current[0]:
            current[1].append(record)
    return [
        Unit(
            doc_id=doc_id,
            year=published.year,
            subclasses=frozenset(s for c in copies for s in c.subclasses),
            groups=frozenset(g for c in copies for g in c.groups),
            kind_group=copies[0].group,
            applicants=tuple(dict.fromkeys(a for c in copies for a in c.applicants)),
        )
        for doc_id, (published, copies) in earliest.items()
    ]


def in_subarea(unit: Unit, subarea: SubArea) -> bool:
    return any(
        rule.subclass in unit.subclasses
        if rule.main_group is None
        else f"{rule.subclass} {rule.main_group}" in unit.groups
        for rule in subarea.codes
    )


def in_topic(unit: Unit, definition: TopicDefinition) -> bool:
    return any(in_subarea(unit, area) for area in definition.subareas)


def topic_counts(units: Iterable[Unit], definition: TopicDefinition) -> TopicCounts:
    units = list(units)
    members = [u for u in units if in_topic(u, definition)]
    by_year = Counter(u.year for u in members)
    ep = Counter(u.year for u in members if u.kind_group == "ep_translation")
    return TopicCounts(
        documents_by_year=dict(sorted(by_year.items())),
        corpus_by_year=dict(sorted(Counter(u.year for u in units).items())),
        subarea_counts={a.key: sum(in_subarea(u, a) for u in members) for a in definition.subareas},
        neighbour_counts=dict(Counter(s for u in members for s in u.subclasses - definition.own_subclasses)),
        ep_share_by_year={y: ep[y] / n for y, n in sorted(by_year.items())},
    )
