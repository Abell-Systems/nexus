"""Orchestration on the synthetic corpus: statuses, classification rules, C3, roll-up. Not measurements."""
import pytest
from application.whitespace.analysis_records import to_analysis_records
from application.whitespace.subclass_pairs import subclass_pairs
from harness.compare import LOAD_CHECKS
from harness.contract import EXIT_FAIL, EXIT_INCIDENT, EXIT_PASS, IntegrityError
from harness.recorder import Recorder
from harness.session import Incident, order_for, wait_for_quiet
from harness.tables import rows_from_outcomes
from harness.workloads import (C3_BOUND_SECONDS, Context, Reference, evaluate, run_biblio_session, w1_prepare, w2_report, w3_verify,
                               w6_recovery)
from support import FILES, outcomes


def pairs_fn(records, origin):
    return subclass_pairs(records, origin, min_documents=1)


def make_ref():
    rows = rows_from_outcomes(outcomes(), FILES)
    records = to_analysis_records(outcomes())
    expected = {str(o): pairs_fn(records, o) for o in (2006, 2022)}
    return Reference(rows=rows, records=records, pairs_expected=expected, pairs_fn=pairs_fn)


@pytest.fixture
def ctx(tmp_path):
    from harness.store_files import FilesStore
    c = Context(stores={"B": FilesStore(tmp_path / "b")}, reference=make_ref(), recorder=Recorder(), quiet=lambda: 0.1)
    return c


def test_shouldRunAFullSyntheticSessionForStoreBAndPassEveryGradedCriterion(ctx, tmp_path):
    results = run_biblio_session(ctx, tmp_path, alternatives=("B",))
    code, table = evaluate(results, ("B",))
    assert table["B"]["incidents"] == 0, [r for r in results if r["status"] != "ok"][:3]
    assert {k: table["B"][k] for k in ("C1", "C2", "C4", "C5")} == dict(C1=True, C2=True, C4=True, C5=True)
    assert table["B"]["C3_stats"]["n"] == 5


def test_shouldRunAFullSyntheticSessionForStoreAWhenPostgresIsAvailable(tmp_path):
    import os
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    import psycopg
    from harness.store_pg import PostgresStore
    ns = f"o{os.getpid()}"
    c = Context(stores={"A": PostgresStore(dsn, os.environ.get("NEXUS_BENCH_PG_CONTAINER", "nexus-spike-pg"), ns)},
                reference=make_ref(), recorder=Recorder(), quiet=lambda: 0.1)
    try:
        results = run_biblio_session(c, tmp_path, alternatives=("A",))
        code, table = evaluate(results, ("A",))
        assert table["A"]["incidents"] == 0, [r for r in results if r["status"] != "ok"][:3]
        assert {k: table["A"][k] for k in ("C1", "C2", "C4", "C5")} == dict(C1=True, C2=True, C4=True, C5=True)
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            for (n,) in conn.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE %s", (f"{ns}_%",)).fetchall():
                conn.execute(f"DROP SCHEMA {n} CASCADE")
            conn.execute(f"DROP DATABASE IF EXISTS {ns}_restored_new WITH (FORCE)")


def test_shouldAlternateWhichAlternativeRunsFirstByRepetition():
    assert [order_for(r)[0] for r in (1, 2, 3, 4, 5)] == ["A", "B", "A", "B", "A"]


def test_shouldWaitForQuietThenReturnTheLoadAtStart():
    loads = iter([2.5, 1.7, 0.4])
    slept = []
    assert wait_for_quiet(lambda: (next(loads), 0, 0), slept.append, lambda: 0.0) == 0.4 and len(slept) == 2


def test_shouldDeclareAnIncidentWhenTheMachineNeverQuiets():
    t = iter(range(0, 1000, 100))
    with pytest.raises(Incident):
        wait_for_quiet(lambda: (3.0, 0, 0), lambda s: None, lambda: next(t), timeout=300)


def test_shouldMarkAWarmRunAsIncidentWhenTheGateFails(ctx):
    def noisy():
        raise Incident("load")
    ctx.quiet = noisy
    ctx.stores["B"].prepare("v", ctx.reference.rows)
    r = w2_report(ctx, "B", 1, "warm", "v")
    assert r["status"] == "incident" and r["checks"] == {}


