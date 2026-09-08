"""Deterministic, demand-blind selection for PatentCorpus (ADR 0020 §3, §4).

sha256(publication_id)-order selection is deterministic (same universe -> same N
records, byte-identical), auditable (recomputable by anyone from the raw fetched
set), and independent of API delivery order or any demand-side property.
"""

import hashlib

from domain.models.patent import PatentDocument


class PatentCorpusConstructionError(Exception):
    """Raised when the eligible universe is below ADR 0020 §4's minimum_acceptable_N
    floor -- corpus construction is treated as failed, never silently accepted shrunken."""


def select_frozen_patents(
    documents: list[PatentDocument],
    target_n: int,
    minimum_acceptable_n: int,
) -> list[PatentDocument]:
    """Deduplicate by publication_id, sort by sha256(publication_id), and take the
    first min(target_n, eligible_available_records). Raises PatentCorpusConstructionError
    if eligible_available_records < minimum_acceptable_n (ADR 0020 §4).

    Dedup is keyed on publication_id via an explicit loop (defense in depth --
    PatentValidator already excludes duplicates from its INCLUDED stream within a
    single run, but this function is general purpose and makes no assumption about
    its caller). Two documents sharing a publication_id with IDENTICAL content
    (equal as Pydantic models) are safely deduplicated -- e.g. the same record
    fetched twice via overlapping pagination windows. Two documents sharing a
    publication_id with DIFFERENT content raise PatentCorpusConstructionError: for
    a frozen, reproducible artifact, silently picking one based on input order
    would make the result depend on OPS's delivery order, and would hide a genuine
    upstream data-quality problem instead of surfacing it.
    """
    unique_by_id: dict[str, PatentDocument] = {}
    for doc in documents:
        existing = unique_by_id.get(doc.publication_id)
        if existing is None:
            unique_by_id[doc.publication_id] = doc
        elif existing != doc:
            raise PatentCorpusConstructionError(
                f"PatentCorpus construction failed: publication_id={doc.publication_id!r} "
                "appears twice with divergent content. Same-identity records must be "
                "identical or construction cannot proceed -- this indicates an upstream "
                "data-quality problem requiring investigation, not something to silently "
                "resolve by picking one."
            )
    eligible_available_records = len(unique_by_id)

    if eligible_available_records < minimum_acceptable_n:
        raise PatentCorpusConstructionError(
            f"PatentCorpus construction failed: eligible_available_records="
            f"{eligible_available_records} < minimum_acceptable_N={minimum_acceptable_n} "
            "(ADR 0020 §4). Resolving this means revisiting the inclusion contract "
            "(§2) explicitly -- not silently accepting a shrunken corpus."
        )

    ordered = sorted(
        unique_by_id.values(),
        key=lambda doc: hashlib.sha256(doc.publication_id.encode("utf-8")).hexdigest(),
    )
    n_final = min(target_n, eligible_available_records)
    return ordered[:n_final]
