"""Census of every element path and attribute in the OEPM ST36 records (ADR 0037 gate 2). Read-only, stdlib only.

Same traversal and same pre-processing as infrastructure/sources/patent/oepm_biblio.py (DOCTYPE removed, control characters
removed); records that do not parse are counted, not inspected. For each element path: records containing it, total
occurrences, maximum occurrences in one record, records where its own text is non-empty, and its attributes.
"""
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def records(archive):
    for name in sorted(archive.namelist()):
        if name.endswith(".zip"):
            yield from records(zipfile.ZipFile(io.BytesIO(archive.read(name))))
        elif name.endswith(".xml"):
            yield archive.read(name)


def walk(el, path, per_record, text_nonempty, attrs, seen_text):
    p = f"{path}/{el.tag}"
    per_record[p] += 1
    if (el.text or "").strip():
        seen_text.add(p)
    for a in el.attrib:
        attrs[p][a] += 1
    for child in el:
        walk(child, p, per_record, text_nonempty, attrs, seen_text)


def main(corpus: Path, out: Path):
    records_with, total, maxper, textrec = Counter(), Counter(), Counter(), Counter()
    attrs = defaultdict(Counter)
    n = unparsed = 0
    for zpath in sorted(corpus.glob("BIBLIO_*.zip")):
        with zipfile.ZipFile(zpath) as arc:
            for raw in records(arc):
                n += 1
                try:
                    root = ET.fromstring(CTRL.sub("", DOCTYPE.sub("", raw.decode("utf-8", "replace"))))
                except ET.ParseError:
                    unparsed += 1
                    continue
                per, seen_text = Counter(), set()
                walk(root, "", per, None, attrs, seen_text)
                for p, c in per.items():
                    records_with[p] += 1; total[p] += c; maxper[p] = max(maxper[p], c)
                for p in seen_text:
                    textrec[p] += 1
    result = {"records": n, "unparsed": unparsed, "paths": {
        p: {"records": records_with[p], "total": total[p], "max_per_record": maxper[p], "records_with_text": textrec[p],
            "attributes": dict(attrs[p])} for p in sorted(records_with)}}
    out.write_text(json.dumps(result, indent=1))
    print(n, unparsed, len(result["paths"]))


main(Path(sys.argv[1]), Path(sys.argv[2]))
