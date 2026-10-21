"""Comparison of reproduced figures with figures as they were printed in a document."""

from typing import Any


def _decimals(value: float) -> int:
    text = repr(value)
    return len(text.split(".")[1]) if "." in text else 0


def compare_published(published: Any, reproduced: Any, path: str = "") -> list[str]:
    """Every published figure that is missing from, or differs from, the reproduced ones; one line each.

    A reproduced number is rounded to the decimals the published one was printed with. Reproduced figures
    that were never published are not differences.
    """
    if isinstance(published, dict):
        found: list[str] = []
        for key in published:
            where = f"{path}/{key}"
            if not isinstance(reproduced, dict) or key not in reproduced:
                found.append(f"{where}: published {published[key]!r}, not reproduced")
            else:
                found += compare_published(published[key], reproduced[key], where)
        return found
    if isinstance(published, (int, float)) and isinstance(reproduced, (int, float)):
        same = round(reproduced, _decimals(published) if isinstance(published, float) else 0) == published
    else:
        same = published == reproduced
    return [] if same else [f"{path}: published {published!r}, reproduced {reproduced!r}"]
