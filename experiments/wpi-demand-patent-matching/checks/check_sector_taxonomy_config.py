#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 sector taxonomy config (#83).

Verifies phase2_sector_taxonomy_v1.json against its own sha256 sidecar and against
docs/phase2-sector-taxonomy-amendment.md's D1 table (the normative source). Does not
validate any classification -- none exists yet. This check certifies only that the
frozen taxonomy config still matches what #83 decided.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

CONFIG_NAME = "phase2_sector_taxonomy_v1.json"
CONFIG_SHA_NAME = "phase2_sector_taxonomy_v1.sha256"

# D1 table, docs/phase2-sector-taxonomy-amendment.md -- six closed categories.
EXPECTED_CODES = (
    "CONSUMER_CHEMISTRY",
    "SANITARY_MATERIALS",
    "INDUSTRIAL_MACHINERY_IOT",
    "ENERGY_STORAGE",
    "METALLURGY",
    "BIOTECHNOLOGY",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    config_path = CONFIG_DIR / CONFIG_NAME
    sidecar_path = CONFIG_DIR / CONFIG_SHA_NAME

    computed = _sha256(config_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{CONFIG_NAME}: bytes do not match {CONFIG_SHA_NAME}"
    assert declared_name == CONFIG_NAME

    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["taxonomy_id"] == "phase2_sector_taxonomy_v1"
    assert config["taxonomy_version"] == "v1"
    assert config["closed"] is True

    codes = [s["code"] for s in config["sectors"]]
    assert len(codes) == len(set(codes)), "Duplicate sector code in taxonomy config"
    assert set(codes) == set(EXPECTED_CODES), (
        f"Taxonomy config does not match #83's D1 table: got={sorted(codes)} "
        f"expected={sorted(EXPECTED_CODES)}"
    )
    for sector in config["sectors"]:
        assert sector["label"].strip()
        assert sector["traceable_to"].strip()

    amendment_path = REPO_ROOT / config["amendment_path"]
    amendment_computed = _sha256(amendment_path)
    assert amendment_computed == config["amendment_sha256"], (
        f"docs/phase2-sector-taxonomy-amendment.md changed since the taxonomy was frozen: "
        f"recorded={config['amendment_sha256']} actual={amendment_computed}. "
        "A changed amendment must not silently revalidate an already-frozen taxonomy config -- "
        "recompute deliberately, or version the taxonomy (phase2_sector_taxonomy_v2)."
    )

    print(f"OK: {len(codes)} sectors, taxonomy_version={config['taxonomy_version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
