"""Alternative A: PostgreSQL + pgvector, one schema per version, per-table canonical digest in a manifest table."""
import hashlib
import subprocess
from pathlib import Path

import psycopg

from harness.contract import AlterKind, IntegrityError, VerifyResult, analysis_record
from harness.tables import BY_NAME, TABLES, ConstraintError, ReferentialError, canonical_rows_digest

_PG = {"int": "integer", "bigint": "bigint", "text": "text", "date": "date"}


class PostgresStore:
    name = "A_postgres"

    def __init__(self, dsn: str, container: str, namespace: str) -> None:
        """`namespace` prefixes every schema so A never shares a schema with anything else."""
        self.dsn, self.container, self.namespace = dsn, container, namespace

    def _schema(self, version: str) -> str:
        return f"{self.namespace}_{version}"

    def _conn(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, autocommit=True)

    def _digest(self, conn: psycopg.Connection, schema: str) -> str:
        parts = []
        for t in TABLES:
            key = ", ".join(t.key)
            (d,) = conn.execute(
                f"SELECT encode(sha256(convert_to(coalesce(string_agg(to_jsonb(x)::text, E'\\n' ORDER BY {key}), ''), 'UTF8')), 'hex') "
                f"FROM {schema}.{t.name} x").fetchone()
            parts.append(f"{t.name}:{d}")
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()

    def prepare(self, version: str, rows: dict[str, list[tuple]]) -> VerifyResult:
        schema = self._schema(version)
        with self._conn() as conn:
            if conn.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name=%s", (schema,)).fetchone():
                raise FileExistsError(f"{schema} already exists: versions are immutable")
            try:
                with conn.transaction():  # published only when complete
                    digest = self._build(conn, schema, version, rows)
            except psycopg.errors.ForeignKeyViolation as exc:
                raise ReferentialError(str(exc)) from exc
            except (psycopg.errors.UniqueViolation, psycopg.errors.CheckViolation) as exc:
                raise ConstraintError(str(exc)) from exc
            conn.execute("ANALYZE")
        return VerifyResult(version, digest)

    def _build(self, conn: psycopg.Connection, schema: str, version: str, rows: dict[str, list[tuple]]) -> str:
        conn.execute(f"CREATE SCHEMA {schema}")
        for t in TABLES:
            cols = ", ".join(f"{c} {_PG[ty]}" for c, ty in t.columns)
            fks = "".join(f", FOREIGN KEY ({c}) REFERENCES {schema}.{ref}" for c, ref in t.references)
            uniq = "".join(f", UNIQUE ({', '.join(u)})" for u in t.unique)
            chk = "".join(f", CHECK ({c} IN ({', '.join(repr(v) for v in vals)}))" for c, vals in t.allowed)
            conn.execute(f"CREATE TABLE {schema}.{t.name} ({cols}, PRIMARY KEY ({', '.join(t.key)}){uniq}{chk}{fks})")
        for t in TABLES:  # TABLES is ordered so referenced tables come first
            with conn.cursor() as cur, cur.copy(f"COPY {schema}.{t.name} FROM STDIN") as cp:
                for r in rows[t.name]:
                    cp.write_row(r)
        conn.execute(f"CREATE INDEX ON {schema}.ipc_entry(subclass_symbol, record_id)")
        conn.execute(f"CREATE INDEX ON {schema}.publication(publication_date)")
        digest = self._digest(conn, schema)
        conn.execute(f"CREATE TABLE {schema}.manifest(version text PRIMARY KEY, content_sha256 text NOT NULL)")
        conn.execute(f"INSERT INTO {schema}.manifest VALUES (%s, %s)", (version, digest))
        return digest

    def verify(self, version: str) -> VerifyResult:
        schema = self._schema(version)
        with self._conn() as conn:
            try:
                (stored,) = conn.execute(f"SELECT content_sha256 FROM {schema}.manifest WHERE version=%s", (version,)).fetchone()
                actual = self._digest(conn, schema)
            except (psycopg.Error, TypeError) as exc:
                raise IntegrityError(f"{version}: cannot verify: {exc}") from exc
        if actual != stored:
            raise IntegrityError(f"{version}: content digest does not match the manifest")
        return VerifyResult(version, stored)

    def read_records(self, version: str) -> list:
        schema = self._schema(version)
        with self._conn() as conn:
            cur = conn.execute(f"""SELECT p.country||p.doc_number||p.kind, p.kind, p.publication_date, p.application_date,
                (SELECT min(priority_date) FROM {schema}.priority_date d WHERE d.record_id=p.record_id),
                coalesce((SELECT array_agg(s ORDER BY s COLLATE "C") FROM (SELECT DISTINCT subclass_symbol s FROM {schema}.ipc_entry e
                          WHERE e.record_id=p.record_id) u), '{{}}')
                FROM {schema}.publication p ORDER BY p.record_id""")
            return [analysis_record(*row) for row in cur.fetchall()]

    def logical_digest(self, version: str) -> str:
        schema = self._schema(version)
        with self._conn() as conn:
            return canonical_rows_digest({t.name: [tuple(r) for r in conn.execute(
                f"SELECT {', '.join(c for c, _ in t.columns)} FROM {schema}.{t.name}").fetchall()] for t in TABLES})

    def load_checks(self, version: str) -> dict[str, int]:
        schema = self._schema(version)
        with self._conn() as conn:
            q = lambda s: conn.execute(s).fetchone()[0]  # noqa: E731
            return {
                "publications": q(f"SELECT count(*) FROM {schema}.publication"), "rejected": q(f"SELECT count(*) FROM {schema}.rejected_record"),
                "subclasses": q(f"SELECT count(*) FROM {schema}.ipc_subclass"),
                "without_ipc": q(f"SELECT count(*) FROM {schema}.publication p WHERE NOT EXISTS (SELECT 1 FROM {schema}.ipc_entry e WHERE e.record_id=p.record_id)"),
                "distinct_doc_id": q(f"SELECT count(DISTINCT country||doc_number||kind) FROM {schema}.publication"),
            }

    def alter(self, version: str, kind: AlterKind) -> None:
        s = self._schema(version)
        with self._conn() as conn:
            if kind == "change_subclass":
                conn.execute(f"""UPDATE {s}.ipc_entry SET subclass_symbol=(SELECT symbol FROM {s}.ipc_subclass WHERE symbol <>
                    (SELECT subclass_symbol FROM {s}.ipc_entry ORDER BY record_id, ordinal LIMIT 1) LIMIT 1)
                    WHERE (record_id, ordinal) = (SELECT record_id, ordinal FROM {s}.ipc_entry ORDER BY record_id, ordinal LIMIT 1)""")
            elif kind == "flip_byte":  # the SQL-level equivalent of corruption: one value of one row changes
                conn.execute(f"UPDATE {s}.publication SET title = title || 'x' WHERE record_id = (SELECT min(record_id) FROM {s}.publication)")
            elif kind == "delete_object":
                conn.execute(f"DROP TABLE {s}.party")
            elif kind == "swap_rows":  # physical order only: delete and reinsert the first two rows, content unchanged
                conn.execute(f"""WITH moved AS (DELETE FROM {s}.ipc_entry WHERE (record_id, ordinal) IN
                    (SELECT record_id, ordinal FROM {s}.ipc_entry ORDER BY record_id, ordinal LIMIT 2) RETURNING *)
                    INSERT INTO {s}.ipc_entry SELECT * FROM moved ORDER BY record_id DESC, ordinal DESC""")
            else:
                raise ValueError(kind)

    def backup(self, version: str, destination: Path) -> None:
        with destination.open("wb") as out:
            subprocess.run(["docker", "exec", self.container, "pg_dump", "-U", "postgres", "-Fc", "-n", self._schema(version), "postgres"],
                           stdout=out, check=True)

    def restore(self, source: Path, version: str) -> None:
        with self._conn() as conn:
            if conn.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name=%s", (self._schema(version),)).fetchone():
                raise FileExistsError(f"{self._schema(version)} exists: restore never overwrites")
        with source.open("rb") as inp:
            subprocess.run(["docker", "exec", "-i", self.container, "pg_restore", "-U", "postgres", "-d", "postgres", "--exit-on-error"],
                           stdin=inp, check=True)

    def drop(self, version: str) -> None:
        with self._conn() as conn:
            conn.execute(f"DROP SCHEMA {self._schema(version)} CASCADE")

    def size_bytes(self, version: str) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT coalesce(sum(pg_total_relation_size(c.oid)),0) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                                "WHERE n.nspname=%s AND c.relkind='r'", (self._schema(version),)).fetchone()[0]

    def configuration(self) -> dict:
        with self._conn() as conn:
            settings = {k: conn.execute("SELECT current_setting(%s)", (k,)).fetchone()[0]
                        for k in ("server_version", "shared_buffers", "work_mem", "max_parallel_workers_per_gather", "effective_cache_size")}
            collate = conn.execute("SELECT datcollate FROM pg_database WHERE datname=current_database()").fetchone()[0]
        return {"engine": "postgresql", **settings, "database_collation": collate, "ordering": 'ORDER BY ... COLLATE "C" in the contractual query',
                "vector_index": "none", "constraints": "enforced by the database (primary key, unique, check, foreign keys)"}
