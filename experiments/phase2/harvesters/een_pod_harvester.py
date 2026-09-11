"""EEN / POD Harvester for Phase-2 corpus expansion (ADR 0032)."""

import hashlib
import logging
import re
import urllib.error
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup

from experiments.phase2.harvesters.base import BaseHarvester, PayloadCollisionError

logger = logging.getLogger(__name__)

_PROPOSAL_LINK_RE = re.compile(
    r"/(?:en/)?collaborations/collaboration-proposals/(\d+)(?:/.*)?",
    re.IGNORECASE,
)
_POD_REF_RE = re.compile(r"\b((?:TR|TO|BO|BR|RD)[A-Z]{2}\d{8}\d+)\b")
_POD_LEAD_RE = re.compile(r"collaborations-info-value lead|pod-ref|reference", re.I)


class EenPodHarvester(BaseHarvester):
    """Polite harvester crawling certified EEN / POD mirrors (Open Innovation Lombardia)."""

    def __init__(
        self,
        delay_seconds: float = 1.0,
        user_agent: str | None = None,
        base_url: str = "https://www.openinnovation.regione.lombardia.it",
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, user_agent=user_agent)
        self.base_url = base_url.rstrip("/")
        self.listing_base = f"{self.base_url}/en/collaborations/collaboration-proposals"
        self.source_id = "een_pod"

    def harvest(
        self,
        out_dir: Path,
        max_pages: int | None = None,
        limit: int | None = None,
    ) -> list[Path]:
        """Crawl collaboration proposals directory, extract detail pages, and store raw payloads.

        Args:
            out_dir: Directory where raw payloads and sidecars are stored.
            max_pages: Maximum number of pagination pages to crawl.
            limit: Maximum total detail payloads to acquire.

        Returns:
            List of Paths to saved raw payloads.
        """
        page = 1
        saved_paths: list[Path] = []
        seen_urls: set[str] = set()

        while True:
            if max_pages is not None and page > max_pages:
                break
            if limit is not None and len(saved_paths) >= limit:
                break

            listing_url = f"{self.listing_base}?page={page}"
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

            discovered = self._extract_proposal_links(listing_bytes)
            if not discovered:
                break

            new_items_on_page: list[str] = []
            for href in discovered:
                detail_url = urllib.parse.urljoin(self.base_url, href)
                if detail_url not in seen_urls:
                    seen_urls.add(detail_url)
                    new_items_on_page.append(detail_url)

            if len(new_items_on_page) == 0:
                break

            for detail_url in new_items_on_page:
                if limit is not None and len(saved_paths) >= limit:
                    break

                demand_id: str | None = None
                try:
                    detail_bytes, detail_status = self.fetch_url(detail_url)
                    demand_id = self._determine_demand_id(detail_bytes, detail_url)
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

    def _determine_demand_id(self, html_bytes: bytes, url: str) -> str:
        """Determine demand_id from embedded POD reference or fallback to URL ID."""
        try:
            html_text = html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            html_text = html_bytes.decode("latin-1", errors="replace")

        # 1. Prioritize official reference container (avoids matching sidebar/related items)
        soup = BeautifulSoup(html_text, "html.parser")
        info_el = soup.find(class_=_POD_LEAD_RE)
        if info_el:
            m_lead = _POD_REF_RE.search(info_el.get_text(strip=True))
            if m_lead:
                return m_lead.group(1)

        # 2. Fallback to full-text reference search
        m_pod = _POD_REF_RE.search(html_text)
        if m_pod:
            return m_pod.group(1)

        # 3. Fallback to URL ID
        m_link = _PROPOSAL_LINK_RE.search(url)
        if m_link:
            return f"LOMBARDIA-{m_link.group(1)}"

        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
        return f"EEN-{url_hash}"

    def _extract_proposal_links(self, html_bytes: bytes) -> list[str]:
        """Extract collaboration proposal detail links from listing page."""
        try:
            html_text = html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            html_text = html_bytes.decode("latin-1", errors="replace")

        soup = BeautifulSoup(html_text, "html.parser")
        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"]).strip()
            if _PROPOSAL_LINK_RE.search(href) and href not in links:
                links.append(href)
        return links

