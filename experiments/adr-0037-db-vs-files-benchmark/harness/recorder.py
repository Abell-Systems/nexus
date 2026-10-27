"""Timing records with an enforced separation of preparation and execution (pre-registration §2, §3)."""
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Phase = Literal["prepare", "execute"]
RunKind = Literal["first_run_after_start", "warm"]


@dataclass(frozen=True)
class Entry:
    workload: str
    alternative: str
    phase: Phase
    label: str
    run_kind: RunKind
    repetition: int
    order_in_repetition: int
    seconds: float


class Recorder:
    def __init__(self, clock=time.perf_counter) -> None:
        self._clock = clock
        self.entries: list[Entry] = []
        self._open: tuple[str, str] | None = None

    @contextmanager
    def section(self, *, workload: str, alternative: str, phase: Phase, label: str, run_kind: RunKind,
                repetition: int, order_in_repetition: int) -> Iterator[None]:
        if self._open is not None:
            raise RuntimeError(f"section {self._open} still open: phases must not nest, they would double count")
        self._open = (workload, label)
        start = self._clock()
        try:
            yield
        finally:
            seconds = self._clock() - start
            self._open = None
            self.entries.append(Entry(workload, alternative, phase, label, run_kind, repetition, order_in_repetition, seconds))

    def summary(self, workload: str, alternative: str, phase: Phase, label: str) -> dict:
        warm = sorted(e.seconds for e in self.entries if (e.workload, e.alternative, e.phase, e.label, e.run_kind) ==
                      (workload, alternative, phase, label, "warm"))
        if not warm:
            return {"warm_runs": 0}
        mid = len(warm) // 2
        median = warm[mid] if len(warm) % 2 else (warm[mid - 1] + warm[mid]) / 2
        return {"warm_runs": len(warm), "min": warm[0], "median": median, "max": warm[-1]}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(e) for e in self.entries], indent=1))


def materially_different(a: dict, b: dict) -> bool:
    """Pre-registration §5: ranges must not overlap AND medians differ by at least 2x. Otherwise not distinguishable."""
    if not a.get("warm_runs") or not b.get("warm_runs"):
        return False
    disjoint = a["max"] < b["min"] or b["max"] < a["min"]
    lo, hi = sorted((a["median"], b["median"]))
    return disjoint and lo > 0 and hi / lo >= 2
