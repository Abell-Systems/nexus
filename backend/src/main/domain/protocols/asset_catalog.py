from typing import Protocol, runtime_checkable

from domain.models.asset import Asset


@runtime_checkable
class AssetCatalog(Protocol):
    def get(self, publication_id: str) -> Asset: ...

    def list_all(self) -> list[Asset]: ...
