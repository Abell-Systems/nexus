"""Deterministic race regressions: another process creates the destination at the first moment this code touches its path.

The racer is injected at every filesystem entry point the stores use (Path.exists, os.mkdir which Path.mkdir calls), so the same
test exercises a 'check then create' design (the race lands between the check and the creation) and an exclusive-creation design
(the race lands on the claim). Invariant: whatever the racer put there is never modified or deleted, and the operation does not
report success over it.
"""
import os
from pathlib import Path

import pytest
from harness.store_files import FilesStore


class Racer:
    def __init__(self, monkeypatch, dest: Path):
        self.dest, self.fired = Path(dest), False
        real_exists, real_mkdir = Path.exists, os.mkdir
        racer = self

        def fire():
            if not racer.fired:
                racer.fired = True
                real_mkdir(racer.dest)
                (racer.dest / "sentinel.txt").write_text("racer")

        def exists(path_self, *a, **k):
            if Path(path_self) == racer.dest:
                fire()
                return False  # the check is answered before the racer's creation became visible to it
            return real_exists(path_self, *a, **k)

        def mkdir(path, *a, **k):
            if Path(path) == racer.dest:
                fire()
            return real_mkdir(path, *a, **k)
        monkeypatch.setattr(Path, "exists", exists)
        monkeypatch.setattr(os, "mkdir", mkdir)

    def intact(self) -> bool:
        return (self.dest / "sentinel.txt").read_text() == "racer"


@pytest.fixture
def prepared(tmp_path, rows):
    s = FilesStore(tmp_path / "f")
    s.prepare("v1", rows)
    dump = tmp_path / "dump"
    s.backup("v1", dump)
    return s, dump


def test_shouldNotTouchADestinationCreatedConcurrentlyDuringPrepare(tmp_path, rows, monkeypatch):
    s = FilesStore(tmp_path / "f")
    racer = Racer(monkeypatch, s.root / "v2")
    with pytest.raises(FileExistsError):
        s.prepare("v2", rows)
    assert racer.fired and racer.intact()


def test_shouldNotTouchADestinationCreatedConcurrentlyDuringBackup(prepared, tmp_path, monkeypatch):
    s, _ = prepared
    racer = Racer(monkeypatch, tmp_path / "b2")
    with pytest.raises(FileExistsError):
        s.backup("v1", tmp_path / "b2")
    assert racer.fired and racer.intact()


def test_shouldNotTouchADestinationCreatedConcurrentlyDuringRestore(prepared, monkeypatch):
    s, dump = prepared
    racer = Racer(monkeypatch, s.root / "v2")
    with pytest.raises(FileExistsError):
        s.restore(dump, "v2")
    assert racer.fired and racer.intact()


def test_shouldNotTouchARootCreatedConcurrentlyDuringRestoreNew(prepared, monkeypatch):
    s, dump = prepared
    racer = Racer(monkeypatch, s.root.parent / (s.root.name + "_restored_new"))
    with pytest.raises(FileExistsError):
        s.restore_new(dump, "v1")
    assert racer.fired and racer.intact()


def test_shouldNotDeleteWhatAnotherProcessPutInTheClaimedDestinationWhenPublishingFails(tmp_path, rows, monkeypatch):
    """The claim is ours, but a racer wrote into it before our rename failed: cleanup must not delete that content."""
    s = FilesStore(tmp_path / "f")
    dest = s.root / "v2"
    real_rename = os.rename

    def rename(src, dst, *a, **k):
        if Path(dst) == dest:
            (dest / "sentinel.txt").write_text("racer")
            raise OSError("rename failed")
        return real_rename(src, dst, *a, **k)
    monkeypatch.setattr(os, "rename", rename)
    with pytest.raises(OSError):
        s.prepare("v2", rows)
    assert (dest / "sentinel.txt").read_text() == "racer"          # os.rmdir refuses a non-empty directory
    assert not (s.root / "v2.staging").exists()                      # our own staging was removed


