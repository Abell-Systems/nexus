"""Session mechanics fixed by the protocol (R1 §2, R2 item 3): alternation, valid-run gate, environment capture."""
import os
import platform
import sys
import time
from collections.abc import Callable

LOAD_LIMIT, LOAD_WAIT_SECONDS = 1.0, 300.0


class Incident(Exception):
    """The run cannot count: its cause is outside the alternative's behaviour. Recorded, not graded, repeated."""


def order_for(repetition: int) -> tuple[str, str]:
    """Warm runs alternate A/B: A first in odd repetitions, B first in even ones."""
    return ("A", "B") if repetition % 2 == 1 else ("B", "A")


def wait_for_quiet(loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg, sleep: Callable[[float], None] = time.sleep,
                   clock: Callable[[], float] = time.monotonic, limit: float = LOAD_LIMIT, timeout: float = LOAD_WAIT_SECONDS) -> float:
    """R2 item 3(c): the 1-minute load average must be <= `limit` before a warm run starts; wait up to `timeout`, else incident.
    Returns the load at which the run started, to be recorded with it."""
    deadline = clock() + timeout
    while True:
        load = loadavg()[0]
        if load <= limit:
            return load
        if clock() >= deadline:
            raise Incident(f"1-minute load average {load:.2f} > {limit} for {timeout:.0f} s before the run")
        sleep(5.0)


def capture_environment(stores: dict) -> dict:
    import importlib.metadata as md

    def v(pkg):
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return None

    return {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(), "cpu_count": os.cpu_count(),
            "packages": {p: v(p) for p in ("duckdb", "pyarrow", "psycopg", "pgvector", "numpy")},
            "stores": {name: s.configuration() for name, s in stores.items()}}
