"""P3 (load + equivalence) and P4 (report time) of the ADR 0037 pre-registration. Throwaway."""
import json
import sys
import time
from datetime import date
from pathlib import Path

import psycopg

sys.path.insert(0, "backend/src/main")
from application.whitespace.analysis_records import AnalysisRecord  # noqa: E402
from application.whitespace.corpus_report import kind_group  # noqa: E402
from application.whitespace.subclass_pairs import subclass_pairs  # noqa: E402
from application.whitespace.analysis_records import to_analysis_records  # noqa: E402
from domain.models.whitespace import PatentPublication, RejectedRecord  # noqa: E402
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource  # noqa: E402

DSN = "host=127.0.0.1 port=55432 user=postgres password=spike dbname=postgres"
CORPUS = Path("data/raw/oepm_open")
FIGURES = json.loads(Path("config/whitespace/oepm_biblio_2000_2025.json").read_text())["files"]
EXPECTED = json.loads(Path("docs/whitespace/oepm-subclass-pairs-results.json").read_text())

DDL = """
DROP SCHEMA IF EXISTS biblio_spike CASCADE; CREATE SCHEMA biblio_spike; SET search_path=biblio_spike,public;
CREATE TABLE source_file(file_id int PRIMARY KEY, name text UNIQUE NOT NULL, sha256 text NOT NULL, bytes bigint NOT NULL);
CREATE TABLE source_record(record_id int PRIMARY KEY, file_id int NOT NULL REFERENCES source_file, archive_path text NOT NULL,
  UNIQUE(file_id, archive_path));
CREATE TABLE publication(record_id int PRIMARY KEY REFERENCES source_record, country text NOT NULL, doc_number text NOT NULL,
  kind text NOT NULL, publication_date date NOT NULL, application_country text, application_number text, application_kind text,
  application_date date, title text NOT NULL, doc_id text GENERATED ALWAYS AS (country||doc_number||kind) STORED);
CREATE TABLE priority_date(record_id int REFERENCES publication, ordinal int, priority_date date NOT NULL, PRIMARY KEY(record_id, ordinal));
CREATE TABLE party(record_id int REFERENCES publication, role text CHECK (role IN ('applicant','inventor')), ordinal int, name text,
  PRIMARY KEY(record_id, role, ordinal));
CREATE TABLE ipc_subclass(symbol text PRIMARY KEY, section text, class_number text, subclass text);
CREATE TABLE ipc_entry(record_id int REFERENCES publication, ordinal int, subclass_symbol text NOT NULL REFERENCES ipc_subclass,
  main_group text, subgroup text, version text, level text, value text, PRIMARY KEY(record_id, ordinal));
CREATE TABLE anomaly(record_id int REFERENCES publication, ordinal int, field text, raw_value text, reason text, PRIMARY KEY(record_id, ordinal));
CREATE TABLE rejected_record(file_id int REFERENCES source_file, archive_path text, reason text, PRIMARY KEY(file_id, archive_path));
"""
INDEXES = """CREATE INDEX ON ipc_entry(subclass_symbol, record_id); CREATE INDEX ON publication(publication_date);
CREATE INDEX ON publication(application_country, application_number); ANALYZE;"""


