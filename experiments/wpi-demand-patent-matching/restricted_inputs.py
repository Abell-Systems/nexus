"""Where the scripts of this experiment find the original demand corpus and its derivatives.

The original N=39 demand corpus carries third-party text (Innoget, Open Innovation Lombardia) and is no longer
tracked in the public repository (docs/data-acquisition/third-party-files-d1-inventory.md). The scripts read it
from WPI_DATA_DIR, by default `restricted/data/` next to this file (git-ignored). If it is not there they stop with a
message: they never fall back to other data and never produce a different artefact silently.
"""

import json
import os
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = EXPERIMENT_DIR / "restricted" / "data"
CORPUS = "dataset_phase2_demand_corpus_n39.json"
# Files of the original study that carry demand text; retired from the public tree.
RESTRICTED_FILES = (
    CORPUS,
    "dataset_phase2_demand_corpus_n39.origin_audit.json",
    "dataset_phase2_eligible_corpus_n24_v1.json",
    "dataset_phase2_organization_audited_corpus_v1.json",
    "phase2_demand_construct_eligibility_n39_v1.json",
    "sector_assignments_n24_v1.json",
)
EVIDENCE_QUOTES = "evidence_quotes.json"


def data_dir(required: tuple[str, ...] = RESTRICTED_FILES + (EVIDENCE_QUOTES,)) -> Path:
    """The directory holding the study data; exits with an explicit message if `required` is not all there."""
    directory = Path(os.environ.get("WPI_DATA_DIR") or DEFAULT_DATA_DIR)
    missing = [name for name in required if not (directory / name).is_file()]
    if missing:
        raise SystemExit(
            f"Original demand corpus not available in {directory}: missing {', '.join(missing)}.\n"
            "These files contain third-party text and are not in the public repository. Provide a copy you are "
            "entitled to hold by setting WPI_DATA_DIR (or placing it in restricted/data/). The hashes of the original "
            "files are recorded in data/RETIRED_FILES.json. For a code-level run use the synthetic set: "
            "python experiments/wpi-demand-patent-matching/synthetic/generate_synthetic_corpus.py"
        )
    return directory


def evidence_quotes(script: str) -> dict[str, object]:
    """Verbatim quotes the auditors recorded as evidence, kept outside the public code, by demand id."""
    return json.loads((data_dir() / EVIDENCE_QUOTES).read_text(encoding="utf-8"))[script]


def attach_evidence(entries: list[dict], script: str) -> None:
    """Fill each entry's `evidence` (a None placeholder in the script) from the external quotes; fail if one is missing."""
    quotes = evidence_quotes(script)
    absent = [e["demand_id"] for e in entries if e["demand_id"] not in quotes]
    if absent:
        raise SystemExit(f"{EVIDENCE_QUOTES} has no {script} quotes for: {', '.join(absent)}")
    for entry in entries:
        entry["evidence"] = quotes[entry["demand_id"]]
