"""EEN/POD Official Portal Harvester for Phase-2 corpus expansion v2+ (ADR 0031 amendments).

Targets `een.ec.europa.eu/partnering-opportunities`, which supersedes the Open
Innovation Lombardia mirror used by `EenPodHarvester` in #101b -- see #101c
Section 3/7 and `docs/phase2-temporal-window-amendment.md`. Crawls the
`Technology request` (`profile_type` id 4320) and `R&D request` (id 4355)
construct facets -- the two constructs ADR 0031 SS2.2 authorizes for this
source per `docs/phase2-temporal-window-amendment.md` and
`docs/phase2-construct-expansion-amendment.md`.
"""

import hashlib
import logging
import re
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup

from experiments.phase2.harvesters.base import BaseHarvester, PayloadCollisionError

logger = logging.getLogger(__name__)

TECHNOLOGY_REQUEST_PROFILE_TYPE_ID = 4320
RD_REQUEST_PROFILE_TYPE_ID = 4355
AUTHORIZED_PROFILE_TYPE_IDS: tuple[int, ...] = (
    TECHNOLOGY_REQUEST_PROFILE_TYPE_ID,
    RD_REQUEST_PROFILE_TYPE_ID,
)

_DETAIL_LINK_RE = re.compile(r"^/partnering-opportunities/[a-z0-9-]+$")
# "RDR" is the official portal's R&D request prefix, confirmed on 33 live records
# during #101d re-acquisition -- distinct from the Lombardia mirror's "RD" (#101b).
# "DR" is kept for #101c SS7.2's single manually-read sample.
_POD_REF_RE = re.compile(r"\b((?:TR|TO|BO|BR|RDR|RD|DR)[A-Z]{2}\d{8,}\d)\b")


class EenPodOfficialHarvester(BaseHarvester):
    """Polite harvester crawling the official EEN/POD portal, authorized constructs only."""

    def __init__(
        self,
        delay_seconds: float = 1.0,
        user_agent: str | None = None,
        base_url: str = "https://een.ec.europa.eu",
        profile_type_ids: tuple[int, ...] = AUTHORIZED_PROFILE_TYPE_IDS,
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, user_agent=user_agent)
        self.base_url = base_url.rstrip("/")
        self.listing_base = f"{self.base_url}/partnering-opportunities"
        self.profile_type_ids = profile_type_ids
        self.source_id = "een_pod"

    def _listing_url(self, profile_type_id: int, page: int) -> str:
        query = urllib.parse.urlencode({"f[0]": f"p:{profile_type_id}", "page": page})
        return f"{self.listing_base}?{query}"

    def harvest(
        self,
        out_dir: Path,
        max_pages: int | None = None,
        limit: int | None = None,
    ) -> list[Path]:
        """Crawl each authorized construct facet, page by page (zero-indexed, 10
        results per page per the confirmed #101c pagination contract), extract
        detail pages, and store raw payloads.

        Args:
            out_dir: Directory where raw payloads and sidecars are stored.
            max_pages: Maximum number of pagination pages to crawl per construct facet.
            limit: Maximum total detail payloads to acquire, across all facets.

        Returns:
            List of Paths to saved raw payloads.
        """
        saved_paths: list[Path] = []
        seen_urls: set[str] = set()

        known_uris = self.get_known_source_uris(out_dir, self.source_id)
        for existing_path in known_uris.values():
            if existing_path not in saved_paths:
                saved_paths.append(existing_path)

        for profile_type_id in self.profile_type_ids:
            if limit is not None and len(saved_paths) >= limit:
                break
            self._harvest_construct_facet(
                profile_type_id=profile_type_id,
                out_dir=out_dir,
                max_pages=max_pages,
                limit=limit,
                known_uris=known_uris,
                seen_urls=seen_urls,
                saved_paths=saved_paths,
            )

        return saved_paths

    def _harvest_construct_facet(
        self,
        profile_type_id: int,
        out_dir: Path,
        max_pages: int | None,
        limit: int | None,
        known_uris: dict[str, Path],
        seen_urls: set[str],
        saved_paths: list[Path],
    ) -> None:
        page = 0

        while True:
            if max_pages is not None and page >= max_pages:
                break
            if limit is not None and len(saved_paths) >= limit:
                break

            listing_url = self._listing_url(profile_type_id, page)
            try:
                listing_bytes, _status = self.fetch_url(listing_url)
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

                if detail_url in known_uris:
                    logger.debug("Skipping already harvested URI: %s", detail_url)
                    continue

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

    def _determine_demand_id(self, html_bytes: bytes, url: str) -> str:
        """Determine demand_id from the embedded POD reference, falling back to a URL slug hash.

        Ports the fix from `EenPodHarvester._determine_demand_id` (commit b0b2c12,
        never applied here -- this harvester actually produced the live v2/v3
        data): the page's own authoritative "POD Reference" dt/dd pair is trusted
        verbatim first, before any unscoped full-page search. An unscoped
        `_POD_REF_RE.search(html_text)` as the *primary* strategy can pick up an
        unrelated reference belonging to a different proposal elsewhere on the
        page (e.g. a related-proposals list) -- the exact false-collision bug
        b0b2c12 fixed for the Lombardia mirror.
        """
        try:
            html_text = html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            html_text = html_bytes.decode("latin-1", errors="replace")

        soup = BeautifulSoup(html_text, "html.parser")
        dt = soup.find("dt", string=re.compile(r"POD\s+Reference", re.I))
        if dt:
            dd = dt.find_next_sibling("dd")
            if dd:
                ref_text = dd.get_text(strip=True)
                m_lead = _POD_REF_RE.search(ref_text)
                if m_lead:
                    return m_lead.group(1)
                sanitized = re.sub(r"[^A-Za-z0-9]", "", ref_text)
                if sanitized:
                    return sanitized

        # No scoped "POD Reference" dt/dd pair found -- fall back to an unscoped
        # full-page search (still better than nothing, but not the first resort).
        m_pod = _POD_REF_RE.search(html_text)
        if m_pod:
            return m_pod.group(1)

        # No recognized POD reference prefix found -- fall back to a URL-derived id.
        # Includes a full-URL hash suffix (not just a truncated slug) so two distinct
        # pages whose slugs happen to agree on their first 40 characters cannot
        # collide into the same synthetic demand_id.
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        return f"EEN-OFFICIAL-{slug[:40]}-{url_hash}"

    def _extract_proposal_links(self, html_bytes: bytes) -> list[str]:
        """Extract partnering-opportunities detail links from a listing page."""
        try:
            html_text = html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            html_text = html_bytes.decode("latin-1", errors="replace")

        soup = BeautifulSoup(html_text, "html.parser")
        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"]).strip()
            path = urllib.parse.urlsplit(href).path
            if _DETAIL_LINK_RE.match(path) and href not in links:
                links.append(href)
        return links
