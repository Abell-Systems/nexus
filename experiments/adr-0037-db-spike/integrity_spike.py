"""P5 of the ADR 0037 pre-registration (amendment A1): content digest and refusal on a loaded biblio_spike. Throwaway.

Limitation, stated up front: there is no real loader yet, so "re-run the loader with an altered source row" is simulated by
loading a copy of the stored rows inside one transaction, altering one row, and verifying that copy against the manifest.
"""
import hashlib
import json
import time
from pathlib import Path

import psycopg

DSN = "host=127.0.0.1 port=55432 user=postgres password=spike dbname=postgres"
TABLES = [("source_file", "file_id"), ("source_record", "record_id"), ("publication", "record_id"),
          ("priority_date", "record_id, ordinal"), ("party", "record_id, role, ordinal"), ("ipc_subclass", "symbol"),
          ("ipc_entry", "record_id, ordinal"), ("anomaly", "record_id, ordinal"), ("rejected_record", "file_id, archive_path")]


def digest(conn, schema):
    """sha256 over the per-table digests; each table = rows as canonical jsonb text, ordered by primary key."""
    parts = []
    for table, key in TABLES:
        (d,) = conn.execute(
            f"SELECT encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text, E'\\n' ORDER BY {key}), ''), 'UTF8')), 'hex') "
            f"FROM {schema}.{table} t").fetchone()
        parts.append(f"{table}:{d}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def main():
    out = {}
    with psycopg.connect(DSN, autocommit=True) as conn:
        t = time.perf_counter()
        d0 = digest(conn, "biblio_spike")
        out["digest_seconds"] = round(time.perf_counter() - t, 1)
        conn.execute("DROP TABLE IF EXISTS biblio_spike.manifest; CREATE TABLE biblio_spike.manifest(version text PRIMARY KEY, content_sha256 text NOT NULL)")
        conn.execute("INSERT INTO biblio_spike.manifest VALUES ('biblio_v1', %s)", (d0,))
        out["digest"] = d0
        out["deterministic"] = digest(conn, "biblio_spike") == d0
        conn.execute("CLUSTER biblio_spike.ipc_entry USING ipc_entry_pkey")
        out["stable_after_physical_reorder"] = digest(conn, "biblio_spike") == d0

        # (a) a second load of identical rows (a copy in another schema) has the same digest -> loader would do nothing
        conn.execute("DROP SCHEMA IF EXISTS biblio_copy CASCADE; CREATE SCHEMA biblio_copy")
        for table, _ in TABLES:
            conn.execute(f"CREATE TABLE biblio_copy.{table} AS SELECT * FROM biblio_spike.{table}")
        out["a_identical_copy_same_digest"] = digest(conn, "biblio_copy") == d0

        # (c) UPDATE of one row in place changes the digest; restoring it restores it
        conn.execute("UPDATE biblio_copy.ipc_entry SET subclass_symbol = (SELECT symbol FROM biblio_spike.ipc_subclass WHERE symbol <> "
                     "(SELECT subclass_symbol FROM biblio_copy.ipc_entry WHERE record_id=1 AND ordinal=0) LIMIT 1) WHERE record_id=1 AND ordinal=0")
        out["c_digest_differs_after_one_row_update"] = digest(conn, "biblio_copy") != d0
        out["manifest_untouched"] = conn.execute("SELECT content_sha256 FROM biblio_spike.manifest").fetchone()[0] == d0
        conn.execute("DROP SCHEMA biblio_copy CASCADE")

        # (b) refusal leaves nothing: load a copy inside one transaction, alter one row, verify against the manifest, ROLLBACK on mismatch
        rel = "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema','pg_toast')"
        rels_before = conn.execute(rel).fetchone()[0]
        conn.autocommit = False
        try:
            conn.execute("CREATE SCHEMA biblio_v1_candidate")
            for table, _ in TABLES:
                conn.execute(f"CREATE TABLE biblio_v1_candidate.{table} AS SELECT * FROM biblio_spike.{table}")
            conn.execute("UPDATE biblio_v1_candidate.publication SET title = title || 'x' WHERE record_id = 1")
            refused = digest(conn, "biblio_v1_candidate") != d0
            if refused:
                conn.rollback()
            else:
                conn.commit()
        finally:
            conn.autocommit = True
        out["b_altered_load_refused"] = refused
        out["b_relations_before_after"] = [rels_before, conn.execute(rel).fetchone()[0]]
        out["b_nothing_left_after_refusal"] = out["b_relations_before_after"][0] == out["b_relations_before_after"][1] and conn.execute(
            "SELECT count(*) FROM information_schema.schemata WHERE schema_name='biblio_v1_candidate'").fetchone()[0] == 0
    Path("experiments/adr-0037-db-spike/integrity_raw.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


main()
