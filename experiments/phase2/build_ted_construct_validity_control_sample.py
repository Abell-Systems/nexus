# experiments/phase2/build_ted_construct_validity_control_sample.py
"""TED construct-validity classifier, step 1: control-sample construction.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS4/SS5. Reads the frozen 114-candidate mapped population verbatim (no
re-mapping), computes the boundary stratum and a stratified fill to n=30,
writes a manifest for the blind labeling export (step 2) and LLM
classification run (step 3).
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.corpus.boundary_stratum import build_control_sample  # noqa: E402
from domain.models.corpus_expansion import calculate_canonical_word_count  # noqa: E402

MIN_WORD_COUNT = 25
TOLERANCE = 10
TARGET_SIZE = 30
SEED = 104


def generate(mapped_path: Path, accepted_path: Path, out_path: Path) -> dict[str, Any]:
    mapped = json.loads(mapped_path.read_text(encoding="utf-8"))
    accepted_ids = {c["demand_id"] for c in json.loads(accepted_path.read_text(encoding="utf-8"))}

    if len(mapped) != 114:
        raise ValueError(f"Expected 114 mapped candidates, found {len(mapped)}")

    candidates = [
        {
            "demand_id": c["demand_id"],
            "word_count": calculate_canonical_word_count(c["description_text"]),
            "status": "accepted" if c["demand_id"] in accepted_ids else "rejected",
            "language_code": c["language_code"],
        }
        for c in mapped
    ]

    sample = build_control_sample(
        candidates, min_word_count=MIN_WORD_COUNT, target_size=TARGET_SIZE, seed=SEED, tolerance=TOLERANCE
    )

    if len(sample.all_ids) != TARGET_SIZE:
        raise ValueError(f"Expected {TARGET_SIZE} total control-sample ids, got {len(sample.all_ids)}")
    if len(set(sample.all_ids)) != TARGET_SIZE:
        raise ValueError("Control sample contains duplicate demand_ids")

    mapped_bytes = mapped_path.read_bytes()
    out = {
        "dataset_id": "nexus-ted-construct-validity-control-sample-v1",
        "purpose": "TED construct-validity classifier control sample -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md",
        "source_mapped_candidates_path": str(mapped_path.relative_to(REPO_ROOT)),
        "source_mapped_candidates_sha256": hashlib.sha256(mapped_bytes).hexdigest(),
        "min_word_count": MIN_WORD_COUNT,
        "boundary_tolerance": TOLERANCE,
        "target_size": TARGET_SIZE,
        "seed": SEED,
        "n_boundary": len(sample.boundary_ids),
        "n_fill": len(sample.fill_ids),
        "boundary_ids": list(sample.boundary_ids),
        "fill_ids": list(sample.fill_ids),
        "all_ids": sorted(sample.all_ids),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {TARGET_SIZE} control-sample ids ({out['n_boundary']} boundary / {out['n_fill']} fill) to {out_path}")
    return out


def main() -> int:
    generate(
        mapped_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_mapped.json",
        accepted_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_accepted.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
