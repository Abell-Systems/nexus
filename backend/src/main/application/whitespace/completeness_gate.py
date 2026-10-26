"""Exposure gate on the completeness of the reference year (vertical 3 contract, section 9.2; ADR 0038).

The view of the exploratory track may be exposed only if, for the reference year, the share of the OEPM inventory's publication
keys that the corpus lacks is at most ``threshold_percent`` in **each** kind group. The gate fails closed: anything that cannot
be shown to meet the criterion (a missing year or group, a malformed or inconsistent count, an empty group, no provenance of
the inventory) blocks. The comparison is against the OEPM's own inventory, not an independent count. The share is judged on the
counts with integer arithmetic, never on the rounded percentage stored in the result.
"""

from collections.abc import Mapping
from typing import Any

from application.whitespace.corpus_exposure import GROUPS

THRESHOLD_PERCENT = 1
REFERENCE_YEAR = 2025
CAVEAT = "The comparison is against the OEPM inventory, not an independent count of the publications."


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _count(cell: Mapping[str, Any], name: str) -> int | None:
    value = cell.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _group(group: str, cell: Any, threshold_percent: int) -> tuple[dict[str, Any] | None, str | None]:
    """The figures of one kind group and, if it cannot be shown to meet the criterion, the reason."""
    inventory, absent, present = (
        _count(cell, k) if isinstance(cell, Mapping) else None for k in ("inventory", "absent", "present")
    )
    if inventory is None or absent is None or present is None:
        return None, f"not measurable: {group} has no valid counts"
    if inventory == 0:
        return None, f"not measurable: {group} has no publications in the inventory"
    if present + absent != inventory:
        return None, f"not measurable: {group} present + absent differ from the inventory"
    ok = absent * 100 <= threshold_percent * inventory  # at most the threshold, exact at the limit
    figures = {
        "inventory": inventory,
        "absent": absent,
        "absent_percent": round(100 * absent / inventory, 4),
        "within_threshold": ok,
    }
    reason = (
        None if ok else f"threshold exceeded: {group} lacks {absent} of {inventory} (more than {threshold_percent} %)"
    )
    return figures, reason


def _cells(exposure: Mapping[str, Any], year: int) -> Mapping[str, Any] | None:
    section = exposure.get("exposure")
    by_year = section.get("by_year") if isinstance(section, Mapping) else None
    cells = by_year.get(str(year)) if isinstance(by_year, Mapping) else None
    return cells if isinstance(cells, Mapping) else None


def completeness_gate(
    exposure: Mapping[str, Any], year: int = REFERENCE_YEAR, threshold_percent: int = THRESHOLD_PERCENT
) -> dict[str, Any]:
    """``allowed`` is True only if every kind group of ``year`` is measured and within the threshold; otherwise the reasons say why."""
    reasons: list[str] = []
    groups: dict[str, dict[str, Any]] = {}
    authority = exposure.get("authority_file")
    if not (isinstance(authority, Mapping) and _text(authority.get("name")) and _text(authority.get("sha256"))):
        reasons.append("not measurable: the result does not identify the inventory it was computed from")
    cells = _cells(exposure, year)
    if cells is None:
        reasons.append(f"not measurable: no figures for {year}")
    for group in GROUPS:
        figures, reason = _group(group, (cells or {}).get(group), threshold_percent)
        if figures is not None:
            groups[group] = figures
        if reason:
            reasons.append(reason)
    return {
        "year": year,
        "threshold_percent": threshold_percent,
        "allowed": not reasons,
        "reasons": reasons,
        "groups": groups,
        "inventory": dict(authority) if isinstance(authority, Mapping) else None,
        "caveat": CAVEAT,
    }
