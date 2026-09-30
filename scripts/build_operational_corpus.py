"""Builds the sealed operational corpus v1 (prototype demo) from the BigQuery staging table.

Separate from the OEPM scientific corpus on purpose: this one exists so the demand->patents demo
has coverage; it is never an evaluation object. Selection policy is embedded in SQL below and
hashed into the manifest so a rebuild that changes the policy changes the hash.

Requires: staging table `nexus_operational_corpus.publications_es_v0` (see docs in manifest),
google-cloud-bigquery, pyarrow. Usage: python scripts/build_operational_corpus.py
"""

import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
from google.cloud import bigquery

PROJECT = os.getenv("GCP_PROJECT", "ip-matchmaker-506820")
STAGING = f"{PROJECT}.nexus_operational_corpus.publications_es_v0"
OUT_DIR = Path("data/snapshots/operational_corpus_v1")

SELECTION_SQL = f"""
WITH base AS (
  SELECT *,
    (SELECT a.text FROM UNNEST(abstract_localized) a WHERE a.language = 'es' AND LENGTH(a.text) > 50 LIMIT 1) AS abs_es,
    (SELECT a.text FROM UNNEST(abstract_localized) a WHERE a.language = 'en' AND LENGTH(a.text) > 50 LIMIT 1) AS abs_en,
    (SELECT t.text FROM UNNEST(title_localized) t WHERE t.language = 'es' LIMIT 1) AS title_es,
    EXISTS (SELECT 1 FROM UNNEST(assignee_harmonized) a WHERE a.country_code = 'ES') AS es_applicant
  FROM `{STAGING}`
),
cand AS (
  SELECT *, COALESCE(abs_es, abs_en) AS abstract, IF(abs_es IS NOT NULL, 'es', 'en') AS abstract_language
  FROM base
  WHERE es_applicant AND COALESCE(abs_es, abs_en) IS NOT NULL
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY IF(family_id IS NULL OR CAST(family_id AS STRING) = '-1', publication_number, CAST(family_id AS STRING))
    ORDER BY (abs_es IS NOT NULL) DESC, publication_date DESC, publication_number ASC
  ) AS rn
  FROM cand
)
SELECT
  publication_number,
  country_code,
  kind_code,
  IF(country_code = 'ES' AND kind_code IN ('U', 'Y'), 'utility_model', 'patent') AS ip_type,
  CAST(family_id AS STRING) AS family_id,
  COALESCE(title_es, title_localized[SAFE_OFFSET(0)].text) AS title,
  abstract,
  abstract_language,
  ARRAY(SELECT DISTINCT a.name FROM UNNEST(assignee_harmonized) a WHERE a.name IS NOT NULL) AS assignees,
  ARRAY(SELECT DISTINCT i.name FROM UNNEST(inventor_harmonized) i WHERE i.name IS NOT NULL) AS inventors,
  ARRAY(SELECT c.code FROM UNNEST(cpc) c) AS cpc_codes,
  FORMAT_DATE('%Y-%m-%d', PARSE_DATE('%Y%m%d', CAST(filing_date AS STRING))) AS filing_date,
  FORMAT_DATE('%Y-%m-%d', PARSE_DATE('%Y%m%d', CAST(publication_date AS STRING))) AS publication_date
FROM ranked
WHERE rn = 1
ORDER BY publication_number
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=PROJECT, location="US")
    job = client.query(SELECTION_SQL, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=10**10))
    table = job.result().to_arrow()
    parquet_path = OUT_DIR / "publications.parquet"
    pq.write_table(table, parquet_path, compression="zstd")

    rows = table.to_pylist()
    manifest = {
        "dataset_id": "NEXUS-OPERATIONAL-CORPUS-V1",
        "dataset_title": "Corpus operativo de activos de propiedad industrial españoles (prototype demo)",
        "purpose": "Demo coverage only. NOT an evaluation corpus; the OEPM corpus remains the scientific one.",
        "source": "patents-public-data.patents.publications (Google Patents Public Data) via staging table " + STAGING,
        "license_status": "UNVERIFIED - internal use only; do not redistribute until verified",
        "staging_extract": "publication_date >= 2015-01-01 AND (country ES OR (country EP AND any ES harmonized assignee))",
        "selection_policy": {
            "applicant": "at least one assignee_harmonized.country_code = 'ES'",
            "abstract": "length > 50 chars; Spanish preferred, English fallback (abstract_language recorded)",
            "one_per_family": "family_id; if null or -1 the publication is its own family",
            "family_representative_order": "Spanish abstract first, then latest publication_date, then publication_number ASC",
            "ip_type": "utility_model if country ES and kind in (U, Y); patent otherwise",
        },
        "selection_sql_sha256": hashlib.sha256(SELECTION_SQL.encode()).hexdigest(),
        "built_at": datetime.now(UTC).isoformat(),
        "bytes_billed": job.total_bytes_billed,
        "total_records": len(rows),
        "by_ip_type": dict(Counter(r["ip_type"] for r in rows)),
        "by_country": dict(Counter(r["country_code"] for r in rows)),
        "by_abstract_language": dict(Counter(r["abstract_language"] for r in rows)),
        "by_publication_year": dict(sorted(Counter(r["publication_date"][:4] for r in rows).items())),
        "with_cpc": sum(1 for r in rows if r["cpc_codes"]),
        "parquet_sha256": _sha256(parquet_path),
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k.startswith(("total", "by_", "with_"))}, indent=2))


if __name__ == "__main__":
    main()