def test_shouldCountAnIntegrityErrorOnAnUnalteredVersionAsACheckFailureNotAnIncident(ctx):
    ctx.stores["B"].prepare("v", ctx.reference.rows)
    ctx.stores["B"].alter("v", "flip_byte")
    r = w3_verify(ctx, "B", 0, "first_run_after_start", "v", "whatever")
    assert r["status"] == "check_failed"


def test_shouldClassifyAnUnexpectedExceptionAsAnIncident(ctx):
    r = w2_report(ctx, "B", 0, "first_run_after_start", "does-not-exist")
    assert r["status"] == "incident" and "error" not in r["outputs"]


def test_shouldCountAFailedRestoreAfterTheDropAsACheckFailure(ctx, tmp_path, monkeypatch):
    store = ctx.stores["B"]
    real = type(store).restore

    def failing(self, src, v):
        if v.startswith("w6b"):
            raise OSError("disk")
        return real(self, src, v)
    monkeypatch.setattr(type(store), "restore", failing)
    a, b = w6_recovery(ctx, "B", tmp_path)
    assert a["status"] == "ok" and b["status"] == "check_failed"


def row(workload, alt, status="ok", run_kind="warm", outputs=None, checks=None):
    return {"workload": workload, "alternative": alt, "status": status, "run_kind": run_kind, "outputs": outputs or {}, "checks": checks or {}}


def full(alt, totals, w4=(True, True, True), w6=("ok", "ok")):
    rs = [row("W1", alt), row("W2", alt, "ok", "first_run_after_start", {"total_seconds": 999.0})]
    rs += [row("W2", alt, outputs={"total_seconds": t}) for t in totals]
    rs += [row("W4", alt, outputs={"kind": k, "detected": d}) for k, d in zip(("change_subclass", "flip_byte", "delete_object"), w4)]
    content = {"pairs_equal": True, "records_equal": True, "digest_equal": True}
    rs += [row("W5", alt), row("W6a", alt, w6[0], checks=dict(content)), row("W6b", alt, w6[1], checks=dict(content))]
    return rs


def test_shouldPassWhenEveryWarmRunIsWithinTheBoundAndIgnoreTheFirstRun():
    code, t = evaluate(full("A", [1, 2, 3, 4, 5]) + full("B", [10] * 5))
    assert code == EXIT_PASS and t["A"]["C3_stats"]["max"] == 5


def test_shouldFailC3WhenOneValidWarmRunExceedsTheBoundEvenIfTheMedianIsFine():
    code, t = evaluate(full("A", [1, 1, 1, 1, C3_BOUND_SECONDS + 0.1]) + full("B", [1] * 5))
    assert code == EXIT_FAIL and not t["A"]["C3"] and t["A"]["C3_stats"]["median"] == 1


def test_shouldFailC3WhenFewerThanFiveValidWarmRunsExist():
    code, t = evaluate(full("A", [1, 1, 1, 1]) + full("B", [1] * 5))
    assert code == EXIT_FAIL and not t["A"]["C3"]


def test_shouldFailC2WhenAnAlterationIsNotDetected():
    code, t = evaluate(full("A", [1] * 5, w4=(True, False, True)) + full("B", [1] * 5))
    assert code == EXIT_FAIL and not t["A"]["C2"] and t["B"]["C2"]


def test_shouldFailC4WhenEitherRecoveryProcedureFails():
    code, t = evaluate(full("A", [1] * 5, w6=("ok", "check_failed")) + full("B", [1] * 5))
    assert code == EXIT_FAIL and not t["A"]["C4"]


def test_shouldReportAnIncidentExitCodeWhileAnIncidentIsUnresolved():
    rs = full("A", [1] * 5) + full("B", [1] * 5) + [row("W2", "B", "incident")]
    assert evaluate(rs)[0] == EXIT_INCIDENT


def test_shouldRefuseAnEmptyReference():
    with pytest.raises(ValueError):
        Reference(rows={}, records=[], pairs_expected={}, pairs_fn=pairs_fn)