def test_shouldReleaseItsOwnEmptyClaimWhenTheStagingNameIsTaken(tmp_path, rows):
    s = FilesStore(tmp_path / "f")
    (s.root / "v2.staging").mkdir()
    (s.root / "v2.staging" / "sentinel.txt").write_text("leftover")
    with pytest.raises(FileExistsError):
        s.prepare("v2", rows)
    assert not (s.root / "v2").exists()                              # the empty claim was released
    assert (s.root / "v2.staging" / "sentinel.txt").read_text() == "leftover"


def test_shouldTurnALostPostgresRaceIntoFileExistsErrorAndLeaveTheOtherSchemaIntact(tmp_path, rows, monkeypatch):
    import psycopg
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    from harness.store_pg import PostgresStore
    ns = f"r{os.getpid()}"
    s = PostgresStore(dsn, "nexus-spike-pg", ns)
    schema = f"{ns}_v1"
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f"CREATE SCHEMA {schema}; CREATE TABLE {schema}.sentinel(x int); INSERT INTO {schema}.sentinel VALUES (7)")
    monkeypatch.setattr(PostgresStore, "_exists", staticmethod(lambda conn, kind, name: False))  # the early check loses the race
    try:
        with pytest.raises(FileExistsError):
            s.prepare("v1", rows)
        with psycopg.connect(dsn, autocommit=True) as c:
            assert c.execute(f"SELECT x FROM {schema}.sentinel").fetchone() == (7,)
    finally:
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def test_shouldTurnALostRestoreNewDatabaseRaceIntoFileExistsErrorAndKeepTheOtherDatabase(tmp_path, monkeypatch):
    import psycopg
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    from harness.store_pg import PostgresStore
    ns = f"q{os.getpid()}"
    s = PostgresStore(dsn, "nexus-spike-pg", ns)
    db = f"{ns}_restored_new"
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f"CREATE DATABASE {db}")
    monkeypatch.setattr(PostgresStore, "_exists", staticmethod(lambda conn, kind, name: False))
    try:
        with pytest.raises(FileExistsError):
            s.restore_new(tmp_path / "irrelevant", "v1")
        with psycopg.connect(dsn, autocommit=True) as c:
            assert c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db,)).fetchone() is not None
    finally:
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")


def test_shouldNotDropAW7SchemaCreatedConcurrently(monkeypatch):
    import numpy as np
    import psycopg
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    from harness.operational import PgRetriever
    schema = f"w7r_{os.getpid()}"
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f"CREATE SCHEMA {schema}; CREATE TABLE {schema}.sentinel(x int); INSERT INTO {schema}.sentinel VALUES (9)")
    monkeypatch.setattr(PgRetriever, "_schema_exists", lambda self, s: False)
    try:
        with pytest.raises(FileExistsError):
            PgRetriever(dsn, schema, ["a"], np.ones((1, 4), dtype=np.float32), [0])
        with psycopg.connect(dsn, autocommit=True) as c:
            assert c.execute(f"SELECT x FROM {schema}.sentinel").fetchone() == (9,)
    finally:
        PgRetriever.remove_leftover_schema(dsn, schema)


def _pg_with_dump(tmp_path, rows, extra_sql=None, drop_after_dump=None):
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    import psycopg
    from harness.store_pg import PostgresStore
    s = PostgresStore(dsn, "nexus-spike-pg", f"z{os.getpid()}")
    schema = s._schema("v1")
    s.prepare("v1", rows)
    if extra_sql:
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(extra_sql.format(s=schema))
    dump = tmp_path / "dump"
    s.backup("v1", dump)
    s.drop("v1")
    if drop_after_dump:
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(drop_after_dump.format(s=schema))
    return dsn, s, dump, schema


