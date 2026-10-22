"""Correctness of the harness stores on synthetic data. Not measurements: nothing here is timed or graded."""
import pytest
from application.whitespace.analysis_records import to_analysis_records
from harness.compare import compare_load_checks, compare_records
from harness.contract import IntegrityError
from support import outcomes


def expected():
    return to_analysis_records(outcomes())


def test_shouldReadTheSameRecordsAsTheAdapterPathInOrder(store, rows):
    store.prepare("v1", rows)
    assert compare_records(expected(), store.read_records("v1")).equal


def test_shouldOrderMixedCaseSymbolsByCodePoint(store, rows):
    store.prepare("v1", rows)
    assert store.read_records("v1")[1].subclasses == ("A61K", "A61k")


def test_shouldCountTheSyntheticCorpusConsistently(store, rows):
    store.prepare("v1", rows)
    assert store.load_checks("v1") == {"publications": 3, "rejected": 1, "subclasses": 6, "without_ipc": 1, "distinct_doc_id": 2}


def test_shouldVerifyAFreshVersionAndReturnItsManifestDigest(store, rows):
    made = store.prepare("v1", rows)
    assert store.verify("v1") == made


@pytest.mark.parametrize("kind", ["change_subclass", "flip_byte", "delete_object"])
def test_shouldFailExplicitlyWhenTheStoredCopyIsAltered(store, rows, kind):
    store.prepare("v1", rows)
    store.alter("v1", kind)
    with pytest.raises(IntegrityError):
        store.verify("v1")


def test_shouldNotChangeTheSharedRowsWhenStoredCopyIsAltered(store, rows):
    snapshot = {k: list(v) for k, v in rows.items()}
    store.prepare("v1", rows)
    store.alter("v1", "change_subclass")
    assert rows == snapshot


def test_shouldRefuseToOverwriteAnExistingVersion(store, rows):
    store.prepare("v1", rows)
    with pytest.raises(FileExistsError):
        store.prepare("v1", rows)


def test_shouldLeaveThePreviousVersionIntactWhenANewVersionIsBuiltAndAltered(store, rows):
    before = store.prepare("v1", rows)
    store.prepare("v2", rows)
    store.alter("v2", "change_subclass")
    assert store.verify("v1") == before


def test_shouldRestoreABackupAndVerifyIt(store, rows, tmp_path):
    made = store.prepare("v1", rows)
    dump = tmp_path / "dump"
    store.backup("v1", dump)
    store.drop("v1")
    store.restore(dump, "v1")
    assert store.verify("v1") == made
    assert compare_records(expected(), store.read_records("v1")).equal


def test_shouldRefuseToRestoreOverAnExistingVersion(store, rows, tmp_path):
    store.prepare("v1", rows)
    dump = tmp_path / "dump"
    store.backup("v1", dump)
    before = store.verify("v1")
    with pytest.raises(FileExistsError):
        store.restore(dump, "v1")
    assert store.verify("v1") == before  # the existing version is untouched and still verifies


def test_shouldReportConfigurationThatCanAffectResults(store):
    cfg = store.configuration()
    assert "engine" in cfg and "constraints" in cfg


def test_shouldHaveEqualLogicalContentAcrossStoresAndEqualToTheSourceRows(store, rows):
    from harness.tables import canonical_rows_digest
    store.prepare("v1", rows)
    assert store.logical_digest("v1") == canonical_rows_digest(rows)


def test_shouldChangeTheLogicalDigestWhenContentIsAltered(store, rows):
    from harness.tables import canonical_rows_digest
    store.prepare("v1", rows)
    store.alter("v1", "change_subclass")
    try:
        digest = store.logical_digest("v1")
    except Exception:  # an unreadable copy is also a difference
        return
    assert digest != canonical_rows_digest(rows)


@pytest.mark.parametrize("table,row", [
    ("ipc_entry", (1, 99, "ZZZZ", None, None, None, None, None)),   # unknown subclass
    ("priority_date", (999, 0, None)),                              # unknown record
])
def test_shouldRejectRowsWithMissingReferencesInBothStores(store, rows, table, row):
    from harness.tables import ReferentialError
    rows[table].append(row)
    with pytest.raises(ReferentialError):
        store.prepare("v1", rows)
    # nothing is published
    with pytest.raises(Exception):
        store.verify("v1")


def test_shouldProduceIdenticalFilesWhenTheSameRowsArePreparedTwice(tmp_path, rows):
    """Determinism of the Parquet writer on this machine and version; if it fails, hash changes cannot be read as corpus changes."""
    from harness.store_files import FilesStore
    s = FilesStore(tmp_path / "f")
    a, b = s.prepare("v1", rows), s.prepare("v2", rows)
    assert a.manifest_digest == b.manifest_digest


