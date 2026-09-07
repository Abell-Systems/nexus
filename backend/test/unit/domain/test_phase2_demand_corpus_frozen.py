"""Frozen invariant tests for the Phase 2 demand corpus (N=39).

Mirrors the spirit of test_frozen_benchmark_invariants.py, adapted for DemandCorpus
(demand-only, pre-patent-pairing stage) rather than the full EvaluationDataset loader,
which requires a non-empty patent corpus this stage does not yet have.
"""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.evaluation import DemandCorpus


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@pytest.fixture
def corpus_paths() -> tuple[Path, Path, Path]:
    repo_root = get_repo_root()
    base = repo_root / "data" / "evaluation" / "dataset_phase2_demand_corpus_n39"
    return (
        base.with_suffix(".json"),
        Path(str(base) + ".sha256"),
        Path(str(base) + ".manifest.json"),
    )


def test_frozen_corpus_loads_and_validates(corpus_paths: tuple[Path, Path, Path]) -> None:
    dataset_path, _checksum_path, _manifest_path = corpus_paths
    corpus = DemandCorpus.model_validate_json(dataset_path.read_text(encoding="utf-8"))

    assert corpus.dataset_id == "nexus-phase2-demand-corpus-n39-v1"
    assert len(corpus.demands) == 39
    innoget = [d for d in corpus.demands if d.demand_id.startswith("INNOGET-")]
    lombardia = [d for d in corpus.demands if d.demand_id.startswith("LOMBARDIA-")]
    assert len(innoget) == 37
    assert len(lombardia) == 2


def test_frozen_corpus_sha256_matches_sidecar(corpus_paths: tuple[Path, Path, Path]) -> None:
    dataset_path, checksum_path, _manifest_path = corpus_paths
    file_bytes = dataset_path.read_bytes()
    computed = hashlib.sha256(file_bytes).hexdigest()

    sidecar_line = checksum_path.read_text(encoding="utf-8").strip()
    declared_sha, declared_name = sidecar_line.split(maxsplit=1)

    assert declared_sha == computed, "Frozen dataset bytes do not match the committed .sha256 sidecar"
    assert declared_name == dataset_path.name


def test_frozen_corpus_carries_origin_evidence_inline(corpus_paths: tuple[Path, Path, Path]) -> None:
    """The frozen artifact itself, not only the origin_audit sidecar, must be
    self-sufficient to verify the Spanish-origin eligibility criterion (PR #55 review)."""
    from domain.models.demand import SpanishOriginLevel

    dataset_path, _checksum_path, _manifest_path = corpus_paths
    corpus = DemandCorpus.model_validate_json(dataset_path.read_text(encoding="utf-8"))

    for demand in corpus.demands:
        assert demand.spanish_origin_level in (
            SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
            SpanishOriginLevel.LEVEL_2_ORGANIZATION_METADATA,
            SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK,
        )

    lombardia = [d for d in corpus.demands if d.demand_id.startswith("LOMBARDIA-")]
    assert len(lombardia) == 2
    for demand in lombardia:
        assert demand.external_reference is not None
        assert demand.external_reference.startswith("TRES")
        assert demand.origin_country == "ES"


def test_frozen_corpus_manifest_matches_dataset(corpus_paths: tuple[Path, Path, Path]) -> None:
    dataset_path, _checksum_path, manifest_path = corpus_paths
    file_bytes = dataset_path.read_bytes()
    computed = hashlib.sha256(file_bytes).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    corpus = DemandCorpus.model_validate_json(file_bytes)

    assert manifest["dataset_id"] == corpus.dataset_id
    assert manifest["demand_count"] == len(corpus.demands)
    assert manifest["patent_count"] == 0
    assert manifest["content_sha256"] == computed


def test_frozen_corpus_all_demands_meet_content_completeness(corpus_paths: tuple[Path, Path, Path]) -> None:
    """Regression guard for docs/empirical-study-protocol.md §4.1's 25-word minimum --
    the exact gap that caused the N=48 -> N=43 -> N=39 corrections (PR #53/#54)."""
    dataset_path, _checksum_path, _manifest_path = corpus_paths
    corpus = DemandCorpus.model_validate_json(dataset_path.read_text(encoding="utf-8"))

    for demand in corpus.demands:
        word_count = len(demand.description.split())
        assert word_count >= 25, (
            f"{demand.demand_id} has {word_count} words, below the protocol's 25-word "
            "minimum -- this demand should not be in the frozen corpus"
        )


def test_demand_corpus_rejects_duplicate_demand_ids() -> None:
    from datetime import UTC, datetime

    from domain.models.demand import SpanishOriginLevel
    from domain.models.evaluation import DataModality, DemandCorpusItem, EvaluationProvenance

    provenance = EvaluationProvenance(
        source_authority="innoget",
        source_uri="https://example.test/1",
        extraction_timestamp=datetime.now(UTC),
        raw_payload_sha256="0" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = DemandCorpusItem(
        demand_id="DUP-1",
        title="t",
        description="d " * 30,
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        provenance=provenance,
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
    from datetime import UTC, datetime

    from domain.models.demand import SpanishOriginLevel
    from domain.models.evaluation import DataModality, DemandCorpusItem, EvaluationProvenance

    provenance = EvaluationProvenance(
        source_authority="innoget",
        source_uri="https://example.test/1",
        extraction_timestamp=datetime.now(UTC),
        raw_payload_sha256="0" * 64,
        modality=DataModality.OBSERVED,
    )

    with pytest.raises(ValidationError, match="Spanish target-origin"):
        DemandCorpusItem(
            demand_id="NON-ES-1",
            title="t",
            description="d " * 30,
            spanish_origin_level=SpanishOriginLevel.NON_SPANISH,
            provenance=provenance,
        )
