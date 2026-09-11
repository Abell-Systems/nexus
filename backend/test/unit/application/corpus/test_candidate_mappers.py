"""Unit tests for Phase-2 candidate mappers (EEN/POD and InnoGet) (ADR 0032)."""

from datetime import date
from pathlib import Path

import pytest

from application.corpus.mappers import (
    EenPodCandidateMapper,
    InnogetCandidateMapper,
    MappingError,
)
from domain.models.corpus_expansion import (
    PublicationDateEvidenceType,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "fixtures"


# --------------------------------------------------------------------------
# Fixtures and helpers
# --------------------------------------------------------------------------

EEN_SPANISH_HTML = b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Innovative solar thermal collector system</title>
</head>
<body>
    <h1>Innovative solar thermal collector system</h1>
    <div class="reference-info">
        <span class="label">POD Reference:</span>
        <span class="value">TRES20250806011</span>
    </div>
    <div class="summary">
        <p>A Spanish research institute has developed a high-efficiency solar thermal collector
        designed for industrial heat processes operating between 100C and 250C with reduced footprint.</p>
    </div>
    <div class="technical-problem">
        <h3>Technical problem</h3>
        <p>Current industrial solar thermal collectors suffer from severe thermal dissipation
        at temperatures above 120C and require bulky vacuum tube arrangements that are vulnerable to hail damage.</p>
    </div>
    <div class="partner-sought">
        <p>Seeking industrial manufacturing partners for commercial production under license.</p>
    </div>
</body>
</html>
"""

EEN_INTERNATIONAL_HTML = b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Novel bio-based resin for composite automotive parts</title>
</head>
<body>
    <h1>Novel bio-based resin for composite automotive parts</h1>
    <div class="pod-ref">
        Reference: TRIT20240315002
    </div>
    <div class="abstract">
        <p>An Italian SME specializes in circular thermoset composites and seeks partners to test
        a new lignin-derived polymer matrix for structural automotive components.</p>
    </div>
    <div class="technical-specification">
        <h3>Technical Specification</h3>
        <p>The matrix must withstand curing temperatures under 150C while maintaining glass transition
        temperatures above 180C and Young's modulus exceeding 3.5 GPa.</p>
    </div>
</body>
</html>
"""

EEN_INVALID_REF_HTML = b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Water treatment membrane technology</title>
</head>
<body>
    <h1>Water treatment membrane technology</h1>
    <div class="pod-ref">
        Reference: TRIT-SPECIAL-REF-NO-DATE
    </div>
    <div class="summary">
        <p>An Italian enterprise offers novel ceramic membranes for industrial wastewater purification.</p>
    </div>
    <div class="technical-problem">
        <h3>Technical problem</h3>
        <p>Membrane fouling caused by heavy organic load in textile dyeing wastewater.</p>
    </div>
</body>
</html>
"""

INNOGET_WITH_META_DATE_HTML = b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Biocompatible coating for titanium implants</title>
    <meta property="og:title" content="Biocompatible coating for titanium implants" />
    <meta property="og:url" content="https://www.innoget.com/technology-calls/3001/biocompatible-coating" />
    <meta property="article:published_time" content="2024-05-10T08:00:00Z" />
</head>
<body>
    <div class="user-meta">
        <h3 class="name light">Posted by <a href="#" class="bold dark">BioMed Innovations SL</a></h3>
    </div>
    <ul class="details">
        <li>BioMed Innovations SL</li>
        <li>from Spain</li>
        <li>Deadline at 31/10/2025</li>
    </ul>
    <h2>Desired outcome</h2>
    <p>Enhanced osseointegration within 14 days without increasing infection risks.</p>
    <h2>Details of the Innovation Need</h2>
    <div class="post-section-container">
        <p>Titanium dental and orthopedic implants frequently suffer from aseptic loosening
        due to insufficient early osseointegration in osteoporotic bone tissue.</p>
    </div>
</body>
</html>
"""

INNOGET_SPAIN_NO_DATE_HTML = b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Recycled polymer compounding for food packaging</title>
    <meta property="og:title" content="Recycled polymer compounding for food packaging" />
    <meta property="og:url" content="https://www.innoget.com/technology-calls/3002/recycled-polymer" />
</head>
<body>
    <div class="user-meta">
        <h3 class="name light">Posted by <a href="#" class="bold dark">EcoPlast Valencia</a></h3>
    </div>
    <ul class="details">
        <li>EcoPlast Valencia</li>
        <li>from Spain</li>
        <li>Deadline at 15/09/2025</li>
    </ul>
    <h2>Desired outcome</h2>
    <p>Barrier properties matching virgin PET with minimum 80 percent post-consumer recyclate.</p>
    <h2>Details of the Innovation Need</h2>
    <div class="post-section-container">
        <p>Thermal degradation during mechanical recycling leads to yellowing and volatile degradation
        products that exceed migration limits for direct food contact.</p>
    </div>
</body>
</html>
"""


# --------------------------------------------------------------------------
# EEN/POD Candidate Mapper Tests
# --------------------------------------------------------------------------

def test_een_pod_mapper_spanish_valid_reference() -> None:
    candidate = EenPodCandidateMapper.map_payload(EEN_SPANISH_HTML, metadata={})

    assert candidate.demand_id == "TRES20250806011"
    assert candidate.source_id == "een_pod"
    assert candidate.source_construct == "Technology request"
    assert candidate.geographic_stratum == "spain"
    assert candidate.publication_date == date(2025, 8, 6)

    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.POD_REFERENCE
    assert evidence.publication_date == date(2025, 8, 6)
    assert evidence.evidence_field == "pod_reference"
    assert evidence.evidence_value == "TRES20250806011"

    assert "solar thermal collector" in candidate.title.lower()
    assert "industrial heat processes" in candidate.description_text.lower()
    assert candidate.has_articulated_technical_problem is True
    assert candidate.technical_problem_evidence_text is not None
    assert "thermal dissipation" in candidate.technical_problem_evidence_text.lower()
    assert candidate.is_publicly_accessible is True
    assert candidate.has_confidentiality_redaction is False


def test_een_pod_mapper_international_valid_reference() -> None:
    candidate = EenPodCandidateMapper.map_payload(EEN_INTERNATIONAL_HTML, metadata={})

    assert candidate.demand_id == "TRIT20240315002"
    assert candidate.source_id == "een_pod"
    assert candidate.source_construct == "Technology request"
    assert candidate.geographic_stratum == "international_european"
    assert candidate.publication_date == date(2024, 3, 15)

    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.POD_REFERENCE
    assert evidence.publication_date == date(2024, 3, 15)
    assert evidence.evidence_field == "pod_reference"
    assert evidence.evidence_value == "TRIT20240315002"

    assert "bio-based resin" in candidate.title.lower()
    assert candidate.has_articulated_technical_problem is True
    assert candidate.technical_problem_evidence_text is not None
    assert "curing temperatures" in candidate.technical_problem_evidence_text.lower()


def test_een_pod_mapper_unverifiable_date_invalid_pattern() -> None:
    metadata = {"demand_id": "EEN-TRIT-SPECIAL"}
    candidate = EenPodCandidateMapper.map_payload(EEN_INVALID_REF_HTML, metadata=metadata)

    assert candidate.demand_id == "EEN-TRIT-SPECIAL"
    assert candidate.source_id == "een_pod"
    assert candidate.publication_date is None

    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE
    assert evidence.publication_date is None
    assert evidence.evidence_field == "pod_reference"
    assert evidence.evidence_value == "TRIT-SPECIAL-REF-NO-DATE"


def test_een_pod_mapper_missing_reference() -> None:
    html_without_ref = b"""
    <html>
    <head><title>Some Proposal Without Reference</title></head>
    <body>
        <h1>Some Proposal Without Reference</h1>
        <div class="summary"><p>A description of a general proposal without reference code.</p></div>
    </body>
    </html>
    """
    metadata = {"demand_id": "EEN-DEMAND-001"}
    candidate = EenPodCandidateMapper.map_payload(html_without_ref, metadata=metadata)

    assert candidate.demand_id == "EEN-DEMAND-001"
    assert candidate.publication_date is None
    assert candidate.publication_date_evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE
    assert candidate.publication_date_evidence.evidence_field == "pod_reference"
    assert candidate.publication_date_evidence.evidence_value == "missing"


def test_een_pod_mapper_malformed_payload_raises_error() -> None:
    with pytest.raises(MappingError):
        EenPodCandidateMapper.map_payload(b"", metadata={})

    with pytest.raises(MappingError):
        EenPodCandidateMapper.map_payload(b"<html><body>Nothing here</body></html>", metadata={})


# --------------------------------------------------------------------------
# InnoGet Candidate Mapper Tests
# --------------------------------------------------------------------------

def test_innoget_mapper_explicit_metadata_date() -> None:
    candidate = InnogetCandidateMapper.map_payload(INNOGET_WITH_META_DATE_HTML, metadata={})

    assert candidate.demand_id == "INNOGET-3001"
    assert candidate.source_id == "innoget"
    assert candidate.source_construct == "Technology call"
    assert candidate.geographic_stratum == "spain"
    assert candidate.publication_date == date(2024, 5, 10)

    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.EXPLICIT_METADATA
    assert evidence.publication_date == date(2024, 5, 10)
    assert evidence.evidence_field == "meta:article:published_time"
    assert evidence.evidence_value == "2024-05-10T08:00:00Z"

    assert "biocompatible coating" in candidate.title.lower()
    assert candidate.has_articulated_technical_problem is True
    assert candidate.technical_problem_evidence_text is not None
    assert "osseointegration" in candidate.technical_problem_evidence_text.lower()
    assert candidate.organization_raw == "BioMed Innovations SL"


def test_innoget_mapper_deadline_only_unverifiable() -> None:
    candidate = InnogetCandidateMapper.map_payload(INNOGET_SPAIN_NO_DATE_HTML, metadata={})

    assert candidate.demand_id == "INNOGET-3002"
    assert candidate.publication_date is None

    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE
    assert evidence.evidence_field == "deadline_date_raw"
    assert evidence.evidence_value == "15/09/2025"
    assert candidate.geographic_stratum == "spain"


def test_innoget_mapper_with_real_fixture_call_2446() -> None:
    fixture_path = FIXTURES_DIR / "innoget_sample_call_2446.html"
    assert fixture_path.exists(), f"Fixture missing: {fixture_path}"

    raw_bytes = fixture_path.read_bytes()
    candidate = InnogetCandidateMapper.map_payload(raw_bytes, metadata={})

    assert candidate.demand_id == "INNOGET-2446"
    assert candidate.source_id == "innoget"
    assert candidate.source_construct == "Technology call"
    assert candidate.title == "Seeking Oral Care Solutions for Non-Bleach Whiteners"
    assert candidate.publication_date is None

    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE
    assert evidence.evidence_field == "deadline_date_raw"
    assert evidence.evidence_value == "31/12/2026"

    assert candidate.organization_raw == "The Procter & Gamble Company"
    assert candidate.geographic_stratum == "international_european"
    assert candidate.has_articulated_technical_problem is True
    assert candidate.technical_problem_evidence_text is not None
    assert "non-peroxide" in candidate.technical_problem_evidence_text.lower()


def test_innoget_mapper_historical_feed_date_in_metadata() -> None:
    metadata = {
        "demand_id": "INNOGET-3002",
        "historical_feed_date": "2023-11-20",
    }
    candidate = InnogetCandidateMapper.map_payload(INNOGET_SPAIN_NO_DATE_HTML, metadata=metadata)

    assert candidate.publication_date == date(2023, 11, 20)
    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.HISTORICAL_FEED
    assert evidence.evidence_field == "historical_feed"
    assert evidence.evidence_value == "2023-11-20"


def test_innoget_mapper_no_date_and_no_deadline() -> None:
    html_no_dates = b"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>General Challenge Call</title>
        <meta property="og:title" content="General Challenge Call" />
        <meta property="og:url" content="https://www.innoget.com/technology-calls/9999/general" />
    </head>
    <body>
        <h2>Desired outcome</h2>
        <p>A solution for general algorithmic challenge.</p>
        <h2>Details of the Innovation Need</h2>
        <div class="post-section-container">
            <p>Complex optimization problem requiring mathematical modeling.</p>
        </div>
    </body>
    </html>
    """
    candidate = InnogetCandidateMapper.map_payload(html_no_dates, metadata={})

    assert candidate.demand_id == "INNOGET-9999"
    assert candidate.publication_date is None
    evidence = candidate.publication_date_evidence
    assert evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE
    assert evidence.evidence_field == "no_date_field_observed"
    assert evidence.evidence_value == "no_date_field_observed"


def test_innoget_mapper_malformed_payload_raises_error() -> None:
    with pytest.raises(MappingError):
        InnogetCandidateMapper.map_payload(b"", metadata={})

    with pytest.raises(MappingError):
        InnogetCandidateMapper.map_payload(b"<html><body><h1>Title Only</h1></body></html>", metadata={})
