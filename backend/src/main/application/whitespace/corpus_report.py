"""Descriptive figures of a patent-publication source, comparable with the figures published for it.

ADR 0036 §11.1: the adapter must reproduce the published tables and show every discrepancy instead of
adjusting it. Nothing here deduplicates, thresholds or interprets: it counts what the source holds.
"""

from collections import Counter
from collections.abc import Iterable
from datetime import date
from typing import Any

from domain.models.whitespace import PatentPublication, RejectedRecord


def kind_group(kind: str) -> str:
    """Document group of the published characterization: EP translations (T*), utility models (U*, Y*), patents."""
    if kind.startswith("T"):
        return "ep_translation"
    return "utility_model" if kind.startswith(("U", "Y")) else "patent"


def _percent(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def build_figures(outcomes: Iterable[PatentPublication | RejectedRecord]) -> dict[str, Any]:
    """One pass over a source; the result has the shape of the ``figures`` object of the published contract."""
    rejected_by_file = Counter[str]()
    by_file: dict[str, dict[str, Any]] = {}
    by_year: dict[int, dict[str, Any]] = {}
    id_dates: set[tuple[str, date]] = set()
    subclasses: set[str] = set()
    groups, no_priority = Counter[str](), Counter[str]()
    versions = Counter[str]()
    total = no_ipc = two_or_more = distinct_subclass_total = no_application = application_after_publication = 0

    for item in outcomes:
        if isinstance(item, RejectedRecord):
            rejected_by_file[item.provenance.source_file] += 1
            continue
        group = kind_group(item.kind)
        total += 1
        groups[group] += 1
        no_priority[group] += not item.priority_dates
        id_dates.add((item.doc_id, item.publication_date))

        file_figures = by_file.setdefault(item.provenance.source_file, {"records": 0, "dates": []})
        file_figures["records"] += 1
        file_figures["dates"].append(item.publication_date)

        year = by_year.setdefault(item.publication_date.year, {"records": 0, "ep": 0, "national": 0, "dates": set()})
        year["records"] += 1
        year["ep" if group == "ep_translation" else "national"] += 1
        year["dates"].add(item.publication_date)

        symbols = {entry.subclass_symbol for entry in item.ipc_entries}
        subclasses |= symbols
        distinct_subclass_total += len(symbols)
        no_ipc += not symbols
        two_or_more += len(symbols) >= 2
        if item.ipc_entries:
            versions[item.ipc_entries[0].version or ""] += 1
        no_application += item.application_date is None
        application_after_publication += (
            item.application_date is not None and item.application_date > item.publication_date
        )

    ids_per_date_count = Counter(doc_id for doc_id, _ in id_dates)
    top_version, top_version_count = versions.most_common(1)[0] if versions else ("", 0)
    first_year, last_year = (min(by_year), max(by_year)) if by_year else (0, -1)
    return {
        "records": total,
        "rejected": sum(rejected_by_file.values()),
        "distinct_doc_ids": len(ids_per_date_count),
        "distinct_doc_id_publication_dates": len(id_dates),
        "exact_repeat_records": total - len(id_dates),
        "doc_ids_with_several_publication_dates": sum(1 for n in ids_per_date_count.values() if n > 1),
        "records_without_ipc": no_ipc,
        "distinct_ipc_subclasses": len(subclasses),
        "records_without_application_date": no_application,
        "records_with_application_after_publication": application_after_publication,
        "kind_groups": dict(sorted(groups.items())),
        "without_priority_claim": {
            "total": sum(no_priority.values()),
            "share_percent": _percent(sum(no_priority.values()), total),
            "by_group_percent": {g: _percent(no_priority[g], groups[g]) for g in sorted(groups)},
        },
        "ipc": {
            "mean_distinct_subclasses": round(distinct_subclass_total / total, 2) if total else 0.0,
            "two_or_more_subclasses_percent": _percent(two_or_more, total),
            "first_entry_versions": len(versions),
            "most_common_version": top_version,
            "most_common_version_percent": _percent(top_version_count, total - no_ipc),
        },
        "years_without_records": [y for y in range(first_year, last_year + 1) if y not in by_year],
        "by_publication_year": {
            str(y): {
                "records": f["records"],
                "ep_translations": f["ep"],
                "national": f["national"],
                "distinct_dates": len(f["dates"]),
            }
            for y, f in sorted(by_year.items())
        },
        "by_file": {
            name: {
                "records": f["records"],
                "first_publication_date": min(f["dates"]).isoformat(),
                "last_publication_date": max(f["dates"]).isoformat(),
                "rejected": rejected_by_file[name],
            }
            for name, f in sorted(by_file.items())
        },
    }


def compare_figures(published: Any, reproduced: Any, path: str = "") -> list[str]:
    """Every difference between the published and the reproduced figures, one line each; empty if identical."""
    if isinstance(published, dict) and isinstance(reproduced, dict):
        found: list[str] = []
        for key in sorted(published.keys() | reproduced.keys(), key=str):
            where = f"{path}/{key}"
            if key not in reproduced:
                found.append(f"{where}: published {published[key]!r}, not reproduced")
            elif key not in published:
                found.append(f"{where}: reproduced {reproduced[key]!r}, not published")
            else:
                found += compare_figures(published[key], reproduced[key], where)
        return found
    return [] if published == reproduced else [f"{path}: published {published!r}, reproduced {reproduced!r}"]
