"""P1 (parity) and P2 (latency) of the ADR 0037 pre-registration. Throwaway."""
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

sys.path.insert(0, "backend/src/main")
from domain.models.matching import RetrievalMethod  # noqa: E402
from infrastructure.embeddings.embedding_texts import demand_embedding_text  # noqa: E402
from infrastructure.operational.artifacts import load_operational_artifacts  # noqa: E402

DIR = Path("data/snapshots/operational_corpus_v1")
DSN = "host=127.0.0.1 port=55432 user=postgres password=spike dbname=postgres"

DDL = """
DROP SCHEMA IF EXISTS operational_spike CASCADE; CREATE SCHEMA operational_spike; SET search_path=operational_spike,public;
CREATE TABLE asset(asset_id int PRIMARY KEY, publication_number text UNIQUE NOT NULL, country text NOT NULL, kind text NOT NULL,
  ip_type text NOT NULL, family_id text, title text NOT NULL, abstract text NOT NULL, abstract_language text,
  filing_date text, publication_date text);
CREATE TABLE asset_party(asset_id int REFERENCES asset, role text CHECK (role IN ('assignee','inventor')), ordinal int, name text,
  PRIMARY KEY(asset_id, role, ordinal));
CREATE TABLE asset_cpc(asset_id int REFERENCES asset, ordinal int, code text, PRIMARY KEY(asset_id, ordinal));
CREATE TABLE asset_embedding(asset_id int PRIMARY KEY REFERENCES asset, embedding vector(768) NOT NULL);
"""

SQL = """SELECT a.publication_number, round((((1 - (e.embedding <=> %s))+1)/2)::numeric, 6)::float8 AS score
FROM asset_embedding e JOIN eligible USING(asset_id) JOIN asset a USING(asset_id)
ORDER BY score DESC, a.publication_number ASC LIMIT %s"""


def p95(xs):
    return statistics.quantiles(xs, n=20)[-1]


def main():
    art = load_operational_artifacts(DIR)
    assets = art.catalog.list_all()
    from infrastructure.embeddings.frozen_embedding_index import load_index
    matrix = load_index(DIR, "embeddings_patents_v1").matrix
    eligible = [i for i, a in enumerate(assets) if art.policy.evaluate(a.patent, art.demands.list_all()[0]).is_eligible]
    out = {"n_assets": len(assets), "n_eligible": len(eligible)}
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        t0 = time.perf_counter()
        conn.execute(DDL)
        with conn.cursor() as cur:
            with cur.copy("COPY asset FROM STDIN") as cp:
                for i, a in enumerate(assets):
                    p = a.patent
                    cp.write_row((i, p.publication_id, p.country_code, p.kind_code, a.ip_type, p.family_id, p.title, p.abstract,
                                  a.abstract_language, p.filing_date, p.publication_date))
            with cur.copy("COPY asset_party FROM STDIN") as cp:
                for i, a in enumerate(assets):
                    for role, names in (("assignee", a.patent.assignees), ("inventor", a.patent.inventors)):
                        for k, n in enumerate(names):
                            cp.write_row((i, role, k, n))
            with cur.copy("COPY asset_cpc FROM STDIN") as cp:
                for i, a in enumerate(assets):
                    for k, c in enumerate(a.patent.classifications_cpc):
                        cp.write_row((i, k, c))
            with cur.copy("COPY asset_embedding FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int4", "vector"])
                for i in range(len(assets)):
                    cp.write_row((i, matrix[i]))
        out["load_seconds"] = round(time.perf_counter() - t0, 2)
        conn.execute("ANALYZE")
        conn.execute("CREATE TEMP TABLE eligible(asset_id int PRIMARY KEY)")
        with conn.cursor() as cur:
            with cur.copy("COPY eligible FROM STDIN") as cp:
                for i in eligible:
                    cp.write_row((i,))
        out["db_size_mb"] = conn.execute("SELECT pg_total_relation_size('asset_embedding')/1e6").fetchone()[0]

        mismatches, calls_sql, calls_np = [], [], []
        for d in art.demands.list_all():
            q = np.asarray(art.retriever._embedder.embed(demand_embedding_text(d.title, d.description)), dtype=np.float32)
            q = q / float(np.linalg.norm(q))
            for limit in (5, 100):
                ref = [(c.publication_id, c.retrieval_scores[RetrievalMethod.SEMANTIC]) for c in art.retriever.retrieve(d, limit=limit)]
                got = conn.execute(SQL, (q, limit)).fetchall()
                if [r[0] for r in ref] != [r[0] for r in got] or any(abs(a[1] - b[1]) > 0 for a, b in zip(ref, got)):
                    mismatches.append({"demand": d.demand_id, "limit": limit,
                                       "ids_equal": [r[0] for r in ref] == [r[0] for r in got],
                                       "max_score_diff": max((abs(a[1] - b[1]) for a, b in zip(ref, got)), default=0)})
            for _ in range(20):
                t = time.perf_counter(); conn.execute(SQL, (q, 5)).fetchall(); calls_sql.append(time.perf_counter() - t)
                t = time.perf_counter(); art.retriever.retrieve(d, limit=5); calls_np.append(time.perf_counter() - t)
        out["P1_cases"] = 2 * len(art.demands.list_all())
        out["P1_mismatches"] = mismatches
        out["P2_sql_p95_s"], out["P2_numpy_p95_s"] = round(p95(calls_sql), 4), round(p95(calls_np), 4)
        out["P2_sql_median_s"], out["P2_numpy_median_s"] = round(statistics.median(calls_sql), 4), round(statistics.median(calls_np), 4)
        out["plan"] = [r[0] for r in conn.execute("EXPLAIN " + SQL, (q, 5)).fetchall()][:6]
        out["plan"] = [x[:140] for x in out["plan"]]
        out["pg_version"] = conn.execute("SELECT version()").fetchone()[0]
    Path("experiments/adr-0037-db-spike/operational_raw.json").write_text(json.dumps(out, indent=2, default=str))
    print("done")


main()
