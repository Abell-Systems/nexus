"""Entry point of the ADR 0037 gate 1 benchmark.

It refuses to run (exit 2) unless AUTHORISATION.json exists and matches the protocol in force (harness/guard.py). The part below the
barrier has been exercised only on synthetic data in tests/; it has never been run on the real corpus.

Return codes: 0 every graded check passed, 1 a check failed, 2 refused, 3 environment incident unresolved.
Usage (after authorisation): python run_benchmark.py --work-dir DIR --pg-dsn DSN --container NAME [--only A|B]
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src" / "main"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.contract import EXIT_REFUSED  # noqa: E402
from harness.guard import NotAuthorised, require_authorisation  # noqa: E402


def build_real_context(args, authorisation: dict):
    sys.path.insert(0, str(REPO / "backend" / "src" / "main"))
    from application.whitespace.analysis_records import to_analysis_records
    from application.whitespace.subclass_pairs import subclass_pairs
    from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

    from harness.recorder import Recorder
    from harness.store_files import FilesStore
    from harness.store_pg import PostgresStore
    from harness.tables import rows_from_outcomes
    from harness.workloads import Context, Reference

    figures = json.loads((REPO / "config/whitespace/oepm_biblio_2000_2025.json").read_text())["files"]
    outcomes = list(OepmBiblioSource(args.corpus_dir, {n: f["sha256"] for n, f in figures.items()}).read())  # shared input, hashes verified
    rows = rows_from_outcomes(outcomes, figures)
    records = to_analysis_records(outcomes)
    expected = json.loads((REPO / "docs/whitespace/oepm-subclass-pairs-results.json").read_text())
    reference = Reference(rows=rows, records=records, pairs_expected=expected, pairs_fn=subclass_pairs,
                          load_checks_expected=__import__("harness.compare", fromlist=["LOAD_CHECKS"]).LOAD_CHECKS)
    stores = {}
    if args.only in (None, "A"):
        stores["A"] = PostgresStore(args.pg_dsn, args.container, "bench")
    if args.only in (None, "B"):
        stores["B"] = FilesStore(Path(args.work_dir) / "files")
    return Context(stores=stores, reference=reference, recorder=Recorder(), sink=Path(args.work_dir) / "raw.jsonl")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--corpus-dir", type=Path, default=REPO / "data/raw/oepm_open")
    parser.add_argument("--operational-dir", type=Path, default=REPO / "data/snapshots/operational_corpus_v1")
    parser.add_argument("--pg-dsn", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--only", choices=["A", "B"])
    try:
        authorisation = require_authorisation()
    except NotAuthorised as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    args = parser.parse_args(argv)
    args.work_dir.mkdir(parents=True, exist_ok=True)

    from harness.contract import EXIT_INCIDENT
    from harness.session import capture_environment
    from harness.workloads import evaluate, run_biblio_session

    closers: list = []
    try:
        ctx = build_real_context(args, authorisation)
        alts = tuple(ctx.stores)
        (args.work_dir / "environment.json").write_text(
            json.dumps({"authorisation": authorisation, **capture_environment(ctx.stores)}, indent=1, default=str))
        results = run_biblio_session(ctx, args.work_dir / "backups", alternatives=alts)
        from harness.operational import build_real_operational, w7_operational

        retrievers, demands, vectors, closers = build_real_operational(args.operational_dir, args.pg_dsn, "bench", alts)
        w7_operational(ctx, retrievers, demands, vectors)
    except Exception:  # noqa: BLE001 - setup or session failure: an incident, never a graded result
        import traceback

        (args.work_dir / "incident.json").write_text(json.dumps({"traceback": traceback.format_exc()}, indent=1))
        print("incident: see incident.json", file=sys.stderr)
        return EXIT_INCIDENT
    finally:
        for close in closers:
            try:
                close()
            except Exception:  # noqa: BLE001
                pass
    code, table = evaluate(ctx.results, alts)
    (args.work_dir / "summary.json").write_text(json.dumps(table, indent=1, default=str))
    ctx.recorder.save(args.work_dir / "timings.json")
    print(json.dumps(table, indent=1, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
