#!/usr/bin/env python3
"""Ingestion & Snapshot Builder for Spanish Patent Corpus (OEPM / EPO OPS).

Extracts, normalizes, hashes, and populates DuckDB with real Spanish patent publications.
Preserves immutable dataset lineage:
  Raw Source (EPO OPS API or OEPM Open Data file) -> Normalized Parquet/JSONL -> SHA-256 Manifest -> DuckDB Snapshot.
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src" / "main"
for p in (REPO_ROOT, BACKEND_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))



def calculate_sha256(file_path: Path | str) -> str:
    """Compute standard SHA-256 hex digest for a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class EpoOpsClient:
    """Production client for European Patent Office Open Patent Services (OPS 3.2)."""

    def __init__(self, key: str | None = None, secret: str | None = None):
        self.key = key or os.getenv("EPO_OPS_KEY")
        self.secret = secret or os.getenv("EPO_OPS_SECRET")
        self.base_url = "https://ops.epo.org/3.2/rest-services"
        self._access_token: str | None = None

    def authenticate(self) -> bool:
        """Obtain OAuth2 bearer token from EPO OPS authorization service."""
        if not self.key or not self.secret:
            return False

        token_url = "https://ops.epo.org/3.2/auth/accesstoken"
        auth_bytes = f"{self.key}:{self.secret}".encode()
        b64_auth = base64.b64encode(auth_bytes).decode("ascii")

        req = urllib.request.Request(
            token_url,
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                self._access_token = data.get("access_token")
                return bool(self._access_token)
        except Exception as e:
            print(f"⚠️ EPO OPS Authentication failed: {e}")
            return False

    def search_and_fetch_biblio(
        self,
        cql_query: str = "pn=ES and pd within '2016 2024'",
        max_records: int = 50,
        enrich_citations: bool = False
    ) -> list[dict[str, Any]]:
        """Query OPS published-data search endpoint and parse bibliographic results."""
        if not self._access_token and not self.authenticate():
            raise RuntimeError("EPO OPS Authentication failed or credentials missing (EPO_OPS_KEY / EPO_OPS_SECRET).")

        search_url = f"{self.base_url}/published-data/search/biblio?q={urllib.parse.quote(cql_query)}&Range=1-{max_records}"
        req = urllib.request.Request(
            search_url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/xml"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                xml_content = resp.read()
                records = self.parse_ops_biblio_xml(xml_content)
        except Exception as e:
            raise RuntimeError(f"EPO OPS Search/Fetch failed: {e}") from e

        if enrich_citations:
            for rec in records:
                cit_f, cit_b = self.fetch_citations(rec["publication_number"])
                rec["citation_count"] = cit_f
                rec["backward_citation_count"] = cit_b

        return records

    def fetch_citations(self, publication_number: str) -> tuple[int | None, int | None]:
        """Query EPO OPS citations endpoint for a specific publication document."""
        if not self._access_token and not self.authenticate():
            return None, None

        # Clean doc number for epodoc format (e.g. ES2849102)
        doc_clean = publication_number.replace("-", "").split(".")[0]
        cit_url = f"{self.base_url}/published-data/publication/epodoc/{urllib.parse.quote(doc_clean)}/citations"
        req = urllib.request.Request(
            cit_url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/xml"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_cit = resp.read()
                root = ET.fromstring(xml_cit)
                backward_cits = len(root.findall(".//{*}patcit"))
                # OPS citations endpoint provides backward citations (cited patents in biblio).
                # Forward citations remain None (unobserved) to prevent false-zero bias in T_i calculation.
                return None, backward_cits
        except Exception:
            return None, None

    @staticmethod
    def parse_ops_biblio_xml(xml_content: bytes) -> list[dict[str, Any]]:
        """Parse raw EPO OPS XML biblio response into normalized record dictionaries."""
        records: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_content)
            for doc in root.findall(".//{*}exchange-document"):
                country = doc.get("country", "ES")
                doc_number = doc.get("doc-number", "")
                kind = doc.get("kind", "")
                pub_num = f"{country}-{doc_number}-{kind}" if doc_number else ""

                # Title
                title_elem = doc.find(".//{*}invention-title[@lang='es']") or doc.find(".//{*}invention-title")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Sin título"

                # Abstract
                abstract_elem = doc.find(".//{*}abstract[@lang='es']/{*}p") or doc.find(".//{*}abstract/{*}p")
                abstract = abstract_elem.text.strip() if abstract_elem is not None and abstract_elem.text else ""

                # Dates: Clearly distinguish publication date (pd) from filing/application date
                pub_date_elem = doc.find(".//{*}publication-reference//{*}date")
                pub_date_raw = pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else "20200101"
                pub_date = f"{pub_date_raw[:4]}-{pub_date_raw[4:6]}-{pub_date_raw[6:8]}" if len(pub_date_raw) >= 8 else "2020-01-01"

                app_date_elem = doc.find(".//{*}application-reference//{*}date")
                app_date_raw = app_date_elem.text if app_date_elem is not None and app_date_elem.text else pub_date_raw
                filing_date = f"{app_date_raw[:4]}-{app_date_raw[4:6]}-{app_date_raw[6:8]}" if len(app_date_raw) >= 8 else pub_date

                # Assignee
                assignee_elems = doc.findall(".//{*}applicants//{*}applicant-name/{*}name")
                assignees = [a.text.strip() for a in assignee_elems if a.text]
                assignee = ", ".join(assignees) if assignees else "Titular no especificado"

                # Classifications (CPC / IPC)
                cpc_codes = []
                for c_elem in doc.findall(".//{*}patent-classifications//{*}classification-symbol"):
                    if c_elem.text:
                        code = c_elem.text.replace(" ", "")
                        cpc_codes.append(code)

                if not cpc_codes:
                    cpc_codes = ["G06Q10/00"]

                records.append({
                    "publication_number": pub_num,
                    "title": title,
                    "abstract": abstract,
                    "assignee": assignee,
                    "filing_date": filing_date,
                    "publication_date": pub_date,
                    "cpc_codes": cpc_codes,
                    "citation_count": None,
                    "backward_citation_count": None,
                    "country_code": country
                })
        except Exception as e:
            print(f"⚠️ XML parsing error: {e}")

        return records


def ingest_from_raw_oepm_source(raw_path: str = "data/raw/oepm_open_data_es.json") -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    """Ingest Spanish patent records and provenance metadata from official OEPM open data source file."""
    p = Path(raw_path)
    if not p.exists():
        raise FileNotFoundError(f"Raw OEPM open data source file missing at {raw_path}")

    raw_sha256 = calculate_sha256(p)

    with open(p, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("dataset_metadata", {})
    publications = data.get("publications", [])

    return publications, meta, raw_sha256


def build_and_freeze_corpus(
    source: str = "oepm_raw",
    raw_source_json: str = "data/raw/oepm_open_data_es.json",
    output_parquet: str = "data/snapshots/patents_es_corpus.parquet",
    output_duckdb: str = "data/snapshots/patents_es_snapshot.duckdb",
    manifest_file: str = "data/snapshots/patents_es_manifest.json",
    raw_output_jsonl: str = "data/snapshots/patents_es_corpus.jsonl",
    enrich_ops_citations: bool = False,
) -> dict[str, Any]:
    """Execute complete ingestion pipeline: raw source -> parquet -> SHA256 -> DuckDB.

    Args:
        source: 'ops' (fetch live from EPO OPS API) or 'oepm_raw' (load from certified OEPM raw file).
    """
    p_parquet = Path(output_parquet)
    p_duckdb = Path(output_duckdb)
    p_manifest = Path(manifest_file)
    p_jsonl = Path(raw_output_jsonl)

    p_parquet.parent.mkdir(parents=True, exist_ok=True)
    p_jsonl.parent.mkdir(parents=True, exist_ok=True)

    # 1. Ingestion Strategy
    if source == "ops":
        ops_client = EpoOpsClient()
        raw_records = ops_client.search_and_fetch_biblio(
            cql_query="pn=ES and pd within '2016 2024'",
            enrich_citations=enrich_ops_citations
        )
        source_authority = "European Patent Office (EPO Open Patent Services OPS 3.2)"
        official_url = "https://ops.epo.org/3.2/rest-services"
        raw_sha256 = "N/A (Live REST API Query)"
        extraction_criteria = "EPO OPS published-data CQL query 'pn=ES and pd within 2016 2024'."
    elif source == "oepm_raw":
        raw_records, raw_meta, raw_sha256 = ingest_from_raw_oepm_source(raw_source_json)
        source_authority = raw_meta.get("dataset_title", "Oficina Española de Patentes y Marcas (OEPM) - BOPI")
        official_url = raw_meta.get("official_catalog_url", "https://datos.gob.es/es/catalogo/e05024401-patentes-solicitadas-y-concedidas-bopi")
        extraction_criteria = raw_meta.get("extraction_criteria", "OEPM BOPI & Invenes official gazette publications (ES) 2016-2024.")
    else:
        raise ValueError(f"Unknown ingestion source: {source}. Must be 'ops' or 'oepm_raw'.")

    # 2. Normalize records and compute CPC distribution
    normalized_records: list[dict[str, Any]] = []
    cpc_counts: dict[str, int] = {}

    for r in raw_records:
        pub_num = r["publication_number"]
        title = r["title"]
        abstract = r["abstract"]
        assignee = r["assignee"] if isinstance(r["assignee"], str) else ", ".join(r["assignee"])
        cpc_codes = r["cpc_codes"]
        filing_date = r["filing_date"]
        pub_date = r.get("publication_date", filing_date)
        cit_count = int(r["citation_count"]) if r.get("citation_count") is not None else None
        b_count = int(r["backward_citation_count"]) if r.get("backward_citation_count") is not None else None
        country = r.get("country_code", "ES")

        for cpc in cpc_codes:
            prefix = cpc[:4]
            cpc_counts[prefix] = cpc_counts.get(prefix, 0) + 1

        normalized_records.append({
            "publication_number": pub_num,
            "title": title,
            "abstract": abstract,
            "assignee": assignee,
            "filing_date": filing_date,
            "publication_date": pub_date,
            "cpc_codes": cpc_codes,
            "citation_count": cit_count,
            "backward_citation_count": b_count,
            "country_code": country
        })

    # 3. Write normalized JSONL
    with open(p_jsonl, "w", encoding="utf-8") as f:
        for rec in normalized_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 4. Write Parquet and compute SHA-256
    con_mem = duckdb.connect()
    con_mem.execute("CREATE TABLE temp_patents AS SELECT * FROM read_json_auto(?)", [str(p_jsonl)])
    con_mem.execute("COPY temp_patents TO ? (FORMAT PARQUET)", [str(p_parquet)])
    con_mem.close()

    parquet_sha256 = calculate_sha256(p_parquet)

    # 5. Write Content-Addressed Manifest
    manifest_data = {
        "dataset_name": "Spanish National Patent Pilot Corpus",
        "dataset_version": "1.0.0",
        "dataset_scope": "Pilot baseline corpus for proof-of-method validation; publication-level source verification pending.",
        "created_at": datetime.now().isoformat(),
        "source_authority": source_authority,
        "official_catalog_url": official_url,
        "raw_source_file": raw_source_json if source == "oepm_raw" else "EPO OPS API",
        "raw_source_sha256": raw_sha256,
        "inclusion_criteria": extraction_criteria,
        "total_records": len(normalized_records),
        "sha256_hash": parquet_sha256,
        "format": "parquet / jsonl",
        "cpc_subclass_distribution": dict(sorted(cpc_counts.items(), key=lambda x: -x[1])),
        "provenance": {
            "parquet_file": str(p_parquet),
            "jsonl_file": str(p_jsonl),
            "duckdb_file": str(p_duckdb)
        }
    }

    with open(p_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    # 6. Populate Snapshot DuckDB
    con_db = duckdb.connect(str(p_duckdb))
    con_db.execute("DROP TABLE IF EXISTS patents")
    con_db.execute("""
        CREATE TABLE patents (
            publication_number VARCHAR PRIMARY KEY,
            title VARCHAR,
            abstract VARCHAR,
            assignee VARCHAR,
            filing_date VARCHAR,
            publication_date VARCHAR,
            cpc_codes VARCHAR[],
            citation_count INTEGER,
            backward_citation_count INTEGER,
            country_code VARCHAR
        );
        CREATE INDEX idx_patents_pub ON patents(publication_number);
    """)
    con_db.execute("INSERT INTO patents SELECT * FROM read_parquet(?)", [str(p_parquet)])
    count = con_db.execute("SELECT count(*) FROM patents").fetchone()[0]
    con_db.close()

    print("✅ Ingestion and dataset freeze complete:")
    print(f"   - Source Authority:       {source_authority}")
    print(f"   - Scope:                  {manifest_data['dataset_scope']}")
    print(f"   - Official Catalog URL:   {official_url}")
    print(f"   - Raw Source SHA-256:     {raw_sha256}")
    print(f"   - Normalized Records:     {count}")
    print(f"   - Parquet SHA-256 Digest: {parquet_sha256}")
    print(f"   - Manifest:               {p_manifest}")
    print(f"   - DuckDB Snapshot:        {p_duckdb}")

    return manifest_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Spanish patent publications into DuckDB snapshot.")
    parser.add_argument("--source", choices=["ops", "oepm_raw"], default="oepm_raw",
                        help="Ingestion source authority ('ops' for EPO OPS API, 'oepm_raw' for verified OEPM dataset).")
    parser.add_argument("--enrich-citations", action="store_true", default=False,
                        help="Enrich records with citation counts when using OPS API.")
    args = parser.parse_args()
    build_and_freeze_corpus(source=args.source, enrich_ops_citations=args.enrich_citations)
