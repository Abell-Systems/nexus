from datetime import datetime

from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.patent import FamilyMembership, PatentDocument, PatentFamily


def test_patent_document_strict_null_preservation():
    doc = PatentDocument(
        publication_id="ES-2849102-B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Formulación detergente",
        abstract="Resumen",
        forward_citation_count=None,
        backward_citation_count=14,
    )
    assert doc.forward_citation_count is None
    assert doc.backward_citation_count == 14
    assert doc.filing_date is None
    assert doc.publication_date is None
    assert doc.priority_date is None
    assert doc.application_number is None
    assert doc.classifications_cpc == []
    assert doc.classifications_ipc == []
    assert doc.assignees == []
    assert doc.inventors == []
    assert doc.family_id is None


def test_patent_document_full_fields():
    doc = PatentDocument(
        publication_id="ES-2849102-B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        application_number="P202030431",
        title="Formulación detergente ecológica",
        abstract="Composición acuosa que comprende tensioactivos biodegradables.",
        assignees=["UNIVERSIDAD DE SEVILLA"],
        inventors=["GARCIA, Juan", "LOPEZ, Maria"],
        filing_date="2020-05-15",
        publication_date="2021-11-25",
        priority_date="2020-05-15",
        classifications_cpc=["C11D1/00", "C11D3/382"],
        classifications_ipc=["C11D1/00", "C11D3/382"],
        forward_citation_count=5,
        backward_citation_count=12,
        family_id="FAM-100",
    )
    assert doc.publication_id == "ES-2849102-B2"
    assert doc.application_number == "P202030431"
    assert doc.forward_citation_count == 5
    assert len(doc.assignees) == 1
    assert len(doc.classifications_cpc) == 2


def test_family_membership_decoupling():
    fam = PatentFamily(
        family_id="FAM-100",
        earliest_priority_date="2018-01-01",
        title_consensus="Detergent system",
        family_cpc_codes=["C11D1/00"],
    )
    obs = FieldObservation(
        entity_id="ES-2849102-B2",
        field_name="family_id",
        observed_value_json='"FAM-100"',
        value_type="str",
        source_authority="EPO INPADOC",
        source_uri="https://ops.epo.org",
        retrieval_timestamp=datetime(2026, 9, 2),
        raw_payload_sha256="a" * 64,
        extraction_version="1.0.0",
        verification_status=VerificationStatus.SOURCE_REPORTED,
    )
    membership = FamilyMembership(
        family_id="FAM-100",
        publication_id="ES-2849102-B2",
        membership_source="EPO INPADOC",
        evidence=obs,
    )
    assert membership.family_id == fam.family_id
    assert membership.publication_id == "ES-2849102-B2"
    assert membership.evidence.source_authority == "EPO INPADOC"