def _tables(dsn, schema):
    import psycopg
    with psycopg.connect(dsn, autocommit=True) as c:
        return sorted(r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=%s", (schema,)))


def _drop(dsn, *schemas):
    import psycopg
    with psycopg.connect(dsn, autocommit=True) as c:
        for sch in schemas:
            c.execute(f"DROP SCHEMA IF EXISTS {sch} CASCADE")


def test_shouldNotWriteIntoASchemaCreatedBetweenTheEarlyCheckAndPgRestore(tmp_path, rows, monkeypatch):
    """The racer creates the schema after the early check passed and just before pg_restore starts."""
    import psycopg
    import harness.store_pg as sp
    dsn, s, dump, schema = _pg_with_dump(tmp_path, rows)
    real_run = sp.subprocess.run

    def run(cmd, *a, **k):
        if "pg_restore" in cmd:
            with psycopg.connect(dsn, autocommit=True) as c:
                c.execute(f"CREATE SCHEMA {schema}; CREATE TABLE {schema}.sentinel(x int); INSERT INTO {schema}.sentinel VALUES (5)")
        return real_run(cmd, *a, **k)
    monkeypatch.setattr(sp.subprocess, "run", run)
    try:
        with pytest.raises(FileExistsError):
            s.restore(dump, "v1")
        assert _tables(dsn, schema) == ["sentinel"]                      # nothing from the dump was written into their schema
        with psycopg.connect(dsn, autocommit=True) as c:
            assert c.execute(f"SELECT x FROM {schema}.sentinel").fetchone() == (5,)
    finally:
        _drop(dsn, schema)


def test_shouldLeaveNoPartialSchemaWhenARestoreFailsAfterCreatingObjects(tmp_path, rows):
    """A dump whose last step (a foreign key to a schema that no longer exists) fails after tables and data were restored."""
    import subprocess
    dsn, s, dump, schema = _pg_with_dump(
        tmp_path, rows,
        extra_sql="CREATE SCHEMA {s}_ref; CREATE TABLE {s}_ref.ref(id int PRIMARY KEY); CREATE TABLE {s}.extra(x int REFERENCES {s}_ref.ref(id))",
        drop_after_dump="DROP SCHEMA {s}_ref CASCADE")
    try:
        with pytest.raises(subprocess.CalledProcessError):
            s.restore(dump, "v1")
        assert _tables(dsn, schema) == []                                 # single transaction: nothing partial is left to block a retry
    finally:
        _drop(dsn, schema, f"{schema}_ref")


# ---- classification of pg_restore failures (review of 67c9f09) ----

class _Run:
    def __init__(self, stderr: bytes, code: int = 1):
        self.returncode, self.stderr, self.args = code, stderr, ["pg_restore"]


@pytest.mark.parametrize("stderr,is_race", [
    (b'pg_restore: error: could not execute query: ERROR:  schema "z_v1" already exists\nCommand was: CREATE SCHEMA z_v1;\n', True),
    # same words, but a different object created later by the restore: a real restore failure, not a lost claim
    (b'pg_restore: error: could not execute query: ERROR:  relation "party" already exists\nCommand was: CREATE TABLE z_v1.party (...);\n', False),
    (b'pg_restore: error: could not execute query: ERROR:  relation "x_pkey" already exists\nCommand was: ALTER TABLE ONLY z_v1.x ADD CONSTRAINT x_pkey ...;\n', False),
    # a schema that already exists, but not the one being restored
    (b'pg_restore: error: could not execute query: ERROR:  schema "other_v1" already exists\nCommand was: CREATE SCHEMA other_v1;\n', False),
    # the right schema name mentioned in the wrong statement
    (b'pg_restore: error: could not execute query: ERROR:  schema "z_v1" already exists\nCommand was: ALTER SCHEMA z_v1 OWNER TO postgres;\n', False),
])
def test_shouldTranslateOnlyTheClaimingStatementFailureIntoFileExistsError(tmp_path, monkeypatch, stderr, is_race):
    import subprocess
    import harness.store_pg as sp
    from harness.store_pg import PostgresStore
    s = PostgresStore("host=127.0.0.1 port=1", "c", "z")          # never connects: the early check and pg_restore are both faked
    monkeypatch.setattr(PostgresStore, "_conn", lambda self: _NoConn())
    monkeypatch.setattr(PostgresStore, "_exists", staticmethod(lambda conn, kind, name: False))
    monkeypatch.setattr(sp.subprocess, "run", lambda cmd, *a, **k: _Run(stderr))
    dump = tmp_path / "d"
    dump.write_bytes(b"x")
    if is_race:
        with pytest.raises(FileExistsError):
            s.restore(dump, "v1")
    else:
        with pytest.raises(subprocess.CalledProcessError) as exc:
            s.restore(dump, "v1")
        assert exc.value.stderr == stderr


class _NoConn:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
