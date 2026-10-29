#!/usr/bin/env python3
"""Copies the versioned results of the white-space study into the frontend as static data, with a provenance manifest.

The browser recomputes nothing: it draws what these files state. The frontend tests require the copies to be identical
to the originals and the recorded hashes to be those of the copies (JS/TS tooling stays inside the frontend workspace,
ADR 0021, so this step is a Python script).

  python scripts/sync_whitespace_frontend_data.py [--target frontend/src/main/infrastructure/data] [--public-target frontend/public/data]

The subclass pairs (6 MB) and the unobserved pairs (2.8 MB) are not bundled: they are copied under `public/` and fetched on demand as static files.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    {
        "source": "docs/whitespace/oepm-corpus-exposure-results.json",
        "producedBy": "scripts/report_oepm_corpus_exposure.py",
        "pullRequest": 140,
    },
    {
        "source": "docs/whitespace/oepm-omission-sensitivity-results.json",
        "producedBy": "scripts/report_oepm_omission_sensitivity.py",
        "pullRequest": 141,
    },
    {
        "source": "docs/whitespace/oepm-section-density-results.json",
        "producedBy": "scripts/report_oepm_section_density.py",
        "pullRequest": 142,
    },
    {
        "source": "config/whitespace/oepm_biblio_2000_2025.json",
        "producedBy": "scripts/reproduce_oepm_biblio_characterization.py",
        "pullRequest": 130,
    },
]
ON_DEMAND_SOURCES = [
    {
        "source": "docs/whitespace/oepm-subclass-pairs-results.json",
        "producedBy": "scripts/report_oepm_subclass_pairs.py",
        "pullRequest": 150,
    },
    {
        "source": "docs/whitespace/oepm-unobserved-pairs-results.json",
        "producedBy": "scripts/report_oepm_unobserved_pairs.py",
        "pullRequest": 180,
    },
]


def _topic_map_sources(root: Path) -> list[dict]:
    """Topic maps are served on demand when their result exists; absent ones are skipped."""
    return [
        {"source": path.relative_to(root).as_posix(), "producedBy": "scripts/report_topic_map.py"}
        for path in sorted((root / "docs" / "whitespace").glob("topic-map-*.json"))
    ]


def sync(target: Path, public_target: Path, root: Path = REPO_ROOT) -> dict:
    files = []
    on_demand = ON_DEMAND_SOURCES + _topic_map_sources(root)
    for entries, destination, served in ((SOURCES, target, "bundled"), (on_demand, public_target, "on_demand")):
        destination.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            name = Path(entry["source"]).name
            shutil.copyfile(root / entry["source"], destination / name)
            data = (destination / name).read_bytes()
            files.append(
                {
                    "file": name,
                    **entry,
                    "served": served,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    manifest = {"files": files}
    (target / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--target", type=Path, default=REPO_ROOT / "frontend" / "src" / "main" / "infrastructure" / "data"
    )
    parser.add_argument("--public-target", type=Path, default=REPO_ROOT / "frontend" / "public" / "data")
    args = parser.parse_args()
    manifest = sync(args.target, args.public_target)
    print(f"copied {len(manifest['files'])} result files and wrote provenance.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
