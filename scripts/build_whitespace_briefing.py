#!/usr/bin/env python3
"""Builds the self-contained descriptive briefing (docs/whitespace/briefing-lydia.html) from the versioned results.

Every number comes from the JSON results of the repository: the corpus exposure, the descriptive sensitivity, the
section map and the published corpus figures. The page ranks nothing and presents no pair as an opportunity.

  python scripts/build_whitespace_briefing.py [--out docs/whitespace/briefing-lydia.html]
"""

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs" / "whitespace"
YEARS = range(2000, 2026)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def coverage_svg(by_year: dict) -> str:
    width, height, left, bottom, top = 880, 300, 46, 28, 14
    peak = max(
        sum(g["inventory"] for k, g in by_year[str(y)].items() if k != "corpus_keys_not_in_inventory") for y in YEARS
    )
    step = (width - left - 8) / len(YEARS)
    scale = (height - bottom - top) / peak
    parts = []
    for tick in range(0, peak + 1, 10000):
        y = height - bottom - tick * scale
        parts.append(
            f'<line class="grid" x1="{left}" x2="{width - 8}" y1="{y:.1f}" y2="{y:.1f}"/><text class="axis" x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{tick // 1000} mil</text>'
        )
    for i, year in enumerate(YEARS):
        cells = by_year[str(year)]
        present = sum(cells[g]["present"] for g in ("ep_translation", "kind_y", "other"))
        absent_y = cells["kind_y"]["absent"]
        absent_rest = cells["ep_translation"]["absent"] + cells["other"]["absent"]
        x = left + i * step + 2
        w = step - 4
        base = height - bottom
        for value, cls in ((present, "present"), (absent_rest, "absent-rest"), (absent_y, "absent-y")):
            h = value * scale
            if h > 0:
                base -= h
                parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{base:.1f}" width="{w:.1f}" height="{h:.1f}"/>')
        if year % 2 == 0 or year in (2010, 2025):
            parts.append(f'<text class="axis" x="{x + w / 2:.1f}" y="{height - 10}" text-anchor="middle">{year}</text>')
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="cov-t cov-d">'
        '<title id="cov-t">Publicaciones por año: presentes y ausentes en el corpus</title>'
        '<desc id="cov-d">Barras apiladas por año de publicación, de 2000 a 2025. Se distinguen las publicaciones presentes, las ausentes del tipo Y y las demás ausentes. En 2010 ninguna publicación está presente.</desc>'
        '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" class="hatch-bg"/><line x1="0" y1="0" x2="0" y2="6" class="hatch-line"/></pattern></defs>'
        + "".join(parts)
        + "</svg>"
    )


def heatmap(density: dict) -> str:
    sections = sorted(density["active_subclasses_by_section"])
    cells = density["cells"]
    peak = max(c["seen_percent"] for c in cells.values())
    rows = [
        '<tr><th scope="col"><span class="sr">Sección</span></th>'
        + "".join(
            f'<th scope="col">{s}<small>{density["active_subclasses_by_section"][s]}</small></th>' for s in sections
        )
        + "</tr>"
    ]
    for a in sections:
        row = [f'<th scope="row">{a}<small>{density["active_subclasses_by_section"][a]}</small></th>']
        for b in sections:
            cell = cells[a + b if a <= b else b + a]
            level = round(5 * cell["seen_percent"] / peak)
            row.append(
                f'<td class="l{level}" title="{cell["seen_pairs"]:,} de {cell["possible_pairs"]:,} pares posibles">{cell["seen_percent"]:.0f}</td>'
            )
        rows.append("<tr>" + "".join(row) + "</tr>")
    return (
        f'<table class="heat"><caption>Origen {density["origin"]}: % de pares de subclases activas ya vistos juntos, por sección</caption>'
        + "".join(rows)
        + "</table>"
    )


def sensitivity_rows(sens: dict) -> str:
    out = []
    for origin in ("2003", "2006"):
        s = sens[origin]
        b1 = [v["positives"] for v in s["S-B1"].values()]
        c = s["S-C"]["positives"]
        base = s["S-A"]["positives"]
        out.append(
            f'<tr><th scope="row">{origin}</th><td>{base:,}</td><td>{min(b1):,} – {max(b1):,}</td>'
            f"<td>{s['S-B2']['positives']:,}</td><td>{c['p2.5']:,} – {c['p97.5']:,}</td></tr>"
        )
    return "".join(out)


TEMPLATE = (
    (Path(__file__).parent / "briefing_template.html").read_text(encoding="utf-8")
    if (Path(__file__).parent / "briefing_template.html").exists()
    else ""
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=DOCS / "briefing-lydia.html")
    args = parser.parse_args()
    exposure = load(DOCS / "oepm-corpus-exposure-results.json")["exposure"]
    sens = load(DOCS / "oepm-omission-sensitivity-results.json")["sensitivity"]
    density = load(DOCS / "oepm-section-density-results.json")
    acc = exposure["accumulated_up_to_origin"]
    values = {
        "COVERAGE_SVG": coverage_svg(exposure["by_year"]),
        "HEAT_2006": heatmap(density["2006"]),
        "HEAT_2022": heatmap(density["2022"]),
        "SENS_ROWS": sensitivity_rows(sens),
        "INVENTORY": f"{exposure['inventory_publications']:,}",
        "CORPUS": f"{exposure['corpus_publications']:,}",
        "ABSENT_2003": f"{acc['2003']['all_groups']['absent_share_percent']:.2f}".replace(".", ","),
        "ABSENT_2006": f"{acc['2006']['all_groups']['absent_share_percent']:.2f}".replace(".", ","),
        "Y_2003": f"{acc['2003']['kind_y']['absent']:,}",
        "Y_2006": f"{acc['2006']['kind_y']['absent']:,}",
        "Y_2010": f"{exposure['by_year']['2010']['kind_y']['inventory']:,}",
        "ALL_2010": f"{sum(exposure['by_year']['2010'][g]['inventory'] for g in ('ep_translation', 'kind_y', 'other')):,}",
    }
    html = TEMPLATE
    for key, value in values.items():
        html = html.replace("{{" + key + "}}", value)
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
