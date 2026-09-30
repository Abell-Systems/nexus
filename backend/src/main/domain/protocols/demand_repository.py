from typing import Protocol, runtime_checkable

from domain.models.demand import DemandSignal


@runtime_checkable
class DemandRepository(Protocol):
    def get(self, demand_id: str) -> DemandSignal | None: ...

    def list_all(self) -> list[DemandSignal]: ...
