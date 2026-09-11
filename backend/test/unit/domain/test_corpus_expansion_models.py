"""Unit tests for corpus expansion domain models and candidate contracts."""

from datetime import date

import pytest
from pydantic import ValidationError

from domain.models.corpus_expansion import (
    FROZEN_CORPUS_EXPANSION_POLICY_VERSION,
    CandidateRejectionReason,
    CandidateValidationResult,
    ConcentrationMonitoringConfig,
    ContentRequirementsConfig,
    CorpusExpansionPolicy,
    DemandCandidateContractRecord,
    GeographicStratumConfig,
    PermittedSourceConfig,
    TargetSampleSizeConfig,
    TemporalWindowConfig,
    UnknownHandlingConfig,
    calculate_canonical_word_count,
)


def test_permitted_source_config_valid() -> None:
    src = PermittedSourceConfig(
        source_id="innoget",
        display_name="InnoGet",
        permitted_constructs=("Technology call",),
        public_access_mode="unauthenticated_public_http",
    )
    assert src.source_id == "innoget"
    assert "Technology call" in src.permitted_constructs


def test_temporal_window_invalid_order_raises() -> None:
    with pytest.raises(ValidationError, match="min_publication_date must be <= max_publication_date"):
        TemporalWindowConfig(
            min_publication_date=date(2026, 1, 1),
            max_publication_date=date(2020, 1, 1),
            date_interpretation="public_publication_date",
        )


def test_content_requirements_min_word_count_non_negative() -> None:
    with pytest.raises(ValidationError, match="min_word_count must be >= 0"):
        ContentRequirementsConfig(
            min_word_count=-1,
            require_technical_problem=True,
            allow_explicit_confidentiality_redaction=False,
        )


def test_concentration_monitoring_threshold_bounds() -> None:
    with pytest.raises(ValidationError, match="sector_warning_threshold must be in"):
        ConcentrationMonitoringConfig(
            sector_warning_threshold=1.5,
            max_independent_per_organization=1,
        )


def test_corpus_expansion_policy_frozen() -> None:
    policy = CorpusExpansionPolicy(
        policy_version="corpus_expansion_policy_v1",
        description="Phase 2 expansion policy",
        target_sample_size=TargetSampleSizeConfig(
            target_independent_demands=60,
            power_analysis_reference="data/experiments/power_analysis_wilcoxon.json",
        ),
        sources=(
            PermittedSourceConfig(
                source_id="innoget",
                display_name="InnoGet",
                permitted_constructs=("Technology call",),
                public_access_mode="unauthenticated_public_http",
            ),
        ),
        temporal_window=TemporalWindowConfig(
            min_publication_date=date(2020, 1, 1),
            max_publication_date=date(2025, 12, 31),
            date_interpretation="public_publication_date",
        ),
        geographic_strata=(
            GeographicStratumConfig(stratum_id="spain", description="Spain"),
            GeographicStratumConfig(stratum_id="international_european", description="Europe"),
        ),
        content_requirements=ContentRequirementsConfig(
            min_word_count=25,
            require_technical_problem=True,
            allow_explicit_confidentiality_redaction=False,
        ),
        concentration_monitoring=ConcentrationMonitoringConfig(
            sector_warning_threshold=0.35,
            max_independent_per_organization=1,
        ),
        unknown_handling=UnknownHandlingConfig(
            unknown_organization_split_policy="dev_only",
            counts_towards_independent_target=False,
        ),
    )
    with pytest.raises(ValidationError):
        policy.policy_version = "corpus_expansion_policy_v2"