def main():
    out = {}
    t0 = time.perf_counter()
    source = OepmBiblioSource(CORPUS, {n: f["sha256"] for n, f in FIGURES.items()})
    outcomes = list(source.read())
    out["parse_seconds"] = round(time.perf_counter() - t0, 1)
    t_zip = time.perf_counter()
    records = to_analysis_records(outcomes)
    for origin in (2006, 2022):
        subclass_pairs(records, origin)
    out["P4_from_zips_seconds_parse_plus_report"] = round(out["parse_seconds"] + time.perf_counter() - t_zip, 1)
    out["P4_report_only_seconds_in_memory"] = round(time.perf_counter() - t_zip, 1)

    file_id = {n: i for i, n in enumerate(sorted(FIGURES))}
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(DDL)
        t0 = time.perf_counter()
        with conn.cursor() as cur:
            with cur.copy("COPY source_file FROM STDIN") as cp:
                for n, i in file_id.items():
                    cp.write_row((i, n, FIGURES[n]["sha256"], FIGURES[n]["bytes"]))
            syms = {}
            for o in outcomes:
                if isinstance(o, PatentPublication):
                    for e in o.ipc_entries:
                        syms[e.subclass_symbol] = (e.section, e.class_number, e.subclass)
            with cur.copy("COPY ipc_subclass FROM STDIN") as cp:
                for s, v in sorted(syms.items()):
                    cp.write_row((s, *v))
            rid = 0
            rows = {k: [] for k in ("rec", "pub", "prio", "party", "ipc", "anom", "rej")}
            for o in outcomes:
                pv = o.provenance
                if isinstance(o, RejectedRecord):
                    rows["rej"].append((file_id[pv.source_file], pv.archive_path, o.reason))
                    continue
                rid += 1
                a = o.application_reference
                rows["rec"].append((rid, file_id[pv.source_file], pv.archive_path))
                rows["pub"].append((rid, o.country, o.doc_number, o.kind, o.publication_date, a.country if a else None,
                                    a.number if a else None, a.kind if a else None, o.application_date, o.title))
                rows["prio"] += [(rid, k, d) for k, d in enumerate(o.priority_dates)]
                rows["party"] += [(rid, "applicant", k, n) for k, n in enumerate(o.applicants)]
                rows["party"] += [(rid, "inventor", k, n) for k, n in enumerate(o.inventors)]
                rows["ipc"] += [(rid, k, e.subclass_symbol, e.main_group, e.subgroup, e.version, e.level, e.value)
                                for k, e in enumerate(o.ipc_entries)]
                rows["anom"] += [(rid, k, x.field, x.raw_value, x.reason) for k, x in enumerate(o.anomalies)]
            for table, key in (("source_record", "rec"), ("publication", "pub"), ("priority_date", "prio"), ("party", "party"),
                               ("ipc_entry", "ipc"), ("anomaly", "anom"), ("rejected_record", "rej")):
                with cur.copy(f"COPY {table} FROM STDIN") as cp:
                    for r in rows[key]:
                        cp.write_row(r)
        conn.execute(INDEXES)
        out["P3_load_seconds"] = round(time.perf_counter() - t0, 1)
        q = lambda s: conn.execute(s).fetchone()[0]  # noqa: E731
        out["P3_checks"] = {
            "publications": (q("SELECT count(*) FROM publication"), 711547),
            "rejected": (q("SELECT count(*) FROM rejected_record"), 341),
            "subclasses": (q("SELECT count(*) FROM ipc_subclass"), 660),
            "without_ipc": (q("SELECT count(*) FROM publication p WHERE NOT EXISTS (SELECT 1 FROM ipc_entry e WHERE e.record_id=p.record_id)"), 2749),
            "distinct_doc_id": (q("SELECT count(DISTINCT doc_id) FROM publication"), 707985),
        }
        out["db_size_mb"] = q("SELECT pg_database_size('postgres')/1e6")

        # the port: record-level rows from SQL into the existing AnalysisRecord, then the existing code computes the metrics
        t0 = time.perf_counter()
        cur = conn.execute("""SELECT p.record_id, p.country||p.doc_number||p.kind, p.kind, p.publication_date, p.application_date,
            (SELECT min(priority_date) FROM priority_date d WHERE d.record_id=p.record_id),
            coalesce((SELECT array_agg(DISTINCT subclass_symbol ORDER BY subclass_symbol) FROM ipc_entry e WHERE e.record_id=p.record_id), '{}')
            FROM publication p ORDER BY p.record_id""")
        sql_records = []
        for _, doc_id, kind, pub, app, prio, subs in cur:
            dates = [d for d in (prio, app) if d]
            sql_records.append(AnalysisRecord(doc_id, pub, kind_group(kind), min(dates).year if dates else None, tuple(subs), kind))
        res = {}
        for origin in (2006, 2022):
            res[str(origin)] = subclass_pairs(sql_records, origin)
        out["P4_from_db_seconds_read_plus_report"] = round(time.perf_counter() - t0, 1)
        out["P3_records_identical_to_adapter_path"] = sql_records == records
        out["P3_pairs_equal_versioned_json"] = {
            o: json.loads(json.dumps(res[o])) == EXPECTED[o] for o in res}
        out["P3_observed_pairs"] = {o: len(res[o]["pairs"]) for o in res}
    print(json.dumps(out, indent=2, default=str))


main()
