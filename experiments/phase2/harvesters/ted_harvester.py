"""TED (Tenders Electronic Daily) Harvester for Phase-2 corpus expansion (ADR 0034).

Targets TED's public, unauthenticated JSON search API for listing (`Innovation
partnership` procedure type, `Competition` notice type only) and the
server-rendered `htmlDirect` detail page per notice -- confirmed during the
ADR 0033 spike to carry buyer name, publication date, and description in
static markup, unlike the Angular SPA route, so no browser automation is
needed.
"""

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from experiments.phase2.harvesters.base import BaseHarvester, PayloadCollisionError

logger = logging.getLogger(__name__)

SEARCH_API_URL = "https://api.ted.europa.eu/v3/notices/search"
SEARCH_QUERY = "procedure-type=innovation AND notice-type=cn-standard"
PAGE_SIZE = 50


class TedHarvester(BaseHarvester):
    """Polite harvester crawling TED's Innovation Partnership Competition notices."""

    def __init__(
        self,
        delay_seconds: float = 1.0,
        user_agent: str | None = None,
        base_url: str = "https://ted.europa.eu",
        search_api_url: str = SEARCH_API_URL,
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, user_agent=user_agent)
        self.base_url = base_url.rstrip("/")
        self.search_api_url = search_api_url
        self.source_id = "ted"

    def _detail_url(self, publication_number: str) -> str:
        return f"{self.base_url}/en/notice/{publication_number}/html"

    def _search_page(self, page: int) -> list[str]:
        """Fetch one page of publication numbers from the TED search API."""
        self._pace()
        body = json.dumps(
            {
                "query": SEARCH_QUERY,
                "fields": ["publication-number"],
                "page": page,
                "limit": PAGE_SIZE,
                "scope": "ALL",
            }
        ).encode("utf-8")
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req = urllib.request.Request(self.search_api_url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            payload: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        return [n["publication-number"] for n in payload.get("notices", []) if n.get("publication-number")]

    def harvest(
        self,
        out_dir: Path,
        max_pages: int | None = None,
        limit: int | None = None,
    ) -> list[Path]:
        """Crawl the Innovation Partnership / Competition notice population, page by
        page (1-indexed, `PAGE_SIZE` results per page), fetch each notice's
        server-rendered detail page, and store raw payloads.

        Args:
            out_dir: Directory where raw payloads and sidecars are stored.
            max_pages: Maximum number of search-API pages to crawl.
            limit: Maximum total detail payloads to acquire.

        Returns:
            List of Paths to saved raw payloads.
        """
        page = 1
        saved_paths: list[Path] = []

        known_uris = self.get_known_source_uris(out_dir, self.source_id)
        for existing_path in known_uris.values():
            if existing_path not in saved_paths:
                saved_paths.append(existing_path)

        while True:
            if max_pages is not None and page > max_pages:
                break
            if limit is not None and len(saved_paths) >= limit:
                break

            try:
                publication_numbers = self._search_page(page)
            except PayloadCollisionError:
                raise
            except Exception as exc:
                self.record_error(
                    source_id=self.source_id,
                    uri=f"{self.search_api_url}?page={page}",
                    error_type=type(exc).__name__,
                    message=str(exc),
                    http_status=getattr(exc, "code", None),
                )
                break

            if not publication_numbers:
                break

            for publication_number in publication_numbers:
                if limit is not None and len(saved_paths) >= limit:
                    break

                detail_url = self._detail_url(publication_number)
                if detail_url in known_uris:
                    logger.debug("Skipping already harvested URI: %s", detail_url)
                    continue

                try:
                    detail_bytes, detail_status = self.fetch_url(detail_url)
                    saved = self.save_raw_payload(
                        demand_id=publication_number,
                        source_id=self.source_id,
                        source_uri=detail_url,
                        payload_bytes=detail_bytes,
                        out_dir=out_dir,
                        metadata={"http_status": detail_status},
                    )
                    saved_paths.append(saved)
                except PayloadCollisionError:
                    raise
                except Exception as exc:
                    self.record_error(
                        source_id=self.source_id,
                        uri=detail_url,
                        error_type=type(exc).__name__,
                        message=str(exc),
                        demand_id=publication_number,
                        http_status=getattr(exc, "code", None),
                    )
                    continue

            if len(publication_numbers) < PAGE_SIZE:
                break

            page += 1

        return saved_paths
