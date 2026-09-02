"""EPO OPS (European Patent Office Open Patent Services 3.2) client adapter."""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Iterator
import httpx

from nexus.domain.protocols.sources import RawPayload


class EpoOpsClient:
    """Production client and fixture loader for European Patent Office Open Patent Services (OPS 3.2)."""

    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        base_url: str = "https://ops.epo.org/3.2/rest-services",
        auth_url: str = "https://ops.epo.org/3.2/auth/accesstoken",
        fixture_path: Path | str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.consumer_key = consumer_key or os.getenv("EPO_OPS_KEY")
        self.consumer_secret = consumer_secret or os.getenv("EPO_OPS_SECRET")
        self.base_url = base_url.rstrip("/")
        self.auth_url = auth_url
        self.fixture_path = Path(fixture_path) if fixture_path else None
        self.timeout = timeout
        self.transport = transport
        self._access_token: str | None = None

    @classmethod
    def from_fixture_file(
        cls,
        xml_fixture_path: Path | str,
        base_url: str = "https://ops.epo.org/3.2/rest-services",
    ) -> "EpoOpsClient":
        """Factory method to instantiate a client backed deterministically by an XML fixture file."""
        return cls(fixture_path=xml_fixture_path, base_url=base_url)

    def authenticate(self, client: httpx.Client | None = None) -> bool:
        """Obtain OAuth 2.0 bearer token from EPO OPS authorization service."""
        if not self.consumer_key or not self.consumer_secret:
            return False

        auth = (self.consumer_key, self.consumer_secret)
        data = {"grant_type": "client_credentials"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        def _do_auth(c: httpx.Client) -> bool:
            try:
                resp = c.post(
                    self.auth_url,
                    auth=auth,
                    data=data,
                    headers=headers,
                    timeout=self.timeout,
                )
                if resp.status_code != 200:
                    return False
                payload = resp.json()
                self._access_token = payload.get("access_token")
                return bool(self._access_token)
            except Exception:
                return False

        if client is not None:
            return _do_auth(client)
        with httpx.Client(transport=self.transport) as c:
            return _do_auth(c)

    def fetch_batches(
        self,
        cql_query: str = "pd within '2016 2024' and pn=ES",
        range_start: int = 1,
        range_end: int = 25,
    ) -> Iterator[RawPayload]:
        """Fetch raw XML payload batches from EPO OPS or offline fixture file."""
        if self.fixture_path is not None:
            if not self.fixture_path.exists():
                raise FileNotFoundError(f"EPO OPS fixture file not found at: {self.fixture_path}")

            raw_bytes = self.fixture_path.read_bytes()
            metadata: dict[str, Any] = {
                "source_authority": "European Patent Office (EPO OPS 3.2)",
                "official_catalog_url": "https://ops.epo.org",
                "source_type": "fixture",
                "fixture_path": str(self.fixture_path),
                "cql_query": cql_query,
                "content_type": "application/xml",
            }
            yield RawPayload(
                source_id="epo_ops",
                batch_id="batch_fixture_0001",
                payload_bytes=raw_bytes,
                metadata=metadata,
                retrieval_timestamp=datetime.now(timezone.utc),
            )
            return

        if not self.consumer_key or not self.consumer_secret:
            raise RuntimeError(
                "EPO OPS API credentials missing. Provide consumer_key and consumer_secret or use from_fixture_file."
            )

        with httpx.Client(transport=self.transport) as client:
            if not self._access_token:
                authenticated = self.authenticate(client)
                if not authenticated or not self._access_token:
                    raise RuntimeError("EPO OPS Authentication failed (invalid credentials or auth error).")

            search_url = f"{self.base_url}/published-data/search/biblio"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/xml",
            }
            params = {
                "q": cql_query,
                "Range": f"{range_start}-{range_end}",
            }

            try:
                resp = client.get(search_url, params=params, headers=headers, timeout=self.timeout)
            except Exception as e:
                raise RuntimeError(f"EPO OPS Search/Fetch failed: {e}") from e

            if resp.status_code != 200:
                raise RuntimeError(f"EPO OPS Search/Fetch failed with status {resp.status_code}: {resp.text}")

            raw_bytes = resp.content
            metadata = {
                "source_authority": "European Patent Office (EPO OPS 3.2)",
                "official_catalog_url": "https://ops.epo.org",
                "source_type": "rest_api",
                "cql_query": cql_query,
                "range": f"{range_start}-{range_end}",
                "content_type": "application/xml",
            }

            yield RawPayload(
                source_id="epo_ops",
                batch_id=f"epo_batch_{range_start}_{range_end}",
                payload_bytes=raw_bytes,
                metadata=metadata,
                retrieval_timestamp=datetime.now(timezone.utc),
            )
