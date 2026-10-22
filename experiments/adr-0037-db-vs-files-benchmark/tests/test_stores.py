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
