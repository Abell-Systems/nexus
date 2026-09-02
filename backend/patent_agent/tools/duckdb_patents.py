"""DuckDB-backed Patents Data Source for Spanish and Regional Patent Corpora."""

from pathlib import Path
from typing import Any
import duckdb

from .schemas import PatentRecord


class DuckDbPatentsDataSource:
    def __init__(self, db_path: str = "data/snapshots/patents_es_snapshot.duckdb"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS patents (
                publication_number VARCHAR PRIMARY KEY,
                title VARCHAR,
                abstract VARCHAR,
                assignee VARCHAR,
                filing_date VARCHAR,
                publication_date VARCHAR,
                cpc_codes VARCHAR[],
                citation_count INTEGER,
                backward_citation_count INTEGER,
                country_code VARCHAR DEFAULT 'ES'
            );
            CREATE INDEX IF NOT EXISTS idx_patents_pub ON patents(publication_number);
        """)

    def insert_patents(self, records: list[PatentRecord]):
        for r in records:
            pub_date = getattr(r, "publication_date", None) or r.filing_date
            b_count = getattr(r, "backward_citation_count", 0) or 0
            country = getattr(r, "country_code", "ES") or "ES"
            assignee_val = r.assignee if isinstance(r.assignee, str) else (", ".join(r.assignee) if r.assignee else "")
            self.conn.execute("""
                INSERT OR REPLACE INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                r.publication_number,
                r.title,
                r.abstract,
                assignee_val,
                r.filing_date,
                pub_date,
                r.cpc_codes,
                r.citation_count,
                b_count,
                country
            ])

    def search_patents(self, cpc_prefix: str, limit: int = 50) -> list[PatentRecord]:
        """Search patents by CPC prefix using unnest subquery."""
        query = """
            SELECT publication_number, title, abstract, assignee, filing_date,
                   publication_date, cpc_codes, citation_count, backward_citation_count, country_code
            FROM patents
            WHERE EXISTS (
                SELECT 1 FROM unnest(cpc_codes) AS t(c)
                WHERE t.c LIKE ?
            )
            ORDER BY citation_count DESC
            LIMIT ?
        """
        like_pattern = f"{cpc_prefix}%"
        df = self.conn.execute(query, [like_pattern, limit]).df()
        
        records = []
        for _, row in df.iterrows():
            rec = PatentRecord(
                publication_number=row["publication_number"],
                title=row["title"],
                abstract=row["abstract"],
                assignee=row["assignee"],
                filing_date=row["filing_date"],
                cpc_codes=list(row["cpc_codes"]),
                citation_count=int(row["citation_count"]) if row["citation_count"] is not None else 0,
            )
            # Attach extra properties
            setattr(rec, "publication_date", row["publication_date"])
            setattr(rec, "backward_citation_count", int(row["backward_citation_count"]) if row["backward_citation_count"] is not None else 0)
            setattr(rec, "country_code", row.get("country_code", "ES"))
            records.append(rec)
        return records

    def get_cluster_stats(self, cpc_prefix: str, ref_year: int = 2026) -> dict[str, Any]:
        patents = self.search_patents(cpc_prefix, limit=1000)
        if not patents:
            return {"patent_count": 0, "mean_age": 0.0, "patents": []}
        
        ages = []
        for p in patents:
            try:
                year = int(p.filing_date.split("-")[0]) if p.filing_date else ref_year
            except (ValueError, IndexError):
                year = ref_year
            age = max(1, ref_year - year)
            ages.append(age)
            
        mean_age = sum(ages) / len(ages) if ages else 0.0
        return {
            "patent_count": len(patents),
            "mean_age": round(mean_age, 2),
            "patents": patents
        }
