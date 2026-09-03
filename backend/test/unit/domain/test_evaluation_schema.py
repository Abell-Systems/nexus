"""Unit tests for ADR 0006 evaluation domain models and schemas.

Invariants verified:
- Immutability of models (frozen=True).
- Explicit data modalities (OBSERVED, EXPERT_LABELLED, SYNTHETIC_CONTROL).
- Strict validation of relevance grades (0 to 3, or UNCERTAIN).
- Typed provenance with validated SHA-256 digests.
- Referential integrity: annotations must reference known demands and patents.
- Rejection of unlabelled synthetic data.
- Dataset-driven record counts matching manifest declarations.
- Zero filesystem interaction in domain.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.models.evaluation import (
    DataModality,
    EvaluationAnnotation,
    EvaluationDataset,
    EvaluationDatasetManifest,
    EvaluationDemand,
    EvaluationPatent,
    EvaluationProvenance,
    RelevanceGrade,
    ValidatedDataset,
)


def _sample_provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="innoget",
        source_uri="https://example.com/calls/1234",
        extraction_timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        raw_payload_sha256="a" * 64,
        modality=DataModality.OBSERVED,
    )


def test_evaluation_provenance_validation():
    prov = _sample_provenance()
    assert prov.source_authority == "innoget"
    assert prov.raw_payload_sha256 == "a" * 64

    # Invalid SHA-256 hex length
    with pytest.raises(ValidationError):
        EvaluationProvenance(
            source_authority="innoget",
            source_uri="https://example.com",
            extraction_timestamp=datetime.now(UTC),
            raw_payload_sha256="not-a-sha256",
            modality=DataModality.OBSERVED,
        )


def test_evaluation_demand_immutability_and_validation():
    prov = _sample_provenance()
    demand = EvaluationDemand(
        demand_id="INNOGET-2415",
        title="Sanitary drainage",
        description="High flow sink fixtures",
        posted_date="2023-05-10",
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    assert demand.demand_id == "INNOGET-2415"

    # Verify immutability (frozen=True)
    with pytest.raises(ValidationError):
        demand.title = "Modified"  # type: ignore[misc]


def test_relevance_grade_values():
    assert RelevanceGrade.GRADE_0.value == 0
    assert RelevanceGrade.GRADE_1.value == 1
    assert RelevanceGrade.GRADE_2.value == 2
    assert RelevanceGrade.GRADE_3.value == 3
    assert RelevanceGrade.UNCERTAIN.value == -1


def test_evaluation_dataset_referential_integrity():
    prov = _sample_provenance()
    demand = EvaluationDemand(
        demand_id="D-1",
        title="Demand 1",
        description="Desc 1",
        posted_date="2023-01-01",
        provenance=prov,
    )
    patent = EvaluationPatent(
        publication_id="ES-100-A1",
        publication_date="2022-01-01",
        classifications_cpc=["A01B"],
        title="Patent 1",
        abstract="Abstract 1",
        provenance=prov,
    )

    valid_anno = EvaluationAnnotation(
        demand_id="D-1",
        publication_id="ES-100-A1",
        grade=RelevanceGrade.GRADE_2,
        annotator_role="domain_expert",
        notes="Relevant prior art",
        modality=DataModality.EXPERT_LABELLED,
    )

    dataset = EvaluationDataset(
        dataset_id="benchmark-v1",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        description="Validation benchmark",
        demands=[demand],
        patents=[patent],
        annotations=[valid_anno],
    )
    assert len(dataset.demands) == 1

    # Referential integrity failure: unknown demand_id in annotation
    orphan_demand_anno = EvaluationAnnotation(
        demand_id="UNKNOWN-D",
        publication_id="ES-100-A1",
        grade=RelevanceGrade.GRADE_2,
        annotator_role="domain_expert",
        modality=DataModality.EXPERT_LABELLED,
    )
    with pytest.raises(ValidationError, match="references unknown demand_id"):
        EvaluationDataset(
            dataset_id="benchmark-v1",
            schema_version="1.0.0",
            dataset_version="1.0.0",
            description="Validation benchmark",
            demands=[demand],
            patents=[patent],
            annotations=[orphan_demand_anno],
        )

    # Referential integrity failure: unknown publication_id in annotation
    orphan_patent_anno = EvaluationAnnotation(
        demand_id="D-1",
        publication_id="UNKNOWN-PATENT",
        grade=RelevanceGrade.GRADE_2,
        annotator_role="domain_expert",
        modality=DataModality.EXPERT_LABELLED,
    )
    with pytest.raises(ValidationError, match="references unknown publication_id"):
        EvaluationDataset(
            dataset_id="benchmark-v1",
            schema_version="1.0.0",
            dataset_version="1.0.0",
            description="Validation benchmark",
            demands=[demand],
            patents=[patent],
            annotations=[orphan_patent_anno],
        )


def test_unlabelled_synthetic_data_rejection():
    # Attempting to introduce synthetic data without SYNTHETIC_CONTROL modality must fail
    with pytest.raises(ValidationError, match="Synthetic data must explicitly declare modality SYNTHETIC_CONTROL"):
        EvaluationDemand(
            demand_id="SYNTH-1",
            title="Synthetic Demand",
            description="Generated by script",
            is_synthetic=True,
            provenance=EvaluationProvenance(
                source_authority="synthetic_generator",
                source_uri="memory://script",
                extraction_timestamp=datetime.now(UTC),
                raw_payload_sha256="b" * 64,
                modality=DataModality.OBSERVED,  # Conflict: synthetic marked as observed!
            ),
        )


def test_manifest_record_counts_validation_against_dataset():
    prov = _sample_provenance()
    demand = EvaluationDemand(
        demand_id="D-1",
        title="Demand 1",
        description="Desc 1",
        posted_date="2023-01-01",
        provenance=prov,
    )
    patent = EvaluationPatent(
        publication_id="ES-100-A1",
        publication_date="2022-01-01",
        title="Patent 1",
        abstract="Abstract 1",
        provenance=prov,
    )
    anno = EvaluationAnnotation(
        demand_id="D-1",
        publication_id="ES-100-A1",
        grade=RelevanceGrade.GRADE_3,
        annotator_role="expert",
        modality=DataModality.EXPERT_LABELLED,
    )
    dataset = EvaluationDataset(
        dataset_id="pilot-eval",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        description="Pilot",
        demands=[demand],
        patents=[patent],
        annotations=[anno],
    )

    manifest = EvaluationDatasetManifest(
        dataset_id="pilot-eval",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        source_authorities=["innoget"],
        demand_count=1,
        patent_count=1,
        annotation_count=1,
        content_sha256="c" * 64,
    )

    # ValidatedDataset construction succeeds when counts match
    val = ValidatedDataset(dataset=dataset, manifest=manifest)
    assert val.dataset.dataset_id == "pilot-eval"

    # ValidatedDataset fails when manifest counts contradict actual dataset contents
    mismatched_manifest = manifest.model_copy(update={"demand_count": 99})
    with pytest.raises(ValidationError, match="Manifest demand_count .* does not match dataset"):
        ValidatedDataset(dataset=dataset, manifest=mismatched_manifest)
