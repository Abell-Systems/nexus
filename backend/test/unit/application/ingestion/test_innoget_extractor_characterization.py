"""Characterization tests for InnoGetExtractor — lock behavior before complexity refactor.

These tests document the *exact current semantics*, including non-obvious precedence
decisions. All 16 must pass after Task 2 — any failure means the refactor changed behavior.
"""
from unittest.mock import MagicMock

from application.ingestion.extractors.innoget_extractor import InnoGetExtractor
from domain.models.demand import ExtractionSourceKind
from domain.protocols.sources import RawPayload


def _make_payload(html: str, metadata: dict | None = None) -> RawPayload:
    payload = MagicMock(spec=RawPayload)
    payload.payload_bytes = html.encode("utf-8")
    payload.metadata = metadata or {}
    return payload


OG_WITH_ID = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/technology-calls/12345/test"/>
  <meta property="og:title" content="Green Chemistry Opportunity"/>
  <meta property="og:description" content="A long enough description that exceeds thirty characters easily."/>
</head><body></body></html>
"""

OG_URL_WITHOUT_ID = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/about"/>
  <meta property="og:title" content="No ID Here"/>
</head><body></body></html>
"""

NO_OG_URL = """
<html><head>
  <title>Fallback Title</title>
  <meta name="description" content="A plain meta description that is long enough to pass the minimum."/>
</head><body></body></html>
"""

SHORT_META_DESC = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/challenges/321/x"/>
  <meta property="og:description" content="Too short"/>
  <meta name="description" content="Also short"/>
</head><body>
  <div class="description">This is a long enough description inside the DOM to pass the thirty character minimum.</div>
</body></html>
"""

ALL_DESC_SHORT = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/challenges/444/x"/>
  <meta property="og:description" content="Short"/>
</head><body><div class="description">Short too</div></body></html>
"""

DETAILS_UL_HTML = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/challenges/999/example"/>
</head><body>
<ul class="details">
  <li>CSIC Madrid</li>
  <li>From Spain</li>
  <li>Project Size: 50k-100k</li>
  <li>Deadline: 31/12/2024</li>
</ul>
</body></html>
"""

NO_DETAILS_UL = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/challenges/555/x"/>
</head><body><p>No list here.</p></body></html>
"""

USER_META_HTML = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/challenges/777/org"/>
</head><body>
<div class="user-meta">Posted by Acme Corp 42 followers</div>
</body></html>
"""

USER_META_NO_MATCH = """
<html><head>
  <meta property="og:url" content="https://www.innoget.com/challenges/888/org"/>
