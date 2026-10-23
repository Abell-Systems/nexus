"""Targeted multiplicity checks for the ST36 inventory (ADR 0037 gate 2). Read-only, stdlib only; same traversal and preprocessing as st36_census.py."""
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def records(archive):
    for name in sorted(archive.namelist()):
        if name.endswith(".zip"):
            yield from records(zipfile.ZipFile(io.BytesIO(archive.read(name))))
        elif name.endswith(".xml"):
            yield archive.read(name)


def main(corpus: Path, out: Path):
    c = Counter()
    for zpath in sorted(corpus.glob("BIBLIO_*.zip")):
        with zipfile.ZipFile(zpath) as arc:
            for raw in records(arc):
                try:
                    root = ET.fromstring(CTRL.sub("", DOCTYPE.sub("", raw.decode("utf-8", "replace"))))
                except ET.ParseError:
                    continue
                c["records"] += 1
                apps = root.findall(".//application-reference/document-id")
                if len(apps) > 1:
                    c["app_ref_multi_records"] += 1
                    keys = {(a.findtext("country"), a.findtext("doc-number"), a.findtext("kind")) for a in apps}
                    dates = {a.findtext("date") for a in apps}
                    if len(keys) > 1:
                        c["app_ref_multi_differing_number"] += 1
                    if len(dates) > 1:
                        c["app_ref_multi_differing_date"] += 1
                containers = root.findall(".//classifications-ipcr")
                entries = root.findall(".//classification-ipcr")
                if len(containers) > 1:
                    c["ipc_multi_container_records"] += 1
                seqs = [e.get("sequence") for e in entries]
                if entries:
                    c["ipc_records"] += 1
                    if len(set(seqs)) != len(seqs):
                        c["ipc_sequence_not_unique_in_record"] += 1
                    if None in seqs or "" in seqs:
                        c["ipc_sequence_missing"] += 1
                    ints = [int(s) for s in seqs if s and s.isdigit()]
                    if ints != sorted(ints):
                        c["ipc_sequence_not_ascending_in_document_order"] += 1
                    levels = Counter((e.findtext("classification-level") or "", e.findtext("classification-value") or "") for e in entries)
                    for k, v in levels.items():
                        c[f"ipc_level_value:{k[0]}|{k[1]}"] += v
                    for e in entries:
                        for tag in ("section", "class", "subclass"):
                            if not (e.findtext(tag) or "").strip():
                                c[f"ipc_empty_{tag}_occurrences"] += 1
                prio = root.findall(".//priority-claim")
                for p in prio:
                    c[f"priority_kind:{p.get('kind')}"] += 1
                c["title_empty_records"] += 0 if (root.findtext(".//invention-title") or "").strip() else 1
    out.write_text(json.dumps(dict(sorted(c.items())), indent=1))
    print(c["records"])


main(Path(sys.argv[1]), Path(sys.argv[2]))
