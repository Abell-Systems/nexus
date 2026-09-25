"""INVENES public search harvester (ADR 0035 SS4/SS11.3).

Targets consultas2.oepm.es/InvenesWeb -- OEPM's public patent/utility-model
search, confirmed to require NO registration (unlike the OpenData bulk XML
portal and the direct BOPI download portal, both registration-walled -- see
docs/adr/0035-oepm-production-scale-patent-corpus-contract.md SS4 and the
2026-09-14 session that found this). The Spanish-original text (title,
abstract) requires an Accept-Language: es-ES header -- without it, the site
silently serves an English machine-translation with no visual indicator other
than a disclaimer text, which would violate ADR 0035 SS5's no-translation
requirement.
"""

from pathlib import Path

from experiments.phase2.harvesters.base import BaseHarvester, PayloadCollisionError

SOURCE_ID = "oepm_invenes"
_SPANISH_ORIGINAL_HEADERS = {"Accept-Language": "es-ES,es;q=0.9"}


class InvenesHarvester(BaseHarvester):
    """Fetches real INVENES detail pages for a given list of `referencia` ids."""

    def __init__(
        self,
        delay_seconds: float = 1.0,
        user_agent: str | None = None,
        timeout_seconds: float = 30.0,
        base_url: str = "https://consultas2.oepm.es/InvenesWeb",
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, user_agent=user_agent, timeout_seconds=timeout_seconds)
        self.base_url = base_url.rstrip("/")
        self.source_id = SOURCE_ID

    def detail_url(self, referencia: str) -> str:
        return f"{self.base_url}/detalle?referencia={referencia}"

    def harvest(self, referencias: list[str], out_dir: Path) -> list[Path]:
        """Fetch each referencia's detail page (Spanish original), staging it
        immutably. Idempotent: already-harvested referencias are skipped."""
        saved_paths: list[Path] = []
        known_uris = self.get_known_source_uris(out_dir, self.source_id)
        known_referencias = {
            Path(p).stem for p in known_uris.values()
        }

        for referencia in referencias:
            if referencia in known_referencias:
                saved_paths.append(out_dir / self.source_id / f"{referencia}.html")
                continue

            url = self.detail_url(referencia)
            try:
                html_bytes, status = self.fetch_url(url, extra_headers=_SPANISH_ORIGINAL_HEADERS)
                saved = self.save_raw_payload(
                    demand_id=referencia,
                    source_id=self.source_id,
                    source_uri=url,
                    payload_bytes=html_bytes,
                    out_dir=out_dir,
                    metadata={"http_status": status, "file_extension": ".html"},
                )
                saved_paths.append(saved)
            except PayloadCollisionError:
                raise
            except Exception as exc:
                self.record_error(
                    source_id=self.source_id,
                    uri=url,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    demand_id=referencia,
                    http_status=getattr(exc, "code", None),
                )
                continue

        return saved_paths
