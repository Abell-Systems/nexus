#!/usr/bin/env python3
"""Downloads OEPM OpenData bibliographic files into data/raw/oepm_open/ with a SHA-256 manifest.

The OEPM sede requires a registered account for these files. Credentials come only from the
environment (OEPM_USER = account email, OEPM_PWD); they are never printed or written.
It logs in with that account and clicks the links like a user, one file at a time; it does not bypass
any access control. Check the OEPM's reuse terms before redistributing what it downloads.

Needs Playwright, which is deliberately not a project dependency (a one-off tool):
  pip install playwright && playwright install chromium

  python scripts/download_oepm_opendata.py --list                   # login, show available files
  python scripts/download_oepm_opendata.py --match 'biblio.*2020'   # download matching files
  python scripts/download_oepm_opendata.py --page CATALOG_URL --list   # files linked from another sede page

The login always happens on the bibliographic-data page; --page then moves, in the same session, to another
page of the sede (for example the catalogue, which links the example file of every dataset).
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

SEDE_HOST = "sede.oepm.gob.es"
PAGE = "https://sede.oepm.gob.es/eSede/datos/es/catalogo/catalogo-patentes-y-modelos-de-utilidad/bibliograficos/"
OUT_DIR = Path("data/raw/oepm_open")
LINK_RE = re.compile(r"descargar\.jsp\?u=(INVENCIONES/[^'\"&]+\.zip)$")


def is_sede_url(url: str) -> bool:
    """True for an https URL on exactly the sede host, without credentials or a non-default port."""
    try:
        parts = urlsplit(url)
        return (
            parts.scheme == "https"
            and parts.hostname == SEDE_HOST
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 443)
        )
    except ValueError:  # malformed port or netloc
        return False


def zip_paths(hrefs: list[str]) -> list[str]:
    """Sorted, distinct INVENCIONES/....zip paths among the links of a page that point to the sede."""
    return sorted({m.group(1) for h in hrefs if is_sede_url(h) and (m := LINK_RE.search(h))})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="only list the files the account can see")
    ap.add_argument("--match", default=None, help="regex on the file path; required to download")
    ap.add_argument(
        "--page", default=PAGE, help="sede page whose links are listed or downloaded (default: bibliographic data)"
    )
    args = ap.parse_args()
    if not is_sede_url(args.page):
        ap.error(f"--page must be an https page of {SEDE_HOST}")
    if not args.list and not args.match:
        ap.error("pass --list or --match")
    user, pwd = os.environ.get("OEPM_USER"), os.environ.get("OEPM_PWD")
    if not user or not pwd:
        sys.exit("set OEPM_USER and OEPM_PWD in your environment")

    from playwright.sync_api import (
        sync_playwright,
    )  # not a project dependency: imported only once the arguments are valid

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(accept_downloads=True).new_page()
        page.goto(PAGE)
        page.get_by_label("Correo electrónico:").fill(user)
        page.get_by_label("Contraseña:").fill(pwd)
        page.get_by_role("button", name="Enviar").click()
        page.wait_for_load_state("networkidle")
        if "tienes que estar registrado" in page.content():
            sys.exit("login failed: the page still asks for registration")

        if args.page != PAGE:
            page.goto(args.page)
            page.wait_for_load_state("networkidle")
            if not is_sede_url(page.url):  # a redirect must not take the logged-in session elsewhere
                sys.exit(f"--page redirected outside {SEDE_HOST}: {page.url}")
        hrefs = page.eval_on_selector_all("a[href*='descargar.jsp']", "els => els.map(e => e.href)")
        files = zip_paths(hrefs)
        if args.list:
            print("\n".join(files) or "no .zip links visible")
            return 0

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        manifest_path = OUT_DIR / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        for path in files:
            if not re.search(args.match, path):
                continue
            target = OUT_DIR / Path(path).name
            if not (target.exists() and target.read_bytes()[:2] == b"PK"):
                for attempt in range(3):  # downloads are sometimes cancelled mid-flight
                    try:
                        # the page audits each download in JS on click; a bare GET is answered with a denial
                        with page.expect_download() as dl:
                            page.locator(f"a[href$='{path}']").first.dispatch_event("click")
                        dl.value.save_as(target)
                        break
                    except Exception as exc:
                        print(f"retry {target.name} ({attempt + 1}/3): {exc}", file=sys.stderr)
                else:
                    sys.exit(f"{path}: download kept failing")
            body = target.read_bytes()
            if body[:2] != b"PK":  # the sede answers 200 with an HTML denial, not an error code
                target.unlink()
                sys.exit(f"{path}: not a zip ({body[:80]!r})")
            if target.name not in manifest:  # also covers files left by an interrupted run
                manifest[target.name] = {
                    "source": path,
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "bytes": len(body),
                    "downloaded_at": datetime.now(UTC).isoformat(),
                }
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
            print(f"ok {target.name} {len(body)} bytes")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
