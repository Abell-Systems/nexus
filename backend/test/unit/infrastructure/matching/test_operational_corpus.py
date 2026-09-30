import pyarrow as pa
import pyarrow.parquet as pq

from domain.models.demand import DemandSignal
from domain.models.matching import EligibilityReason
from domain.models.patent import PatentDocument
from infrastructure.matching.operational_corpus import (
    load_operational_assets,
    load_operational_patents,
    operational_eligibility_policy,
)


def _patent(country="ES", title="T", abstract="A", published="2020-01-01"):
    return PatentDocument(
        publication_id=f"{country}-1-A1", country_code=country, doc_number="1", kind_code="A1",
        title=title, abstract=abstract, publication_date=published,
    )


def _demand(posted_date=None):
    return DemandSignal(demand_id="D", title="t", description="d", posted_date=posted_date)


class OperationalCorpusTest:
    def test_should_load_patents_in_parquet_row_order_when_file_has_expected_columns(self, tmp_path):
        table = pa.table(
            {
                "publication_number": ["ES-2594181-A1", "EP-3000000-B1"],
                "country_code": ["ES", "EP"],
                "kind_code": ["A1", "B1"],
                "title": ["Dispositivo de campo de cocción", "Cooking device"],
                "abstract": ["Un dispositivo para cocinar.", "A device for cooking."],
                "publication_date": ["2016-12-16", "2019-03-06"],
            }
        )
        path = tmp_path / "publications.parquet"
        pq.write_table(table, path)

        patents = load_operational_patents(path)

        assert [p.publication_id for p in patents] == ["ES-2594181-A1", "EP-3000000-B1"]
        assert patents[0].doc_number == "2594181"
        assert patents[0].kind_code == "A1"
        assert patents[1].country_code == "EP"
        assert patents[1].publication_date == "2019-03-06"


class OperationalEligibilityPolicyTest:
    def test_should_accept_es_asset_when_demand_has_no_posted_date(self):
        result = operational_eligibility_policy().evaluate(_patent(), _demand(posted_date=None))
        assert result.is_eligible and result.reason == EligibilityReason.ELIGIBLE

    def test_should_accept_asset_published_after_demand_date_because_no_temporal_rule_exists(self):
        result = operational_eligibility_policy().evaluate(_patent(published="2030-01-01"), _demand("2018-01-01"))
        assert result.is_eligible

    def test_should_exclude_ep_asset_when_jurisdiction_is_not_es(self):
        result = operational_eligibility_policy().evaluate(_patent(country="EP"), _demand())
        assert not result.is_eligible and result.reason == EligibilityReason.EXCLUDED_JURISDICTION

    def test_should_exclude_asset_when_abstract_is_blank(self):
        result = operational_eligibility_policy().evaluate(_patent(abstract="   "), _demand())
        assert not result.is_eligible and result.reason == EligibilityReason.EXCLUDED_MISSING_TEXT

    def test_should_exclude_asset_when_title_is_blank(self):
        result = operational_eligibility_policy().evaluate(_patent(title=""), _demand())
        assert not result.is_eligible and result.reason == EligibilityReason.EXCLUDED_MISSING_TEXT


class LoadOperationalAssetsTest:
    def test_should_fill_holders_cpc_type_and_language_when_optional_columns_exist(self, tmp_path):
        table = pa.table(
            {
                "publication_number": ["ES-2594181-U"],
                "country_code": ["ES"],
                "kind_code": ["U"],
                "title": ["Dispositivo"],
                "abstract": ["Un dispositivo."],
                "publication_date": ["2016-12-16"],
                "ip_type": ["utility_model"],
                "abstract_language": ["es"],
                "assignees": [["ACME SA"]],
                "inventors": [["ANA", "LUIS"]],
                "cpc_codes": [["B60K1/00"]],
                "filing_date": ["2016-01-02"],
                "family_id": ["123"],
            }
        )
        path = tmp_path / "publications.parquet"
        pq.write_table(table, path)

        asset = load_operational_assets(path)[0]

        assert asset.ip_type == "utility_model" and asset.abstract_language == "es"
        assert asset.patent.assignees == ["ACME SA"] and asset.patent.inventors == ["ANA", "LUIS"]
        assert asset.patent.classifications_cpc == ["B60K1/00"]
        assert asset.patent.filing_date == "2016-01-02" and asset.patent.family_id == "123"

    def test_should_default_optional_fields_when_columns_are_absent(self, tmp_path):
        table = pa.table(
            {
                "publication_number": ["ES-1-A1"], "country_code": ["ES"], "kind_code": ["A1"],
                "title": ["T"], "abstract": ["A"], "publication_date": ["2020-01-01"],
            }
        )
        path = tmp_path / "publications.parquet"
        pq.write_table(table, path)

        asset = load_operational_assets(path)[0]

        assert asset.ip_type == "unknown" and asset.abstract_language == ""
        assert asset.patent.assignees == [] and asset.patent.classifications_cpc == []
