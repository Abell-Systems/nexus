"""Unit tests for the TED (Tenders Electronic Daily) candidate mapper (ADR 0034)."""

from datetime import date

import pytest

from application.corpus.mappers import MappingError, TedCandidateMapper
from domain.models.corpus_expansion import PublicationDateEvidenceType


def _ted_notice_html(
    *,
    publication_number: str = "462609-2026",
    title: str = "Monimuotoisuuden monitorointi",
    description: str = (
        "Hankinnan tavoitteena on löytää innovaatiokumppani, jonka kanssa "
        "kehitetään aineistopohjainen järjestelmä metsän "
        "monimuotoisuuden seurantaan tekoälyavusteisesti."
    ),
    buyer_name: str = "Suomen metsäkeskus",
    oj_s_line: str = "OJ S 127/2026 06/07/2026",
    nuts_code: str = "FI1C6",
    language_code_3: str = "FIN",
    notice_type_line: str = "Contract or concession notice – standard regime",
) -> bytes:
    return f"""
    <html lang="EN">
    <body>
    <div id="summary">
     <span class="bold" id="notInPdf">{publication_number} - Competition</span>
     <div class="bold">Finland – Services incidental to forestry – {title}</div>
     <div class="bold">{oj_s_line}</div>
     <div class="bold">{notice_type_line}</div>
    </div>
    <div id="notice">
      <div>
       <span class="label" data-labels-key="field|name|BT-500-Organization-Company">Official name</span><span>:&nbsp;</span><span class="data">{buyer_name}</span>
      </div>
      <div>
       <span class="label" data-labels-key="business-term|name|BT-513">Town</span><span>:&nbsp;</span><span class="data">Lahti</span>
      </div>
      <div>
       <span class="label" data-labels-key="business-term|name|BT-507">Country subdivision (NUTS)</span><span>:&nbsp;</span><span class="line" data-labels-key="code|name|nuts.{nuts_code}">Päijät-Häme</span><span>&nbsp;(</span><span class="data">{nuts_code}</span>
      </div>
      <div>
       <span class="label" data-labels-key="field|name|BT-21-Procedure">Title</span><span>:&nbsp;</span><span class="data">{title}</span>
      </div>
      <div>
       <span class="label" data-labels-key="field|name|BT-24-Procedure">Description</span><span>:&nbsp;</span><span class="data">{description}</span>
      </div>
      <div>
       <span class="label" data-labels-key="field|name|BT-105-Procedure">Type of procedure</span><span>:&nbsp;</span><span class="data" data-labels-key="code|name|procurement-procedure-type.innovation">Innovation partnership</span>
      </div>
      <div>
       <span class="label" data-labels-key="business-term|name|BT-702">Languages in which this notice is officially available</span><span>:&nbsp;</span><span class="data" data-labels-key="code|name|language.{language_code_3}">Finnish</span>
      </div>
      <div>
       <span class="label" data-labels-key="business-term|name|OPP-010">Notice publication number</span><span>:&nbsp;</span><span class="data">{publication_number}</span>
      </div>
    </div>
    </body>
    </html>
    """.encode()


def test_ted_mapper_extracts_full_candidate() -> None:
    html = _ted_notice_html()

    candidate = TedCandidateMapper.map_payload(html, metadata={"demand_id": "462609-2026"})

    assert candidate.demand_id == "462609-2026"
    assert candidate.source_id == "ted"
    assert candidate.source_construct == "Innovation partnership"
    assert candidate.title == "Monimuotoisuuden monitorointi"
    assert "innovaatiokumppani" in candidate.description_text
    assert candidate.organization_raw == "Suomen metsäkeskus"
    assert candidate.geographic_stratum == "international_european"
    assert candidate.language_code == "fi"
    assert candidate.publication_date == date(2026, 7, 6)
    assert candidate.publication_date_evidence.evidence_type == PublicationDateEvidenceType.EXPLICIT_METADATA
    assert candidate.has_articulated_technical_problem is True
    assert candidate.technical_problem_evidence_text == candidate.description_text


def test_ted_mapper_spain_buyer_maps_to_spain_stratum() -> None:
    html = _ted_notice_html(
        publication_number="452177-2026-original",
        buyer_name="AENA, S.M.E., S.A.",
        nuts_code="ES300",
        language_code_3="SPA",
        oj_s_line="OJ S 100/2026 01/01/2026",
    )

    candidate = TedCandidateMapper.map_payload(html, metadata={"demand_id": "452177-2026-original"})

    assert candidate.geographic_stratum == "spain"
    assert candidate.language_code == "es"


def test_ted_mapper_excludes_change_notice() -> None:
    html = _ted_notice_html(notice_type_line="Contract or concession notice – standard regime - Change notice")

    with pytest.raises(MappingError, match="Change notice"):
        TedCandidateMapper.map_payload(html, metadata={"demand_id": "452177-2026"})


def test_ted_mapper_excludes_corrigendum() -> None:
    html = _ted_notice_html(notice_type_line="Contract notice - Corrigendum")

    with pytest.raises(MappingError, match="Corrigendum"):
        TedCandidateMapper.map_payload(html, metadata={"demand_id": "452177-2026"})


def test_ted_mapper_unparseable_date_is_unverifiable() -> None:
    html = _ted_notice_html(oj_s_line="OJ S 999/2026 31/02/2026")  # invalid calendar date

    candidate = TedCandidateMapper.map_payload(html, metadata={"demand_id": "462609-2026"})

    assert candidate.publication_date is None
    assert candidate.publication_date_evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE


def test_ted_mapper_missing_date_is_unverifiable() -> None:
    html = _ted_notice_html(oj_s_line="")

    candidate = TedCandidateMapper.map_payload(html, metadata={"demand_id": "462609-2026"})

    assert candidate.publication_date is None
    assert candidate.publication_date_evidence.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE
    assert candidate.publication_date_evidence.evidence_value == "missing"


def test_ted_mapper_missing_description_raises_error() -> None:
    html = f"""
    <html lang="EN"><body>
      <div><span class="label" data-labels-key="field|name|BT-21-Procedure">Title</span><span>:&nbsp;</span><span class="data">Some title</span></div>
      <div><span class="label" data-labels-key="field|name|BT-500-Organization-Company">Official name</span><span>:&nbsp;</span><span class="data">Some Buyer</span></div>
    </body></html>
    """.encode()

    with pytest.raises(MappingError, match="Description"):
        TedCandidateMapper.map_payload(html, metadata={"demand_id": "1-2026"})


def test_ted_mapper_malformed_payload_raises_error() -> None:
    with pytest.raises(MappingError):
        TedCandidateMapper.map_payload(b"", metadata={})

    with pytest.raises(MappingError):
        TedCandidateMapper.map_payload(b"<html><body>Nothing here</body></html>", metadata={})
