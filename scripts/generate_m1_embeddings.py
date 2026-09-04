#!/usr/bin/env python3
"""Offline generator for the frozen M1 semantic embedding artifact (ADR 0014).

Invariants (ADR 0014 — deviating from any of these is non-compliant, see its
"Enforcement" section):
- Runs entirely outside the evaluation harness, once, offline. The evaluation runtime
  never imports this script or its dependencies (enforced by the
  `embedding-generation-stack-isolation` Import Linter contract).
- Model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2, pinned revision
  4328cf26390c98c5e3c738b4460a05b95f4911f5 — not "latest", not configurable via CLI.
- Device: CPU only. Input text: patent `title + ' ' + abstract`, demand
  `title + ' ' + description` — no annotation text.
- encode(normalize_embeddings=True, batch_size=1, device="cpu").
- Verifies the sealed dataset (ADR 0006) before generating, and its own determinism
  and output shape before writing the artifact.

Requires the environment in requirements/evaluation-generation.txt — NOT
backend/requirements.txt.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from importlib.metadata import version as pkg_version
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend" / "src" / "main"))

import numpy as np
from sentence_transformers import SentenceTransformer

from domain.models.evaluation import FrozenEmbeddingArtifact
from infrastructure.evaluation.dataset_loader import DefaultEvaluationDatasetLoader

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
MODEL_REVISION = "4328cf26390c98c5e3c738b4460a05b95f4911f5"
MODEL_LICENSE = "Apache-2.0"
GENERATION_SCRIPT_PATH = "scripts/generate_m1_embeddings.py"


def _get_git_commit(cwd: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return res.stdout.strip()
    except Exception as err:
        raise RuntimeError(
            "Unable to discover git commit hash via 'git rev-parse HEAD'. "
            "This artifact's provenance requires the generating script's exact commit — "
            "run inside a git repository."
        ) from err


def _encode_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    return model.encode(texts, normalize_embeddings=True, batch_size=1, device="cpu")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the frozen M1 semantic embedding artifact (ADR 0014)")
    parser.add_argument(
        "--dataset", type=Path, default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.json"
    )
    parser.add_argument(
        "--checksum", type=Path, default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.sha256"
    )
    parser.add_argument(
        "--manifest", type=Path, default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.manifest.json"
    )
    parser.add_argument(
        "--output", type=Path, default=repo_root / "data" / "evaluation" / "embeddings_pilot_benchmark.json"
    )
    args = parser.parse_args()

    print("================================================================================")
    print("Nexus M1 Semantic Embedding Artifact Generator (ADR 0014)")
    print("================================================================================")

    # 1. Load and cryptographically verify the sealed dataset (ADR 0006) before anything else.
    loader = DefaultEvaluationDatasetLoader()
    validated_dataset = loader.load_validated_dataset(
        dataset_path=args.dataset, checksum_path=args.checksum, manifest_path=args.manifest
    )
    dataset = validated_dataset.dataset
    print(
        f"✓ Dataset verified: {dataset.dataset_id} "
        f"(SHA: {validated_dataset.manifest.content_sha256[:12]}...), "
        f"{len(dataset.demands)} demands, {len(dataset.patents)} patents"
    )

    # 2. Load the pinned model, CPU only, exact revision — no "latest".
    print(f"Loading model {MODEL_NAME} @ {MODEL_REVISION} (CPU)...")
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    embedding_dimension = model.get_sentence_embedding_dimension()
    if embedding_dimension != 768:
        raise ValueError(
            f"Pinned model reports embedding_dimension={embedding_dimension}, expected 768 (ADR 0014 §8). "
            "This means the resolved revision no longer matches what this ADR reviewed."
        )

    # 3. Generate embeddings from observed text only — no annotation/ground-truth text.
    demand_ids = [d.demand_id for d in dataset.demands]
    demand_texts = [f"{d.title} {d.description}" for d in dataset.demands]
    patent_ids = [p.publication_id for p in dataset.patents]
    patent_texts = [f"{p.title} {p.abstract}" for p in dataset.patents]

    demand_vectors = _encode_texts(model, demand_texts)
    patent_vectors = _encode_texts(model, patent_texts)

    # 4. Determinism check at the generation boundary: re-encode and require identical
    # output. This verifies our documented procedure is reproducible on this run — it is
    # not a general audit of PyTorch/sentence-transformers determinism.
    demand_vectors_repeat = _encode_texts(model, demand_texts)
    if not np.allclose(demand_vectors, demand_vectors_repeat):
        raise RuntimeError(
            "Determinism check failed: re-encoding the same demand texts under the same "
            "pinned model/parameters produced different vectors. Refusing to generate an "
            "artifact from a non-reproducible run."
        )
    print("✓ Determinism check passed (identical output on repeated encode())")

    demand_embeddings = {d_id: vec.tolist() for d_id, vec in zip(demand_ids, demand_vectors, strict=True)}
    patent_embeddings = {p_id: vec.tolist() for p_id, vec in zip(patent_ids, patent_vectors, strict=True)}

    # 5. Assemble provenance and self-referential hash.
    library_versions = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "torch": pkg_version("torch"),
        "transformers": pkg_version("transformers"),
        "sentence-transformers": pkg_version("sentence-transformers"),
    }

    payload = {
        "artifact_id": f"m1_embeddings_{dataset.dataset_id}_{dataset.dataset_version}",
        "frozen_at": date.today().isoformat(),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "generation_script_path": GENERATION_SCRIPT_PATH,
        "generation_script_commit": _get_git_commit(repo_root),
        "library_versions": library_versions,
        "generation_device": "cpu",
        "dataset_sha256": validated_dataset.manifest.content_sha256,
        "embedding_dimension": embedding_dimension,
        "normalization": "l2",
        "similarity_metric": "cosine",
        "demand_embeddings": demand_embeddings,
        "patent_embeddings": patent_embeddings,
    }

    canonical_bytes = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    artifact_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
    payload["artifact_sha256"] = artifact_sha256

    # 6. Validate through the domain model (schema + embedding-dimension + hex checks)
    # and re-verify against the sealed dataset before writing anything to disk.
    artifact = FrozenEmbeddingArtifact(**payload)
    artifact.verify_source_dataset(validated_dataset)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"✓ Artifact verified against sealed dataset: {len(demand_embeddings)} demands, {len(patent_embeddings)} patents")
    print(f"✓ Wrote frozen artifact: {args.output}")
    print(f"  artifact_sha256={artifact_sha256}")
    print(f"  generated_at={datetime.now(UTC).isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
