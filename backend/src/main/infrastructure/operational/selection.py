import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from domain.protocols.demand_repository import DemandRepository

_OPTIONAL_GROUPS = ("borderline_excluded_by_default", "excluded")


@dataclass(frozen=True)
class DemoSelection:
    included: frozenset[str]
    borderline: frozenset[str]
    excluded: frozenset[str]
    primary: tuple[str, ...]
    secondary: tuple[str, ...]

    @property
    def all_ids(self) -> frozenset[str]:
        return self.included | self.borderline | self.excluded


def _reasons(doc: dict[str, Any], key: str) -> dict[str, str]:
    group = doc.get(key)
    if not isinstance(group, dict):
        raise ValueError(f"Demo selection '{key}' must be an object mapping demand id to reason")
    for demand_id, reason in group.items():
        if not isinstance(demand_id, str) or not demand_id.strip():
            raise ValueError(f"Demo selection '{key}' has a blank demand id")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"Demo selection '{key}': demand {demand_id} needs a non-blank reason")
    return group


def _journey(doc: dict[str, Any], name: str, included: frozenset[str]) -> tuple[str, ...]:
    journeys = doc.get("demo_journeys", {})
    if not isinstance(journeys, dict):
        raise ValueError("Demo selection 'demo_journeys' must be an object of journey name to demand ids")
    ids = journeys.get(name, [])
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ValueError(f"Demo selection journey '{name}' must be a list of demand ids")
    stray = [i for i in ids if i not in included]
    if stray:
        raise ValueError(f"Demo selection journey '{name}' names demands that are not included: {stray}")
    return tuple(ids)


def parse_selection(raw: object) -> DemoSelection:
    if not isinstance(raw, dict):
        raise ValueError("Demo selection must be a JSON object")
    if not isinstance(raw.get("rule"), str) or not raw["rule"].strip():
        raise ValueError("Demo selection needs a non-blank 'rule'")
    included = frozenset(_reasons(raw, "included"))
    if not included:
        raise ValueError("Demo selection is empty")

    seen = set(included)
    optional: dict[str, frozenset[str]] = {}
    for key in _OPTIONAL_GROUPS:
        ids = set(_reasons(raw, key)) if key in raw else set()
        if ids & seen:
            raise ValueError(f"Demo selection has demands in more than one group: {sorted(ids & seen)}")
        seen |= ids
        optional[key] = frozenset(ids)
    return DemoSelection(
        included=included,
        borderline=optional["borderline_excluded_by_default"],
        excluded=optional["excluded"],
        primary=_journey(raw, "primary", included),
        secondary=_journey(raw, "secondary", included),
    )


def validate_against_demands(selection: DemoSelection, demand_ids: set[str] | frozenset[str]) -> None:
    unknown = sorted(selection.all_ids - demand_ids)
    if unknown:
        raise ValueError(f"Demo selection names unknown demands: {unknown}")
    missing = sorted(demand_ids - selection.all_ids)
    if missing:
        raise ValueError(f"Demo selection puts demands in no group: {missing}")


def read_demo_selection(path: Path, demands: DemandRepository) -> frozenset[str]:
    selection = parse_selection(json.loads(path.read_text(encoding="utf-8")))
    validate_against_demands(selection, {d.demand_id for d in demands.list_all()})
    return selection.included
