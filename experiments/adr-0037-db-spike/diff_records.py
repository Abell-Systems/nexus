"""Why are the records read back from the database not identical to the adapter's? Throwaway diagnostic."""
import sys
from collections import Counter
from pathlib import Path
import json
import psycopg
sys.path.insert(0, "backend/src/main")
from application.whitespace.analysis_records import AnalysisRecord, to_analysis_records  # noqa: E402
from application.whitespace.corpus_report import kind_group  # noqa: E402
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource  # noqa: E402

F = json.loads(Path("config/whitespace/oepm_biblio_2000_2025.json").read_text())["files"]
records = to_analysis_records(OepmBiblioSource(Path("data/raw/oepm_open"), {n: f["sha256"] for n, f in F.items()}).read())
with psycopg.connect("host=127.0.0.1 port=55432 user=postgres password=spike dbname=postgres") as conn:
    conn.execute("SET search_path=biblio_spike")
    rows = conn.execute("""SELECT p.country||p.doc_number||p.kind, p.kind, p.publication_date, p.application_date,
      (SELECT min(priority_date) FROM priority_date d WHERE d.record_id=p.record_id),
      coalesce((SELECT array_agg(DISTINCT subclass_symbol ORDER BY subclass_symbol) FROM ipc_entry e WHERE e.record_id=p.record_id),'{}')
      FROM publication p ORDER BY p.record_id""").fetchall()
sql = []
for doc_id, kind, pub, app, prio, subs in rows:
    dates = [d for d in (prio, app) if d]
    sql.append(AnalysisRecord(doc_id, pub, kind_group(kind), min(dates).year if dates else None, tuple(subs), kind))
print("len", len(records), len(sql))
fields = AnalysisRecord._fields
diff = Counter(); first = {}
for i, (a, b) in enumerate(zip(records, sql)):
    for f, x, y in zip(fields, a, b):
        if x != y:
            diff[f] += 1; first.setdefault(f, (i, x, y))
print("differing fields:", dict(diff)); print("first examples:", first)
print("same multiset ignoring order:", Counter(records) == Counter(sql))
