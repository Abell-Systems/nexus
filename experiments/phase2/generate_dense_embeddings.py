"""#104 dense retrieval diagnostic, step 1b: frozen embedding artifact for
the experimental corpus (docs/phase2-ted-dense-retrieval-diagnostic-contract.md).

Deliberately a SEPARATE script from scripts/generate_m1_embeddings.py (ADR
0014's own generator), not a modified/extended version of it -- that script
belongs to the ADR 0014 pipeline and is bound to the sealed pilot benchmark
(dataset_pilot_benchmark.json, ADR 0006). Coupling a second data regime into
it would make it harder to tell which behavior belongs to which experiment.

Reuses ADR 0014's exact encode() call shape, model loading, determinism
check, and JSON+sha256 serialization pattern verbatim (inspected directly
from generate_m1_embeddings.py before writing this, not re-derived from
memory) -- adapted only for TWO source corpora (the 30-demand TED Dev set +
the 63-patent OEPM corpus) instead of ADR 0006's single sealed dataset, so
FrozenEmbeddingArtifact (domain/models/evaluation.py) is not reused as-is:
its schema and verify_source_dataset are tied to a single ValidatedDataset.

Runs INSIDE .venv-embedding-generation (the isolated stack verified in
docs/phase2-ted-dense-retrieval-diagnostic-contract.md SS7 checkpoint 2) --
deliberately has NO duckdb/pandas/pyarrow dependency, so that environment's
already-verified package set is not extended. Reads the plain JSON produced
by extract_dense_source_texts.py (run separately, in the main backend venv,
which already has duckdb) instead of touching the Parquet corpus directly.

Does NOT run any retrieval. Produces the frozen artifact + manifest only.
"""

import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
MODEL_REVISION = "4328cf26390c98c5e3c738b4460a05b95f4911f5"
MODEL_LICENSE = "Apache-2.0"
GENERATION_SCRIPT_PATH = "experiments/phase2/generate_dense_embeddings.py"


def _get_git_commit(cwd: Path) -> str:
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True,
    )
    return res.stdout.strip()


def _encode_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    # Identical call shape to scripts/generate_m1_embeddings.py:_encode_texts --
    # normalize_embeddings=True, batch_size=1, device="cpu" (ADR 0014 SS5).
    return model.encode(texts, normalize_embeddings=True, batch_size=1, device="cpu")


def generate(
    source_texts_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    source = json.loads(source_texts_path.read_text(encoding="utf-8"))
    demand_ids = source["demand_ids"]
    demand_texts = source["demand_texts"]
    patent_ids = source["patent_ids"]
    patent_texts = source["patent_texts"]
    demand_corpus_sha256 = source["demand_corpus_sha256"]
    patent_corpus_sha256 = source["patent_corpus_sha256"]

    print(f"Loading model {MODEL_NAME} @ {MODEL_REVISION} (CPU)...")
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    embedding_dimension = model.get_sentence_embedding_dimension()
    if embedding_dimension != 768:
        raise ValueError(
            f"Pinned model reports embedding_dimension={embedding_dimension}, expected 768 (ADR 0014 SS8). "
            "The resolved revision no longer matches what ADR 0014 reviewed."
        )

    demand_vectors = _encode_texts(model, demand_texts)
    patent_vectors = _encode_texts(model, patent_texts)

    # Determinism check identical in spirit to generate_m1_embeddings.py: bit-identical
    # re-encode required (np.array_equal, not np.allclose).
    demand_vectors_repeat = _encode_texts(model, demand_texts)
    if not np.array_equal(demand_vectors, demand_vectors_repeat):
        raise RuntimeError(
            "Determinism check failed: re-encoding the same demand texts under the same "
            "pinned model/parameters produced bit-different vectors. Refusing to generate an "
            "artifact from a non-reproducible run."
        )
    print("Determinism check passed (bit-identical output on repeated encode())")

    demand_embeddings = {d_id: vec.tolist() for d_id, vec in zip(demand_ids, demand_vectors, strict=True)}
    patent_embeddings = {p_id: vec.tolist() for p_id, vec in zip(patent_ids, patent_vectors, strict=True)}

    library_versions = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "torch": pkg_version("torch"),
        "transformers": pkg_version("transformers"),
        "sentence-transformers": pkg_version("sentence-transformers"),
    }

    payload = {
        "artifact_id": "m1_embeddings_ted_at_scale_dense_diagnostic_v1",
        "purpose": "Frozen embedding artifact for docs/phase2-ted-dense-retrieval-diagnostic-contract.md -- generation only, retrieval NOT run here.",
        "frozen_at": date.today().isoformat(),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "generation_script_path": GENERATION_SCRIPT_PATH,
        "generation_script_commit": _get_git_commit(REPO_ROOT),
        "library_versions": library_versions,
        "generation_device": "cpu",
        "demand_corpus_sha256": demand_corpus_sha256,
        "patent_corpus_sha256": patent_corpus_sha256,
        "embedding_dimension": embedding_dimension,
        "normalization": "l2",
        "similarity_metric": "cosine",
        "n_demands": len(demand_embeddings),
        "n_patents": len(patent_embeddings),
        "demand_embeddings": demand_embeddings,
        "patent_embeddings": patent_embeddings,
    }

    canonical_bytes = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    artifact_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
    payload["artifact_sha256"] = artifact_sha256

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    out_path.with_suffix(".sha256").write_text(f"{artifact_sha256}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote frozen artifact: {out_path}")
    print(f"  {len(demand_embeddings)} demands, {len(patent_embeddings)} patents")
    print(f"  artifact_sha256={artifact_sha256}")
    print(f"  generated_at={datetime.now(UTC).isoformat()}")
    return payload


def main() -> int:
    generate(
        source_texts_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_source_texts.json",
        out_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_embeddings_v1.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
