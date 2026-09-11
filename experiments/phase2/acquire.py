"""Acquire CLI runner for Phase-2 demand corpus expansion (ADR 0032)."""

import argparse
import json
import logging
import sys
from pathlib import Path

from experiments.phase2.harvesters import (
    BaseHarvester,
    EenPodHarvester,
    InnogetHarvester,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("experiments.phase2.acquire")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Harvester runner for Phase-2 demand corpus expansion raw staging (ADR 0032)."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/raw/phase2_candidates"),
        help="Target output directory for immutable raw payloads and sidecars.",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="innoget,een_pod",
        help="Comma-separated list of sources to harvest (e.g. 'innoget,een_pod').",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of payloads to harvest per source.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pagination pages to crawl per source.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Polite pacing delay in seconds between requests (default: 1.0).",
    )
    parser.add_argument(
        "--errors-file",
        type=Path,
        default=Path("data/experiments/phase2/acquisition_errors.json"),
        help="Destination path to persist operational acquisition errors log.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]

    all_errors: list[dict] = []
    total_acquired = 0

    for source in sources:
        logger.info("Beginning harvesting for source: %s", source)
        harvester: BaseHarvester
        if source == "innoget":
            harvester = InnogetHarvester(delay_seconds=args.delay)
        elif source in ("een_pod", "een", "lombardia"):
            harvester = EenPodHarvester(delay_seconds=args.delay)
        else:
            logger.error("Unknown source: %s (supported: innoget, een_pod)", source)
            continue

        try:
            acquired = harvester.harvest(
                out_dir=out_dir,
                max_pages=args.max_pages,
                limit=args.limit,
            )
            total_acquired += len(acquired)
            logger.info("Acquired %d payloads from %s", len(acquired), source)
        except Exception as exc:
            logger.exception("Harvester execution failed for %s: %s", source, exc)
            harvester.record_error(
                source_id=source,
                uri=getattr(harvester, "listing_base", getattr(harvester, "base_url", "unknown")),
                error_type=type(exc).__name__,
                message=str(exc),
            )

        all_errors.extend(harvester.acquisition_errors)

    if all_errors:
        args.errors_file.parent.mkdir(parents=True, exist_ok=True)
        args.errors_file.write_text(
            json.dumps(all_errors, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        logger.warning(
            "Encountered %d acquisition error(s); recorded to %s",
            len(all_errors),
            args.errors_file,
        )

    logger.info("Harvest complete. Total payloads acquired across all sources: %d", total_acquired)
    return 0


if __name__ == "__main__":
    sys.exit(main())
