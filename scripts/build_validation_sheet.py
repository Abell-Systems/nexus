"""Writes the product-validation sheet: one row per (listed demand, top-5 asset), exactly what the screen shows.

Usage: python scripts/build_validation_sheet.py ARTIFACTS_DIR [OUT_CSV]
"""
import csv
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src" / "main"))
from infrastructure.operational.app import create_mvp_app  # noqa: E402

COLUMNS = ["demand_id", "demand_title", "rank", "publication_id", "ip_type", "asset_title",
           "relevance", "evidence_sufficient", "traceability_ok", "comment"]


def main() -> None:
    artifacts = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/validation/validation_sheet_v1.csv")
    client = TestClient(create_mvp_app(artifacts))
    rows = []
    for demand in client.get("/api/demand-examples").json()["demands"]:
        body = client.get("/api/matches", params={"demand_id": demand["demand_id"], "limit": 5}).json()
        rows += [
            [demand["demand_id"], demand["title"], a["rank"], a["publication_id"], a["ip_type"], a["title"], "", "", "", ""]
            for a in body["assets"]
        ]
    with out.open("w", newline="", encoding="utf-8-sig") as f:  # BOM: Excel opens Spanish accents correctly
        csv.writer(f).writerows([COLUMNS, *rows])
    print(f"{len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
