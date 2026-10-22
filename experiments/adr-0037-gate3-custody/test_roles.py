"""Tests of experiments/adr-0037-gate3-custody/roles.sql on a throwaway database and throwaway roles of the spike container.

Needs NEXUS_BENCH_PG_DSN (the container's superuser). Creates database g3_<pid> and roles g3<pid>_*, and removes them afterwards. roles.sql also revokes CONNECT on the cluster's
postgres and template1 databases; the fixture grants it back to PUBLIC on teardown so the container ends as it started.
Passwords are generated per run and never printed. Not run by CI.
"""
import os
import secrets
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

ADMIN = os.environ.get("NEXUS_BENCH_PG_DSN")
pytestmark = pytest.mark.skipif(not ADMIN, reason="NEXUS_BENCH_PG_DSN not set")
SQL = (Path(__file__).parent / "roles.sql").read_text()


def split(sql: str):
    bootstrap, finalize = sql.split("-- Finalize one version", 1)
    return bootstrap, "-- Finalize one version" + finalize


@pytest.fixture(scope="module")
def env():
    pid = os.getpid()
    db, loader, app, frozen = f"g3_{pid}", f"g3{pid}_loader", f"g3{pid}_app", f"g3{pid}_frozen"
    pw = {loader: secrets.token_urlsafe(24), app: secrets.token_urlsafe(24)}
    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f"CREATE DATABASE {db}")
    admin_db = make_conninfo(ADMIN, dbname=db)
    bootstrap, finalize = split(SQL)
    names = dict(db=db, loader=loader, app=app, frozen=frozen)
    with psycopg.connect(admin_db, autocommit=True) as c:
        c.execute(bootstrap.format(**names))
        for role, pwd in pw.items():
            c.execute(psycopg.sql.SQL("ALTER ROLE {} PASSWORD {}").format(psycopg.sql.Identifier(role), psycopg.sql.Literal(pwd)))
    yield dict(names, admin=admin_db, finalize=finalize,
               loader_dsn=make_conninfo(ADMIN, dbname=db, user=loader, password=pw[loader]),
               app_dsn=make_conninfo(ADMIN, dbname=db, user=app, password=pw[app]))
    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")
        for r in (loader, app, frozen):
            c.execute(f"DROP ROLE IF EXISTS {r}")
        # roles.sql revokes CONNECT on the cluster's default databases; put the container back as it was
        c.execute("GRANT CONNECT ON DATABASE postgres TO PUBLIC")
        c.execute("GRANT CONNECT ON DATABASE template1 TO PUBLIC")


def load_version(env, schema):
    with psycopg.connect(env["loader_dsn"], autocommit=True) as c:
        c.execute(f"CREATE SCHEMA {schema}")
        c.execute(f"CREATE TABLE {schema}.asset(id int PRIMARY KEY, name text)")
        c.execute(f"INSERT INTO {schema}.asset VALUES (1, 'a'), (2, 'b')")


def finalize(env, schema):
    with psycopg.connect(env["admin"], autocommit=True) as c:
        c.execute(env["finalize"].format(schema=schema, **{k: env[k] for k in ("loader", "app", "frozen")}))


def denied(dsn, sql):
    with psycopg.connect(dsn, autocommit=True) as c:
        try:
            c.execute(sql)
        except psycopg.errors.InsufficientPrivilege:
            return True
        except psycopg.errors.Error as exc:
            raise AssertionError(f"failed for another reason than privilege: {exc}") from exc
    return False


def test_shouldLetTheLoaderCreateAndLoadAVersionBeforeItIsFinalized(env):
    load_version(env, "v_load")
    with psycopg.connect(env["loader_dsn"]) as c:
        assert c.execute("SELECT count(*) FROM v_load.asset").fetchone()[0] == 2


def test_shouldKeepAnUnfinalizedVersionInvisibleToTheApp(env):
    load_version(env, "v_hidden")
    assert denied(env["app_dsn"], "SELECT * FROM v_hidden.asset")


