from typing import Protocol, runtime_checkable

from domain.models.demand import DemandSignal


@runtime_checkable
class DemandRepository(Protocol):
    """Port for the demands a product screen may offer."""

    def get(self, demand_id: str) -> DemandSignal | None: ...

    def list_all(self) -> list[DemandSignal]: ...