</head><body>
<div class="user-meta">12345 some weird format</div>
</body></html>
"""

EMPTY_HTML = "<html><head></head><body></body></html>"


class TestDemandIdPrecedence:
    """Critical: document the exact metadata → canonical → source cascade."""

    def setup_method(self) -> None:
        self.extractor = InnoGetExtractor()

    def test_metadata_demand_id_takes_priority_over_canonical(self) -> None:
        payload = _make_payload(OG_WITH_ID, metadata={"demand_id": "INNOGET-OVERRIDE"})
        result = self.extractor.extract(payload, "https://www.innoget.com/challenges/99999/x")
        assert result.demand_id == "INNOGET-OVERRIDE"
        assert result.demand_id_source == ExtractionSourceKind.PAYLOAD_METADATA

    def test_canonical_uri_used_when_no_metadata_id(self) -> None:
        payload = _make_payload(OG_WITH_ID)
        result = self.extractor.extract(payload, "https://www.innoget.com/challenges/99999/x")
        assert result.demand_id == "INNOGET-12345"
        assert result.demand_id_source == ExtractionSourceKind.META_TAG

    def test_source_uri_is_NOT_tried_when_canonical_uri_exists_without_id(self) -> None:
        """
        IMPORTANT: if canonical_uri is present but contains no numeric ID,
        source_uri is NOT consulted — the original code uses elif, not independent if.
        This test must survive the refactor unchanged.
        """
        payload = _make_payload(OG_URL_WITHOUT_ID)
        result = self.extractor.extract(
            payload, "https://www.innoget.com/challenges/8888/some-slug"
        )
        # canonical_uri_observed is truthy → elif branch for source_uri is skipped
        assert result.demand_id is None

    def test_source_uri_used_when_no_canonical_and_no_metadata(self) -> None:
        payload = _make_payload(EMPTY_HTML)
        result = self.extractor.extract(
            payload, "https://www.innoget.com/challenges/8888/some-slug"
        )
        assert result.demand_id == "INNOGET-8888"
        assert result.demand_id_source == ExtractionSourceKind.SOURCE_URI

    def test_no_id_available_returns_none(self) -> None:
        payload = _make_payload(EMPTY_HTML)
        result = self.extractor.extract(payload, "https://www.innoget.com/about")
        assert result.demand_id is None

    def test_empty_source_uri_with_no_og_url(self) -> None:
        payload = _make_payload(EMPTY_HTML)
        result = self.extractor.extract(payload, "")
        assert result.demand_id is None


class TestTitleExtraction:
    def setup_method(self) -> None:
        self.extractor = InnoGetExtractor()

    def test_og_title_used_when_present(self) -> None:
        payload = _make_payload(OG_WITH_ID)
        result = self.extractor.extract(payload, "")
        assert result.title == "Green Chemistry Opportunity"

    def test_html_title_fallback_when_no_og_title(self) -> None:
        payload = _make_payload(NO_OG_URL)
        result = self.extractor.extract(payload, "")
        assert result.title == "Fallback Title"


class TestDescriptionExtraction:
    def setup_method(self) -> None:
        self.extractor = InnoGetExtractor()

    def test_og_description_used_when_long_enough(self) -> None:
        payload = _make_payload(OG_WITH_ID)
        result = self.extractor.extract(payload, "")
        assert result.description is not None
        assert "thirty characters" in result.description

    def test_meta_description_fallback(self) -> None:
        payload = _make_payload(NO_OG_URL)
        result = self.extractor.extract(payload, "")
        assert result.description is not None
        assert "plain meta description" in result.description

    def test_dom_block_fallback_when_meta_too_short(self) -> None:
        payload = _make_payload(SHORT_META_DESC)
        result = self.extractor.extract(payload, "")
        assert result.description is not None
        assert "long enough description inside the DOM" in result.description

    def test_short_meta_description_retained_if_dom_block_also_short(self) -> None:
        """
        CHARACTERIZATION: If og:description is < 30 chars and DOM fallback is also < 30 chars,
        the short og:description is NOT cleared — it remains the extracted description.
        """
        payload = _make_payload(ALL_DESC_SHORT)
        result = self.extractor.extract(payload, "")
        assert result.description == "Short"

    def test_description_is_none_when_no_sources_present(self) -> None:
        payload = _make_payload(EMPTY_HTML)
        result = self.extractor.extract(payload, "")
        assert result.description is None



class TestOrganizationAndDetails:
    def setup_method(self) -> None:
        self.extractor = InnoGetExtractor()

    def test_details_ul_extracts_org_country_budget_deadline(self) -> None:
        payload = _make_payload(DETAILS_UL_HTML)
        result = self.extractor.extract(payload, "")
        assert result.organization_raw == "CSIC Madrid"
        assert result.country_raw == "Spain"
        assert result.budget_range_raw is not None
        assert "Project Size" in result.budget_range_raw
        assert result.deadline_date_raw == "31/12/2024"

    def test_metadata_org_overrides_dom(self) -> None:
        payload = _make_payload(
            DETAILS_UL_HTML, metadata={"requesting_organization": "Override Org"}
        )
        result = self.extractor.extract(payload, "")
        assert result.organization_raw == "Override Org"

    def test_user_meta_fallback_when_no_details_ul(self) -> None:
        payload = _make_payload(USER_META_HTML)
        result = self.extractor.extract(payload, "")
        assert result.organization_raw == "Acme Corp"

    def test_user_meta_not_extracted_when_format_unrecognized(self) -> None:
        payload = _make_payload(USER_META_NO_MATCH)
        result = self.extractor.extract(payload, "")
        assert result.organization_raw is None

    def test_no_details_and_no_user_meta_yields_none_org(self) -> None:
        payload = _make_payload(NO_DETAILS_UL)
        result = self.extractor.extract(payload, "")
        assert result.organization_raw is None

    def test_extraction_timestamp_is_timezone_aware(self) -> None:
        payload = _make_payload(OG_WITH_ID)
        result = self.extractor.extract(payload, "")
        assert result.extraction_timestamp.tzinfo is not None
