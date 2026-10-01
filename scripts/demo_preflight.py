"""Checks that the server answering on BASE_URL is the current build, before a demo. Usage: demo_preflight.py [BASE_URL]."""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src" / "main"))

from infrastructure.operational.notices import NOTICES  # noqa: E402
from infrastructure.operational.selection import parse_selection  # noqa: E402

DEFAULT_DIR = ROOT / "data" / "snapshots" / "operational_corpus_v1"
SCORE_KEYS = {"score", "scores", "retrieval_scores", "similarity", "band", "relevance_band", "distance"}
CLOSED_ROUTES = (("POST", "/run"), ("POST", "/api/analyze"), ("GET", "/docs"), ("GET", "/openapi.json"), ("GET", "/list-apps"))
SELECTION = ROOT / "backend" / "src" / "main" / "infrastructure" / "operational" / "demo_selection_v1.json"


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


def expected_identity(directory: Path) -> dict[str, str]:
    """The build identity the artifacts on disk claim; a server must report exactly this in `meta`."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((directory / "embeddings_patents_v1.manifest.json").read_text(encoding="utf-8"))
    return {
        "corpus_id": manifest["dataset_id"],
        "corpus_parquet_sha256": manifest["parquet_sha256"],
        "embedding_index_sha256": index["matrix_sha256"],
    }


def check(get_json, directory: Path = DEFAULT_DIR, status_of=None) -> list[str]:
    """Returns the problems found; empty means the server is ready to demo."""
    identity = expected_identity(directory)
    selection = parse_selection(json.loads(SELECTION.read_text(encoding="utf-8")))
    problems: list[str] = []
    examples = get_json("/api/demand-examples")
    if {d["demand_id"] for d in examples["demands"]} != set(selection.included):
        problems.append("listed demands differ from demo_selection_v1.json (stale server?)")
    if examples["notices"] != list(NOTICES):
        problems.append("notices differ from the current build (stale server?)")
    for demand_id in (*selection.primary, *selection.secondary):
        body = get_json(f"/api/matches?{urllib.parse.urlencode({'demand_id': demand_id})}")
        if len(body["assets"]) != 5:
            problems.append(f"{demand_id}: expected 5 assets, got {len(body['assets'])}")
        if set(_keys(body)) & SCORE_KEYS:
            problems.append(f"{demand_id}: response exposes a score")
        served = {k: body["meta"].get(k) for k in identity}
        if served != identity:
            problems.append(f"{demand_id}: server reports another build {served}, artifacts on disk say {identity}")
    for method, path in CLOSED_ROUTES if status_of else ():
        if status_of(method, path) not in (404, 405):
            problems.append(f"{method} {path} is reachable; only the product routes may be exposed")
    return problems


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")

    def get_json(path: str):
        with urllib.request.urlopen(base + path, timeout=30) as response:
            return json.load(response)

    def status_of(method: str, path: str) -> int:
        request = urllib.request.Request(base + path, method=method, data=b"{}" if method == "POST" else None)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status
        except urllib.error.HTTPError as err:
            return err.code

    started = time.perf_counter()
    problems = check(get_json, Path(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DIR), status_of)
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{'NOT READY' if problems else 'READY'} ({time.perf_counter() - started:.1f}s for all journeys)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
