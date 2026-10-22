import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "backend" / "src" / "main"))
sys.path.insert(0, str(HERE / "tests"))

from harness.store_files import FilesStore  # noqa: E402
from harness.store_pg import PostgresStore  # noqa: E402
from harness.tables import rows_from_outcomes  # noqa: E402
from support import FILES, outcomes  # noqa: E402

@pytest.fixture
def rows():
    return rows_from_outcomes(outcomes(), FILES)


@pytest.fixture(params=["files", "postgres"])
def store(request, tmp_path):
    if request.param == "files":
        yield FilesStore(tmp_path / "files")
        return
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    s = PostgresStore(dsn, os.environ.get("NEXUS_BENCH_PG_CONTAINER", "nexus-spike-pg"), f"t{os.getpid()}")
    yield s
    import psycopg
    with psycopg.connect(dsn, autocommit=True) as c:
        for (n,) in c.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE %s", (f"t{os.getpid()}_%",)).fetchall():
            c.execute(f"DROP SCHEMA {n} CASCADE")
