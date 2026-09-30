from pathlib import Path

import pyarrow.parquet as pq

from domain.models.patent import PatentDocument

_COLUMNS = ["publication_number", "country_code", "kind_code", "title", "abstract", "publication_date"]


def load_operational_patents(parquet_path: Path) -> list[PatentDocument]:
    """Loads the operational corpus snapshot as PatentDocuments, preserving parquet row order."""
    rows = pq.read_table(parquet_path, columns=_COLUMNS).to_pylist()
    patents: list[PatentDocument] = []
    for row in rows:
        publication_id = str(row["publication_number"])
        parts = publication_id.split("-")
        patents.append(
            PatentDocument(
                publication_id=publication_id,
                country_code=str(row["country_code"] or ""),
                doc_number=parts[1] if len(parts) > 1 else "",
                kind_code=str(row["kind_code"] or ""),
                title=str(row["title"] or ""),
                abstract=str(row["abstract"] or ""),
                publication_date=str(row["publication_date"]) if row["publication_date"] else None,
            )
        )
    return patents