def test_corpus_expansion_policy_version_strict_v1() -> None:
    base_kwargs = {
        "description": "Phase 2 expansion policy",
        "target_sample_size": TargetSampleSizeConfig(
            target_independent_demands=60,
            power_analysis_reference="data/experiments/power_analysis_wilcoxon.json",
        ),
        "sources": (
            PermittedSourceConfig(
                source_id="innoget",
                display_name="InnoGet",
                permitted_constructs=("Technology call",),
                public_access_mode="unauthenticated_public_http",
            ),
        ),
        "temporal_window": TemporalWindowConfig(
            min_publication_date=date(2020, 1, 1),
            max_publication_date=date(2025, 12, 31),
            date_interpretation="public_publication_date",
        ),
        "geographic_strata": (GeographicStratumConfig(stratum_id="spain", description="Spain"),),
        "content_requirements": ContentRequirementsConfig(
            min_word_count=25,
            require_technical_problem=True,
            allow_explicit_confidentiality_redaction=False,
        ),
        "concentration_monitoring": ConcentrationMonitoringConfig(
            sector_warning_threshold=0.35,
            max_independent_per_organization=1,
        ),
        "unknown_handling": UnknownHandlingConfig(
            unknown_organization_split_policy="dev_only",
            counts_towards_independent_target=False,
        ),
    }

    # Valid v1 succeeds
    p = CorpusExpansionPolicy(policy_version=FROZEN_CORPUS_EXPANSION_POLICY_VERSION, **base_kwargs)
    assert p.policy_version == "corpus_expansion_policy_v1"

    # Any other version string is strictly rejected
    for invalid_version in [
        "corpus_expansion_policy_v2",
        "corpus_expansion_policy_v999",
        "corpus_expansion_policy_draft",
        "random_policy",
    ]:
        with pytest.raises(ValidationError) as exc_info:
            CorpusExpansionPolicy(policy_version=invalid_version, **base_kwargs)
        assert "policy_version must be strictly 'corpus_expansion_policy_v1'" in str(exc_info.value)


def test_demand_candidate_contract_record_frozen_extra_forbid() -> None:
    candidate = DemandCandidateContractRecord(
        demand_id="INNOGET-3001",
        source_id="innoget",
        source_construct="Technology call",
        publication_date=date(2023, 5, 14),
        publication_date_evidence_field="posted_date",
        publication_date_evidence_text="14 May 2023",
        geographic_stratum="spain",
        title="Biodegradable surfactant demand",
        description_text="Seeking surfactant with high biodegradability under 20 degrees Celsius.",
        language_code="en",
        organization_raw="EcoClean S.L.",
        is_publicly_accessible=True,
        has_confidentiality_redaction=False,
        has_articulated_technical_problem=True,
        technical_problem_evidence_text="Seeking surfactant with high biodegradability under 20 degrees Celsius.",
    )
    assert candidate.demand_id == "INNOGET-3001"
    assert candidate.has_articulated_technical_problem is True
    with pytest.raises(ValidationError):
        candidate.title = "New title"


def test_candidate_validation_result_deterministic_sorting() -> None:
    res = CandidateValidationResult.reject(
        [
            CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW,
            CandidateRejectionReason.CONTENT_TOO_SHORT,
            CandidateRejectionReason.NO_TECHNICAL_PROBLEM,
        ]
    )
    assert res.status == "REJECT"
    assert res.rejection_reasons == (
        CandidateRejectionReason.CONTENT_TOO_SHORT,
        CandidateRejectionReason.NO_TECHNICAL_PROBLEM,
        CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW,
    )


def test_calculate_canonical_word_count() -> None:
    # Normative test cases
    assert calculate_canonical_word_count("state-of-the-art") == 1
    assert calculate_canonical_word_count("high-performance") == 1
    assert calculate_canonical_word_count("company's") == 1
    assert calculate_canonical_word_count("<p>Hello &amp; world!</p>") == 2
    assert calculate_canonical_word_count("Line 1\nLine 2\r\nLine 3") == 6
    assert calculate_canonical_word_count("") == 0
    assert calculate_canonical_word_count("   ") == 0
    assert calculate_canonical_word_count("15-25 °C temperature range") == 4
    assert calculate_canonical_word_count("Innovación y tecnología española en biomateriales.") == 6
    assert calculate_canonical_word_count("word - other") == 2
