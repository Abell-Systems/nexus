"""Nexus CLI entrypoint for ingestion and dataset operations."""

import argparse
from pathlib import Path
import sys

from application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
from application.ingestion.pipeline import IngestionPipeline
from application.ingestion.validator import PatentValidator, ValidationError
from infrastructure.sources.patent.oepm_raw_source import OepmRawSource
from infrastructure.storage.parquet_store import ParquetCanonicalStore
from infrastructure.storage.raw_store import FilesystemRawStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="Nexus 2.0 Ingestion & Scientific Research CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw patent data into canonical store")
    ingest_parser.add_argument(
        "--source-type",
        required=True,
        help="Source format adapter (e.g. oepm_bopi, oepm_open_data, oepm_raw)",
    )
    ingest_parser.add_argument(
        "--source-file",
        required=True,
        help="Path to raw source file",
    )
    ingest_parser.add_argument(
        "--dataset-id",
        required=True,
        help="Target canonical dataset ID",
    )
    ingest_parser.add_argument(
        "--output-dir",
        default="data",
        help="Base directory for raw, canonical, and snapshot outputs",
    )
    ingest_parser.add_argument(
        "--transformation-version",
        default="1.0.0",
        help="Schema transformation version string",
    )

    args = parser.parse_args(argv)

    if args.command == "ingest":
        source_path = Path(args.source_file)
        if not source_path.exists():
            print(f"Error: Source file not found: {args.source_file}", file=sys.stderr)
            return 1

        source_type = args.source_type.lower()
        if source_type not in ("oepm_bopi", "oepm", "oepm_raw", "oepm_open_data"):
            print(f"Error: Unsupported source-type: {args.source_type}", file=sys.stderr)
            return 1

        try:
            base_output = Path(args.output_dir)
            raw_store = FilesystemRawStore(base_dir=base_output / "raw")
            canonical_store = ParquetCanonicalStore(base_dir=base_output / "canonical")
            validator = PatentValidator()
            pipeline = IngestionPipeline(
                raw_store=raw_store,
                canonical_store=canonical_store,
                validator=validator,
            )

            source = OepmRawSource(file_path=source_path)
            normalizer = OepmNormalizer(extraction_version=args.transformation_version)

            manifest_dir = base_output / "canonical" / args.dataset_id
            summary = pipeline.ingest_patent_source(
                source=source,
                normalizer=normalizer,
                dataset_id=args.dataset_id,
                manifest_output_dir=manifest_dir,
                transformation_version=args.transformation_version,
            )

            print("Ingestion completed successfully.")
            print(f"Dataset ID: {summary.snapshot.dataset_id}")
            print(f"Records Ingested: {summary.processed_records}")
            print(f"Failed Records: {summary.error_count}")
            print(f"Dataset Content SHA-256: {summary.snapshot.dataset_content_sha256}")
            print(f"Manifest SHA-256: {summary.snapshot.manifest_sha256}")
            return 0
        except ValidationError as val_err:
            print(f"Validation Error: {val_err}", file=sys.stderr)
            return 1
        except Exception as err:
            print(f"Ingestion failed: {err}", file=sys.stderr)
            return 1

    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
