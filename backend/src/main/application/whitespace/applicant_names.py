"""Applicant names merged by versioned, explicit rules (spec section 6): never by substring."""

import json
import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple


class Rule(NamedTuple):
    pattern: str
    canonical: str
    reason: str
    date: str


def load_rules(path: Path) -> tuple[Rule, ...]:
    return tuple(Rule(**r) for r in json.loads(path.read_text(encoding="utf-8")))


def normalise(raw: str) -> str:
    folded = "".join(c for c in unicodedata.normalize("NFKD", raw.upper()) if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", folded).strip()


def canonical_name(raw: str, rules: Sequence[Rule]) -> tuple[str, str]:
    """(canonical, original). A rule matches the whole name or a whole-word prefix of it."""
    name = normalise(raw)
    matched = {r.canonical for r in rules if name == normalise(r.pattern) or name.startswith(normalise(r.pattern) + " ")}
    if len(matched) > 1:
        raise ValueError(f"{raw!r} matches rules with different canonicals: {sorted(matched)}")
    return (matched.pop() if matched else name.title()), raw
