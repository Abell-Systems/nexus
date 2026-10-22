"""Alternative B: one Parquet file per table + manifest.json with sha256 per file, queried with DuckDB (pre-registration §1)."""
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from harness.compare import canonical_json
from harness.contract import AlterKind, IntegrityError, VerifyResult, analysis_record
from harness.tables import BY_NAME, TABLES, Table, canonical_rows_digest, check_constraints

_ARROW = {"int": pa.int64(), "bigint": pa.int64(), "text": pa.string(), "date": pa.date32()}
COMPRESSION, ROW_GROUP = "zstd", 1_000_000


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _schema(t: Table) -> pa.Schema:
    return pa.schema([(c, _ARROW[ty]) for c, ty in t.columns])


def _write(path: Path, t: Table, rows: list[tuple]) -> None:
    index = [c for c, _ in t.columns]
    order = sorted(range(len(rows)), key=lambda i: tuple(rows[i][index.index(k)] for k in t.key))
    cols = {c: [rows[i][j] for i in order] for j, (c, _) in enumerate(t.columns)}
    pq.write_table(pa.table(cols, schema=_schema(t)), path, compression=COMPRESSION, row_group_size=ROW_GROUP)


def _manifest_digest(files: dict) -> str:
    return hashlib.sha256(canonical_json(files).encode()).hexdigest()


class FilesStore:
    name = "B_parquet_duckdb"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, version: str) -> Path:
        return self.root / version

    def prepare(self, version: str, rows: dict[str, list[tuple]]) -> VerifyResult:
        check_constraints(rows)  # the constraints A enforces in the database; counted in B's preparation
        target = self._dir(version)
        if target.exists():
            raise FileExistsError(f"{version} already exists: versions are immutable")
        staging = target.with_name(target.name + ".staging")
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        files = {}
        for t in TABLES:
            path = staging / f"{t.name}.parquet"
            _write(path, t, rows[t.name])
            files[t.name] = {"sha256": _sha256(path), "bytes": path.stat().st_size, "rows": len(rows[t.name])}
        digest = _manifest_digest(files)
        (staging / "manifest.json").write_text(json.dumps({"version": version, "files": files, "manifest_sha256": digest}, indent=1))
        staging.rename(target)  # published only when complete
        return VerifyResult(version, digest)

    def verify(self, version: str) -> VerifyResult:
        d = self._dir(version)
        try:
            manifest = json.loads((d / "manifest.json").read_text())
        except (OSError, ValueError) as exc:
            raise IntegrityError(f"{version}: manifest unreadable: {exc}") from exc
        if _manifest_digest(manifest["files"]) != manifest["manifest_sha256"]:
            raise IntegrityError(f"{version}: manifest does not match its own digest")
        for name in BY_NAME:
            entry, path = manifest["files"].get(name), d / f"{name}.parquet"
            if entry is None or not path.is_file():
                raise IntegrityError(f"{version}: {name}.parquet is missing")
            if _sha256(path) != entry["sha256"]:
                raise IntegrityError(f"{version}: {name}.parquet does not match the manifest")
        return VerifyResult(version, manifest["manifest_sha256"])

    def _connect(self, version: str) -> duckdb.DuckDBPyConnection:
        con = duckdb.connect()
        for name in BY_NAME:
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{self._dir(version) / (name + '.parquet')}')")
        if con.execute("SELECT 'a' < 'B'").fetchone()[0]:
            raise RuntimeError("DuckDB collation is not binary: the ordering contract of ADR 0037 §3.8 would not hold")
        return con

    def read_records(self, version: str) -> list:
        con = self._connect(version)
        cur = con.execute("""SELECT p.country||p.doc_number||p.kind, p.kind, p.publication_date, p.application_date,
            (SELECT min(priority_date) FROM priority_date d WHERE d.record_id=p.record_id),
            coalesce((SELECT list(DISTINCT subclass_symbol ORDER BY subclass_symbol) FROM ipc_entry e WHERE e.record_id=p.record_id), [])
            FROM publication p ORDER BY p.record_id""")
        return [analysis_record(*row) for row in cur.fetchall()]

    def logical_digest(self, version: str) -> str:
        con = self._connect(version)
        return canonical_rows_digest({t.name: [tuple(r) for r in con.execute(f"SELECT {', '.join(c for c, _ in t.columns)} FROM {t.name}").fetchall()]
                                      for t in TABLES})

    def load_checks(self, version: str) -> dict[str, int]:
        con, q = self._connect(version), lambda s: self._connect(version).execute(s).fetchone()[0]
        return {
            "publications": q("SELECT count(*) FROM publication"), "rejected": q("SELECT count(*) FROM rejected_record"),
            "subclasses": q("SELECT count(*) FROM ipc_subclass"),
            "without_ipc": q("SELECT count(*) FROM publication p WHERE NOT EXISTS (SELECT 1 FROM ipc_entry e WHERE e.record_id=p.record_id)"),
            "distinct_doc_id": q("SELECT count(DISTINCT country||doc_number||kind) FROM publication"),
        }

    def alter(self, version: str, kind: AlterKind) -> None:
        d = self._dir(version)
        ipc = d / "ipc_entry.parquet"
        if kind == "flip_byte":
            data = bytearray((d / "publication.parquet").read_bytes())
            data[len(data) // 2] ^= 0x01
            (d / "publication.parquet").write_bytes(bytes(data))
        elif kind == "delete_object":
            (d / "party.parquet").unlink()
        elif kind in ("change_subclass", "swap_rows"):
            t = pq.read_table(ipc).to_pylist()
            if kind == "change_subclass":
                other = next(r["subclass_symbol"] for r in t if r["subclass_symbol"] != t[0]["subclass_symbol"])
                t[0]["subclass_symbol"] = other
            else:
                t[0], t[1] = t[1], t[0]
            pq.write_table(pa.Table.from_pylist(t, schema=_schema(BY_NAME["ipc_entry"])), ipc, compression=COMPRESSION, row_group_size=ROW_GROUP)
        else:
            raise ValueError(kind)

    def backup(self, version: str, destination: Path) -> None:
        shutil.copytree(self._dir(version), destination)

    def restore(self, source: Path, version: str) -> None:
        if self._dir(version).exists():
            raise FileExistsError(f"{version} exists: restore never overwrites")
        shutil.copytree(source, self._dir(version))

    def drop(self, version: str) -> None:
        shutil.rmtree(self._dir(version))

    def size_bytes(self, version: str) -> int:
        return sum(p.stat().st_size for p in self._dir(version).iterdir())

    def configuration(self) -> dict:
        return {"engine": f"duckdb {duckdb.__version__}", "pyarrow": pa.__version__, "compression": COMPRESSION,
                "row_group_size": ROW_GROUP, "sorted_by": "primary key", "collation": "binary (verified at connect)",
                "constraints": "checked at prepare by check_constraints (primary key, unique, allowed values, references; same set as A), not enforced afterwards"}