def test_shouldFailTheRollUpWhenOperationalRetrievalOrderDiffers():
    rs = full("A", [1] * 5) + full("B", [1] * 5) + [row("W7", "A", "check_failed")]
    code, t = evaluate(rs)
    assert code == EXIT_FAIL and t["A"]["W7_ids_order"] is False and t["B"]["W7_ids_order"] is None


# ---- review findings of 2026-10-22 ----

def test_shouldCreateTheBackupDirectoryWhenItDoesNotExist(ctx, tmp_path):
    missing = tmp_path / "no" / "such" / "backups"
    a, b = w6_recovery(ctx, "B", missing)
    assert (a["status"], b["status"]) == ("ok", "ok") and missing.is_dir()


def _w6b_after_drop_fails(ctx, monkeypatch, problems):
    store = ctx.stores["B"]
    real = type(store).restore

    def failing(self, src, v):
        if v.startswith("w6b"):
            raise OSError("restore failed")
        return real(self, src, v)
    monkeypatch.setattr(type(store), "restore", failing)
    monkeypatch.setattr(type(store), "environment_problems", lambda self, n: problems)


def test_shouldRecordTheDropStateAndNoEnvironmentEvidenceWhenW6bFailsAfterTheDrop(ctx, tmp_path, monkeypatch):
    _w6b_after_drop_fails(ctx, monkeypatch, [])
    _, b = w6_recovery(ctx, "B", tmp_path)
    assert b["status"] == "check_failed"
    assert b["outputs"]["original_dropped"] is True and b["outputs"]["phase"] == "restore_in_place" and b["outputs"]["environment_problems"] == []


def test_shouldCallItAnIncidentWithEvidenceWhenAnEnvironmentCauseIsFoundAtTheTimeOfTheFailure(ctx, tmp_path, monkeypatch):
    _w6b_after_drop_fails(ctx, monkeypatch, ["free disk space 10 < 1000"])
    _, b = w6_recovery(ctx, "B", tmp_path)
    assert b["status"] == "incident" and "free disk space" in b["incident"]


def test_shouldNotCallAFailureBeforeTheDropAProcedureFailure(ctx, tmp_path, monkeypatch):
    store = ctx.stores["B"]
    real = type(store).backup

    def failing(self, v, dest):
        if v.startswith("w6b"):
            raise OSError("cannot back up")
        return real(self, v, dest)
    monkeypatch.setattr(type(store), "backup", failing)
    _, b = w6_recovery(ctx, "B", tmp_path)
    assert b["status"] == "incident"  # the original was never dropped


def test_shouldRefuseAnExistingRestoreNewDestinationForFiles(ctx, tmp_path):
    store = ctx.stores["B"]
    store.prepare("v", ctx.reference.rows)
    dump = tmp_path / "d"
    store.backup("v", dump)
    other, _ = store.restore_new(dump, "v")
    with pytest.raises(FileExistsError):
        store.restore_new(dump, "v")
    assert other.verify("v")
    other.dispose()


def test_shouldRefuseAnExistingRestoreNewDatabaseAndLeaveItUntouched(tmp_path):
    import os
    dsn = os.environ.get("NEXUS_BENCH_PG_DSN")
    if not dsn:
        pytest.skip("NEXUS_BENCH_PG_DSN not set")
    import psycopg
    from harness.store_pg import PostgresStore
    ns = f"x{os.getpid()}"
    s = PostgresStore(dsn, os.environ.get("NEXUS_BENCH_PG_CONTAINER", "nexus-spike-pg"), ns)
    db = f"{ns}_restored_new"
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f"CREATE DATABASE {db}")
    try:
        s.prepare("v", make_ref().rows)
        dump = tmp_path / "d"
        s.backup("v", dump)
        with pytest.raises(FileExistsError):
            s.restore_new(dump, "v")
        with psycopg.connect(dsn, autocommit=True) as c:
            assert c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db,)).fetchone()
        assert s.remove_leftover_database() == db
    finally:
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")
            c.execute(f"DROP SCHEMA IF EXISTS {ns}_v CASCADE")


# ---- second review of 2026-10-22 ----

