"""Deterministic, atomic publisher for the scientific_results.json contract (ADR 0025).

This module is a publication/serialization boundary only — it accepts a payload that
already satisfies `ScientificResultsDocument` (domain.models.scientific_results) and
writes it to disk. It performs no scientific computation, no metric recalculation, and
no execution aggregation (`executions_are_aggregable` is a concern for a future
consumer, not for this writer). It never fabricates a missing `dataset_id`/`policy_id`/
etc. — whatever the validated document declares, including absence, is exactly what
gets published.

`scientific_results.json` is a sibling of `project_status.json` (ADR 0022/0023/0025),
never the same file; this module has no knowledge of `project_status.json`'s path or
schema and never touches it.

Serialization is deterministic and canonical: `sort_keys=True` guarantees a validated
document always serializes to byte-identical output regardless of how its fields were
constructed or ordered along the way. This is a deliberate departure from
`scripts/audit_project_status.py`'s own writer (which relies on `build_project_status`'s
natural field order and does not sort keys) — ADR 0025 requires this specific artifact
to be reproducibly comparable byte-for-byte (e.g. in CI diffing of published snapshots),
a requirement `project_status.json` was never given.

Writes are atomic: content is written to a temporary file in the same directory as the
target (so the final `os.replace` is a same-filesystem rename, not a cross-filesystem
copy), flushed and fsynced, then atomically renamed over the target. A failure at any
point before that final rename leaves an existing target file completely untouched and
deletes its own temporary file — no partial artifact is ever left at `target_path`.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from domain.models.scientific_results import ScientificResultsDocument


class ScientificResultsPublicationError(Exception):
    """Raised when a payload does not satisfy the ScientificResultsDocument contract."""


def canonical_scientific_results_json(document: ScientificResultsDocument) -> bytes:
    """Deterministic, canonical UTF-8 JSON encoding of an already-validated document.

    `sort_keys=True` makes the output depend only on the document's content, never on
    incidental field-construction order: two `ScientificResultsDocument` instances built
    differently but carrying equal data serialize to byte-identical output.
    """
    payload = document.model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _validate(document: ScientificResultsDocument | Mapping[str, Any]) -> ScientificResultsDocument:
    if isinstance(document, ScientificResultsDocument):
        return document
    try:
        return ScientificResultsDocument.model_validate(document)
    except ValidationError as exc:
        raise ScientificResultsPublicationError(
            f"payload does not satisfy the ScientificResultsDocument contract: {exc}"
        ) from exc


def publish_scientific_results(
    document: ScientificResultsDocument | Mapping[str, Any],
    target_path: Path,
) -> Path:
    """Validates `document` and atomically publishes it to `target_path`.

    Raises `ScientificResultsPublicationError` if `document` (or the raw mapping passed
    in its place) does not satisfy the `ScientificResultsDocument` contract — nothing is
    written to disk in that case. On any failure during serialization or the write
    itself, an existing file at `target_path` is left completely unchanged.

    `document` is never mutated: `ScientificResultsDocument` is a frozen model, and this
    function only reads from it (`model_dump`) — it never calls a setter or otherwise
    modifies caller-owned state.
    """
    validated = _validate(document)
    payload_bytes = canonical_scientific_results_json(validated)

    target_path = Path(target_path)
    target_dir = target_path.parent

    fd, tmp_name = tempfile.mkstemp(prefix=".scientific_results.", suffix=".json.tmp", dir=str(target_dir))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(payload_bytes)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, target_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    return target_path
