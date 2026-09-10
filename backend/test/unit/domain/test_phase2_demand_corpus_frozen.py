"""Generic domain invariant tests for DemandCorpus/DemandCorpusItem.

Artifact-specific tests (loading the real frozen Phase 2 N=39 corpus, checking
its manifest/sha256 sidecar, and asserting observed counts) live in
experiments/wpi-demand-patent-matching/checks/check_demand_corpus.py per
ADR 0026 -- backend/test proves generic invariants against synthetic
fixtures, not paper-specific scientific evidence.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.models.demand import SpanishOriginLevel
from domain.models.evaluation import DataModality, DemandCorpus, DemandCorpusItem, EvaluationProvenance


def _provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="innoget",
        source_uri="https://example.test/1",
        extraction_timestamp=datetime.now(UTC),
        raw_payload_sha256="0" * 64,
        modality=DataModality.OBSERVED,
    )


def test_demand_corpus_rejects_duplicate_demand_ids() -> None:
    demand = DemandCorpusItem(
        demand_id="DUP-1",
        title="t",
        description="d " * 30,
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        provenance=_provenance(),
    )

    with pytest.raises(ValidationError, match="Duplicate demand_id"):
        DemandCorpus(
            dataset_id="x",
            schema_version="1.0.0",
            dataset_version="1.0.0",
            description="test",
            demands=[demand, demand],
        )


def test_demand_corpus_item_rejects_non_target_origin_level() -> None:
    with pytest.raises(ValidationError, match="Spanish target-origin"):
        DemandCorpusItem(
            demand_id="NON-ES-1",
            title="t",
            description="d " * 30,
            spanish_origin_level=SpanishOriginLevel.NON_SPANISH,
            provenance=_provenance(),
        )