@pytest.mark.parametrize("table,mutate", [
    ("source_record", lambda r: r.append((99, r[0][1], r[0][2]))),             # same (file_id, archive_path), new record_id
    ("party", lambda r: r.append((1, "agent", 9, "X"))),                       # role outside the allowed values
    ("publication", lambda r: r.append(r[0])),                                 # duplicate primary key
])
def test_shouldRejectRowsViolatingUniqueAllowedOrKeyConstraintsInBothStores(store, rows, table, mutate):
    from harness.tables import ConstraintError
    mutate(rows[table])
    with pytest.raises(ConstraintError):
        store.prepare("v1", rows)
    with pytest.raises(Exception):
        store.verify("v1")  # nothing published


def test_shouldFindNoEnvironmentProblemWhenTheStoreIsHealthy(store):
    assert store.environment_problems(1) == []


def test_shouldReportEvidenceWhenThereIsNotEnoughDiskOrTheContainerIsMissing(store):
    from harness.store_pg import PostgresStore
    if isinstance(store, PostgresStore):
        store.container = "no-such-container-xyz"
        assert any("not running" in p for p in store.environment_problems(1))
    else:
        assert store.environment_problems(10**18)


# ---- fourth review of 2026-10-22: no pre-existing resource is modified or deleted because a run fails to create it ----

def test_shouldNeverDeleteAPreExistingStagingDirectory(tmp_path, rows):
    from harness.store_files import FilesStore
    s = FilesStore(tmp_path / "f")
    leftover = s.root / "v1.staging"
    leftover.mkdir()
    (leftover / "sentinel.txt").write_text("not ours")
    with pytest.raises(FileExistsError):
        s.prepare("v1", rows)
    assert (leftover / "sentinel.txt").read_text() == "not ours" and not (s.root / "v1").exists()
    assert s.remove_leftover_staging("v1") == leftover and not leftover.exists()  # explicit, traceable, on request only


def test_shouldRemoveOnlyTheStagingItCreatedWhenPrepareFailsMidway(tmp_path, rows, monkeypatch):
    import harness.store_files as sf
    from harness.store_files import FilesStore
    s = FilesStore(tmp_path / "f")
    calls = {"n": 0}
    real = sf._write

    def failing(path, t, r):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("disk full")
        return real(path, t, r)
    monkeypatch.setattr(sf, "_write", failing)
    with pytest.raises(OSError):
        s.prepare("v1", rows)
    assert not (s.root / "v1.staging").exists() and not (s.root / "v1").exists()


def test_shouldRemoveTheDirectoryItCreatedWhenRestoreNewFails(tmp_path, rows, monkeypatch):
    from harness.store_files import FilesStore
    s = FilesStore(tmp_path / "f")
    s.prepare("v1", rows)
    dump = tmp_path / "d"
    s.backup("v1", dump)
    monkeypatch.setattr(FilesStore, "restore", lambda self, src, v: (_ for _ in ()).throw(OSError("copy failed")))
    with pytest.raises(OSError):
        s.restore_new(dump, "v1")
    assert not (s.root.parent / (s.root.name + "_restored_new")).exists()


def test_shouldNeverOverwriteAnExistingBackup(store, rows, tmp_path):
    store.prepare("v1", rows)
    dump = tmp_path / "dump"
    if dump.suffix == "" and type(store).__name__ == "FilesStore":
        dump.mkdir()
        (dump / "sentinel.txt").write_text("not ours")
        marker = dump / "sentinel.txt"
    else:
        dump.write_bytes(b"not ours")
        marker = dump
    with pytest.raises(FileExistsError):
        store.backup("v1", dump)
    assert marker.read_bytes() in (b"not ours",)


def test_shouldCloseTheDuckDbConnectionWhenInitialisationFails(tmp_path, rows, monkeypatch):
    import duckdb
    import harness.store_files as sf
    from harness.store_files import FilesStore
    s = FilesStore(tmp_path / "f")
    s.prepare("v1", rows)
    (s.root / "v1" / "party.parquet").unlink()
    opened, closed = [], []
    real = duckdb.connect

    class Spy:
        def __init__(self):
            self.inner = real()
            opened.append(self)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def close(self):
            closed.append(self)
            self.inner.close()
    monkeypatch.setattr(sf.duckdb, "connect", lambda *a, **k: Spy())
    with pytest.raises(Exception):
        s.read_records("v1")
    assert len(opened) == 1 and len(closed) == 1


def test_shouldDropTheDatabaseItCreatedWhenPgRestoreFailsAndNotOneItDidNot(tmp_path, rows):
    import os
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    import subprocess
    import psycopg
    from harness.store_pg import PostgresStore
    ns = f"y{os.getpid()}"
    s = PostgresStore(dsn, os.environ.get("NEXUS_BENCH_PG_CONTAINER", "nexus-spike-pg"), ns)
    garbage = tmp_path / "garbage"
    garbage.write_bytes(b"this is not a pg_dump archive")
    with pytest.raises(subprocess.CalledProcessError):
        s.restore_new(garbage, "v1")
    with psycopg.connect(dsn, autocommit=True) as c:
        assert c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (f"{ns}_restored_new",)).fetchone() is None
