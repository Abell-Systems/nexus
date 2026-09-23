# experiments/phase2/run_ted_construct_validity_llm_classification.py
"""TED construct-validity classifier, step 3: LLM classification of the control sample.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS7. Classifies the same 30 control-sample candidates the blind labeling CSVs
cover, using LlmTechnicalProblemClassifier -- blind to any human label (reads
only description_text)."""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from infrastructure.llm.groq_client import GroqClient  # noqa: E402
from infrastructure.llm.technical_problem_classifier import LlmTechnicalProblemClassifier  # noqa: E402


def generate(manifest_path: Path, mapped_path: Path, out_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapped_by_id = {c["demand_id"]: c for c in json.loads(mapped_path.read_text(encoding="utf-8"))}

    classifier = LlmTechnicalProblemClassifier(GroqClient())

    results: dict[str, str] = {}
    for demand_id in manifest["all_ids"]:
        description = mapped_by_id[demand_id]["description_text"]
        results[demand_id] = classifier.classify(description).value

    if set(results) != set(manifest["all_ids"]):
        raise ValueError("LLM classification did not cover exactly the control sample's ids")

    out = {
        "dataset_id": "nexus-ted-construct-validity-llm-classification-v1",
        "purpose": "TED construct-validity classifier LLM run against the control sample -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md",
        "source_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "classifier": "LlmTechnicalProblemClassifier",
        "temperature": 0.0,
        "classifications": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {len(results)} LLM classifications to {out_path}")
    return out


def main() -> int:
    generate(
        manifest_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json",
        mapped_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_mapped.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_llm_classification.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
