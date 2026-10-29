#!/usr/bin/env python3
"""Per-topic result of the topic map (spec sections 5, 6 and 8): aggregates over O4 units, no per-document data.

The corpus is read through the adapter after its hashes are verified, and its four counts are checked against the
manifest before anything is computed. A topic with unreviewed plain names is refused unless --allow-unreviewed, and
then the result says names_reviewed: false.

  python scripts/report_topic_map.py --topic baterias --corpus-dir data/raw/oepm_open --write FILE [--allow-unreviewed]
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import AnalysisRecord, to_analysis_records
from application.whitespace.applicant_names import load_rules
from application.whitespace.omission_sensitivity_2025 import check_manifest_counts
from application.whitespace.topic_definition import load_definition
from application.whitespace.topic_map import build_topic_result
from application.whitespace.topic_units import o4_units
from domain.models.whitespace import RejectedRecord
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
TOPICS = REPO_ROOT / "config" / "topics"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--topic", required=True)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path, required=True)
    parser.add_argument("--allow-unreviewed", action="store_true")
    return parser.parse_args(argv)


def read_corpus(corpus_dir: Path) -> tuple[list[AnalysisRecord], dict]:
    figures = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))
    files = {n: f["sha256"] for n, f in figures["files"].items()}
    outcomes = list(OepmBiblioSource(corpus_dir, files).read())
    rejected = sum(isinstance(o, RejectedRecord) for o in outcomes)
    records = to_analysis_records(outcomes)
    check_manifest_counts(len(outcomes), rejected, len(records), len(o4_units(records)), figures["figures"])
    return records, {"source_id": figures["source_id"], "files": files}


def build_for_topic(topic_key: str, records: list[AnalysisRecord], corpus: dict, allow_unreviewed: bool) -> dict:
    definition = load_definition(TOPICS / f"{topic_key}.json")
    rules = load_rules(TOPICS / "applicant_rules.json")
    return build_topic_result(records, definition, rules, corpus, allow_unreviewed=allow_unreviewed)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records, corpus = read_corpus(args.corpus_dir)
    result = build_for_topic(args.topic, records, corpus, args.allow_unreviewed)
    args.write.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        args.topic,
        result["total_documents"],
        "documents of",
        result["corpus_documents"],
        "; names reviewed:",
        result["names_reviewed"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
