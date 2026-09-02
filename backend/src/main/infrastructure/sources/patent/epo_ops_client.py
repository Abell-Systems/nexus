"""EPO OPS (European Patent Office Open Patent Services 3.2) client adapter."""

import base64
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from domain.protocols.sources import PatentSourceProtocol, RawPayload

APPLICATION_XML = "application/xml"


class EpoOpsClient(PatentSourceProtocol):
    """EPO Open Patent Services (OPS) v3.2 Client implementing PatentSourceProtocol."""

    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        fixture_path: Path | str | None = None,
        base_url: str = "https://ops.epo.org/3.2/rest-services",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.consumer_key = consumer_key or os.getenv("EPO_OPS_KEY")
        self.consumer_secret = consumer_secret or os.getenv("EPO_OPS_SECRET")
        self.fixture_path = Path(fixture_path) if fixture_path else None
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self._access_token: str | None = None

    @classmethod
    def from_fixture_file(cls, fixture_path: Path | str) -> "EpoOpsClient":
        """Factory method to initialize client in offline fixture replay mode."""
        return cls(fixture_path=fixture_path)

    def authenticate(self, client: httpx.Client) -> bool:
        """Obtain OAuth 2.0 Client Credentials Bearer Token from EPO OPS."""
        if not self.consumer_key or not self.consumer_secret:
            return False

        auth_header = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode("ascii")
        url = f"{self.base_url.replace('/rest-services', '')}/auth/accesstoken"
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        try:
            resp = client.post(url, headers=headers, data=data, timeout=30.0)
            if resp.status_code == 200:
                payload = resp.json()
                self._access_token = payload.get("access_token")
                return True
        except Exception:
            return False
        return False

    def fetch_batches(
        self,
        cql_query: str = 'ta="solid state battery" AND pn="ES"',
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
                "content_type": APPLICATION_XML,
            }
            yield RawPayload(
                source_id="epo_ops",
                batch_id="batch_fixture_0001",
                payload_bytes=raw_bytes,
                metadata=metadata,
                retrieval_timestamp=datetime.now(UTC),
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
                "Accept": APPLICATION_XML,
            }
            params = {
                "q": cql_query,
                "Range": f"{range_start}-{range_end}",
            }
            resp = client.get(search_url, headers=headers, params=params, timeout=30.0)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"EPO OPS Search/Fetch failed with status {resp.status_code}: {resp.text}"
                )

            raw_bytes = resp.content
            metadata = {
                "source_authority": "European Patent Office (EPO OPS 3.2)",
                "official_catalog_url": "https://ops.epo.org",
                "source_type": "api",
                "cql_query": cql_query,
                "range": f"{range_start}-{range_end}",
                "status_code": resp.status_code,
                "content_type": APPLICATION_XML,
            }

            yield RawPayload(
                source_id="epo_ops",
                batch_id=f"epo_batch_{range_start}_{range_end}",
                payload_bytes=raw_bytes,
                metadata=metadata,
                retrieval_timestamp=datetime.now(UTC),
            )