def test_shouldLetTheAppReadAFinalizedVersionAndNothingElse(env):
    load_version(env, "v_read")
    finalize(env, "v_read")
    with psycopg.connect(env["app_dsn"]) as c:
        assert c.execute("SELECT count(*) FROM v_read.asset").fetchone()[0] == 2
    for stmt in ("INSERT INTO v_read.asset VALUES (3, 'c')", "UPDATE v_read.asset SET name='x'", "DELETE FROM v_read.asset",
                 "TRUNCATE v_read.asset", "DROP TABLE v_read.asset", "ALTER TABLE v_read.asset ADD COLUMN z int",
                 "CREATE TABLE v_read.other(x int)", "DROP SCHEMA v_read CASCADE", "CREATE SCHEMA app_made", "CREATE TABLE public.t(x int)"):
        assert denied(env["app_dsn"], stmt), stmt


def test_shouldLetTheAppUseTemporaryTablesWithoutTouchingFinalizedData(env):
    load_version(env, "v_temp")
    finalize(env, "v_temp")
    with psycopg.connect(env["app_dsn"], autocommit=True) as c:
        c.execute("CREATE TEMP TABLE eligible(asset_id int)")   # alternative A's session-local table
        c.execute("INSERT INTO eligible VALUES (1)")
        assert c.execute("SELECT a.name FROM v_temp.asset a JOIN eligible e ON e.asset_id=a.id").fetchone() == ("a",)


def test_shouldMakeAFinalizedVersionImmutableEvenForItsLoader(env):
    load_version(env, "v_frozen")
    finalize(env, "v_frozen")
    for stmt in ("INSERT INTO v_frozen.asset VALUES (9, 'z')", "UPDATE v_frozen.asset SET name='x'", "DELETE FROM v_frozen.asset",
                 "TRUNCATE v_frozen.asset", "DROP TABLE v_frozen.asset", "ALTER TABLE v_frozen.asset ADD COLUMN z int",
                 "DROP SCHEMA v_frozen CASCADE", "CREATE TABLE v_frozen.more(x int)", "SELECT * FROM v_frozen.asset",
                 "GRANT ALL ON v_frozen.asset TO PUBLIC", "ALTER TABLE v_frozen.asset OWNER TO CURRENT_USER"):
        assert denied(env["loader_dsn"], stmt), stmt


def test_shouldNotLetTheLoaderPlantADifferentVersionUnderTheNameOfAFinalizedOne(env):
    load_version(env, "v_name")
    finalize(env, "v_name")
    with psycopg.connect(env["loader_dsn"], autocommit=True) as c:
        with pytest.raises(psycopg.errors.DuplicateSchema):
            c.execute("CREATE SCHEMA v_name")


def test_shouldNotLetEitherRoleReachOtherDatabasesOrPublic(env):
    for dsn in (env["loader_dsn"], env["app_dsn"]):
        other = make_conninfo(dsn, dbname="postgres")
        with pytest.raises(psycopg.OperationalError, match="permission denied for database"):
            psycopg.connect(other)
        assert denied(dsn, "CREATE TABLE public.leak(x int)")


def test_shouldNotGiveEitherRoleSuperuserOrRoleCreationRights(env):
    with psycopg.connect(env["admin"]) as c:
        rows = c.execute("SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
                         "FROM pg_roles WHERE rolname IN (%s, %s, %s)", (env["loader"], env["app"], env["frozen"])).fetchall()
    assert len(rows) == 3 and all(not any(r[1:]) for r in rows)
    assert denied(env["loader_dsn"], "CREATE ROLE x")


def test_shouldStorePasswordsAsScramHashesAndMakeTheFrozenOwnerNonLoginable(env):
    with psycopg.connect(env["admin"]) as c:
        hashes = [r[0] for r in c.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s, %s)", (env["loader"], env["app"]))]
        login = c.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname=%s", (env["frozen"],)).fetchone()[0]
    assert all(h.startswith("SCRAM-SHA-256$") for h in hashes) and login is False


def test_shouldBlockTheLoaderOutsideItsLoadWindowWhenItsLoginIsSwitchedOff(env):
    with psycopg.connect(env["admin"], autocommit=True) as c:
        c.execute(f"ALTER ROLE {env['loader']} NOLOGIN")
    try:
        with pytest.raises(psycopg.OperationalError, match="not permitted to log in"):
            psycopg.connect(env["loader_dsn"])
    finally:
        with psycopg.connect(env["admin"], autocommit=True) as c:
            c.execute(f"ALTER ROLE {env['loader']} LOGIN")
    with psycopg.connect(env["loader_dsn"]) as c:                       # and it works again when the operator opens the window
        assert c.execute("SELECT 1").fetchone() == (1,)
