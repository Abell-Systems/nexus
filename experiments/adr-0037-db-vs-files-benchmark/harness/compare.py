"""Output comparisons (pre-registration §4). They refuse incomplete inputs instead of calling them equal."""
import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from application.whitespace.analysis_records import AnalysisRecord


class IncompleteComparison(Exception):
    """One side is missing, empty where it must not be, or of a different length: nothing can be said about equality."""


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


@dataclass
class Diff:
    equal: bool
    differing_fields: dict[str, int] = field(default_factory=dict)
    examples: list[dict] = field(default_factory=list)


def compare_json(expected, actual, what: str) -> bool:
    if expected is None or actual is None:
        raise IncompleteComparison(f"{what}: a side is missing")
    return canonical_json(expected) == canonical_json(actual)


def compare_pairs(versioned: dict, results: dict[str, dict]) -> dict[str, bool]:
    """Complete pairs result per origin against the versioned file: every origin of the file must be present in the result."""
    missing = set(versioned) ^ set(results)
    if missing:
        raise IncompleteComparison(f"origins differ between versioned file and result: {sorted(missing)}")
    return {origin: compare_json(versioned[origin], results[origin], f"pairs {origin}") for origin in versioned}


def compare_records(expected: Sequence[AnalysisRecord] | None, actual: Sequence[AnalysisRecord] | None, max_examples: int = 5) -> Diff:
    """Field by field and in order; a length mismatch is incomplete, not 'different'."""
    if expected is None or actual is None:
        raise IncompleteComparison("records: a side is missing")
    if len(expected) == 0 or len(actual) == 0:
        raise IncompleteComparison("records: a side is empty")
    if len(expected) != len(actual):
        raise IncompleteComparison(f"records: lengths differ ({len(expected)} vs {len(actual)})")
    diff = Diff(True)
    for i, (a, b) in enumerate(zip(expected, actual, strict=True)):
        for name, x, y in zip(AnalysisRecord._fields, a, b, strict=True):
            if x != y:
                diff.equal = False
                diff.differing_fields[name] = diff.differing_fields.get(name, 0) + 1
                if len(diff.examples) < max_examples:
                    diff.examples.append({"index": i, "field": name, "expected": repr(x), "actual": repr(y)})
    return diff


LOAD_CHECKS = {"publications": 711547, "rejected": 341, "subclasses": 660, "without_ipc": 2749, "distinct_doc_id": 707985}


def compare_load_checks(observed: dict[str, int], expected: dict[str, int] = LOAD_CHECKS) -> dict[str, bool]:
    if set(observed) != set(expected):
        raise IncompleteComparison(f"load checks incomplete: {sorted(set(observed) ^ set(expected))}")
    return {k: observed[k] == expected[k] for k in expected}
