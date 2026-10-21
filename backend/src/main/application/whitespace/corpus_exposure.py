"""Exposure of the corpus to omissions (ADR 0036, O5.1): what the OEPM's inventory lists and the corpus lacks.

Counts publication keys (number, kind code, publication date) of the inventory, of the corpus, and the inventory keys the
corpus does not have, by publication year and kind group, and accumulated up to each origin. An absence is a count; it
is not read as evidence of a classification bias. The kind groups are the code families of the inventory (``T*``, ``Y``,
everything else); what ``Y`` denotes has not been read.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

from domain.models.whitespace import AuthorityEntry, PatentPublication

GROUPS = ("ep_translation", "kind_y", "other")


def exposure_group(kind: str) -> str:
    if kind.startswith("T"):
        return "ep_translation"
    return "kind_y" if kind.startswith("Y") else "other"


def _share(part: int, whole: int) -> float:
    return round(100 * part / whole, 2) if whole else 0.0


def exposure_table(
    publications: Iterable[PatentPublication],
    authority: Iterable[AuthorityEntry],
    origins: Sequence[int],
    first_year: int = 2000,
    last_year: int = 2025,
) -> dict[str, Any]:
    """Per year and group: inventory, corpus, absent and their share; accumulated absences up to each origin."""
    corpus = {(p.doc_number, p.kind, p.publication_date.strftime("%Y%m%d")) for p in publications}
    inventory: set[tuple[str, str, str]] = {
        (e.publication_number, e.kind, e.publication_date)
        for e in authority
        if first_year <= int(e.publication_date[:4]) <= last_year
    }
    counts: dict[tuple[int, str], Counter[str]] = {}
    for key in inventory:
        cell = counts.setdefault((int(key[2][:4]), exposure_group(key[1])), Counter())
        cell["inventory"] += 1
        cell["absent" if key not in corpus else "present"] += 1
    corpus_years = {int(key[2][:4]) for key in corpus}
    only_corpus = Counter(int(key[2][:4]) for key in corpus - inventory)

    by_year = {
        str(year): {
            group: {
                "inventory": (c := counts.get((year, group), Counter()))["inventory"],
                "present": c["present"],
                "absent": c["absent"],
                "absent_share_percent": _share(c["absent"], c["inventory"]),
            }
            for group in GROUPS
        }
        | {"corpus_keys_not_in_inventory": only_corpus[year]}
        for year in range(first_year, last_year + 1)
    }
    cumulative = {}
    for origin in origins:
        years = range(first_year, origin + 1)
        cumulative[str(origin)] = {
            "calendar_years_in_window": len(years),
            "years_with_corpus_publications": len({y for y in corpus_years if first_year <= y <= origin}),
            **{
                group: {
                    "inventory": (i := sum(counts.get((y, group), Counter())["inventory"] for y in years)),
                    "absent": (a := sum(counts.get((y, group), Counter())["absent"] for y in years)),
                    "absent_share_percent": _share(a, i),
                }
                for group in GROUPS
            },
            "all_groups": {
                "inventory": (i := sum(counts.get((y, g), Counter())["inventory"] for y in years for g in GROUPS)),
                "absent": (a := sum(counts.get((y, g), Counter())["absent"] for y in years for g in GROUPS)),
                "absent_share_percent": _share(a, i),
            },
        }
    return {
        "first_year": first_year,
        "inventory_publications": len(inventory),
        "corpus_publications": len(corpus),
        "by_year": by_year,
        "accumulated_up_to_origin": cumulative,
    }