def test_shouldFailW1WhenVerifyDoesNotReturnTheDigestPrepareReturned(ctx, monkeypatch):
    from harness.contract import VerifyResult
    store = ctx.stores["B"]
    monkeypatch.setattr(type(store), "verify", lambda self, v: VerifyResult(v, "different"))
    r = w1_prepare(ctx, "B", 0, "first_run_after_start", "v")
    assert r["status"] == "check_failed" and r["checks"]["verify_returns_prepared_digest"] is False


def test_shouldNeverWriteIntoOrRemoveAPreExistingRestoreNewRoot(ctx, tmp_path):
    store = ctx.stores["B"]
    store.prepare("v", ctx.reference.rows)
    dump = tmp_path / "d"
    store.backup("v", dump)
    precious = store.root.parent / (store.root.name + "_restored_new")
    precious.mkdir()
    (precious / "other.txt").write_text("not ours")
    with pytest.raises(FileExistsError):
        store.restore_new(dump, "v")
    store.dispose()  # the primary store never owns that directory
    assert (precious / "other.txt").read_text() == "not ours"


def test_shouldEndW6aAsAnIncidentWhenItsDestinationAlreadyExistsAndLeaveItAlone(ctx, tmp_path):
    store = ctx.stores["B"]
    precious = store.root.parent / (store.root.name + "_restored_new")
    precious.mkdir()
    (precious / "other.txt").write_text("not ours")
    a, _ = w6_recovery(ctx, "B", tmp_path)
    assert a["status"] == "incident" and "exists" in a["incident"]
    assert (precious / "other.txt").exists()


COUNTS = {"publications": 3, "rejected": 1, "subclasses": 6, "without_ipc": 1, "distinct_doc_id": 2}


def _with_load_checks(ctx, expected):
    ctx.reference.load_checks_expected = expected


def test_shouldCheckThePreregisteredLoadCountsOnBothRestoredCopies(ctx, tmp_path):
    _with_load_checks(ctx, COUNTS)
    a, b = w6_recovery(ctx, "B", tmp_path)
    assert (a["status"], b["status"]) == ("ok", "ok")
    assert all(f"load_{k}" in a["checks"] and f"load_{k}" in b["checks"] for k in COUNTS)


def test_shouldFailW6WhenARestoredCopyHasTheWrongCounts(ctx, tmp_path):
    _with_load_checks(ctx, {**COUNTS, "publications": 4})
    a, b = w6_recovery(ctx, "B", tmp_path)
    assert a["status"] == "check_failed" and b["status"] == "check_failed"


def test_shouldFailC1AndC4WhenARestoredCopyContentDiffers():
    rs = full("A", [1] * 5) + full("B", [1] * 5)
    for r in rs:
        if r["workload"] == "W6a" and r["alternative"] == "A":
            r["checks"]["pairs_equal"] = False
            r["status"] = "check_failed"
    code, t = evaluate(rs)
    assert code == EXIT_FAIL and not t["A"]["C1"] and not t["A"]["C4"] and t["B"]["C1"]


def test_shouldFailC1WhenNoRestoreContentWasChecked():
    rs = [r for r in full("A", [1] * 5) + full("B", [1] * 5) if not (r["workload"] in ("W6a", "W6b") and r["alternative"] == "A")]
    code, t = evaluate(rs)
    assert not t["A"]["C1"] and not t["A"]["C4"]


def test_shouldCloseEveryDuckDbConnectionItOpens(ctx, monkeypatch):
    import duckdb
    import harness.store_files as sf
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
    store = ctx.stores["B"]
    store.prepare("v", ctx.reference.rows)
    store.load_checks("v"); store.read_records("v"); store.logical_digest("v")
    assert len(opened) == 3 and len(closed) == 3


def test_shouldReportASetupFailureAsAnIncidentWithExitCode3AndWriteItsTraceback(tmp_path, monkeypatch):
    import json
    import run_benchmark
    monkeypatch.setattr(run_benchmark, "require_authorisation", lambda: {"authorised_by": "t"})
    monkeypatch.setattr(run_benchmark, "build_real_context", lambda a, b: (_ for _ in ()).throw(RuntimeError("boom")))
    code = run_benchmark.main(["--work-dir", str(tmp_path / "w"), "--pg-dsn", "x", "--container", "x"])
    assert code == 3 and "boom" in json.loads((tmp_path / "w" / "incident.json").read_text())["traceback"]
