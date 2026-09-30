import pyarrow as pa
import pyarrow.parquet as pq

from infrastructure.matching.operational_corpus import load_operational_patents


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
