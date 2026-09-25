"""InnoGet Demand Harvester for Phase-2 corpus expansion (ADR 0032)."""

import logging
import re
import urllib.error
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup

from experiments.phase2.harvesters.base import BaseHarvester, PayloadCollisionError

logger = logging.getLogger(__name__)

_ID_PATH_RE = re.compile(r"/(?:technology-calls|challenges)/(\d+)")


class InnogetHarvester(BaseHarvester):
    """Polite harvester scraping public technology-calls from InnoGet."""

    def __init__(
        self,
        delay_seconds: float = 1.0,
        user_agent: str | None = None,
        base_url: str = "https://www.innoget.com",
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, user_agent=user_agent)
        self.base_url = base_url.rstrip("/")
        self.source_id = "innoget"

    def harvest(
        self,
        out_dir: Path,
        max_pages: int | None = None,
        limit: int | None = None,
    ) -> list[Path]:
        """Scrape directory pages, follow challenge detail links, and save raw payloads.

        Args:
            out_dir: Directory where raw payloads and sidecars are stored.
            max_pages: Maximum number of pagination pages to crawl.
            limit: Maximum total detail payloads to acquire.

        Returns:
            List of Paths to saved raw payloads.
        """
        page = 1
        saved_paths: list[Path] = []
        seen_demand_ids: set[str] = set()
        seen_urls: set[str] = set()

        known_uris = self.get_known_source_uris(out_dir, self.source_id)
        for existing_path in known_uris.values():
            if existing_path not in saved_paths:
                saved_paths.append(existing_path)

        while True:
            if max_pages is not None and page > max_pages:
                break
            if limit is not None and len(saved_paths) >= limit:
                break

            listing_url = f"{self.base_url}/technology-calls?page={page}"
            try:
                listing_bytes, status = self.fetch_url(listing_url)
            except PayloadCollisionError:
                raise
            except Exception as exc:
                self.record_error(
                    source_id=self.source_id,
                    uri=listing_url,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    http_status=getattr(exc, "code", None),
                )
                break

            discovered = self._extract_challenge_links(listing_bytes)
            if not discovered:
                break

            new_items_on_page: list[str] = []
            for href in discovered:
                detail_url = urllib.parse.urljoin(self.base_url, href)
                if detail_url not in seen_urls:
                    seen_urls.add(detail_url)
                    new_items_on_page.append(href)

            if len(new_items_on_page) == 0:
                break

            for href in new_items_on_page:
                if limit is not None and len(saved_paths) >= limit:
                    break

                m = _ID_PATH_RE.search(href)
                if not m:
                    continue
                demand_id = f"INNOGET-{m.group(1)}"
                if demand_id in seen_demand_ids:
                    continue
                seen_demand_ids.add(demand_id)

                detail_url = urllib.parse.urljoin(self.base_url, href)
                if detail_url in known_uris:
                    logger.debug("Skipping already harvested URI: %s", detail_url)
                    continue

                try:
                    detail_bytes, detail_status = self.fetch_url(detail_url)
                    saved = self.save_raw_payload(
                        demand_id=demand_id,
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
                        demand_id=demand_id,
                        http_status=getattr(exc, "code", None),
                    )
                    continue

            page += 1

        return saved_paths

    def _extract_challenge_links(self, html_bytes: bytes) -> list[str]:
        """Parse listing HTML and extract candidate challenge detail link hrefs."""
        try:
            html_text = html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            html_text = html_bytes.decode("latin-1", errors="replace")

        soup = BeautifulSoup(html_text, "html.parser")
        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"]).strip()
            if _ID_PATH_RE.search(href) and href not in links:
                links.append(href)
        return links

