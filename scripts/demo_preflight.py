"""Checks that the server answering on BASE_URL is the current build, before a demo. Usage: demo_preflight.py [BASE_URL]."""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src" / "main"))

from infrastructure.operational.notices import NOTICES  # noqa: E402
from infrastructure.operational.selection import parse_selection  # noqa: E402

SELECTION = ROOT / "backend" / "src" / "main" / "infrastructure" / "operational" / "demo_selection_v1.json"


def check(get_json) -> list[str]:
    """Returns the problems found; empty means the server is ready to demo."""
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
        if "score" in json.dumps(body).lower():
            problems.append(f"{demand_id}: response exposes a score")
    return problems


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")

    def get_json(path: str):
        with urllib.request.urlopen(base + path, timeout=30) as response:
            return json.load(response)

    started = time.perf_counter()
    problems = check(get_json)
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{'NOT READY' if problems else 'READY'} ({time.perf_counter() - started:.1f}s for all journeys)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
