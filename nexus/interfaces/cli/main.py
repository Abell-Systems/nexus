"""Nexus Unified Command Line Interface (CLI).

Provides production and research commands for data ingestion, canonical dataset sealing,
opportunity analysis, and scientific experiment execution.
"""

import argparse
from pathlib import Path
import sys
from typing import Sequence

from nexus.application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
from nexus.application.ingestion.pipeline import IngestionPipeline, IngestionSummary
from nexus.application.ingestion.validator import PatentValidator, ValidationError
from nexus.infrastructure.sources.patent.oepm_raw_source import OepmRawSource
from nexus.infrastructure.storage.parquet_store import ParquetCanonicalStore
from nexus.infrastructure.storage.raw_store import FilesystemRawStore


SUPPORTED_SOURCE_TYPES = {"oepm_bopi", "oepm", "oepm_raw", "oepm_open_data"}


def handle_ingest(args: argparse.Namespace) -> int:
    """Handle 'nexus ingest' command execution."""
    source_type = args.source_type.lower()
    if source_type not in SUPPORTED_SOURCE_TYPES:
        sys.stderr.write(
            f"Error: Unsupported source type '{args.source_type}'. "
            f"Supported source types: {', '.join(sorted(SUPPORTED_SOURCE_TYPES))}\n"
        )
        return 1

    source_file = Path(args.source_file)
    if not source_file.exists():
        sys.stderr.write(f"Error: Source file does not exist: {source_file}\n")
        return 1

    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    canonical_dir = output_dir / "canonical"
    snapshots_dir = output_dir / "snapshots"

    raw_store = FilesystemRawStore(base_dir=raw_dir)
    canonical_store = ParquetCanonicalStore(base_dir=canonical_dir)
    validator = PatentValidator()
    pipeline = IngestionPipeline(
        raw_store=raw_store,
        canonical_store=canonical_store,
        validator=validator,
    )

    try:
        source = OepmRawSource(
            file_path=source_file,
            source_id=args.source_type,
            batch_id="batch_0001",
        )
        normalizer = OepmNormalizer(extraction_version=args.transformation_version)

        summary: IngestionSummary = pipeline.ingest_patent_source(
            source=source,
            normalizer=normalizer,
            dataset_id=args.dataset_id,
            manifest_output_dir=snapshots_dir,
            transformation_version=args.transformation_version,
        )

        manifest_path = snapshots_dir / f"{args.dataset_id}_manifest.json"
        print(f"✅ Ingestion successfully completed for dataset: {args.dataset_id}")
        print(f"   - Processed Records:       {summary.processed_records}")
        print(f"   - Dataset Content SHA256:  {summary.snapshot.dataset_content_sha256}")
        print(f"   - Manifest SHA256:         {summary.snapshot.manifest_sha256}")
        print(f"   - Manifest File:           {manifest_path}")
        print(f"   - Canonical Storage:       {canonical_dir / args.dataset_id}")
        return 0

    except ValidationError as e:
        sys.stderr.write(f"Error: Ingestion validation failure: {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"Error: Ingestion execution error: {e}\n")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="Nexus: Autonomous Patent Intelligence & Scientific Research Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Ingest subcommand
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest raw patent data into immutable raw store, normalize, validate, and seal canonical dataset",
    )
    ingest_parser.add_argument(
        "--source-type",
        required=True,
        help="Source type identifier (e.g. 'oepm_bopi', 'oepm', 'oepm_raw')",
    )
    ingest_parser.add_argument(
        "--source-file",
        required=True,
        help="Path to raw source file (e.g. data/raw/oepm_open_data_es.json)",
    )
    ingest_parser.add_argument(
        "--dataset-id",
        required=True,
        help="Canonical dataset identifier (e.g. patents_es_v1)",
    )
    ingest_parser.add_argument(
        "--output-dir",
        required=True,
        help="Base directory for output storage (creates raw/, canonical/, snapshots/)",
    )
    ingest_parser.add_argument(
        "--transformation-version",
        default="1.0.0",
        help="Transformation logic version string (default: '1.0.0')",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help(sys.stderr)
        return 1

    if args.command == "ingest":
        return handle_ingest(args)

    sys.stderr.write(f"Error: Unknown command '{args.command}'\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
