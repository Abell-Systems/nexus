#!/usr/bin/env python3
"""Copies the versioned results of the white-space study into the frontend as static data, with a provenance manifest.

The browser recomputes nothing: it draws what these files state. The frontend tests require the copies to be identical
to the originals and the recorded hashes to be those of the copies (JS/TS tooling stays inside the frontend workspace,
ADR 0021, so this step is a Python script).

  python scripts/sync_whitespace_frontend_data.py [--target frontend/src/main/infrastructure/data]
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


def sync(target: Path, root: Path = REPO_ROOT) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    files = []
    for entry in SOURCES:
        name = Path(entry["source"]).name
        shutil.copyfile(root / entry["source"], target / name)
        data = (target / name).read_bytes()
        files.append({"file": name, **entry, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"files": files}
    (target / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--target", type=Path, default=REPO_ROOT / "frontend" / "src" / "main" / "infrastructure" / "data"
    )
    args = parser.parse_args()
    manifest = sync(args.target)
    print(f"copied {len(manifest['files'])} result files and wrote provenance.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
