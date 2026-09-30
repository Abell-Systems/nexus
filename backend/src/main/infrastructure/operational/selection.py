from dataclasses import dataclass
from typing import Any

_OPTIONAL_GROUPS = ("borderline_excluded_by_default", "excluded")


@dataclass(frozen=True)
class DemoSelection:
    included: frozenset[str]
    primary: tuple[str, ...]
    secondary: tuple[str, ...]


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
    ids = doc.get("demo_journeys", {}).get(name, [])
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ValueError(f"Demo selection journey '{name}' must be a list of demand ids")
    stray = [i for i in ids if i not in included]
    if stray:
        raise ValueError(f"Demo selection journey '{name}' names demands that are not included: {stray}")
    return tuple(ids)


def parse_selection(raw: object) -> DemoSelection:
    """Validates the shape of demo_selection_v1.json, which controls what a user sees."""
    if not isinstance(raw, dict):
        raise ValueError("Demo selection must be a JSON object")
    if not isinstance(raw.get("rule"), str) or not raw["rule"].strip():
        raise ValueError("Demo selection needs a non-blank 'rule'")
    included = frozenset(_reasons(raw, "included"))
    if not included:
        raise ValueError("Demo selection is empty")

    seen = set(included)
    for key in _OPTIONAL_GROUPS:
        if key in raw:
            ids = set(_reasons(raw, key))
            if ids & seen:
                raise ValueError(f"Demo selection has demands in more than one group: {sorted(ids & seen)}")
            seen |= ids
    return DemoSelection(
        included=included,
        primary=_journey(raw, "primary", included),
        secondary=_journey(raw, "secondary", included),
    )
