"""Step 2 of 2: offline embedding generation for the operational corpus (spec 2026-09-30, section 4).

Run ONLY inside .venv-embedding-generation (requirements/evaluation-generation.txt):
    .venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py --limit 500   # throughput gate
    .venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py               # full run

Model, revision, CPU, L2 normalization as in ADR 0014. batch_size defaults to 1. A larger batch is a
recorded deviation: the manifest stores the batch size and the max absolute difference against
batch_size=1 on the first 500 patent texts.
"""

import argparse
import json
import subprocess
import sys
import time
from importlib.metadata import version as pkg_version
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from infrastructure.embeddings.frozen_embedding_index import save_index  # noqa: E402

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
MODEL_REVISION = "4328cf26390c98c5e3c738b4460a05b95f4911f5"
SCRIPT_PATH = "scripts/generate_operational_embeddings.py"
MAX_SEQ_TOKENS = 128
OVERLAP_CHECK_SIZE = 500
DEFAULT_DIR = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1"


def _encode(model: SentenceTransformer, texts: list[str], batch_size: int, progress: bool = False) -> np.ndarray:
    return model.encode(
        texts, normalize_embeddings=True, batch_size=batch_size, device="cpu", show_progress_bar=progress
    ).astype(np.float32)


def _truncated_fraction(model: SentenceTransformer, texts: list[str]) -> float:
    over = 0
    for start in range(0, len(texts), 1000):
        ids = model.tokenizer(texts[start : start + 1000], add_special_tokens=True, truncation=False)["input_ids"]
        over += sum(1 for seq in ids if len(seq) > MAX_SEQ_TOKENS)
    return over / len(texts)


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate operational corpus embeddings (offline, CPU)")
    parser.add_argument("--sources", type=Path, default=DEFAULT_DIR / "embedding_sources_v1.json")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None, help="Throughput gate: encode N patent texts, write nothing")
    args = parser.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    print(f"Loading {MODEL_NAME} @ {MODEL_REVISION} (CPU)...")
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    if model.get_sentence_embedding_dimension() != 768:
        raise ValueError("Pinned model no longer reports 768 dimensions (ADR 0014 section 8)")

    if args.limit is not None:
        sample = sources["patent_texts"][: args.limit]
        start = time.perf_counter()
        _encode(model, sample, args.batch_size)
        rate = len(sample) / (time.perf_counter() - start)
        hours = len(sources["patent_texts"]) / rate / 3600
        print(f"GATE batch_size={args.batch_size}: {rate:.2f} texts/s; projected full run {hours:.2f} h (limit 4 h)")
        return 0

    patent_texts, demand_texts = sources["patent_texts"], sources["demand_texts"]
    demand_vectors = _encode(model, demand_texts, args.batch_size)
    if not np.array_equal(demand_vectors, _encode(model, demand_texts, args.batch_size)):
        raise RuntimeError("Determinism check failed: re-encoding the demand texts produced different vectors")
    print("Determinism check passed (bit-identical re-encode of demand texts)")

    deviation = None
    if args.batch_size != 1:
        overlap = patent_texts[:OVERLAP_CHECK_SIZE]
        diff = float(np.max(np.abs(_encode(model, overlap, 1) - _encode(model, overlap, args.batch_size))))
        deviation = {"batch_size": args.batch_size, "overlap_texts": len(overlap), "max_abs_diff_vs_batch_1": diff}
        print(f"Recorded batch deviation: {deviation}")

    patent_vectors = _encode(model, patent_texts, args.batch_size, progress=True)

    common = {
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "generation_device": "cpu",
        "batch_size": args.batch_size,
        "library_versions": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "torch": pkg_version("torch"),
            "transformers": pkg_version("transformers"),
            "sentence-transformers": pkg_version("sentence-transformers"),
            "numpy": pkg_version("numpy"),
        },
        "source_sha256": sources["source_sha256"],
        "generation_script_path": SCRIPT_PATH,
        "generation_script_commit": _git_commit(),
        "batch_deviation": deviation,
    }
    patents_manifest = save_index(
        args.out_dir, "embeddings_patents_v1", sources["patent_ids"], patent_vectors,
        truncated_fraction=_truncated_fraction(model, patent_texts), **common,
    )
    save_index(
        args.out_dir, "embeddings_demands_v1", sources["demand_ids"], demand_vectors,
        truncated_fraction=_truncated_fraction(model, demand_texts), **common,
    )
    print(f"Wrote indexes to {args.out_dir}; patents truncated at {MAX_SEQ_TOKENS} tokens: "
          f"{patents_manifest.truncated_fraction:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
