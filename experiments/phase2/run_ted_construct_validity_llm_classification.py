# experiments/phase2/run_ted_construct_validity_llm_classification.py
"""TED construct-validity classifier, step 3: LLM classification of the control sample.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS7. Classifies the same 30 control-sample candidates the blind labeling CSVs
cover, using LlmTechnicalProblemClassifier -- blind to any human label (reads
only description_text)."""

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from infrastructure.llm.groq_client import GroqClient  # noqa: E402
from infrastructure.llm.technical_problem_classifier import LlmTechnicalProblemClassifier  # noqa: E402

_MAX_RETRIES = 8


def _retry_seconds(exc: httpx.HTTPStatusError) -> float:
    """Groq's 429 body carries the wait in its message ('try again in 4.216s');
    the response has no Retry-After header, so parse the message text."""
    match = re.search(r"try again in ([\d.]+)s", exc.response.text)
    return float(match.group(1)) + 0.5 if match else 5.0


def _classify_with_retry(classifier: LlmTechnicalProblemClassifier, description: str) -> str:
    for attempt in range(_MAX_RETRIES):
        try:
            return classifier.classify(description).value
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429 or attempt == _MAX_RETRIES - 1:
                raise
            wait = _retry_seconds(exc)
            print(f"  rate limited, waiting {wait:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
            time.sleep(wait)
    raise AssertionError("unreachable")  # pragma: no cover

# Pinned per spec SS7 ("fixed model/version pinned in the implementation plan").
# Originally pinned to llama-3.3-70b-versatile (matching the then-current GROQ_MODEL
# default); retired from Groq's catalog by the time this ran for real (2026-09-24,
# /v1/models confirmed it gone -- 404 model_not_found). Re-pinned to
# openai/gpt-oss-120b, the closest available model in size/generality; verified
# manually against the classifier's exact JSON-object/temperature=0 protocol before
# use. See docs/ted-construct-validity-classifier-results.md for the ruling.
PINNED_MODEL = "openai/gpt-oss-120b"


def generate(manifest_path: Path, mapped_path: Path, out_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapped_path_bytes = mapped_path.read_bytes()
    actual_mapped_sha256 = hashlib.sha256(mapped_path_bytes).hexdigest()
    if actual_mapped_sha256 != manifest["source_mapped_candidates_sha256"]:
        raise ValueError(
            "candidates_mapped.json has changed since the control sample was built "
            f"(expected sha256 {manifest['source_mapped_candidates_sha256']}, got {actual_mapped_sha256})"
        )
    mapped_by_id = {c["demand_id"]: c for c in json.loads(mapped_path_bytes)}

    classifier = LlmTechnicalProblemClassifier(GroqClient(model=PINNED_MODEL))

    results: dict[str, str] = {}
    for demand_id in manifest["all_ids"]:
        description = mapped_by_id[demand_id]["description_text"]
        results[demand_id] = _classify_with_retry(classifier, description)
        print(f"  {demand_id} -> {results[demand_id]}")

    if set(results) != set(manifest["all_ids"]):
        raise ValueError("LLM classification did not cover exactly the control sample's ids")

    out = {
        "dataset_id": "nexus-ted-construct-validity-llm-classification-v1",
        "purpose": "TED construct-validity classifier LLM run against the control sample -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md",
        "source_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "classifier": "LlmTechnicalProblemClassifier",
        "model": PINNED_MODEL,
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
