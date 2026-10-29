"""The per-topic result the topic map draws (spec sections 5, 6 and 8): aggregates over O4 units, no per-document data."""

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.applicant_names import Rule, canonical_name, normalise
from application.whitespace.topic_definition import definition_id, unreviewed_names
from application.whitespace.topic_rare import MAX_RATIO, MIN_EXPECTED, MIN_OBSERVED, rare_combinations
from application.whitespace.topic_units import in_subarea, in_topic, o4_units, topic_counts
from application.whitespace.unobserved_pairs import configuration_id
from domain.models.topic_map import TopicDefinition

SCHEMA = "topic-map/1"
TOP_NEIGHBOURS = 12
TOP_APPLICANTS = 12


def _top(counts: dict[str, int], n: int) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def build_topic_result(
    records: Iterable[AnalysisRecord],
    definition: TopicDefinition,
    rules: Sequence[Rule],
    corpus: dict[str, Any],
    *,
    allow_unreviewed: bool = False,
) -> dict[str, Any]:
    unreviewed = sorted(unreviewed_names(definition))
    if unreviewed and not allow_unreviewed:
        raise ValueError(f"topic {definition.key} has unreviewed names: {unreviewed}")
    units = o4_units(records)
    counts = topic_counts(units, definition)
    members = [u for u in units if in_topic(u, definition)]
    years = list(counts.corpus_by_year)
    ep = Counter(u.year for u in members if u.kind_group == "ep_translation")
    total = len(members)

    names = {n.subclass: n.name for n in definition.neighbour_names}
    neighbours = _top(counts.neighbour_counts, TOP_NEIGHBOURS)
    rare = rare_combinations(units, definition)
    unnamed = sorted(
        {s for s, _ in neighbours if s not in names} | {r.subclass for r in rare if r.subclass not in names}
    )
    if unnamed:
        raise ValueError(f"topic {definition.key}: subclasses without a plain name would be shown: {unnamed}")

    applicant_documents: Counter[str] = Counter()
    applicant_years: dict[str, Counter[int]] = defaultdict(Counter)
    originals: dict[str, set[str]] = defaultdict(set)
    for unit in members:
        canonicals = set()
        for raw in unit.applicants:
            if not normalise(raw):
                continue
            canonical, original = canonical_name(raw, rules)
            canonicals.add(canonical)
            originals[canonical].add(original)
        for canonical in canonicals:  # each canonical applicant at most once per unit
            applicant_documents[canonical] += 1
            applicant_years[canonical][unit.year] += 1
    applicants = _top(applicant_documents, TOP_APPLICANTS)

    parameters = {
        "schema": SCHEMA,
        "definition_id": definition_id(definition),
        "applicant_rules_id": configuration_id({"rules": [list(r) for r in rules]}),
        "min_observed": MIN_OBSERVED,
        "min_expected": MIN_EXPECTED,
        "max_ratio": MAX_RATIO,
        "unit": "O4",
    }
    result = {
        "schema": SCHEMA,
        "configuration": {"id": configuration_id(parameters), "parameters": parameters},
        "corpus": corpus,
        "names_reviewed": not unreviewed,
        "unreviewed": unreviewed,
        "topic": {"key": definition.key, "name": definition.name, "noun": definition.noun, "joined": definition.joined},
        "total_documents": total,
        "corpus_documents": len(units),
        "years": years,
        "trend": [
            {
                "year": y,
                "documents": counts.documents_by_year.get(y, 0),
                "share": round(100 * counts.documents_by_year.get(y, 0) / n, 9),
                "ep_documents": ep[y],
            }
            for y, n in counts.corpus_by_year.items()
        ],
        "ep_share": round(sum(ep.values()) / total, 9) if total else 0.0,
        "top_applicant_recent": (
            {"name": applicants[0][0], "by_year": [applicant_years[applicants[0][0]][y] for y in years]}
            if applicants
            else None
        ),
        "subareas": [
            {
                "key": area.key,
                "name": area.name,
                "description": area.description,
                "documents": counts.subarea_counts[area.key],
                "series": [sum(u.year == y and in_subarea(u, area) for u in members) for y in years],
            }
            for area in definition.subareas
        ],
        "neighbours": [{"subclass": s, "name": names[s], "documents": d} for s, d in neighbours],
        "rare": [asdict(r) for r in rare],
        "applicants": [{"name": a, "documents": d, "originals": sorted(originals[a])} for a, d in applicants],
    }
    check_invariants(result)
    return result


def check_invariants(result: dict[str, Any]) -> None:
    total = result["total_documents"]
    for area in result["subareas"]:
        if area["documents"] > total:
            raise ValueError(f"sub-area {area['key']} has {area['documents']} documents, more than the topic's {total}")
    if sum(row["documents"] for row in result["trend"]) != total:
        raise ValueError(f"trend documents do not add up to the topic's {total}")
    if any(row["observed"] < MIN_OBSERVED for row in result["rare"]):
        raise ValueError(f"a rare row has fewer than {MIN_OBSERVED} observed documents")
    keys = [(row["name"], row["subclass"]) for row in result["rare"]]
    if keys != sorted(keys):
        raise ValueError("rare rows are not in alphabetical order")
